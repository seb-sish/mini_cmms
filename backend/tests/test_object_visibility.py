"""Регрессионные тесты объектной видимости по матрице x-object-visibility."""

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_opaque_token, hash_password
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.fault import Fault, FaultSeverity, FaultStatus
from app.db.models.session import UserSession
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType


async def _make_user(
    db_session: AsyncSession,
    *,
    login: str,
    role: UserRole,
    with_session: bool = True,
) -> tuple[User, str | None]:
    user = User(
        login=login,
        password_hash=hash_password("Pass12345!"),
        full_name=login,
        role=role,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    if not with_session:
        return user, None

    raw_token, t_hash = create_opaque_token()
    db_session.add(
        UserSession(
            user_id=user.id,
            token_hash=t_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=12),
        )
    )
    await db_session.commit()
    return user, raw_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_technician_sees_only_equipment_of_current_assignments(
    async_client: AsyncClient, db_session: AsyncSession
):
    """RELATED_ASSIGNMENT: техник видит только оборудование своих назначений."""
    technician, token = await _make_user(db_session, login="tech_visibility", role=UserRole.TECHNICIAN)
    engineer, _ = await _make_user(db_session, login="eng_visibility", role=UserRole.ENGINEER, with_session=False)

    assigned = Equipment(
        name="Assigned Machine",
        inventory_number="EQ-VIS-1",
        category="Machining",
        location="Shop",
        commissioned_on=date(2026, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
    )
    foreign = Equipment(
        name="Foreign Machine",
        inventory_number="EQ-VIS-2",
        category="Machining",
        location="Shop",
        commissioned_on=date(2026, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add_all([assigned, foreign])
    await db_session.commit()
    await db_session.refresh(assigned)
    await db_session.refresh(foreign)

    db_session.add(
        WorkOrder(
            number="WO-VIS-1",
            type=WorkOrderType.REPAIR,
            status=WorkOrderStatus.ASSIGNED,
            title="Assigned repair",
            description="Assigned repair",
            equipment_id=assigned.id,
            author_id=engineer.id,
            assignee_id=technician.id,
        )
    )
    await db_session.commit()

    headers = _auth(token)

    res = await async_client.get("/api/v1/equipment", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [str(assigned.id)]

    res = await async_client.get(f"/api/v1/equipment/{assigned.id}", headers=headers)
    assert res.status_code == 200

    res = await async_client.get(f"/api/v1/equipment/{foreign.id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_operator_cannot_create_work_order_for_foreign_fault(async_client: AsyncClient, db_session: AsyncSession):
    """AUTHOR: оператор не обходит видимость чужой неисправности ссылкой в теле."""
    operator, token = await _make_user(db_session, login="op_fault_owner", role=UserRole.OPERATOR)
    other_operator, _ = await _make_user(db_session, login="op_other_owner", role=UserRole.OPERATOR, with_session=False)

    equipment = Equipment(
        name="Machine For Fault",
        inventory_number="EQ-VIS-3",
        category="Machining",
        location="Shop",
        commissioned_on=date(2026, 1, 1),
        status=EquipmentStatus.OPERATIONAL,
    )
    db_session.add(equipment)
    await db_session.commit()
    await db_session.refresh(equipment)

    fault = Fault(
        equipment_id=equipment.id,
        author_id=other_operator.id,
        description="Foreign fault",
        detected_on=date(2026, 2, 1),
        severity=FaultSeverity.HIGH,
        status=FaultStatus.OPEN,
    )
    db_session.add(fault)
    await db_session.commit()
    await db_session.refresh(fault)

    res = await async_client.get(f"/api/v1/faults/{fault.id}", headers=_auth(token))
    assert res.status_code == 404

    res = await async_client.post(
        "/api/v1/work-orders",
        headers=_auth(token),
        json={
            "type": "REPAIR",
            "title": "Repair of foreign fault",
            "description": "Repair of foreign fault",
            "equipment_id": str(equipment.id),
            "fault_id": str(fault.id),
            "priority": "NORMAL",
        },
    )
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"

    # Своя неисправность — принимается.
    own_fault = Fault(
        equipment_id=equipment.id,
        author_id=operator.id,
        description="Own fault",
        detected_on=date(2026, 2, 1),
        severity=FaultSeverity.HIGH,
        status=FaultStatus.OPEN,
    )
    db_session.add(own_fault)
    await db_session.commit()
    await db_session.refresh(own_fault)

    res = await async_client.post(
        "/api/v1/work-orders",
        headers=_auth(token),
        json={
            "type": "REPAIR",
            "title": "Repair of own fault",
            "description": "Repair of own fault",
            "equipment_id": str(equipment.id),
            "fault_id": str(own_fault.id),
            "priority": "NORMAL",
        },
    )
    assert res.status_code == 201
