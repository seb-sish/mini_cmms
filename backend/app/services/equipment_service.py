from datetime import date, datetime, timezone
from typing import Optional
import uuid
import zoneinfo
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models.equipment import Equipment, EquipmentStatus
from app.db.models.user import User, UserRole
from app.errors.exceptions import AppException
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate

def get_local_today() -> date:
    tz = zoneinfo.ZoneInfo(settings.app.COMPANY_TIMEZONE)
    return datetime.now(tz).date()

def escape_like(val: str) -> str:
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

class EquipmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_equipment(
        self,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
        category: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[EquipmentStatus] = None,
        is_archived: Optional[bool] = None,
        commissioned_from: Optional[date] = None,
        commissioned_to: Optional[date] = None,
        q: Optional[str] = None,
    ) -> tuple[list[Equipment], int]:
        if commissioned_from and commissioned_to and commissioned_from > commissioned_to:
            raise AppException(
                status=422,
                code="INVALID_DATE_RANGE",
                title="Invalid Date Range",
                detail="commissioned_from cannot be greater than commissioned_to.",
            )

        stmt = select(Equipment)
        count_stmt = select(func.count(Equipment.id))

        # Role-based visibility: OPERATOR sees only non-archived equipment
        if current_user.role == UserRole.OPERATOR:
            stmt = stmt.where(Equipment.archived_at.is_(None))
            count_stmt = count_stmt.where(Equipment.archived_at.is_(None))

        if category is not None and category.strip():
            stmt = stmt.where(Equipment.category == category.strip())
            count_stmt = count_stmt.where(Equipment.category == category.strip())
        if location is not None and location.strip():
            stmt = stmt.where(Equipment.location == location.strip())
            count_stmt = count_stmt.where(Equipment.location == location.strip())
        if status is not None:
            stmt = stmt.where(Equipment.status == status)
            count_stmt = count_stmt.where(Equipment.status == status)
        if is_archived is not None:
            if is_archived:
                stmt = stmt.where(Equipment.archived_at.is_not(None))
                count_stmt = count_stmt.where(Equipment.archived_at.is_not(None))
            else:
                stmt = stmt.where(Equipment.archived_at.is_(None))
                count_stmt = count_stmt.where(Equipment.archived_at.is_(None))
        if commissioned_from is not None:
            stmt = stmt.where(Equipment.commissioned_on >= commissioned_from)
            count_stmt = count_stmt.where(Equipment.commissioned_on >= commissioned_from)
        if commissioned_to is not None:
            stmt = stmt.where(Equipment.commissioned_on <= commissioned_to)
            count_stmt = count_stmt.where(Equipment.commissioned_on <= commissioned_to)

        if q is not None and q.strip():
            escaped = f"%{escape_like(q.strip().lower())}%"
            q_filter = func.lower(Equipment.name).like(escaped) | func.lower(Equipment.inventory_number).like(escaped)
            stmt = stmt.where(q_filter)
            count_stmt = count_stmt.where(q_filter)

        # Ordering per spec Q17/Design Notes: name ASC, id ASC
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

        # OPERATOR cannot see archived equipment -> return 404
        if current_user.role == UserRole.OPERATOR and eq.archived_at is not None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Equipment Not Found",
                detail=f"Equipment with id '{equipment_id}' does not exist.",
            )

        return eq

    async def create_equipment(self, payload: EquipmentCreate) -> Equipment:
        local_today = get_local_today()
        if payload.commissioned_on > local_today:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail="commissioned_on date cannot be in the future.",
            )

        inv_num = payload.inventory_number.strip()
        stmt = select(Equipment).where(Equipment.inventory_number == inv_num)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise AppException(
                status=409,
                code="EQUIPMENT_ALREADY_EXISTS",
                title="Conflict",
                detail=f"Equipment with inventory number '{inv_num}' already exists.",
            )

        eq = Equipment(
            name=payload.name.strip(),
            inventory_number=inv_num,
            category=payload.category.strip(),
            location=payload.location.strip(),
            status=EquipmentStatus.OPERATIONAL,
            commissioned_on=payload.commissioned_on,
        )
        self.session.add(eq)
        await self.session.commit()
        await self.session.refresh(eq)
        return eq

    async def update_equipment(
        self,
        equipment_id: uuid.UUID,
        expected_version: int,
        payload: EquipmentUpdate,
        current_user: User,
    ) -> Equipment:
        eq = await self.get_equipment_by_id(equipment_id, current_user)
        if eq.version != expected_version:
            raise AppException(
                status=412,
                code="VERSION_CONFLICT",
                title="Version Conflict",
                detail=f"Resource version {eq.version} does not match expected {expected_version}.",
            )

        has_changes = False
        if payload.name is not None and payload.name.strip() != eq.name:
            eq.name = payload.name.strip()
            has_changes = True
        if payload.location is not None and payload.location.strip() != eq.location:
            eq.location = payload.location.strip()
            has_changes = True
        if payload.category is not None and payload.category.strip() != eq.category:
            eq.category = payload.category.strip()
            has_changes = True
        if payload.status is not None and payload.status != eq.status:
            eq.status = payload.status
            has_changes = True

        if has_changes:
            eq.version += 1
            await self.session.commit()
            await self.session.refresh(eq)

        return eq

    async def archive_equipment(self, equipment_id: uuid.UUID, current_user: User) -> Equipment:
        eq = await self.get_equipment_by_id(equipment_id, current_user)
        if eq.archived_at is not None:
            raise AppException(
                status=409,
                code="ALREADY_ARCHIVED",
                title="Conflict",
                detail="Equipment is already archived.",
            )

        # Check for uncompleted work orders (to be integrated with WorkOrders table once created)
        eq.archived_at = datetime.now(timezone.utc)
        eq.version += 1
        await self.session.commit()
        await self.session.refresh(eq)
        return eq

    async def restore_equipment(self, equipment_id: uuid.UUID, current_user: User) -> Equipment:
        eq = await self.get_equipment_by_id(equipment_id, current_user)
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
        await self.session.commit()
        await self.session.refresh(eq)
        return eq
