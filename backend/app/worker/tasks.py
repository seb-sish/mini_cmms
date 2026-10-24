from datetime import date, datetime, timezone
from typing import Any
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

        # 2. Fetch active engineers and technicians
        users_q = select(User).where(
            User.role.in_([UserRole.ENGINEER, UserRole.TECHNICIAN]),
            User.status == UserStatus.ACTIVE,
        )
        recipients = (await session.execute(users_q)).scalars().all()
        if not recipients:
            return 0

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

            for recipient in recipients:
                # Idempotency check: (schedule_id, planned_due_on, type, recipient_id)
                check_q = select(Notification.id).where(
                    Notification.schedule_id == sched.id,
                    Notification.planned_due_on == sched.next_due_on,
                    Notification.type == notif_type,
                    Notification.recipient_id == recipient.id,
                )
                existing = (await session.execute(check_q)).first()
                if existing:
                    continue

                notif = Notification(
                    recipient_id=recipient.id,
                    plan_id=sched.plan_id,
                    schedule_id=sched.id,
                    equipment_id=sched.equipment_id,
                    planned_due_on=sched.next_due_on,
                    type=notif_type,
                    message=message,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(notif)
                created_count += 1

        if created_count > 0:
            await session.commit()

        return created_count

    finally:
        if should_close and session is not None:
            await session.close()
