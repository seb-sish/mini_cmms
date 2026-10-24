from datetime import date, datetime, timezone
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User, UserRole, UserStatus
from app.db.models.equipment import Equipment
from app.db.models.work_order import WorkOrder, WorkOrderType, WorkOrderStatus, WorkChecklistItem
from app.db.models.work_order_event import WorkOrderEvent, WorkOrderEventType
from app.db.models.work_history import WorkHistory
from app.core.security import hash_password

@pytest.mark.asyncio
async def test_work_order_and_relations(db_session: AsyncSession):
    user = User(
        login="engineer",
        password_hash=hash_password("Pass123!"),
        full_name="Engineer User",
        role=UserRole.ENGINEER,
        status=UserStatus.ACTIVE,
    )
    equipment = Equipment(
        name="Pump #1",
        inventory_number="EQ-PUMP-01",
        category="PUMPS",
        location="Sector A",
        commissioned_on=date(2024, 1, 1),
    )
    db_session.add_all([user, equipment])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(equipment)

    wo = WorkOrder(
        number="WO-2026-00001",
        type=WorkOrderType.REPAIR,
        status=WorkOrderStatus.CREATED,
        title="Check pump vibration",
        equipment_id=equipment.id,
        author_id=user.id,
    )
    db_session.add(wo)
    await db_session.commit()
    await db_session.refresh(wo)

    assert wo.version == 1
    assert wo.status == WorkOrderStatus.CREATED
    assert wo.type == WorkOrderType.REPAIR
    assert wo.number == "WO-2026-00001"

    item = WorkChecklistItem(
        work_order_id=wo.id,
        order=1,
        description="Check oil level",
        is_required=True,
    )
    event = WorkOrderEvent(
        work_order_id=wo.id,
        event_type=WorkOrderEventType.CREATED,
        actor_id=user.id,
        details={"comment": "Work order created"},
    )
    now = datetime.now(timezone.utc)
    history = WorkHistory(
        equipment_id=equipment.id,
        work_order_id=wo.id,
        title=wo.title,
        type=WorkOrderType.REPAIR,
        completed_at=now,
        closed_at=now,
        assignee_id=user.id,
        closed_by=user.id,
        result="Successfully inspected",
        checklist_snapshot=[{"description": "Check oil level", "is_checked": True}],
    )
    db_session.add_all([item, event, history])
    await db_session.commit()
    await db_session.refresh(item)
    await db_session.refresh(event)
    await db_session.refresh(history)

    assert item.is_checked is False
    assert event.event_type == WorkOrderEventType.CREATED
    assert history.title == "Check pump vibration"
    assert len(history.checklist_snapshot) == 1
