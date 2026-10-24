from datetime import date, datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus

@pytest.fixture
async def operator_auth(db_session: AsyncSession) -> tuple[User, str]:
    user = User(
        login="operator_1",
        password_hash=hash_password("Pass12345!"),
        full_name="Plant Operator",
        role=UserRole.OPERATOR,
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
        name="CNC Milling Machine",
        inventory_number="EQ-M01",
        category="Machining",
        location="Shop 2",
        status=EquipmentStatus.OPERATIONAL,
        commissioned_on=date(2025, 1, 1),
    )
    db_session.add(eq)
    await db_session.commit()
    await db_session.refresh(eq)
    return eq

@pytest.mark.asyncio
async def test_fault_create_and_operator_edit(async_client: AsyncClient, operator_auth, sample_equipment):
    user, token = operator_auth
    headers = {"Authorization": f"Bearer {token}"}

    # Create fault
    res = await async_client.post("/api/v1/faults", headers=headers, json={
        "equipment_id": str(sample_equipment.id),
        "description": "Vibration in spindle motor",
        "detected_on": "2026-10-24"
    })
    assert res.status_code == 201
    f_data = res.json()
    assert f_data["status"] == "OPEN"
    assert f_data["author_id"] == str(user.id)
    assert f_data["version"] == 1
    etag = res.headers["ETag"]

    # Edit fault while OPEN by author
    patch_res = await async_client.patch(
        f"/api/v1/faults/{f_data['id']}",
        headers={**headers, "If-Match": etag},
        json={"description": "High vibration in spindle motor bearing"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["version"] == 2
    assert patch_res.json()["description"] == "High vibration in spindle motor bearing"
