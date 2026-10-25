from datetime import date, datetime, timezone
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.notification import Notification, NotificationType
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderStatus
from app.services.equipment_service import get_company_today


def _get_insert_class(session: AsyncSession):
    dialect_name = getattr(getattr(session, "bind", None), "dialect", None)
    name = dialect_name.name if dialect_name else ""
    if not name and hasattr(session, "get_bind"):
        try:
            bind = session.get_bind()
            if bind and hasattr(bind, "dialect"):
                name = bind.dialect.name
        except Exception:
            pass
    if name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    return dialect_insert


async def generate_maintenance_notifications(ctx: dict[str, Any]) -> int:
    session: AsyncSession = ctx.get("session")
    should_close = False
    if session is None:
        session_maker = ctx.get("session_maker")
        if session_maker:
            session = session_maker()
            should_close = True
        else:
            raise ValueError("No session or session_maker in worker context")

    try:
        company_today = get_company_today()

        # 1. Fetch active schedules
        sched_q = (
            select(MaintenanceSchedule)
            .options(
                selectinload(MaintenanceSchedule.plan),
                selectinload(MaintenanceSchedule.equipment),
            )
            .where(MaintenanceSchedule.is_active == True)
        )
        schedules = (await session.execute(sched_q)).scalars().all()

        # 2. Fetch all active engineers
        engineers_q = select(User).where(
            User.role == UserRole.ENGINEER,
            User.status == UserStatus.ACTIVE,
        )
        engineers = list((await session.execute(engineers_q)).scalars().all())

        created_count = 0

        for sched in schedules:
            if not sched.plan or not sched.plan.is_active:
                continue
            if not sched.equipment or sched.equipment.archived_at is not None:
                continue

            # Check if current due date has already been completed or closed
            done_q = select(WorkOrder.id).where(
                WorkOrder.schedule_id == sched.id,
                WorkOrder.planned_due_on == sched.next_due_on,
                WorkOrder.status.in_([WorkOrderStatus.COMPLETED, WorkOrderStatus.CLOSED]),
            )
            done = (await session.execute(done_q)).first()
            if done:
                continue

            days_until = (sched.next_due_on - company_today).days
            if 1 <= days_until <= 3:
                notif_type = NotificationType.THREE_DAYS_BEFORE
                message = f"Maintenance for {sched.equipment.name} is due in {days_until} days ({sched.next_due_on})"
            elif days_until <= 0:
                notif_type = NotificationType.ON_DUE_DATE
                message = f"Maintenance for {sched.equipment.name} is due today ({sched.next_due_on})"
            else:
                continue

            # Build recipients for this schedule: all active engineers + assigned active technician
            recipients = list(engineers)

            tech_q = (
                select(User)
                .join(WorkOrder, WorkOrder.assignee_id == User.id)
                .where(
                    WorkOrder.schedule_id == sched.id,
                    WorkOrder.status.in_([WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS]),
                    User.role == UserRole.TECHNICIAN,
                    User.status == UserStatus.ACTIVE,
                )
            )
            assigned_tech = (await session.execute(tech_q)).scalars().first()
            if assigned_tech and assigned_tech.id not in [r.id for r in recipients]:
                recipients.append(assigned_tech)

            insert_fn = _get_insert_class(session)
            now = datetime.now(timezone.utc)
            for recipient in recipients:
                stmt = (
                    insert_fn(Notification)
                    .values(
                        id=uuid.uuid4(),
                        recipient_id=recipient.id,
                        plan_id=sched.plan_id,
                        schedule_id=sched.id,
                        equipment_id=sched.equipment_id,
                        planned_due_on=sched.next_due_on,
                        type=notif_type,
                        message=message,
                        created_at=now,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["schedule_id", "planned_due_on", "type", "recipient_id"]
                    )
                )
                res = await session.execute(stmt)
                if res.rowcount and res.rowcount > 0:
                    created_count += res.rowcount

        if created_count > 0:
            await session.commit()

        return created_count

    finally:
        if should_close and session is not None:
            await session.close()
