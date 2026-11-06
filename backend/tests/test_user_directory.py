from datetime import UTC, datetime

import pytest

from app.core.security import create_opaque_token
from app.db.models.equipment import Equipment
from app.db.models.fault import Fault
from app.db.models.session import UserSession
from app.db.models.user import User
from app.db.models.work_order import WorkOrder
from app.db.models.work_order_event import WorkOrderEvent
from tests.contract.oracle import build_oracle, load_spec


async def actor(db, login, role, status="ACTIVE"):
    user = User(login=login, password_hash="unused", role=role, status=status)
    db.add(user)
    await db.flush()
    token, token_hash = create_opaque_token()
    db.add(UserSession(user_id=user.id, token_hash=token_hash, expires_at=datetime(2099, 1, 1, tzinfo=UTC)))
    await db.commit()
    return user, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_engineer_directory_is_read_only_and_filtered(async_client, db_session):
    _, headers = await actor(db_session, "engineer", "ENGINEER")
    tech, _ = await actor(db_session, "technician", "TECHNICIAN")
    await actor(db_session, "blocked", "TECHNICIAN", "BLOCKED")
    response = await async_client.get("/api/v1/users/directory?role=TECHNICIAN&status=ACTIVE", headers=headers)
    assert response.status_code == 200
    build_oracle(load_spec()).assert_response(response, "GET", "/api/v1/users/directory", expected_status=200)
    assert response.json()["total"] == 1
    assert response.json()["items"] == [
        {"id": str(tech.id), "login": tech.login, "role": tech.role, "status": tech.status}
    ]
    assert (await async_client.get("/api/v1/users", headers=headers)).status_code == 403
    assert (await async_client.get(f"/api/v1/users/{tech.id}", headers=headers)).status_code == 403
    assert (
        await async_client.patch(f"/api/v1/users/{tech.id}", headers=headers, json={"status": "BLOCKED"})
    ).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["TECHNICIAN", "OPERATOR"])
async def test_user_summary_follows_work_visibility(async_client, db_session, role):
    viewer, headers = await actor(db_session, "viewer", role)
    engineer, _ = await actor(db_session, "engineer", "ENGINEER")
    other, _ = await actor(db_session, "unrelated", "OPERATOR")
    previous, _ = await actor(db_session, "previous", "TECHNICIAN", "BLOCKED")
    equipment = Equipment(
        name="Press",
        inventory_number="DIR-1",
        category="Presses",
        location="Shop",
        commissioned_on=datetime(2020, 1, 1).date(),
    )
    db_session.add(equipment)
    await db_session.flush()
    fault = Fault(
        equipment_id=equipment.id, author_id=other.id, description="Fault", detected_on=equipment.commissioned_on
    )
    db_session.add(fault)
    await db_session.flush()
    work = WorkOrder(
        number="DIR-1",
        type="REPAIR",
        status="ASSIGNED",
        title="Repair",
        description="Repair press",
        equipment_id=equipment.id,
        author_id=viewer.id if role == "OPERATOR" else engineer.id,
        assignee_id=viewer.id if role == "TECHNICIAN" else engineer.id,
        fault_id=fault.id,
    )
    db_session.add(work)
    await db_session.flush()
    db_session.add(
        WorkOrderEvent(
            work_order_id=work.id, event_type="REASSIGNED", actor_id=engineer.id, old_assignee_id=previous.id
        )
    )
    await db_session.commit()
    for person in [engineer, previous, viewer] + ([other] if role == "TECHNICIAN" else []):
        response = await async_client.get(f"/api/v1/users/{person.id}/summary", headers=headers)
        assert response.status_code == 200
        build_oracle(load_spec()).assert_response(
            response, "GET", f"/api/v1/users/{person.id}/summary", expected_status=200
        )
        assert set(response.json()) == {"id", "login", "role", "status"}
    stranger, _ = await actor(db_session, "stranger", "TECHNICIAN")
    assert (await async_client.get(f"/api/v1/users/{stranger.id}/summary", headers=headers)).status_code == 404
    assert (await async_client.get("/api/v1/users/directory", headers=headers)).status_code == 403
    work.author_id = other.id
    work.assignee_id = stranger.id
    await db_session.commit()
    assert (await async_client.get(f"/api/v1/users/{engineer.id}/summary", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_summary_requires_authentication(async_client):
    response = await async_client.get("/api/v1/users/directory")
    assert response.status_code == 401
