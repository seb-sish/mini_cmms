from datetime import date, datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus

@pytest.fixture
async def engineer_auth(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login="lead_engineer",
        password_hash=hash_password("Pass12345!"),
        full_name="Lead Maintenance Engineer",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    raw_token, t_hash = create_opaque_token()
    session = UserSession(
        user_id=user.id,
        token_hash=t_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
    )
    db_session.add(session)
    await db_session.commit()
    return user, raw_token

@pytest.fixture
async def sample_equipment(db_session: AsyncSession) -> Equipment:
    eq = Equipment(
        name="Hydraulic Press 50T",
        inventory_number="HP-050",
        category="Presses",
        location="Shop 3",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2025, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)
    return eq

@pytest.mark.asyncio
async def test_create_plan_creates_schedules(async_client: AsyncClient, engineer_auth, sample_equipment):
    user, token = engineer_auth
    headers = {"Authorization": f"Bearer {token}"}

    # Create plan
    res = await async_client.post("/api/v1/maintenance-plans", headers=headers, json={
        "name": "Monthly Press Inspection",
        "scope": "EQUIPMENT",
        "equipment_id": str(sample_equipment.id),
        "interval_days": 30,
        "first_due_on": "2026-11-01",
        "checklist": [
            {"order": 1, "title": "Check oil level and pressure", "required": True}
        ]
    })
    assert res.status_code == 201
    plan = res.json()
    assert plan["name"] == "Monthly Press Inspection"
    assert plan["enabled"] is True
    assert plan["version"] == 1
    assert len(plan["checklist"]) == 1

    # Check that MaintenanceSchedule was automatically created
    sched_res = await async_client.get(f"/api/v1/maintenance-schedules?plan_id={plan['id']}", headers=headers)
    assert sched_res.status_code == 200
    items = sched_res.json()["items"]
    assert len(items) == 1
    assert items[0]["equipment_id"] == str(sample_equipment.id)
    assert items[0]["next_due_on"] == "2026-11-01"
    assert items[0]["active"] is True
