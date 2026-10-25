"""Документированные потоки из Mini_CMMS_API_Examples.yaml исполняются на живой стеке.

Каждый шаг потока — фактический HTTP-запрос: статус сверяется с ожиданием,
тело проверяется по схеме контракта, стабильные поля — по ожидаемому телу.
Символические идентификаторы потока отображаются на созданные сервером.
"""

import uuid
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_redis
from app.core.security import hash_password
from app.db.models.user import User, UserRole, UserStatus
from app.db.session import get_session
from tests.contract.oracle import ContractOracle

EXAMPLES_PATH = Path(__file__).resolve().parents[3] / "docs" / "Mini_CMMS_API_Examples.yaml"
ROLE_ACTORS = {
    UserRole.ADMIN: "admin",
    UserRole.ENGINEER: "engineer",
    UserRole.OPERATOR: "operator",
    UserRole.TECHNICIAN: "technician",
}


@pytest.fixture(scope="session")
def documented_flows() -> list[dict[str, Any]]:
    flows = yaml.safe_load(EXAMPLES_PATH.read_text(encoding="utf-8")).get("flows") or []
    assert flows, "Документированные потоки не найдены"
    return flows


@pytest.fixture
async def pg_client(
    session_factory: async_sessionmaker[AsyncSession],
    real_redis,
) -> AsyncClient:
    """HTTP-клиент приложения, работающий на живой PostgreSQL и Redis."""
    from app.__main__ import app

    async def _session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_redis] = lambda: real_redis
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


