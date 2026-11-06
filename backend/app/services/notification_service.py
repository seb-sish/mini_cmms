import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.notification import Notification, NotificationType
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_order import WorkOrder, WorkOrderStatus
from app.errors.handlers import AppException


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


class NotificationService:
    @classmethod
    async def generate(
        cls,
        session: AsyncSession,
        company_today: date,
        *,
        plan_id: uuid.UUID | None = None,
        equipment_id: uuid.UUID | None = None,
        schedule_id: uuid.UUID | None = None,
    ) -> int:
        await session.flush()
        # 1. Fetch active schedules
        sched_q = (
            select(MaintenanceSchedule)
            .options(
                selectinload(MaintenanceSchedule.plan),
                selectinload(MaintenanceSchedule.equipment),
            )
            .where(MaintenanceSchedule.is_active.is_(True))
        )
        if plan_id is not None:
            sched_q = sched_q.where(MaintenanceSchedule.plan_id == plan_id)
        if equipment_id is not None:
            sched_q = sched_q.where(MaintenanceSchedule.equipment_id == equipment_id)
        if schedule_id is not None:
            sched_q = sched_q.where(MaintenanceSchedule.id == schedule_id)
        schedules = (await session.execute(sched_q.order_by(MaintenanceSchedule.id))).scalars().all()

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
                message = f"ТО оборудования «{sched.equipment.name}» через {days_until} дн. ({sched.next_due_on:%d.%m.%Y})"
            elif days_until <= 0:
                notif_type = NotificationType.ON_DUE_DATE
                message = f"Срок ТО оборудования «{sched.equipment.name}»: {sched.next_due_on:%d.%m.%Y}"
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
            now = datetime.now(UTC)
            # Worker и API берут уникальные ключи в одном порядке, исключая взаимную блокировку.
            for recipient in sorted(recipients, key=lambda person: person.id):
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
                    .on_conflict_do_nothing(index_elements=["schedule_id", "planned_due_on", "type", "recipient_id"])
                )
                res = await session.execute(stmt)
                if res.rowcount and res.rowcount > 0:
                    created_count += res.rowcount

        return created_count

    @classmethod
    async def list_notifications(
        cls,
        session: AsyncSession,
        current_user: User,
        type: NotificationType | None = None,
        limit: int = 20,
        offset: int = 0,
        planned_due_on: date | None = None,
    ) -> tuple[list[Notification], int]:
        if current_user.role not in (UserRole.ENGINEER, UserRole.TECHNICIAN):
            raise AppException(403, "ACCESS_DENIED", "Access denied to notifications")

        conditions = [Notification.recipient_id == current_user.id]
        if type:
            conditions.append(Notification.type == type)
        if planned_due_on is not None:
            conditions.append(Notification.planned_due_on == planned_due_on)

        count_q = select(func.count(Notification.id)).where(*conditions)
        total = (await session.execute(count_q)).scalar() or 0

        q = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = (await session.execute(q)).scalars().all()
        return list(items), total

    @classmethod
    async def get_notification(
        cls, session: AsyncSession, current_user: User, notification_id: uuid.UUID
    ) -> Notification:
        if current_user.role not in (UserRole.ENGINEER, UserRole.TECHNICIAN):
            raise AppException(403, "ACCESS_DENIED", "Access denied to notifications")

        notif = await session.get(Notification, notification_id)
        if not notif or notif.recipient_id != current_user.id:
            raise AppException(404, "NOT_FOUND", "Notification not found")

        return notif
