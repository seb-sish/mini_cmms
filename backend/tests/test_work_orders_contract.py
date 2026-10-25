from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType


async def create_user(db: AsyncSession, login: str, role: UserRole, full_name: str | None = None) -> tuple[User, str]:
    user = User(
        login=login,
        password_hash=hash_password("SuperSecret123!"),
        full_name=full_name,
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    raw_token, t_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    db.add(session)
    await db.commit()
    return user, raw_token


@pytest.fixture
async def sample_equip(db_session: AsyncSession) -> Equipment:
    eq = Equipment(
        name="Conveyor Motor 01",
        inventory_number="MOT-001",
        category="Motors",
        location="Line A",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2025, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)
    return eq


@pytest.fixture
async def users_setup(db_session: AsyncSession):
    eng, eng_tok = await create_user(db_session, "eng_wo_test", UserRole.ENGINEER, "Engineer Test")
    tech_a, tech_a_tok = await create_user(db_session, "tech_a_wo", UserRole.TECHNICIAN, "Tech A")
    tech_b, tech_b_tok = await create_user(db_session, "tech_b_wo", UserRole.TECHNICIAN, "Tech B")
    op1, op1_tok = await create_user(db_session, "op1_wo", UserRole.OPERATOR, "Operator 1")
    op2, op2_tok = await create_user(db_session, "op2_wo", UserRole.OPERATOR, "Operator 2")
    adm, adm_tok = await create_user(db_session, "adm_wo", UserRole.ADMIN, "Admin Test")
    return {
        "engineer": (eng, eng_tok),
        "tech_a": (tech_a, tech_a_tok),
        "tech_b": (tech_b, tech_b_tok),
        "op1": (op1, op1_tok),
        "op2": (op2, op2_tok),
        "admin": (adm, adm_tok),
    }


@pytest.mark.asyncio
async def test_admin_blocked_from_work_orders_and_history(async_client: AsyncClient, users_setup, sample_equip):
    _, adm_token = users_setup["admin"]
    headers = {"Authorization": f"Bearer {adm_token}"}

    # 1. GET /work-orders
    res = await async_client.get("/api/v1/work-orders", headers=headers)
    assert res.status_code == 403
    assert res.json()["code"] == "ACCESS_DENIED"

    # 2. POST /work-orders
    res = await async_client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "type": "REPAIR",
            "equipment_id": str(sample_equip.id),
            "title": "Admin Order",
            "description": "Admin trying to create order",
            "priority": "NORMAL",
        },
    )
    assert res.status_code == 403
    assert res.json()["code"] == "ACCESS_DENIED"

    # 3. GET /work-history
    res = await async_client.get("/api/v1/work-history", headers=headers)
    assert res.status_code == 403
    assert res.json()["code"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_technician_cross_access_blocked_on_fsm(async_client: AsyncClient, users_setup, sample_equip):
    _, eng_tok = users_setup["engineer"]
    tech_a, tech_a_tok = users_setup["tech_a"]
    _, tech_b_tok = users_setup["tech_b"]

    # Engineer creates and assigns order to Tech A
    eng_h = {"Authorization": f"Bearer {eng_tok}"}
    create_res = await async_client.post(
        "/api/v1/work-orders",
        headers=eng_h,
        json={
            "type": "REPAIR",
            "equipment_id": str(sample_equip.id),
            "title": "Motor Vibration Check",
            "description": "Investigate unusual noise from motor",
            "priority": "HIGH",
        },
    )
    assert create_res.status_code == 201
    wo_id = create_res.json()["id"]

    assign_res = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        headers=eng_h,
        json={"assignee_id": str(tech_a.id)},
    )
    assert assign_res.status_code == 200

    # Tech B tries to start Tech A's order -> must be 403 or 404
    tech_b_h = {"Authorization": f"Bearer {tech_b_tok}"}
    start_b = await async_client.post(f"/api/v1/work-orders/{wo_id}/start", headers=tech_b_h)
    assert start_b.status_code in (403, 404)

    # Tech A starts successfully
    tech_a_h = {"Authorization": f"Bearer {tech_a_tok}"}
    start_a = await async_client.post(f"/api/v1/work-orders/{wo_id}/start", headers=tech_a_h)
    assert start_a.status_code == 200
    assert start_a.json()["status"] == "IN_PROGRESS"

    # Tech B tries to complete -> must be 403 or 404
    comp_b = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        headers=tech_b_h,
        json={"result": "Done by wrong person"},
    )
    assert comp_b.status_code in (403, 404)


@pytest.mark.asyncio
async def test_operator_isolation_in_work_orders(async_client: AsyncClient, users_setup, sample_equip):
    _, op1_tok = users_setup["op1"]
    _, op2_tok = users_setup["op2"]

    op1_h = {"Authorization": f"Bearer {op1_tok}"}
    op2_h = {"Authorization": f"Bearer {op2_tok}"}

    # Op1 creates order
    res = await async_client.post(
        "/api/v1/work-orders",
        headers=op1_h,
        json={
            "type": "REPAIR",
            "equipment_id": str(sample_equip.id),
            "title": "Loose Belt",
            "description": "Operator noticed loose conveyor belt",
            "priority": "LOW",
        },
    )
    assert res.status_code == 201
    wo1_id = res.json()["id"]

    # Op1 sees it in list
    list1 = await async_client.get("/api/v1/work-orders", headers=op1_h)
    assert list1.status_code == 200
    ids_op1 = [x["id"] for x in list1.json()["items"]]
    assert wo1_id in ids_op1

    # Op2 cannot see Op1's order
    list2 = await async_client.get("/api/v1/work-orders", headers=op2_h)
    assert list2.status_code == 200
    ids_op2 = [x["id"] for x in list2.json()["items"]]
    assert wo1_id not in ids_op2

    # Op2 GET by ID returns 404
    get_res = await async_client.get(f"/api/v1/work-orders/{wo1_id}", headers=op2_h)
    assert get_res.status_code == 404
