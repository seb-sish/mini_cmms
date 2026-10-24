from datetime import date, datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User, UserRole, UserStatus
from app.db.models.equipment import Equipment
from app.db.models.work_order import WorkOrder, WorkOrderType, WorkOrderStatus, WorkOrderPriority
from app.core.security import hash_password, create_opaque_token
from app.db.models.session import UserSession

@pytest.fixture
async def engineer_token(db_session: AsyncSession) -> str:
    user = User(
        login="engineer_search",
        password_hash=hash_password("Pass123!"),
        full_name="Engineer Search",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token

@pytest.fixture
async def technician_token(db_session: AsyncSession) -> tuple[str, User]:
    user = User(
        login="tech_search",
        password_hash=hash_password("Pass123!"),
        full_name="Technician Search",
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token, user

@pytest.fixture
async def seed_orders(db_session: AsyncSession, technician_token: tuple[str, User]) -> list[WorkOrder]:
    _, tech = technician_token
    eq = Equipment(
        name="Turbine 1",
        inventory_number="EQ-TRB-01",
        category="TURBINES",
        location="Station 1",
        commissioned_on=date(2024, 1, 1),
    )
    admin = User(
        login="admin_search",
        password_hash=hash_password("Pass123!"),
        full_name="Admin Search",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([eq, admin])
    await db_session.commit()

    wo1 = WorkOrder(
        number="WO-2026-0010",
        type=WorkOrderType.REPAIR,
        status=WorkOrderStatus.CREATED,
        title="Check turbine vibration",
        description="Vibration detected in upper turbine shaft",
        priority=WorkOrderPriority.HIGH,
        equipment_id=eq.id,
        author_id=admin.id,
    )
    wo2 = WorkOrder(
        number="WO-2026-0011",
        type=WorkOrderType.REPAIR,
        status=WorkOrderStatus.ASSIGNED,
        title="Oil replacement",
        description="Routine oil change for generator",
        priority=WorkOrderPriority.NORMAL,
        equipment_id=eq.id,
        author_id=admin.id,
        assignee_id=tech.id,
    )
    wo3 = WorkOrder(
        number="WO-2026-0012",
        type=WorkOrderType.REPAIR,
        status=WorkOrderStatus.IN_PROGRESS,
        title="Sensor calibration",
        description="Temperature sensor recalibration needed",
        priority=WorkOrderPriority.LOW,
        equipment_id=eq.id,
        author_id=admin.id,
        assignee_id=tech.id,
    )
    db_session.add_all([wo1, wo2, wo3])
    await db_session.commit()
    return [wo1, wo2, wo3]

@pytest.mark.asyncio
async def test_work_order_search_q(
    async_client: AsyncClient,
    engineer_token: str,
    seed_orders: list[WorkOrder],
):
    # Search q matches title
    res1 = await async_client.get(
        "/api/v1/work-orders?q=vibration",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert res1.status_code == 200
    items1 = res1.json()["items"]
    assert len(items1) == 1
    assert items1[0]["number"] == "WO-2026-0010"

    # Search q matches description
    res2 = await async_client.get(
        "/api/v1/work-orders?q=generator",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert res2.status_code == 200
    items2 = res2.json()["items"]
    assert len(items2) == 1
    assert items2[0]["number"] == "WO-2026-0011"

    # Search q matches number
    res3 = await async_client.get(
        "/api/v1/work-orders?q=WO-2026-0012",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert res3.status_code == 200
    items3 = res3.json()["items"]
    assert len(items3) == 1
    assert items3[0]["number"] == "WO-2026-0012"

@pytest.mark.asyncio
async def test_work_order_sort_status(
    async_client: AsyncClient,
    engineer_token: str,
    seed_orders: list[WorkOrder],
):
    # Sort status ASC: CREATED, ASSIGNED, IN_PROGRESS
    res_asc = await async_client.get(
        "/api/v1/work-orders?sort=status",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert res_asc.status_code == 200
    statuses_asc = [item["status"] for item in res_asc.json()["items"] if item["number"] in ["WO-2026-0010", "WO-2026-0011", "WO-2026-0012"]]
    assert statuses_asc == ["CREATED", "ASSIGNED", "IN_PROGRESS"]

    # Sort status DESC: IN_PROGRESS, ASSIGNED, CREATED
    res_desc = await async_client.get(
        "/api/v1/work-orders?sort=-status",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert res_desc.status_code == 200
    statuses_desc = [item["status"] for item in res_desc.json()["items"] if item["number"] in ["WO-2026-0010", "WO-2026-0011", "WO-2026-0012"]]
    assert statuses_desc == ["IN_PROGRESS", "ASSIGNED", "CREATED"]

@pytest.mark.asyncio
async def test_technician_sees_only_assigned_work_orders(
    async_client: AsyncClient,
    technician_token: tuple[str, User],
    seed_orders: list[WorkOrder],
):
    token, _ = technician_token
    res = await async_client.get(
        "/api/v1/work-orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    items = res.json()["items"]
    # Only wo2 and wo3 are assigned to tech, wo1 is CREATED without assignee
    assert all(item["number"] in ["WO-2026-0011", "WO-2026-0012"] for item in items)
    assert not any(item["number"] == "WO-2026-0010" for item in items)