class FlowRunner:
    def __init__(self, client: AsyncClient, oracle: ContractOracle) -> None:
        self.client = client
        self.oracle = oracle
        self.sessions: dict[str, str] = {}
        self.id_map: dict[str, str] = {}

    def _substitute(self, value: Any) -> Any:
        if isinstance(value, str):
            for session_key, token in self.sessions.items():
                value = value.replace(f"${{session.{session_key}}}", token)
            for symbolic, actual in self.id_map.items():
                value = value.replace(symbolic, actual)
            return value
        if isinstance(value, dict):
            return {key: self._substitute(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._substitute(item) for item in value]
        return value

    def _path(self, step: dict[str, Any]) -> str:
        path = step["path_template"]
        for name, value in (step.get("path_params") or {}).items():
            path = path.replace(f"{{{name}}}", str(self._substitute(str(value))))
        return f"/api/v1{path}"

    async def run(self, flow: dict[str, Any]) -> list[str]:
        executed: list[str] = []
        for index, step in enumerate(flow.get("steps") or []):
            context = f"flow '{flow['id']}' step {index} ({step.get('operationId')})"
            path = self._path(step)
            headers = {k: self._substitute(v) for k, v in (step.get("headers") or {}).items()}
            body = self._substitute(step.get("body"))
            method = step["method"].upper()

            if method == "GET":
                response = await self.client.get(path, headers=headers)
            elif method == "POST":
                response = await self.client.post(path, headers=headers, json=body)
            elif method == "PATCH":
                response = await self.client.patch(path, headers=headers, json=body)
            else:
                raise AssertionError(f"{context}: неподдерживаемый метод {method}")

            payload = self.oracle.assert_response(response, method, path, expected_status=step.get("expected_status"))

            raw_expected = step.get("expected_body") or {}
            # Символические идентификаторы потока отображаются на созданные сервером.
            self._map_ids(raw_expected, payload, self.id_map)

            expected_body = self._substitute(raw_expected)
            self.oracle.assert_fields(payload, expected_body, context=context)

            if step.get("operationId") == "login" and response.status_code == 200:
                actor = ROLE_ACTORS.get(self._actor_role(flow, body.get("login")))
                if actor:
                    self.sessions[actor] = payload.get("access_token", "")

            executed.append(f"{step.get('operationId')}:{response.status_code}")
        return executed

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            uuid.UUID(value)
        except (ValueError, AttributeError):
            return False
        return True

    @classmethod
    def _map_ids(cls, expected: Any, actual: Any, mapping: dict[str, str]) -> None:
        """Сопоставляет идентификаторы потока с фактическими (по позиции)."""
        if isinstance(expected, dict) and isinstance(actual, dict):
            for key, value in expected.items():
                if key in actual:
                    cls._map_ids(value, actual[key], mapping)
            return
        if isinstance(expected, list) and isinstance(actual, list):
            for exp_item, act_item in zip(expected, actual):
                cls._map_ids(exp_item, act_item, mapping)
            return
        if isinstance(expected, str) and isinstance(actual, str):
            if cls._is_uuid(expected) and cls._is_uuid(actual) and expected != actual:
                mapping[expected] = actual

    @staticmethod
    def _actor_role(flow: dict[str, Any], login: str | None) -> UserRole | None:
        for user in (flow.get("initial_state") or {}).get("users") or []:
            if user.get("login") == login:
                return UserRole(user["role"])
        return None


async def _clean_db(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Очистка состояния перед потоком: потоки используют собственные идентификаторы."""
    from sqlalchemy import text

    tables = [
        "notifications",
        "work_order_events",
        "work_history",
        "work_orders",
        "faults",
        "maintenance_schedules",
        "maintenance_plans",
        "equipment",
        "user_sessions",
        "users",
    ]
    async with session_factory() as session:
        await session.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE"))
        await session.commit()


async def _login_actors(flow: dict[str, Any], client: AsyncClient) -> dict[str, str]:
    """Получает реальные сессии всех пользователей потока."""
    sessions: dict[str, str] = {}
    for user in (flow.get("initial_state") or {}).get("users") or []:
        actor = ROLE_ACTORS[UserRole(user["role"])]
        response = await client.post(
            "/api/v1/auth/login",
            json={"login": user["login"], "password": "SyntheticPass-2026!"},
        )
        assert response.status_code == 200, f"Не удалось войти за {user['login']}: {response.status_code}"
        sessions[actor] = response.json()["access_token"]
    return sessions


async def _seed_users(flow: dict[str, Any], session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Создаёт начальное состояние потока: пользователей, оборудование и неисправности."""
    from app.db.models.equipment import Equipment, EquipmentStatus
    from app.db.models.fault import Fault, FaultSeverity, FaultStatus

    state = flow.get("initial_state") or {}
    users = state.get("users") or []
    equipment = state.get("equipment") or []
    faults = state.get("faults") or []
    if not (users or equipment or faults):
        return
    async with session_factory() as session:
        for item in equipment:
            session.add(
                Equipment(
                    id=uuid.UUID(item["id"]),
                    name=item["name"],
                    inventory_number=item["inventory_number"],
                    category=item["category"],
                    location=item["location"],
                    commissioned_on=date.fromisoformat(item["commissioned_on"]),
                    status=EquipmentStatus(item["status"]),
                    version=item.get("version", 1),
                )
            )
        for item in faults:
            session.add(
                Fault(
                    id=uuid.UUID(item["id"]),
                    equipment_id=uuid.UUID(item["equipment_id"]),
                    description=item["description"],
                    detected_on=date.fromisoformat(item["detected_on"]),
                    severity=FaultSeverity(item["severity"]),
                    status=FaultStatus(item["status"]),
                    author_id=uuid.UUID(item["author_id"]),
                    version=item.get("version", 1),
                )
            )
        for user in users:
            session.add(
                User(
                    id=uuid.UUID(user["id"]),
                    login=user["login"],
                    full_name=user["login"],
                    password_hash=hash_password("SyntheticPass-2026!"),
                    role=UserRole(user["role"]),
                    status=UserStatus(user.get("status", "ACTIVE")),
                    version=user.get("version", 1),
                )
            )
        await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_documented_flows_run_against_contract(
    pg_client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    documented_flows: list[dict[str, Any]],
    contract_oracle: ContractOracle,
):
    """Все документированные потоки исполняются, а их ответы соответствуют контракту."""
    executed_flows: dict[str, list[str]] = {}
    for flow in documented_flows:
        await _clean_db(session_factory)
        await _seed_users(flow, session_factory)
        runner = FlowRunner(pg_client, contract_oracle)
        runner.sessions.update(await _login_actors(flow, pg_client))
        executed_flows[flow["id"]] = await runner.run(flow)

    assert set(executed_flows) == {"repair", "planned", "cancel_and_recreate", "block_and_revoke"}
    for flow_id, steps in executed_flows.items():
        assert steps, f"Поток {flow_id} не выполнил ни одного шага"
