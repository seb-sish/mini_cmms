from app.services.equipment_service import get_company_today
import zoneinfo
from app.config import settings
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import uuid
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.equipment import Equipment
from app.db.models.fault import Fault, FaultStatus
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.user import User, UserRole, UserStatus
from app.db.models.work_history import WorkHistory
from app.db.models.work_order import (
    WorkChecklistItem,
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
    WorkOrderType,
)
from app.db.models.work_order_event import WorkOrderEvent, WorkOrderEventType
from app.errors.handlers import AppException
from app.schemas.work_order import WorkOrderCreate, WorkOrderPatch

ACTIVE_STATUSES = [
    WorkOrderStatus.CREATED,
    WorkOrderStatus.ASSIGNED,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.COMPLETED,
]

STATUS_RANK_ASC = {
    WorkOrderStatus.CREATED: 0,
    WorkOrderStatus.ASSIGNED: 1,
    WorkOrderStatus.IN_PROGRESS: 2,
    WorkOrderStatus.COMPLETED: 3,
    WorkOrderStatus.CLOSED: 4,
    WorkOrderStatus.CANCELLED: 5,
}

STATUS_RANK_DESC = {
    WorkOrderStatus.CANCELLED: 0,
    WorkOrderStatus.CLOSED: 1,
    WorkOrderStatus.COMPLETED: 2,
    WorkOrderStatus.IN_PROGRESS: 3,
    WorkOrderStatus.ASSIGNED: 4,
    WorkOrderStatus.CREATED: 5,
}

