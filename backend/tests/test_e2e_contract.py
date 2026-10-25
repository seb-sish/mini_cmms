from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User, UserRole, UserStatus
from app.services.equipment_service import get_company_today
from app.worker.tasks import generate_maintenance_notifications


@pytest.mark.asyncio
async def test_full_acceptance_flows(async_client: AsyncClient, db_session: AsyncSession):
    # =========================================================================
    # FLOW 1: Admin setup & User Onboarding
    # =========================================================================
    admin_user = User(
        login="global_admin",
        password_hash=hash_password("AdminPass123!"),
        full_name="Global Administrator",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin_user)
    await db_session.commit()

    # 1.1 Admin logs in
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"login": "global_admin", "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1.2 Verify /me
    me_res = await async_client.get("/api/v1/auth/me", headers=admin_headers)
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "ADMIN"

    # 1.3 Admin creates Engineer, Technician, and Operator
    eng_res = await async_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "login": "eng_flow",
            "password": "Password123!",
            "role": "ENGINEER",
        },
    )
    assert eng_res.status_code == 201
    eng_id = eng_res.json()["id"]

    tech_res = await async_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "login": "tech_flow",
            "password": "Password123!",
            "role": "TECHNICIAN",
        },
    )
    assert tech_res.status_code == 201
    tech_id = tech_res.json()["id"]

    op_res = await async_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "login": "op_flow",
            "password": "Password123!",
            "role": "OPERATOR",
        },
    )
    assert op_res.status_code == 201
    op_id = op_res.json()["id"]

    # 1.4 Log in as each user
    eng_login = await async_client.post("/api/v1/auth/login", json={"login": "eng_flow", "password": "Password123!"})
    eng_headers = {"Authorization": f"Bearer {eng_login.json()['access_token']}"}

    tech_login = await async_client.post("/api/v1/auth/login", json={"login": "tech_flow", "password": "Password123!"})
    tech_headers = {"Authorization": f"Bearer {tech_login.json()['access_token']}"}

    op_login = await async_client.post("/api/v1/auth/login", json={"login": "op_flow", "password": "Password123!"})
    op_headers = {"Authorization": f"Bearer {op_login.json()['access_token']}"}

    # =========================================================================
    # FLOW 2: Equipment & Fault & Repair Work Order
    # =========================================================================
    # 2.1 Engineer creates equipment
    eq_res = await async_client.post(
        "/api/v1/equipment",
        headers=eng_headers,
        json={
            "name": "Centrifugal Pump Alpha",
            "inventory_number": "EQ-PUMP-ALPHA",
            "category": "PUMPS",
            "location": "Pumping Station 1",
            "commissioned_on": "2024-01-15",
        },
    )
    assert eq_res.status_code == 201
    eq_id = eq_res.json()["id"]

    # 2.2 Operator registers a Fault
    fault_res = await async_client.post(
        "/api/v1/faults",
        headers=op_headers,
        json={
            "equipment_id": eq_id,
            "description": "Unusual cavitation noise during operation",
            "severity": "HIGH",
            "detected_on": "2026-10-24",
        },
    )
    assert fault_res.status_code == 201
    fault_id = fault_res.json()["id"]
    fault_etag = fault_res.headers["ETag"]

    # 2.3 Operator edits fault while OPEN
    patch_fault = await async_client.patch(
        f"/api/v1/faults/{fault_id}",
        headers={**op_headers, "If-Match": fault_etag},
        json={"description": "High cavitation noise and minor vibration"},
    )
    assert patch_fault.status_code == 200

    # 2.4 Operator creates REPAIR work order
    wo_rep_res = await async_client.post(
        "/api/v1/work-orders",
        headers=op_headers,
        json={
            "type": "REPAIR",
            "equipment_id": eq_id,
            "fault_id": fault_id,
            "title": "Repair Pump Alpha Cavitation",
            "description": "Inspect impeller and replace seals if damaged",
            "priority": "HIGH",
        },
    )
    assert wo_rep_res.status_code == 201
    wo_rep_id = wo_rep_res.json()["id"]

    # 2.5 Engineer assigns to Technician
    assign_rep = await async_client.post(
        f"/api/v1/work-orders/{wo_rep_id}/assign",
        headers=eng_headers,
        json={"assignee_id": tech_id},
    )
    assert assign_rep.status_code == 200
    assert assign_rep.json()["status"] == "ASSIGNED"

    # 2.6 Technician starts the work order
    start_rep = await async_client.post(
        f"/api/v1/work-orders/{wo_rep_id}/start",
        headers=tech_headers,
    )
    assert start_rep.status_code == 200
    assert start_rep.json()["status"] == "IN_PROGRESS"

    # 2.7 Technician completes the work order
    comp_rep = await async_client.post(
        f"/api/v1/work-orders/{wo_rep_id}/complete",
        headers=tech_headers,
        json={"result": "Impeller cleaned, damaged mechanical seal replaced", "replaced_parts": ["SEAL-PUMP-01"]},
    )
    assert comp_rep.status_code == 200
    assert comp_rep.json()["status"] == "COMPLETED"

    # 2.8 Engineer closes the work order
    close_rep = await async_client.post(
        f"/api/v1/work-orders/{wo_rep_id}/close",
        headers=eng_headers,
    )
    assert close_rep.status_code == 200
    assert close_rep.json()["status"] == "CLOSED"

    # 2.9 Fault is now RESOLVED
    fault_check = await async_client.get(f"/api/v1/faults/{fault_id}", headers=eng_headers)
    assert fault_check.status_code == 200
    assert fault_check.json()["status"] == "RESOLVED"

    # =========================================================================
    # FLOW 3: Maintenance Plan, Schedule & Planned Work Order
    # =========================================================================
    today = get_company_today()
    plan_res = await async_client.post(
        "/api/v1/maintenance-plans",
        headers=eng_headers,
        json={
            "name": "Quarterly Pump Maintenance",
            "interval_days": 30,
            "first_due_on": str(today),
            "scope": "EQUIPMENT",
            "equipment_id": eq_id,
            "checklist": [
                {"order": 1, "title": "Check oil level and quality", "required": True},
                {"order": 2, "title": "Clean intake filter", "required": True},
                {"order": 3, "title": "Inspect paint coating", "required": False},
            ],
        },
    )
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    # 3.1 Verify schedule created
    sched_list = await async_client.get(
        f"/api/v1/maintenance-schedules?plan_id={plan_id}",
        headers=eng_headers,
    )
    assert sched_list.status_code == 200
    scheds = sched_list.json()["items"]
    assert len(scheds) == 1
    sched_id = scheds[0]["id"]
    assert scheds[0]["next_due_on"] == str(today)

    # 3.2 Run background notification task (engineers notified)
    ctx = {"session": db_session}
    notif_count = await generate_maintenance_notifications(ctx)
    assert notif_count >= 1

    eng_notifs = await async_client.get("/api/v1/notifications", headers=eng_headers)
    assert eng_notifs.status_code == 200
    assert eng_notifs.json()["total"] >= 1

    # 3.4 Engineer creates PLANNED work order
    wo_plan_res = await async_client.post(
        "/api/v1/work-orders",
        headers=eng_headers,
        json={
            "type": "PLANNED",
            "equipment_id": eq_id,
            "schedule_id": sched_id,
            "title": "Quarterly Service for Pump Alpha",
            "description": "Scheduled maintenance checklist execution",
            "priority": "NORMAL",
        },
    )
    assert wo_plan_res.status_code == 201
    wo_plan_data = wo_plan_res.json()
    wo_plan_id = wo_plan_data["id"]
    assert len(wo_plan_data["checklist"]) == 3

    # 3.5 Assign to Technician, trigger notification tick, and Start
    await async_client.post(
        f"/api/v1/work-orders/{wo_plan_id}/assign",
        headers=eng_headers,
        json={"assignee_id": tech_id},
    )
    # Late assignment notification for technician
    tech_notif_count = await generate_maintenance_notifications(ctx)
    assert tech_notif_count >= 1

    tech_notifs = await async_client.get("/api/v1/notifications", headers=tech_headers)
    assert tech_notifs.status_code == 200
    assert tech_notifs.json()["total"] >= 1
    start_plan = await async_client.post(
        f"/api/v1/work-orders/{wo_plan_id}/start",
        headers=tech_headers,
    )
    assert start_plan.status_code == 200
    current_etag = start_plan.headers["ETag"]

    # 3.6 Check checklist items with ETag
    for item in start_plan.json()["checklist"]:
        if item["required"]:
            chk_res = await async_client.patch(
                f"/api/v1/work-orders/{wo_plan_id}/checklist/{item['id']}",
                headers={**tech_headers, "If-Match": current_etag},
                json={"checked": True, "comment": "Completed successfully"},
            )
            assert chk_res.status_code == 200
            current_etag = chk_res.headers["ETag"]

    # 3.7 Complete work order
    comp_plan = await async_client.post(
        f"/api/v1/work-orders/{wo_plan_id}/complete",
        headers=tech_headers,
        json={"result": "All required checklist items done"},
    )
    assert comp_plan.status_code == 200

    # 3.8 Close work order and verify schedule advanced
    close_plan = await async_client.post(
        f"/api/v1/work-orders/{wo_plan_id}/close",
        headers=eng_headers,
    )
    assert close_plan.status_code == 200

    sched_after = await async_client.get(
        f"/api/v1/maintenance-schedules/{sched_id}",
        headers=eng_headers,
    )
    assert sched_after.status_code == 200
    assert sched_after.json()["next_due_on"] == str(today + timedelta(days=30))

    # 3.9 Verify WorkHistory has 2 entries now (1 REPAIR, 1 PLANNED)
    hist_all = await async_client.get(
        f"/api/v1/work-history?equipment_id={eq_id}",
        headers=eng_headers,
    )
    assert hist_all.status_code == 200
    assert hist_all.json()["total"] == 2

    # =========================================================================
    # FLOW 4: Concurrency & System health checks
    # =========================================================================
    health_res = await async_client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"
