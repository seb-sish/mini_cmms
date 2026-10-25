import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import escape_like, locked
from app.db.models.equipment import Equipment
from app.db.models.fault import Fault, FaultSeverity, FaultStatus
from app.db.models.user import User, UserRole
from app.errors.exceptions import AppException
from app.schemas.fault import FaultCreate, FaultPatch
from app.services.equipment_service import get_local_today


class FaultService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_faults(
        self,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
        equipment_id: uuid.UUID | None = None,
        status_filter: FaultStatus | None = None,
        severity_filter: FaultSeverity | None = None,
        author_id: uuid.UUID | None = None,
        detected_from: date | None = None,
        detected_to: date | None = None,
        q: str | None = None,
    ) -> tuple[list[Fault], int]:
        if detected_from and detected_to and detected_from > detected_to:
            raise AppException(
                status=422,
                code="INVALID_DATE_RANGE",
                title="Invalid Date Range",
                detail="detected_from cannot be greater than detected_to.",
            )

        stmt = select(Fault)
        count_stmt = select(func.count(Fault.id))

        # Role-based visibility
        if current_user.role == UserRole.OPERATOR:
            stmt = stmt.where(Fault.author_id == current_user.id)
            count_stmt = count_stmt.where(Fault.author_id == current_user.id)
        elif current_user.role == UserRole.TECHNICIAN:
            from app.db.models.work_order import WorkOrder

            tech_wo_subq = select(WorkOrder.fault_id).where(
                WorkOrder.assignee_id == current_user.id,
                WorkOrder.fault_id.is_not(None),
            )
            stmt = stmt.where(Fault.id.in_(tech_wo_subq))
            count_stmt = count_stmt.where(Fault.id.in_(tech_wo_subq))

        if equipment_id is not None:
            stmt = stmt.where(Fault.equipment_id == equipment_id)
            count_stmt = count_stmt.where(Fault.equipment_id == equipment_id)
        if status_filter is not None:
            stmt = stmt.where(Fault.status == status_filter)
            count_stmt = count_stmt.where(Fault.status == status_filter)
        if severity_filter is not None:
            stmt = stmt.where(Fault.severity == severity_filter)
            count_stmt = count_stmt.where(Fault.severity == severity_filter)
        if author_id is not None:
            stmt = stmt.where(Fault.author_id == author_id)
            count_stmt = count_stmt.where(Fault.author_id == author_id)
        if detected_from is not None:
            stmt = stmt.where(Fault.detected_on >= detected_from)
            count_stmt = count_stmt.where(Fault.detected_on >= detected_from)
        if detected_to is not None:
            stmt = stmt.where(Fault.detected_on <= detected_to)
            count_stmt = count_stmt.where(Fault.detected_on <= detected_to)

        if q is not None and q.strip():
            escaped = f"%{escape_like(q.strip().lower())}%"
            stmt = stmt.where(func.lower(Fault.description).like(escaped, escape="\\"))
            count_stmt = count_stmt.where(func.lower(Fault.description).like(escaped, escape="\\"))

        # Ordering per spec Q17/Design Notes: detected_on DESC, id DESC
        stmt = stmt.order_by(Fault.detected_on.desc(), Fault.id.desc()).offset(offset).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total

    async def get_fault_by_id(self, fault_id: uuid.UUID, current_user: User) -> Fault:
        stmt = select(Fault).where(Fault.id == fault_id)
        res = await self.session.execute(stmt)
        fault = res.scalar_one_or_none()

        if fault is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Fault Not Found",
                detail=f"Fault with id '{fault_id}' does not exist.",
            )

        if current_user.role == UserRole.OPERATOR and fault.author_id != current_user.id:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Fault Not Found",
                detail=f"Fault with id '{fault_id}' does not exist.",
            )

        if current_user.role == UserRole.TECHNICIAN:
            from app.db.models.work_order import WorkOrder

            tech_wo_stmt = select(func.count(WorkOrder.id)).where(
                WorkOrder.assignee_id == current_user.id,
                WorkOrder.fault_id == fault.id,
            )
            count = (await self.session.execute(tech_wo_stmt)).scalar() or 0
            if count == 0:
                raise AppException(
                    status=404,
                    code="NOT_FOUND",
                    title="Fault Not Found",
                    detail=f"Fault with id '{fault_id}' does not exist.",
                )

        return fault

    async def create_fault(self, payload: FaultCreate, current_user: User) -> Fault:
        local_today = get_local_today()
        if payload.detected_on > local_today:
            raise AppException(
                status=422,
                code="FUTURE_DETECTED_DATE",
                title="Validation Error",
                detail="detected_on date cannot be in the future.",
            )

        # Check equipment exists and is not archived
        eq_stmt = select(Equipment).where(Equipment.id == payload.equipment_id)
        eq = (await self.session.execute(eq_stmt)).scalar_one_or_none()
        if eq is None or eq.archived_at is not None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Equipment Not Found",
                detail="Target equipment does not exist or is archived.",
            )

        desc = payload.description.strip()
        if not desc:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail="description cannot be empty.",
            )

        fault = Fault(
            equipment_id=payload.equipment_id,
            description=desc,
            detected_on=payload.detected_on,
            severity=payload.severity,
            status=FaultStatus.OPEN,
            author_id=current_user.id,
        )
        self.session.add(fault)
        await self.session.commit()
        await self.session.refresh(fault)
        return fault

    async def update_fault(
        self,
        fault_id: uuid.UUID,
        expected_version: int,
        payload: FaultPatch,
        current_user: User,
    ) -> Fault:
        await self.get_fault_by_id(fault_id, current_user)
        stmt = locked(select(Fault).where(Fault.id == fault_id))
        res = await self.session.execute(stmt)
        fault = res.scalar_one_or_none()
        if fault is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Fault Not Found",
                detail=f"Fault with id '{fault_id}' does not exist.",
            )

        # Only author (OPERATOR) or ENGINEER can update
        if current_user.role == UserRole.OPERATOR and fault.author_id != current_user.id:
            raise AppException(
                status=403,
                code="ACCESS_DENIED",
                title="Forbidden",
                detail="Operators can only edit faults they registered.",
            )

        # Порядок проверок: precondition (412) раньше бизнес-правил (409).
        if fault.version != expected_version:
            raise AppException(
                status=412,
                code="VERSION_CONFLICT",
                title="Version Conflict",
                detail=f"Resource version {fault.version} does not match expected {expected_version}.",
            )

        if fault.status != FaultStatus.OPEN:
            raise AppException(
                status=409,
                code="INVALID_FAULT_STATUS",
                title="Conflict",
                detail="Fault can only be edited while in OPEN status.",
            )

        from app.db.models.work_order import WorkOrder, WorkOrderStatus

        active_wo_stmt = select(func.count(WorkOrder.id)).where(
            WorkOrder.fault_id == fault.id,
            WorkOrder.status.in_(
                [
                    WorkOrderStatus.CREATED,
                    WorkOrderStatus.ASSIGNED,
                    WorkOrderStatus.IN_PROGRESS,
                    WorkOrderStatus.COMPLETED,
                ]
            ),
        )
        has_active_wo = ((await self.session.execute(active_wo_stmt)).scalar() or 0) > 0
        if has_active_wo:
            raise AppException(
                status=409,
                code="FAULT_HAS_ACTIVE_WORK_ORDER",
                title="Conflict",
                detail="Cannot edit fault with active work order.",
            )

        has_changes = False
        if payload.description is not None:
            desc = payload.description.strip()
            if desc and desc != fault.description:
                fault.description = desc
                has_changes = True

        if payload.severity is not None and payload.severity != fault.severity:
            fault.severity = payload.severity
            has_changes = True

        if payload.detected_on is not None and payload.detected_on != fault.detected_on:
            if payload.detected_on > get_local_today():
                raise AppException(
                    status=422,
                    code="FUTURE_DETECTED_DATE",
                    title="Validation Error",
                    detail="detected_on date cannot be in the future.",
                )
            fault.detected_on = payload.detected_on
            has_changes = True

        if has_changes:
            fault.version += 1
            await self.session.commit()
            await self.session.refresh(fault)

        return fault
