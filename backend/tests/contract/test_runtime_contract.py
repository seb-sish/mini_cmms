"""Фактические HTTP-ответы сверяются с нормативным контрактом."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from tests.contract.oracle import ContractOracle, ContractViolation


@pytest.fixture(scope="session")
def contract_oracle(openapi_spec, schema_validator) -> ContractOracle:
    return ContractOracle(openapi_spec, schema_validator)


async def _engineer(db_session: AsyncSession, login: str = "oracle_engineer") -> tuple[User, str]:
    user = User(
        login=login,
        full_name="Oracle Engineer",
        password_hash=hash_password("Password123!"),
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    raw_token, t_hash = create_opaque_token()
    db_session.add(
        UserSession(
            user_id=user.id,
            token_hash=t_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=12),
        )
    )
    await db_session.commit()
    return user, raw_token


@pytest.mark.asyncio
async def test_actual_responses_match_contract(
    async_client: AsyncClient, db_session: AsyncSession, contract_oracle: ContractOracle
):
    """Создание, чтение и изменение оборудования сверяются с контрактом по факту."""
    _, token = await _engineer(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.post(
        "/api/v1/equipment",
        headers=headers,
        json={
            "name": "Oracle Machine",
            "inventory_number": "EQ-ORACLE-1",
            "category": "Machining",
            "location": "Shop",
            "commissioned_on": "2026-01-01",
            "status": "OPERATIONAL",
        },
    )
    payload = contract_oracle.assert_response(res, "POST", "/api/v1/equipment", expected_status=201)
    equipment_id = payload["id"]

    res = await async_client.get(f"/api/v1/equipment/{equipment_id}", headers=headers)
    contract_oracle.assert_response(res, "GET", f"/api/v1/equipment/{equipment_id}", expected_status=200)

    res = await async_client.get("/api/v1/equipment", headers=headers)
    contract_oracle.assert_response(res, "GET", "/api/v1/equipment", expected_status=200)

    res = await async_client.patch(
        f"/api/v1/equipment/{equipment_id}",
        headers={**headers, "If-Match": f'"{equipment_id}:{payload["version"]}"'},
        json={"name": "Oracle Machine Updated"},
    )
    updated = contract_oracle.assert_response(res, "PATCH", f"/api/v1/equipment/{equipment_id}", expected_status=200)
    assert updated["name"] == "Oracle Machine Updated"
    assert res.headers.get("ETag")


@pytest.mark.asyncio
async def test_error_responses_match_contract(
    async_client: AsyncClient, db_session: AsyncSession, contract_oracle: ContractOracle
):
    """Ошибочные ответы также сверяются с контрактом: статус и тело ProblemDetail."""
    _, token = await _engineer(db_session, "oracle_errors_engineer")
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.get(f"/api/v1/equipment/{uuid.uuid4()}", headers=headers)
    payload = contract_oracle.assert_response(res, "GET", "/api/v1/equipment/{equipment_id}", expected_status=404)
    assert payload["code"] == "NOT_FOUND"
    assert payload["status"] == 404

    res = await async_client.post(
        "/api/v1/equipment",
        headers=headers,
        json={"name": "Broken"},
    )
    contract_oracle.assert_response(res, "POST", "/api/v1/equipment", expected_status=422)


@pytest.mark.asyncio
async def test_undocumented_status_is_reported(
    async_client: AsyncClient, db_session: AsyncSession, contract_oracle: ContractOracle
):
    """Oracle отклоняет статус, не документированный в контракте."""
    _, token = await _engineer(db_session, "oracle_status_engineer")
    headers = {"Authorization": f"Bearer {token}"}

    equipment = Equipment(
        name="Status Machine",
        inventory_number="EQ-ORACLE-2",
        category="Machining",
        location="Shop",
        commissioned_on=datetime(2026, 1, 1).date(),
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    res = await async_client.post(
        f"/api/v1/equipment/{equipment.id}/archive",
        headers=headers,
    )
    contract_oracle.assert_response(res, "POST", "/api/v1/equipment/{equipment_id}/archive", expected_status=200)

    # Повторный архив — документированный конфликт.
    res = await async_client.post(
        f"/api/v1/equipment/{equipment.id}/archive",
        headers=headers,
    )
    contract_oracle.assert_response(res, "POST", "/api/v1/equipment/{equipment_id}/archive", expected_status=409)


def test_oracle_rejects_unknown_operation(contract_oracle: ContractOracle):
    with pytest.raises(ContractViolation):
        contract_oracle.resolve("GET", "/api/v1/unknown-resource")