class WorkOrderService:
    @staticmethod
    async def generate_work_order_number(session: AsyncSession) -> str:
        now = datetime.now(timezone.utc)
        suffix = f"{now.strftime('%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
        return f"WO-{now.strftime('%Y%m%d')}-{suffix}"

    @classmethod
    async def create_work_order(
        cls, session: AsyncSession, current_user: User, data: WorkOrderCreate
    ) -> WorkOrder:
        if current_user.role == UserRole.OPERATOR:
            if data.type != WorkOrderType.REPAIR:
                raise AppException(403, "ACCESS_DENIED", "Operators can only create REPAIR work orders")
        elif current_user.role != UserRole.ENGINEER:
            raise AppException(403, "ACCESS_DENIED", "Insufficient permissions to create work order")

        equipment = await session.get(Equipment, data.equipment_id)
        if not equipment:
            raise AppException(404, "NOT_FOUND", "Equipment not found")
        if equipment.archived_at is not None:
            raise AppException(409, "EQUIPMENT_ARCHIVED", "Equipment is archived")

        planned_due_on = None
        checklist_templates = []

        if data.type == WorkOrderType.REPAIR:
            if data.schedule_id is not None:
                raise AppException(422, "VALIDATION_ERROR", "schedule_id forbidden for REPAIR")
            if data.fault_id is not None:
                fault = await session.get(Fault, data.fault_id)
                if not fault:
                    raise AppException(404, "NOT_FOUND", "Fault not found")
                if fault.equipment_id != equipment.id:
                    raise AppException(422, "EQUIPMENT_MISMATCH", "Fault does not match equipment")

                dup_q = select(WorkOrder).where(
                    WorkOrder.fault_id == fault.id,
                    WorkOrder.status.in_(ACTIVE_STATUSES),
                )
                existing = (await session.execute(dup_q)).scalars().first()
                if existing:
                    raise AppException(409, "DUPLICATE_ACTIVE_WORK_ORDER", "Active work order exists for this fault")

                if fault.status == FaultStatus.OPEN:
                    fault.status = FaultStatus.IN_PROGRESS
                    fault.version += 1
                    session.add(fault)

        elif data.type == WorkOrderType.PLANNED:
            if data.schedule_id is None:
                raise AppException(422, "VALIDATION_ERROR", "schedule_id required for PLANNED")
            if data.fault_id is not None:
                raise AppException(422, "VALIDATION_ERROR", "fault_id forbidden for PLANNED")

            schedule = await session.get(MaintenanceSchedule, data.schedule_id)
            if not schedule:
                raise AppException(404, "NOT_FOUND", "Maintenance schedule not found")
            if schedule.equipment_id != equipment.id:
                raise AppException(422, "EQUIPMENT_MISMATCH", "Schedule does not match equipment")

            plan = await session.get(MaintenancePlan, schedule.plan_id)
            if not plan or not plan.is_active or not schedule.is_active:
                raise AppException(409, "INACTIVE_MAINTENANCE_SCHEDULE", "Schedule or plan is inactive")

            dup_q = select(WorkOrder).where(
                WorkOrder.schedule_id == schedule.id,
                WorkOrder.status.in_(ACTIVE_STATUSES),
            )
            existing = (await session.execute(dup_q)).scalars().first()
            if existing:
                raise AppException(409, "DUPLICATE_PLANNED_WORK_ORDER", "Active planned work order exists for this schedule")

            planned_due_on = schedule.next_due_on
            checklist_templates = plan.checklist or []

        number = await cls.generate_work_order_number(session)

        wo = WorkOrder(
            number=number,
            type=data.type,
            status=WorkOrderStatus.CREATED,
            title=data.title,
            description=data.description,
            priority=data.priority,
            equipment_id=equipment.id,
            fault_id=data.fault_id,
            schedule_id=data.schedule_id,
            planned_due_on=planned_due_on,
            author_id=current_user.id,
            version=1,
        )
        session.add(wo)
        await session.flush()

        for item in checklist_templates:
            chk = WorkChecklistItem(
                work_order_id=wo.id,
                order=item["order"],
                title=item.get("title") or item.get("description", "Task"),
                required=item.get("required", item.get("is_required", True)),
                checked=False,
            )
            session.add(chk)

        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.CREATED,
            actor_id=current_user.id,
            to_status=WorkOrderStatus.CREATED,
            details="Work order created",
        )
        session.add(event)

        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def list_work_orders(
        cls,
        session: AsyncSession,
        current_user: User,
        equipment_id: Optional[uuid.UUID] = None,
        type: Optional[WorkOrderType] = None,
        status: Optional[WorkOrderStatus] = None,
        priority: Optional[WorkOrderPriority] = None,
        assignee_id: Optional[uuid.UUID] = None,
        fault_id: Optional[uuid.UUID] = None,
        schedule_id: Optional[uuid.UUID] = None,
        q: Optional[str] = None,
        sort: str = "-created_at",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[WorkOrder], int]:
        if current_user.role == UserRole.TECHNICIAN:
            assignee_id = current_user.id
        elif current_user.role not in (UserRole.ENGINEER, UserRole.OPERATOR):
            raise AppException(403, "ACCESS_DENIED", "Access denied")

        conditions = []
        if equipment_id:
            conditions.append(WorkOrder.equipment_id == equipment_id)
        if type:
            conditions.append(WorkOrder.type == type)
        if status:
            conditions.append(WorkOrder.status == status)
        if priority:
            conditions.append(WorkOrder.priority == priority)
        if assignee_id:
            conditions.append(WorkOrder.assignee_id == assignee_id)
        if fault_id:
            conditions.append(WorkOrder.fault_id == fault_id)
        if schedule_id:
            conditions.append(WorkOrder.schedule_id == schedule_id)
        if current_user.role == UserRole.OPERATOR:
            conditions.append(WorkOrder.author_id == current_user.id)

        if q and q.strip():
            clean_q = q.strip()
            escaped_q = clean_q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped_q}%"
            conditions.append(
                or_(
                    WorkOrder.number.ilike(pattern, escape="\\"),
                    WorkOrder.title.ilike(pattern, escape="\\"),
                    WorkOrder.description.ilike(pattern, escape="\\"),
                )
            )

        count_q = select(func.count(WorkOrder.id))
        if conditions:
            count_q = count_q.where(*conditions)
        total = (await session.execute(count_q)).scalar() or 0

        query = (
            select(WorkOrder)
            .options(
                selectinload(WorkOrder.checklist),
                selectinload(WorkOrder.events),
            )
        )
        if conditions:
            query = query.where(*conditions)

        if sort == "created_at":
            query = query.order_by(WorkOrder.created_at.asc(), WorkOrder.id.asc())
        elif sort == "-created_at":
            query = query.order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
        elif sort == "status":
            case_stmt = case(STATUS_RANK_ASC, value=WorkOrder.status)
            query = query.order_by(case_stmt.asc(), WorkOrder.created_at.desc(), WorkOrder.id.desc())
        elif sort == "-status":
            case_stmt = case(STATUS_RANK_DESC, value=WorkOrder.status)
            query = query.order_by(case_stmt.asc(), WorkOrder.created_at.desc(), WorkOrder.id.desc())
        else:
            raise AppException(422, "VALIDATION_ERROR", f"Invalid sort parameter: {sort}")

        query = query.offset(offset).limit(limit)
        items = (await session.execute(query)).scalars().all()
        return list(items), total

    @classmethod
    async def get_work_order(
        cls, session: AsyncSession, current_user: User, work_order_id: uuid.UUID
    ) -> WorkOrder:
        query = (
            select(WorkOrder)
            .options(
                selectinload(WorkOrder.checklist),
                selectinload(WorkOrder.events),
            )
            .where(WorkOrder.id == work_order_id)
        )
        wo = (await session.execute(query)).scalars().first()
        if not wo:
            raise AppException(404, "NOT_FOUND", "Work order not found")

        # Access check
        if current_user.role == UserRole.TECHNICIAN:
            if wo.assignee_id != current_user.id:
                raise AppException(404, "NOT_FOUND", "Work order not found")
        elif current_user.role == UserRole.OPERATOR:
            if wo.author_id != current_user.id:
                raise AppException(404, "NOT_FOUND", "Work order not found")

        return wo

    @classmethod
    async def get_work_order_for_update(cls, session: AsyncSession, work_order_id: uuid.UUID) -> WorkOrder:
        query = (
            select(WorkOrder)
            .options(
                selectinload(WorkOrder.checklist),
                selectinload(WorkOrder.events),
            )
            .where(WorkOrder.id == work_order_id)
            .with_for_update()
        )
        wo = (await session.execute(query)).scalars().first()
        if not wo:
            raise AppException(404, "NOT_FOUND", "Work order not found")
        return wo

    @classmethod
    async def patch_work_order(
        cls,
        session: AsyncSession,
        current_user: User,
        work_order_id: uuid.UUID,
        expected_version: int,
        payload: WorkOrderPatch,
    ) -> WorkOrder:
        wo = await cls.get_work_order_for_update(session, work_order_id)
        if wo.version != expected_version:
            raise AppException(412, "VERSION_CONFLICT", "ETag mismatch")

        if wo.status != WorkOrderStatus.CREATED:
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Cannot patch work order after assignment")

        if payload.title is not None:
            wo.title = payload.title
        if payload.description is not None:
            wo.description = payload.description
        if payload.priority is not None:
            wo.priority = payload.priority

        wo.version += 1
        session.add(wo)
        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def assign_work_order(
        cls, session: AsyncSession, current_user: User, work_order_id: uuid.UUID, assignee_id: uuid.UUID
    ) -> WorkOrder:
        if current_user.role != UserRole.ENGINEER:
            raise AppException(403, "ACCESS_DENIED", "Only engineer can assign work orders")

        wo = await cls.get_work_order_for_update(session, work_order_id)

        if wo.status != WorkOrderStatus.CREATED:
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Can only assign work orders in CREATED state")

        tech = await session.get(User, assignee_id)
        if not tech or tech.role != UserRole.TECHNICIAN or tech.status != UserStatus.ACTIVE:
            raise AppException(422, "INVALID_ASSIGNEE", "Assignee must be an active technician")

        wo.assignee_id = tech.id
        wo.status = WorkOrderStatus.ASSIGNED
        wo.version += 1

        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.ASSIGNED,
            actor_id=current_user.id,
            from_status=WorkOrderStatus.CREATED,
            to_status=WorkOrderStatus.ASSIGNED,
            new_assignee_id=tech.id,
            details=f"Assigned to {tech.full_name}",
        )
        session.add(event)
        session.add(wo)
        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def reassign_work_order(
        cls, session: AsyncSession, current_user: User, work_order_id: uuid.UUID, assignee_id: uuid.UUID
    ) -> WorkOrder:
        if current_user.role != UserRole.ENGINEER:
            raise AppException(403, "ACCESS_DENIED", "Only engineer can reassign work orders")

        wo = await cls.get_work_order_for_update(session, work_order_id)

        if wo.status not in (WorkOrderStatus.ASSIGNED, WorkOrderStatus.IN_PROGRESS):
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Can only reassign ASSIGNED or IN_PROGRESS work orders")

        tech = await session.get(User, assignee_id)
        if not tech or tech.role != UserRole.TECHNICIAN or tech.status != UserStatus.ACTIVE:
            raise AppException(422, "INVALID_ASSIGNEE", "Assignee must be an active technician")

        if tech.id == wo.assignee_id:
            raise AppException(409, "SAME_ASSIGNEE", "Work order already assigned to this technician")

        old_assignee_id = wo.assignee_id
        wo.assignee_id = tech.id
        wo.version += 1

        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.REASSIGNED,
            actor_id=current_user.id,
            old_assignee_id=old_assignee_id,
            new_assignee_id=tech.id,
            details=f"Reassigned from {old_assignee_id} to {tech.full_name}",
        )
        session.add(event)
        session.add(wo)
        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def start_work_order(
        cls, session: AsyncSession, current_user: User, work_order_id: uuid.UUID
    ) -> WorkOrder:
        wo = await cls.get_work_order_for_update(session, work_order_id)

        if current_user.role == UserRole.TECHNICIAN and wo.assignee_id != current_user.id:
            raise AppException(404, "NOT_FOUND", "Work order not found")
        elif current_user.role != UserRole.TECHNICIAN:
            raise AppException(403, "ACCESS_DENIED", "Only assigned technician can start work order")

        if wo.status != WorkOrderStatus.ASSIGNED:
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Work order can only be started from ASSIGNED state")

        wo.status = WorkOrderStatus.IN_PROGRESS
        wo.started_at = datetime.now(timezone.utc)
        wo.version += 1

        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.STARTED,
            actor_id=current_user.id,
            from_status=WorkOrderStatus.ASSIGNED,
            to_status=WorkOrderStatus.IN_PROGRESS,
            details="Work started",
        )
        session.add(event)
        session.add(wo)
        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def check_item(
        cls,
        session: AsyncSession,
        current_user: User,
        work_order_id: uuid.UUID,
        item_id: uuid.UUID,
        checked: bool,
        comment: Optional[str],
        if_match: Optional[str],
    ) -> tuple[WorkChecklistItem, WorkOrder]:
        if not if_match:
            raise AppException(428, "PRECONDITION_REQUIRED", "If-Match header is required")

        wo = await cls.get_work_order_for_update(session, work_order_id)

        if current_user.role == UserRole.TECHNICIAN and wo.assignee_id != current_user.id:
            raise AppException(404, "NOT_FOUND", "Work order not found")
        elif current_user.role != UserRole.TECHNICIAN:
            raise AppException(403, "ACCESS_DENIED", "Only assigned technician can update checklist items")

        expected_etag = f"{wo.id}:{wo.version}"
        if if_match.strip('"') != expected_etag:
            raise AppException(412, "VERSION_CONFLICT", "ETag mismatch")

        if wo.status != WorkOrderStatus.IN_PROGRESS:
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Checklist can only be updated when IN_PROGRESS")

        item = await session.get(WorkChecklistItem, item_id)
        if not item or item.work_order_id != wo.id:
            raise AppException(404, "NOT_FOUND", "Checklist item not found")

        item.checked = checked
        item.checked_at = datetime.now(timezone.utc) if checked else None
        if comment is not None:
            item.comment = comment

        wo.version += 1
        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.CHECKLIST_ITEM_UPDATED,
            actor_id=current_user.id,
            details=f"Item {item.id} checked={checked}",
        )
        session.add(item)
        session.add(event)
        session.add(wo)
        await session.commit()
        await session.refresh(item)
        await session.refresh(wo)
        return item, wo

    @classmethod
    async def cancel_work_order(
        cls, session: AsyncSession, current_user: User, work_order_id: uuid.UUID, reason: str
    ) -> WorkOrder:
        if current_user.role != UserRole.ENGINEER:
            raise AppException(403, "ACCESS_DENIED", "Only engineer can cancel work order")

        wo = await cls.get_work_order_for_update(session, work_order_id)

        if wo.status not in (WorkOrderStatus.CREATED, WorkOrderStatus.ASSIGNED):
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Can only cancel CREATED or ASSIGNED work orders")

        prev_status = wo.status
        wo.status = WorkOrderStatus.CANCELLED
        wo.cancelled_at = datetime.now(timezone.utc)
        wo.cancelled_by = current_user.id
        wo.cancellation_reason = reason

        if wo.fault_id:
            fault = await session.get(Fault, wo.fault_id)
            if fault and fault.status == FaultStatus.IN_PROGRESS:
                fault.status = FaultStatus.OPEN
                fault.version += 1
                session.add(fault)

        wo.version += 1
        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.CANCELLED,
            actor_id=current_user.id,
            from_status=prev_status,
            to_status=WorkOrderStatus.CANCELLED,
            details=reason,
        )
        session.add(event)
        session.add(wo)
        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def complete_work_order(
        cls,
        session: AsyncSession,
        current_user: User,
        work_order_id: uuid.UUID,
        result: str,
        replaced_parts: list[str],
    ) -> WorkOrder:
        wo = await cls.get_work_order_for_update(session, work_order_id)

        if current_user.role == UserRole.TECHNICIAN and wo.assignee_id != current_user.id:
            raise AppException(404, "NOT_FOUND", "Work order not found")
        elif current_user.role != UserRole.TECHNICIAN:
            raise AppException(403, "ACCESS_DENIED", "Only assigned technician can complete work order")

        if wo.status != WorkOrderStatus.IN_PROGRESS:
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Work order must be IN_PROGRESS to complete")

        if wo.type == WorkOrderType.PLANNED:
            for item in wo.checklist:
                if item.required and not item.checked:
                    raise AppException(409, "INCOMPLETE_CHECKLIST", "Not all required checklist items are checked")

            schedule = await session.get(MaintenanceSchedule, wo.schedule_id)
            if schedule:
                plan = await session.get(MaintenancePlan, schedule.plan_id)
                company_today = get_company_today()
                if wo.planned_due_on and (company_today + timedelta(days=plan.interval_days) <= wo.planned_due_on):
                    raise AppException(409, "TOO_EARLY_TO_COMPLETE", "Completed too early before next schedule window")

        now = datetime.now(timezone.utc)
        wo.status = WorkOrderStatus.COMPLETED
        wo.completed_at = now
        wo.result = result
        wo.replaced_parts = replaced_parts or []
        wo.version += 1

        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.COMPLETED,
            actor_id=current_user.id,
            from_status=WorkOrderStatus.IN_PROGRESS,
            to_status=WorkOrderStatus.COMPLETED,
            details=result,
        )
        session.add(event)
        session.add(wo)
        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def close_work_order(
        cls,
        session: AsyncSession,
        current_user: User,
        work_order_id: uuid.UUID,
    ) -> WorkOrder:
        if current_user.role != UserRole.ENGINEER:
            raise AppException(403, "ACCESS_DENIED", "Only engineer can close work orders")

        wo = await cls.get_work_order_for_update(session, work_order_id)
        if wo.status != WorkOrderStatus.COMPLETED:
            raise AppException(409, "INVALID_WORK_ORDER_STATE", "Work order must be COMPLETED to close")

        now = datetime.now(timezone.utc)
        wo.status = WorkOrderStatus.CLOSED
        wo.closed_at = now
        wo.closed_by = current_user.id
        wo.version += 1

        if wo.fault_id:
            fault = await session.get(Fault, wo.fault_id)
            if fault and fault.status != FaultStatus.RESOLVED:
                fault.status = FaultStatus.RESOLVED
                fault.version += 1
                session.add(fault)

        schedule = None
        if wo.type == WorkOrderType.PLANNED and wo.schedule_id:
            schedule = await session.get(MaintenanceSchedule, wo.schedule_id)
            if schedule:
                if wo.completed_at:
                    c_dt = wo.completed_at
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    completed_date = c_dt.astimezone(zoneinfo.ZoneInfo(settings.app.COMPANY_TIMEZONE)).date()
                else:
                    completed_date = get_company_today()
                schedule.last_completed_on = completed_date
                plan = await session.get(MaintenancePlan, schedule.plan_id)
                interval = plan.interval_days if plan else 30
                schedule.next_due_on = completed_date + timedelta(days=interval)
                schedule.version += 1
                session.add(schedule)

        wh = WorkHistory(
            work_order_id=wo.id,
            equipment_id=wo.equipment_id,
            plan_id=schedule.plan_id if (wo.type == WorkOrderType.PLANNED and schedule) else None,
            fault_id=wo.fault_id,
            technician_id=wo.assignee_id,
            completed_at=wo.completed_at or now,
            closed_at=now,
            result=wo.result or "Work completed",
            replaced_parts=wo.replaced_parts or [],
            created_at=now,
        )
        session.add(wh)

        event = WorkOrderEvent(
            work_order_id=wo.id,
            event_type=WorkOrderEventType.CLOSED,
            actor_id=current_user.id,
            from_status=WorkOrderStatus.COMPLETED,
            to_status=WorkOrderStatus.CLOSED,
            details="Work order closed",
        )
        session.add(event)
        session.add(wo)
        await session.commit()
        return await cls.get_work_order(session, current_user, wo.id)

    @classmethod
    async def list_events(
        cls, session: AsyncSession, current_user: User, work_order_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[WorkOrderEvent], int]:
        await cls.get_work_order(session, current_user, work_order_id)

        count_q = select(func.count(WorkOrderEvent.id)).where(WorkOrderEvent.work_order_id == work_order_id)
        total = (await session.execute(count_q)).scalar() or 0

        q = (
            select(WorkOrderEvent)
            .where(WorkOrderEvent.work_order_id == work_order_id)
            .order_by(WorkOrderEvent.occurred_at.asc(), WorkOrderEvent.id.asc())
            .offset(offset)
            .limit(limit)
        )
        items = (await session.execute(q)).scalars().all()
        return list(items), total

