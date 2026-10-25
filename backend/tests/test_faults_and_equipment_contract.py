from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus


async def create_user_with_token(db: AsyncSession, login: str, role: UserRole) -> dict[str, str]:
    user = User(
        login=login,
        password_hash=hash_password("Pass12345678!"),
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
        expires_at=date.today() + timedelta(days=1),
    )
    db.add(session)
    await db.commit()
    return {"Authorization": f"Bearer {raw_token}"}


@pytest.mark.asyncio
async def test_admin_blocked_from_equipment_and_faults(async_client: AsyncClient, db_session: AsyncSession):
    admin_headers = await create_user_with_token(db_session, "admin_forbidden", UserRole.ADMIN)

    res_eq = await async_client.get("/api/v1/equipment", headers=admin_headers)
    assert res_eq.status_code == 403
    assert res_eq.json()["code"] == "ACCESS_DENIED"

    res_fault = await async_client.get("/api/v1/faults", headers=admin_headers)
    assert res_fault.status_code == 403
    assert res_fault.json()["code"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_fault_requires_severity_and_validates_future_date(async_client: AsyncClient, db_session: AsyncSession):
    eng_headers = await create_user_with_token(db_session, "eng_faults", UserRole.ENGINEER)

    # 1. Create equipment
    eq_res = await async_client.post(
        "/api/v1/equipment",
        headers=eng_headers,
        json={
            "name": "Turbine 1",
            "inventory_number": "EQ-TURBINE-1",
            "category": "TURBINES",
            "location": "Sector A",
            "commissioned_on": "2023-01-01",
            "status": "OPERATIONAL",
        },
    )
    assert eq_res.status_code == 201
    eq_id = eq_res.json()["id"]

    # 2. Fault create without severity -> 422
    fault_no_sev = await async_client.post(
        "/api/v1/faults",
        headers=eng_headers,
        json={
            "equipment_id": eq_id,
            "description": "Vibration in turbine bearing",
            "detected_on": str(date.today()),
        },
    )
    assert fault_no_sev.status_code == 422

    # 3. Fault create with future date -> 422 FUTURE_DETECTED_DATE
    future_date = date.today() + timedelta(days=5)
    fault_future = await async_client.post(
        "/api/v1/faults",
        headers=eng_headers,
        json={
            "equipment_id": eq_id,
            "description": "Vibration in turbine bearing",
            "severity": "HIGH",
            "detected_on": str(future_date),
        },
    )
    assert fault_future.status_code == 422
    assert fault_future.json()["code"] == "FUTURE_DETECTED_DATE"

    # 4. Valid fault create
    fault_valid = await async_client.post(
        "/api/v1/faults",
        headers=eng_headers,
        json={
            "equipment_id": eq_id,
            "description": "Vibration in turbine bearing",
            "severity": "HIGH",
            "detected_on": str(date.today()),
        },
    )
    assert fault_valid.status_code == 201
    assert fault_valid.json()["severity"] == "HIGH"
