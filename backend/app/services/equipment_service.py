import uuid
import zoneinfo
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import escape_like, is_unique_violation, locked, pairing_lock
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder
from app.errors.exceptions import AppException
from app.schemas.equipment import EquipmentCreate, EquipmentPatch


def get_company_today() -> date:
    tz = zoneinfo.ZoneInfo(settings.app.COMPANY_TIMEZONE)
    return datetime.now(tz).date()


get_local_today = get_company_today


class EquipmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_equipment(
        self,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
        status_filter: EquipmentStatus | None = None,
        category: str | None = None,
        location: str | None = None,
        include_archived: bool = False,
        q: str | None = None,
    ) -> tuple[list[Equipment], int]:
        if include_archived and current_user.role != UserRole.ENGINEER:
            raise AppException(
                status=403,
                code="ACCESS_DENIED",
                title="Access Denied",
                detail="Only engineers can view archived equipment.",
            )

        stmt = select(Equipment)
        count_stmt = select(func.count(Equipment.id))

        if not include_archived:
            stmt = stmt.where(Equipment.archived_at.is_(None))
            count_stmt = count_stmt.where(Equipment.archived_at.is_(None))

        if current_user.role == UserRole.TECHNICIAN:
            # Technician sees only equipment related to their current assignments
            assigned_equipment = select(WorkOrder.equipment_id).where(WorkOrder.assignee_id == current_user.id)
            stmt = stmt.where(Equipment.id.in_(assigned_equipment))
            count_stmt = count_stmt.where(Equipment.id.in_(assigned_equipment))

        if status_filter is not None:
            stmt = stmt.where(Equipment.status == status_filter)
            count_stmt = count_stmt.where(Equipment.status == status_filter)

        if category is not None and category.strip():
            stmt = stmt.where(Equipment.category == category.strip())
            count_stmt = count_stmt.where(Equipment.category == category.strip())

        if location is not None and location.strip():
            stmt = stmt.where(Equipment.location == location.strip())
            count_stmt = count_stmt.where(Equipment.location == location.strip())

        if q is not None and q.strip():
            escaped = f"%{escape_like(q.strip().lower())}%"
            filter_expr = func.lower(Equipment.name).like(escaped, escape="\\") | func.lower(
                Equipment.inventory_number
            ).like(escaped, escape="\\")
            stmt = stmt.where(filter_expr)
            count_stmt = count_stmt.where(filter_expr)

        stmt = stmt.order_by(Equipment.name.asc(), Equipment.id.asc()).offset(offset).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total

    async def get_equipment_by_id(self, equipment_id: uuid.UUID, current_user: User) -> Equipment:
        stmt = select(Equipment).where(Equipment.id == equipment_id)
        res = await self.session.execute(stmt)
        eq = res.scalar_one_or_none()

        if eq is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Equipment Not Found",
                detail=f"Equipment with id '{equipment_id}' does not exist.",
            )

        if eq.archived_at is not None and current_user.role != UserRole.ENGINEER:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Equipment Not Found",
                detail=f"Equipment with id '{equipment_id}' does not exist.",
            )

        if current_user.role == UserRole.TECHNICIAN:
            # Technician sees only equipment related to their current assignments
            has_assigned = (
                await self.session.execute(
                    select(func.count(WorkOrder.id)).where(
                        WorkOrder.equipment_id == eq.id,
                        WorkOrder.assignee_id == current_user.id,
                    )
                )
            ).scalar_one()
            if not has_assigned:
                raise AppException(
                    status=404,
                    code="NOT_FOUND",
                    title="Equipment Not Found",
                    detail=f"Equipment with id '{equipment_id}' does not exist.",
                )

        return eq

    async def create_equipment(self, payload: EquipmentCreate) -> Equipment:
        await pairing_lock(self.session)
        local_today = get_local_today()
        if payload.commissioned_on > local_today:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail="commissioned_on date cannot be in the future.",
            )

        inv = payload.inventory_number.strip()
        stmt = select(Equipment).where(func.lower(Equipment.inventory_number) == inv.lower())
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise AppException(
                status=409,
                code="EQUIPMENT_ALREADY_EXISTS",
                title="Conflict",
                detail=f"Equipment with inventory number '{payload.inventory_number}' already exists.",
            )

        eq = Equipment(
            name=payload.name.strip(),
            inventory_number=inv,
            category=payload.category.strip(),
            location=payload.location.strip(),
            commissioned_on=payload.commissioned_on,
            status=payload.status if payload.status is not None else EquipmentStatus.OPERATIONAL,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(eq)
                await self.session.flush()
        except IntegrityError as exc:
            if is_unique_violation(exc, "uq_equipment_inventory_number"):
                raise AppException(
                    status=409,
                    code="EQUIPMENT_ALREADY_EXISTS",
                    title="Conflict",
                    detail=f"Equipment with inventory number '{payload.inventory_number}' already exists.",
                ) from exc
            raise

        from app.services.maintenance_service import MaintenanceService

        m_service = MaintenanceService(self.session)
        await m_service.sync_equipment_schedules(eq)

        await self.session.commit()
        await self.session.refresh(eq)
        return eq

    async def update_equipment(
        self,
        equipment_id: uuid.UUID,
        expected_version: int,
        payload: EquipmentPatch,
        current_user: User,
    ) -> Equipment:
        if payload.category is not None:
            await pairing_lock(self.session)
        await self.get_equipment_by_id(equipment_id, current_user)
        stmt = locked(select(Equipment).where(Equipment.id == equipment_id))
        res = await self.session.execute(stmt)
        eq = res.scalar_one_or_none()
        if eq is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Equipment Not Found",
                detail=f"Equipment with id '{equipment_id}' does not exist.",
            )

        # Порядок проверок: precondition (412) раньше бизнес-правил (409).
        if eq.version != expected_version:
            raise AppException(
                status=412,
                code="VERSION_CONFLICT",
                title="Version Conflict",
                detail=f"Resource version {eq.version} does not match expected {expected_version}.",
            )

        if eq.archived_at is not None:
            raise AppException(
                status=409,
                code="EQUIPMENT_ARCHIVED",
                title="Conflict",
                detail="Archived equipment cannot be edited.",
            )

        has_changes = False
        if payload.name is not None and payload.name.strip() != eq.name:
            eq.name = payload.name.strip()
            has_changes = True

        if payload.inventory_number is not None:
            inv = payload.inventory_number.strip()
            if inv.lower() != eq.inventory_number.lower():
                dup_stmt = select(Equipment).where(
                    func.lower(Equipment.inventory_number) == inv.lower(),
                    Equipment.id != equipment_id,
                )
                duplicate = (await self.session.execute(dup_stmt)).scalar_one_or_none()
                if duplicate is not None:
                    raise AppException(
                        status=409,
                        code="EQUIPMENT_ALREADY_EXISTS",
                        title="Conflict",
                        detail=f"Equipment with inventory number '{payload.inventory_number}' already exists.",
                    )
                eq.inventory_number = inv
                has_changes = True

        if payload.commissioned_on is not None and payload.commissioned_on != eq.commissioned_on:
            if payload.commissioned_on > get_local_today():
                raise AppException(
                    status=422,
                    code="VALIDATION_ERROR",
                    title="Validation Error",
                    detail="commissioned_on date cannot be in the future.",
                )
            eq.commissioned_on = payload.commissioned_on
            has_changes = True

        if payload.location is not None and payload.location.strip() != eq.location:
            eq.location = payload.location.strip()
            has_changes = True

        if payload.status is not None and payload.status != eq.status:
            eq.status = payload.status
            has_changes = True

        if payload.category is not None and payload.category.strip() != eq.category:
            from app.db.models.work_order import WorkOrder, WorkOrderStatus, WorkOrderType

            uncompleted = [
                WorkOrderStatus.CREATED,
                WorkOrderStatus.ASSIGNED,
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.COMPLETED,
            ]
            wo_stmt = select(func.count(WorkOrder.id)).where(
                WorkOrder.equipment_id == equipment_id,
                WorkOrder.type == WorkOrderType.PLANNED,
                WorkOrder.status.in_(uncompleted),
            )
            if ((await self.session.execute(wo_stmt)).scalar() or 0) > 0:
                raise AppException(
                    status=409,
                    code="ACTIVE_MAINTENANCE_WORK",
                    title="Active Maintenance Work",
                    detail="Cannot change equipment category with active planned work orders.",
                )

            eq.category = payload.category.strip()
            has_changes = True

            from app.services.maintenance_service import MaintenanceService

            await MaintenanceService(self.session).sync_equipment_schedules(eq)

        if has_changes:
            eq.version += 1
            try:
                await self.session.commit()
            except IntegrityError as exc:
                await self.session.rollback()
                if is_unique_violation(exc, "uq_equipment_inventory_number"):
                    raise AppException(
                        status=409,
                        code="EQUIPMENT_ALREADY_EXISTS",
                        title="Conflict",
                        detail=f"Equipment with inventory number '{payload.inventory_number}' already exists.",
                    ) from exc
                raise
            await self.session.refresh(eq)

        return eq

    async def archive_equipment(self, equipment_id: uuid.UUID, current_user: User) -> Equipment:
        await pairing_lock(self.session)
        await self.get_equipment_by_id(equipment_id, current_user)

        # Блокировка строки оборудования сериализует архивацию с созданием заявок:
        # проверка незавершённых нарядов и запись archived_at выполняются под ней.
        stmt = locked(select(Equipment).where(Equipment.id == equipment_id))
        eq = (await self.session.execute(stmt)).scalar_one_or_none()
        if eq is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Equipment Not Found",
                detail=f"Equipment with id '{equipment_id}' does not exist.",
            )
        if eq.archived_at is not None:
            raise AppException(
                status=409,
                code="ALREADY_ARCHIVED",
                title="Conflict",
                detail="Equipment is already archived.",
            )

        from app.db.models.work_order import WorkOrder, WorkOrderStatus

        uncompleted = [
            WorkOrderStatus.CREATED,
            WorkOrderStatus.ASSIGNED,
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.COMPLETED,
        ]
        wo_stmt = select(func.count(WorkOrder.id)).where(
            WorkOrder.equipment_id == equipment_id,
            WorkOrder.status.in_(uncompleted),
        )
        if ((await self.session.execute(wo_stmt)).scalar() or 0) > 0:
            raise AppException(
                status=409,
                code="ACTIVE_WORK_ORDERS",
                title="Conflict",
                detail="Cannot archive equipment with uncompleted work orders.",
            )

        eq.archived_at = datetime.now(UTC)
        eq.version += 1
        self.session.add(eq)

        from app.services.maintenance_service import MaintenanceService

        await MaintenanceService(self.session).sync_equipment_schedules(eq)

        await self.session.commit()
        await self.session.refresh(eq)
        return eq

    async def restore_equipment(self, equipment_id: uuid.UUID, current_user: User) -> Equipment:
        await pairing_lock(self.session)
        await self.get_equipment_by_id(equipment_id, current_user)

        stmt = locked(select(Equipment).where(Equipment.id == equipment_id))
        eq = (await self.session.execute(stmt)).scalar_one_or_none()
        if eq is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Equipment Not Found",
                detail=f"Equipment with id '{equipment_id}' does not exist.",
            )
        if eq.archived_at is None:
            raise AppException(
                status=409,
                code="NOT_ARCHIVED",
                title="Conflict",
                detail="Equipment is not archived.",
            )

        eq.archived_at = None
        eq.status = EquipmentStatus.OUT_OF_SERVICE
        eq.version += 1
        self.session.add(eq)

        from app.services.maintenance_service import MaintenanceService

        await MaintenanceService(self.session).sync_equipment_schedules(eq)

        await self.session.commit()
        await self.session.refresh(eq)
        return eq
