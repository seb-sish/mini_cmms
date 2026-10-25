import uuid
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password, hash_token
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_history import WorkHistory
from app.db.models.work_order import WorkOrder, WorkOrderPriority, WorkOrderStatus, WorkOrderType


async def create_user_with_session(db: AsyncSession, login: str, role: UserRole) -> tuple[User, str]:
    raw_token, t_hash = create_opaque_token()
    user = User(
        login=login,
        full_name=login,
        password_hash=hash_password("Password123!"),
        role=role,
        status=UserStatus.ACTIVE,
        version=1,
    )
    db.add(user)
    await db.flush()

    sess = UserSession(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )
    db.add(sess)
    await db.commit()
    await db.refresh(user)
    return user, raw_token


@pytest.mark.asyncio
async def test_work_history_access_matrix(async_client: AsyncClient, db_session: AsyncSession):
    # Setup users: 1 Admin, 1 Engineer, 2 Technicians, 1 Operator
    admin, admin_token = await create_user_with_session(db_session, "wh_admin", UserRole.ADMIN)
    engineer, eng_token = await create_user_with_session(db_session, "wh_eng", UserRole.ENGINEER)
    tech1, tech1_token = await create_user_with_session(db_session, "wh_tech1", UserRole.TECHNICIAN)
    tech2, tech2_token = await create_user_with_session(db_session, "wh_tech2", UserRole.TECHNICIAN)
    operator, op_token = await create_user_with_session(db_session, "wh_op", UserRole.OPERATOR)

    # Setup equipment
    eq = Equipment(
        name="Milling Machine 1",
        inventory_number="MILL-01",
        category="MILLS",
        location="Shop 1",
        commissioned_on=date(2025, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
        version=1,
    )
    db_session.add(eq)
    await db_session.flush()

    # Create work order assigned to tech1, authored by operator
    now = datetime.now(UTC)
    wo = WorkOrder(
        number="WO-2026-88881",
        title="Fix Spindle Alignment",
        description="Spindle vibrating",
        type=WorkOrderType.REPAIR,
        status=WorkOrderStatus.CLOSED,
        priority=WorkOrderPriority.HIGH,
        equipment_id=eq.id,
        author_id=operator.id,
        assignee_id=tech1.id,
        completed_at=now - timedelta(hours=2),
        closed_at=now,
        result="Spindle aligned and tightened",
        replaced_parts=["SHIM-01"],
        version=4,
    )
    db_session.add(wo)
    await db_session.flush()

    # Create work history for this work order
    wh = WorkHistory(
        work_order_id=wo.id,
        equipment_id=eq.id,
        technician_id=tech1.id,
        completed_at=now - timedelta(hours=2),
        closed_at=now,
        result="Spindle aligned and tightened",
        replaced_parts=["SHIM-01"],
        created_at=now,
    )
    db_session.add(wh)
    await db_session.commit()
    await db_session.refresh(wh)

    # 1. Tech1 (assignee) requests WorkHistory entry -> 200 with full card
    res_tech1 = await async_client.get(
        f"/api/v1/work-history/{wh.id}",
        headers={"Authorization": f"Bearer {tech1_token}"},
    )
    assert res_tech1.status_code == 200
    card1 = res_tech1.json()
    assert card1["id"] == str(wh.id)
    assert card1["work_order_id"] == str(wo.id)
    assert card1["technician_id"] == str(tech1.id)
    assert card1["result"] == "Spindle aligned and tightened"
    assert card1["replaced_parts"] == ["SHIM-01"]

    # 2. Tech2 (not assignee) requests same WorkHistory entry -> 404 NOT_FOUND (privacy per spec)
    res_tech2 = await async_client.get(
        f"/api/v1/work-history/{wh.id}",
        headers={"Authorization": f"Bearer {tech2_token}"},
    )
    assert res_tech2.status_code == 404
    assert res_tech2.json()["code"] == "NOT_FOUND"

    # 3. Admin requests WorkHistory entry -> 403 ACCESS_DENIED
    res_admin = await async_client.get(
        f"/api/v1/work-history/{wh.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 403
    assert res_admin.json()["code"] == "ACCESS_DENIED"

    # 4. Engineer requests WorkHistory entry -> 200
    res_eng = await async_client.get(
        f"/api/v1/work-history/{wh.id}",
        headers={"Authorization": f"Bearer {eng_token}"},
    )
    assert res_eng.status_code == 200
    assert res_eng.json()["id"] == str(wh.id)

    # 5. Operator (author of work order) requests WorkHistory entry -> 200
    res_op = await async_client.get(
        f"/api/v1/work-history/{wh.id}",
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert res_op.status_code == 200
    assert res_op.json()["id"] == str(wh.id)


@pytest.mark.asyncio
async def test_work_history_date_range_validation(async_client: AsyncClient, db_session: AsyncSession):
    """Обратный диапазон дат отклоняется, границы фильтра — локальные дни предприятия."""
    _, token = await create_user_with_session(db_session, "hist_range_engineer", UserRole.ENGINEER)
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.get(
        "/api/v1/work-history?completed_from=2026-02-10&completed_to=2026-02-01",
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["code"] == "INVALID_DATE_RANGE"

    res = await async_client.get(
        "/api/v1/work-history?completed_from=2026-02-01&completed_to=2026-02-10",
        headers=headers,
    )
    assert res.status_code == 200
    assert "items" in res.json()
