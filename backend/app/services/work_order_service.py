from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.equipment import Equipment
from app.db.models.fault import Fault, FaultStatus
from app.db.models.maintenance_plan import MaintenancePlan
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.user import User, UserRole
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

class WorkOrderService:
    @staticmethod
    async def generate_work_order_number(session: AsyncSession) -> str:
        year = datetime.now(timezone.utc).year
        prefix = f"WO-{year}-"
        query = select(func.count(WorkOrder.id)).where(WorkOrder.number.like(f"{prefix}%"))
        count = (await session.execute(query)).scalar() or 0
        return f"{prefix}{count + 1:04d}"

    @classmethod
    async def create_work_order(
        cls, session: AsyncSession, current_user: User, data: WorkOrderCreate
    ) -> WorkOrder:
        if current_user.role == UserRole.OPERATOR:
            if data.type != WorkOrderType.REPAIR:
                raise AppException(403, "ACCESS_DENIED", "Operators can only create REPAIR work orders")
        elif current_user.role not in (UserRole.ADMIN, UserRole.ENGINEER):
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

                # Check duplicate active work order for this fault
                dup_q = select(WorkOrder).where(
                    WorkOrder.fault_id == fault.id,
                    WorkOrder.status.in_(ACTIVE_STATUSES),
                )
                existing = (await session.execute(dup_q)).scalars().first()
                if existing:
                    raise AppException(409, "DUPLICATE_ACTIVE_WORK_ORDER", "Active work order exists for this fault")

                if fault.status == FaultStatus.OPEN:
                    fault.status = FaultStatus.IN_PROGRESS
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

            # Check duplicate active planned work order
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
                title=item["description"],
                required=item.get("is_required", True),
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