class WorkHistoryService:
    @classmethod
    async def list_work_history(
        cls,
        session: AsyncSession,
        current_user: User,
        equipment_id: Optional[uuid.UUID] = None,
        technician_id: Optional[uuid.UUID] = None,
        completed_from: Optional[date] = None,
        completed_to: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[WorkHistory], int]:
        if current_user.role == UserRole.TECHNICIAN:
            technician_id = current_user.id
        elif current_user.role not in (UserRole.ENGINEER, UserRole.OPERATOR):
            raise AppException(403, "ACCESS_DENIED", "Access denied")

        conditions = []
        if equipment_id:
            conditions.append(WorkHistory.equipment_id == equipment_id)
        if technician_id:
            conditions.append(WorkHistory.technician_id == technician_id)
        if completed_from:
            conditions.append(func.date(WorkHistory.completed_at) >= completed_from)
        if completed_to:
            conditions.append(func.date(WorkHistory.completed_at) <= completed_to)

        if current_user.role == UserRole.OPERATOR:
            author_orders_subq = (
                select(WorkOrder.id)
                .where(WorkOrder.author_id == current_user.id)
                .scalar_subquery()
            )
            conditions.append(WorkHistory.work_order_id.in_(author_orders_subq))

        count_q = select(func.count(WorkHistory.id))
        if conditions:
            count_q = count_q.where(*conditions)
        total = (await session.execute(count_q)).scalar() or 0

        q = select(WorkHistory)
        if conditions:
            q = q.where(*conditions)
        q = q.order_by(WorkHistory.completed_at.desc(), WorkHistory.id.desc()).offset(offset).limit(limit)
        items = (await session.execute(q)).scalars().all()
        return list(items), total

    @classmethod
    async def get_work_history(
        cls, session: AsyncSession, current_user: User, history_id: uuid.UUID
    ) -> WorkHistory:
        wh = await session.get(WorkHistory, history_id)
        if not wh:
            raise AppException(404, "NOT_FOUND", "Work history entry not found")

        if current_user.role == UserRole.TECHNICIAN and wh.technician_id != current_user.id:
            raise AppException(404, "NOT_FOUND", "Work history entry not found")
        elif current_user.role == UserRole.OPERATOR:
            wo = await session.get(WorkOrder, wh.work_order_id)
            if not wo or wo.author_id != current_user.id:
                raise AppException(404, "NOT_FOUND", "Work history entry not found")
        elif current_user.role != UserRole.ENGINEER:
            raise AppException(403, "ACCESS_DENIED", "Access denied")

        return wh
