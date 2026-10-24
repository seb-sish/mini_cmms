from datetime import date, datetime, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User, UserRole, UserStatus
from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.core.security import hash_password, create_opaque_token
from app.db.models.session import UserSession

@pytest.fixture
async def technician_user(db_session: AsyncSession) -> User:
    tech = User(
        login="tech_notif",
        password_hash=hash_password("Pass123!"),
        full_name="Technician Notif",
        role=UserRole.TECHNICIAN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(tech)
    await db_session.commit()
    await db_session.refresh(tech)
    return tech

@pytest.fixture
async def engineer_user(db_session: AsyncSession) -> User:
    eng = User(
        login="eng_notif",
        password_hash=hash_password("Pass123!"),
        full_name="Engineer Notif",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(eng)
    await db_session.commit()
    await db_session.refresh(eng)
    return eng

@pytest.fixture
async def tech_token(db_session: AsyncSession, technician_user: User) -> str:
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=technician_user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token

@pytest.fixture
async def eng_token(db_session: AsyncSession, engineer_user: User) -> str:
    raw_token, token_hash = create_opaque_token()
    session = UserSession(
        user_id=engineer_user.id,
        token_hash=token_hash,
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    return raw_token

@pytest.mark.asyncio
async def test_notifications_recipient_isolation(
    async_client: AsyncClient,
    tech_token: str,
    eng_token: str,
    technician_user: User,
    engineer_user: User,
    db_session: AsyncSession,
):
    from app.db.models.notification import Notification, NotificationType

    eq = Equipment(
        name="Chiller 1",
        inventory_number="EQ-CHL-01",
        category="CHILLERS",
        location="Roof",
        commissioned_on=date(2024, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()

    plan = MaintenancePlan(
        name="Chiller Maintenance",
        description="Quarterly check",
        interval_days=90,
        first_due_on=date(2026, 11, 15),
        scope="EQUIPMENT",
        equipment_id=eq.id,
        checklist=[],
    )
    db_session.add(plan)
    await db_session.commit()

    sched = MaintenanceSchedule(
        plan_id=plan.id,
        equipment_id=eq.id,
        next_due_on=date(2026, 11, 15),
    )
    db_session.add(sched)
    await db_session.commit()

    # Create one notification for technician, one for engineer
    notif_tech = Notification(
        recipient_id=technician_user.id,
        plan_id=plan.id,
        schedule_id=sched.id,
        equipment_id=eq.id,
        planned_due_on=date(2026, 11, 15),
        type=NotificationType.THREE_DAYS_BEFORE,
        message="Upcoming maintenance for Chiller 1 in 3 days",
    )
    notif_eng = Notification(
        recipient_id=engineer_user.id,
        plan_id=plan.id,
        schedule_id=sched.id,
        equipment_id=eq.id,
        planned_due_on=date(2026, 11, 15),
        type=NotificationType.ON_DUE_DATE,
        message="Maintenance for Chiller 1 is due today",
    )
    db_session.add_all([notif_tech, notif_eng])
    await db_session.commit()
    await db_session.refresh(notif_tech)
    await db_session.refresh(notif_eng)

    # Technician only sees their notification
    res_tech = await async_client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    assert res_tech.status_code == 200
    data_tech = res_tech.json()
    assert data_tech["total"] == 1
    assert data_tech["items"][0]["id"] == str(notif_tech.id)
    assert data_tech["items"][0]["recipient_id"] == str(technician_user.id)

    # Technician accessing engineer's notification by id returns 404 NOT_FOUND
    res_unauth = await async_client.get(
        f"/api/v1/notifications/{notif_eng.id}",
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    assert res_unauth.status_code == 404

    # Engineer accessing their own notification returns 200
    res_eng = await async_client.get(
        f"/api/v1/notifications/{notif_eng.id}",
        headers={"Authorization": f"Bearer {eng_token}"},
    )
    assert res_eng.status_code == 200
    assert res_eng.json()["id"] == str(notif_eng.id)

@pytest.mark.asyncio
async def test_notifications_rbac_admin_and_operator_forbidden(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    admin = User(
        login="admin_notif_forbidden",
        password_hash=hash_password("Pass123!"),
        full_name="Admin Notif",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    operator = User(
        login="op_notif_forbidden",
        password_hash=hash_password("Pass123!"),
        full_name="Op Notif",
        role=UserRole.OPERATOR,
        status=UserStatus.ACTIVE,
    )
    db_session.add_all([admin, operator])
    await db_session.commit()

    raw_admin_token, token_hash_admin = create_opaque_token()
    raw_op_token, token_hash_op = create_opaque_token()
    db_session.add_all([
        UserSession(user_id=admin.id, token_hash=token_hash_admin, expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc)),
        UserSession(user_id=operator.id, token_hash=token_hash_op, expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc)),
    ])
    await db_session.commit()

    res_admin = await async_client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {raw_admin_token}"},
    )
    assert res_admin.status_code == 403
    assert res_admin.json()["code"] == "ACCESS_DENIED"

    res_op = await async_client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {raw_op_token}"},
    )
    assert res_op.status_code == 403
    assert res_op.json()["code"] == "ACCESS_DENIED"
