from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select, text

from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.notification import Notification
from app.db.models.user import User
from app.db.models.work_order import WorkOrder
from app.services.equipment_service import get_company_today
from app.services.notification_service import NotificationService
from app.worker.tasks import generate_maintenance_notifications
from tests.contract.oracle import build_oracle, load_spec
from tests.test_user_directory import actor


@pytest.mark.asyncio
async def test_plan_and_assignments_notify_without_worker_tick(async_client, db_session):
    engineer, headers = await actor(db_session, "engineer", "ENGINEER")
    technician, _ = await actor(db_session, "technician", "TECHNICIAN")
    replacement, _ = await actor(db_session, "replacement", "TECHNICIAN")
    equipment = Equipment(
        name="Press", inventory_number="NOW-1", category="Presses", location="Shop", commissioned_on=get_company_today()
    )
    db_session.add(equipment)
    await db_session.commit()
    response = await async_client.post(
        "/api/v1/maintenance-plans",
        headers=headers,
        json={
            "name": "Inspection",
            "scope": "EQUIPMENT",
            "equipment_id": str(equipment.id),
            "interval_days": 30,
            "first_due_on": (get_company_today() + timedelta(days=2)).isoformat(),
            "checklist": [{"order": 1, "title": "Inspect press", "required": True}],
        },
    )
    assert response.status_code == 201, response.text
    notifications = (await db_session.execute(select(Notification))).scalars().all()
    assert len(notifications) == 1
    assert notifications[0].recipient_id == engineer.id
    assert "ТО" in notifications[0].message
    schedule_id = notifications[0].schedule_id
    response = await async_client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "type": "PLANNED",
            "equipment_id": str(equipment.id),
            "schedule_id": str(schedule_id),
            "title": "Inspect press",
            "description": "Inspect the press",
            "priority": "NORMAL",
        },
    )
    assert response.status_code == 201, response.text
    work_id = response.json()["id"]
    for command, person in [("assign", technician), ("reassign", replacement)]:
        response = await async_client.post(
            f"/api/v1/work-orders/{work_id}/{command}", headers=headers, json={"assignee_id": str(person.id)}
        )
        assert response.status_code == 200, response.text
        assert (
            await db_session.execute(select(func.count(Notification.id)).where(Notification.recipient_id == person.id))
        ).scalar_one() == 1
    assert await generate_maintenance_notifications({"session": db_session}) == 0
    assert (await db_session.execute(select(func.count(Notification.id)))).scalar_one() == 3


@pytest.mark.asyncio
async def test_new_event_details_are_readable(async_client, db_session):
    _, headers = await actor(db_session, "engineer", "ENGINEER")
    equipment = Equipment(
        name="Press",
        inventory_number="EVENT-1",
        category="Presses",
        location="Shop",
        commissioned_on=get_company_today(),
    )
    db_session.add(equipment)
    await db_session.commit()
    response = await async_client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "type": "REPAIR",
            "equipment_id": str(equipment.id),
            "title": "Repair press",
            "description": "Inspect the press",
            "priority": "NORMAL",
        },
    )
    assert response.status_code == 201, response.text
    work_id = response.json()["id"]
    response = await async_client.get(f"/api/v1/work-orders/{work_id}/events", headers=headers)
    assert response.json()["items"][0]["details"] == "Заявка создана"


@pytest.mark.asyncio
async def test_notification_failure_does_not_commit_half_a_plan(async_client, db_session, monkeypatch):
    _, headers = await actor(db_session, "engineer", "ENGINEER")
    equipment = Equipment(
        name="Press",
        inventory_number="FAIL-1",
        category="Presses",
        location="Shop",
        commissioned_on=get_company_today(),
    )
    db_session.add(equipment)
    await db_session.commit()
    equipment_id = str(equipment.id)
    generate = NotificationService.generate

    async def failing_generate(cls, session, today, **scope):
        await generate(session, today, **scope)
        raise RuntimeError("simulated notification failure")

    monkeypatch.setattr(NotificationService, "generate", classmethod(failing_generate))
    with pytest.raises(RuntimeError, match="simulated notification failure"):
        await async_client.post(
            "/api/v1/maintenance-plans",
            headers=headers,
            json={
                "name": "Inspection",
                "scope": "EQUIPMENT",
                "equipment_id": equipment_id,
                "interval_days": 30,
                "first_due_on": get_company_today().isoformat(),
                "checklist": [{"order": 1, "title": "Inspect press", "required": True}],
            },
        )
    await db_session.rollback()
    for model in [MaintenancePlan, MaintenanceSchedule, Notification]:
        assert (await db_session.execute(select(func.count(model.id)))).scalar_one() == 0


@pytest.mark.asyncio
async def test_activity_accepts_the_full_allowed_completion_result(async_client, db_session):
    _, headers = await actor(db_session, "engineer", "ENGINEER")
    technician, tech_headers = await actor(db_session, "technician", "TECHNICIAN")
    equipment = Equipment(
        name="Press",
        inventory_number="LONG-1",
        category="Presses",
        location="Shop",
        commissioned_on=get_company_today(),
    )
    db_session.add(equipment)
    await db_session.commit()
    response = await async_client.post(
        "/api/v1/work-orders",
        headers=headers,
        json={
            "type": "REPAIR",
            "equipment_id": str(equipment.id),
            "title": "Repair press",
            "description": "Inspect the press",
            "priority": "NORMAL",
        },
    )
    assert response.status_code == 201
    path = f"/api/v1/work-orders/{response.json()['id']}"
    assert (
        await async_client.post(path + "/assign", headers=headers, json={"assignee_id": str(technician.id)})
    ).status_code == 200
    assert (await async_client.post(path + "/start", headers=tech_headers)).status_code == 200
    result = "R" * 4000
    assert (
        await async_client.post(path + "/complete", headers=tech_headers, json={"result": result, "replaced_parts": []})
    ).status_code == 200
    response = await async_client.get(path + "/events", headers=headers)
    build_oracle(load_spec()).assert_response(response, "GET", path + "/events", expected_status=200)
    assert response.json()["items"][-1]["details"] == result


@pytest.mark.asyncio
async def test_notifications_acquire_recipient_keys_in_a_consistent_order(db_session):
    """Worker and API must acquire shared notification keys in the same order."""
    technician = User(
        id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"), login="technician", password_hash="unused", role="TECHNICIAN"
    )
    engineer = User(
        id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"), login="engineer", password_hash="unused", role="ENGINEER"
    )
    equipment = Equipment(
        name="Press",
        inventory_number="ORDER-1",
        category="Presses",
        location="Shop",
        commissioned_on=get_company_today(),
    )
    db_session.add_all([engineer, technician, equipment])
    await db_session.flush()
    plan = MaintenancePlan(
        name="Inspection",
        scope="EQUIPMENT",
        equipment_id=equipment.id,
        interval_days=30,
        first_due_on=get_company_today(),
        checklist=[],
    )
    db_session.add(plan)
    await db_session.flush()
    schedule = MaintenanceSchedule(plan_id=plan.id, equipment_id=equipment.id, next_due_on=get_company_today())
    db_session.add(schedule)
    await db_session.flush()
    db_session.add(
        WorkOrder(
            number="ORDER-1",
            type="PLANNED",
            status="ASSIGNED",
            title="Inspection",
            description="Inspect press",
            equipment_id=equipment.id,
            schedule_id=schedule.id,
            planned_due_on=schedule.next_due_on,
            author_id=engineer.id,
            assignee_id=technician.id,
        )
    )
    await db_session.commit()
    assert await generate_maintenance_notifications({"session": db_session}) == 2
    inserted = (await db_session.execute(text("SELECT recipient_id FROM notifications ORDER BY rowid"))).scalars().all()
    assert [UUID(value) for value in inserted] == [technician.id, engineer.id]
