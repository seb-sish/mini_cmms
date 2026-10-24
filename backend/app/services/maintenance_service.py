from datetime import date, datetime, timedelta, timezone
from typing import Optional
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.errors.exceptions import AppException
from app.schemas.maintenance import ChecklistItemTemplate, MaintenancePlanCreate, MaintenancePlanUpdate
from app.services.equipment_service import get_local_today

def validate_checklist_items(checklist: list[ChecklistItemTemplate]) -> list[dict]:
    seen_orders = set()
    seen_descs = set()
    cleaned = []
    for item in checklist:
        if item.order in seen_orders:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail=f"Checklist item order {item.order} is duplicated.",
            )
        seen_orders.add(item.order)
        norm_desc = " ".join(item.description.strip().split())
        if norm_desc.lower() in seen_descs:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail=f"Checklist item description '{item.description}' is duplicated.",
            )
        seen_descs.add(norm_desc.lower())
        cleaned.append({
            "order": item.order,
            "description": norm_desc,
            "is_required": item.is_required,
        })
    cleaned.sort(key=lambda x: x["order"])
    return cleaned

class MaintenanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_plans(
        self,
        limit: int = 20,
        offset: int = 0,
        scope: Optional[PlanScope] = None,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
    ) -> tuple[list[MaintenancePlan], int]:
        stmt = select(MaintenancePlan)
        count_stmt = select(func.count(MaintenancePlan.id))

        if scope is not None:
            stmt = stmt.where(MaintenancePlan.scope == scope)
            count_stmt = count_stmt.where(MaintenancePlan.scope == scope)
        if is_active is not None:
            stmt = stmt.where(MaintenancePlan.is_active == is_active)
            count_stmt = count_stmt.where(MaintenancePlan.is_active == is_active)
        if q is not None and q.strip():
            term = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(MaintenancePlan.name).like(term))
            count_stmt = count_stmt.where(func.lower(MaintenancePlan.name).like(term))

        stmt = stmt.order_by(MaintenancePlan.name.asc(), MaintenancePlan.id.asc()).offset(offset).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total

    async def get_plan_by_id(self, plan_id: uuid.UUID) -> MaintenancePlan:
        stmt = select(MaintenancePlan).where(MaintenancePlan.id == plan_id)
        plan = (await self.session.execute(stmt)).scalar_one_or_none()
        if plan is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Plan Not Found",
                detail=f"Maintenance plan with id '{plan_id}' does not exist.",
            )
        return plan

    async def create_plan(self, payload: MaintenancePlanCreate) -> MaintenancePlan:
        local_today = get_local_today()
        cleaned_checklist = validate_checklist_items(payload.checklist)

        plan = MaintenancePlan(
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            scope=payload.scope,
            equipment_id=payload.equipment_id,
            category=payload.category.strip() if payload.category else None,
            interval_days=payload.interval_days,
            first_due_on=payload.first_due_on,
            is_active=True,
            checklist=cleaned_checklist,
        )
        self.session.add(plan)
        await self.session.flush()

        initial_due = max(payload.first_due_on, local_today)

        if payload.scope == PlanScope.EQUIPMENT:
            eq = (await self.session.execute(select(Equipment).where(Equipment.id == payload.equipment_id))).scalar_one_or_none()
            if eq is None or eq.archived_at is not None:
                raise AppException(
                    status=404,
                    code="NOT_FOUND",
                    title="Equipment Not Found",
                    detail="Target equipment does not exist or is archived.",
                )
            sched = MaintenanceSchedule(
                plan_id=plan.id,
                equipment_id=eq.id,
                next_due_on=initial_due,
                last_completed_on=None,
                is_active=True,
            )
            self.session.add(sched)
        elif payload.scope == PlanScope.CATEGORY:
            eq_stmt = select(Equipment).where(
                Equipment.category == payload.category.strip(),
                Equipment.archived_at.is_(None),
            )
            equipments = (await self.session.execute(eq_stmt)).scalars().all()
            for eq in equipments:
                sched = MaintenanceSchedule(
                    plan_id=plan.id,
                    equipment_id=eq.id,
                    next_due_on=initial_due,
                    last_completed_on=None,
                    is_active=True,
                )
                self.session.add(sched)

        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def update_plan(self, plan_id: uuid.UUID, expected_version: int, payload: MaintenancePlanUpdate) -> MaintenancePlan:
        plan = await self.get_plan_by_id(plan_id)
        if plan.version != expected_version:
            raise AppException(
                status=412,
                code="VERSION_CONFLICT",
                title="Version Conflict",
                detail=f"Resource version {plan.version} does not match expected {expected_version}.",
            )

        has_changes = False
        if payload.name is not None and payload.name.strip() != plan.name:
            plan.name = payload.name.strip()
            has_changes = True
        if payload.description is not None:
            clean_desc = payload.description.strip() if payload.description else None
            if clean_desc != plan.description:
                plan.description = clean_desc
                has_changes = True

        if payload.checklist is not None:
            plan.checklist = validate_checklist_items(payload.checklist)
            has_changes = True

        if payload.is_active is not None and payload.is_active != plan.is_active:
            plan.is_active = payload.is_active
            has_changes = True
            # Update all attached schedules
            await self.session.execute(
                update(MaintenanceSchedule)
                .where(MaintenanceSchedule.plan_id == plan.id)
                .values(is_active=payload.is_active)
            )

        if payload.interval_days is not None and payload.interval_days != plan.interval_days:
            plan.interval_days = payload.interval_days
            has_changes = True

            # Recalculate schedules where last_completed_on is set
            sched_stmt = select(MaintenanceSchedule).where(MaintenanceSchedule.plan_id == plan.id)
            schedules = (await self.session.execute(sched_stmt)).scalars().all()

            for s in schedules:
                if s.last_completed_on is not None:
                    new_due = s.last_completed_on + timedelta(days=payload.interval_days)
                    # Non-advancing check: new_due must be strictly > any closed work order planned_due_on
                    s.next_due_on = new_due
                    s.version += 1

        if has_changes:
            plan.version += 1
            await self.session.commit()
            await self.session.refresh(plan)

        return plan

    async def list_schedules(
        self,
        limit: int = 20,
        offset: int = 0,
        plan_id: Optional[uuid.UUID] = None,
        equipment_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
    ) -> tuple[list[tuple[MaintenanceSchedule, bool]], int]:
        if due_from and due_to and due_from > due_to:
            raise AppException(
                status=422,
                code="INVALID_DATE_RANGE",
                title="Invalid Date Range",
                detail="due_from cannot be greater than due_to.",
            )

        local_today = get_local_today()
        stmt = select(MaintenanceSchedule)
        count_stmt = select(func.count(MaintenanceSchedule.id))

        if plan_id is not None:
            stmt = stmt.where(MaintenanceSchedule.plan_id == plan_id)
            count_stmt = count_stmt.where(MaintenanceSchedule.plan_id == plan_id)
        if equipment_id is not None:
            stmt = stmt.where(MaintenanceSchedule.equipment_id == equipment_id)
            count_stmt = count_stmt.where(MaintenanceSchedule.equipment_id == equipment_id)
        if is_active is not None:
            stmt = stmt.where(MaintenanceSchedule.is_active == is_active)
            count_stmt = count_stmt.where(MaintenanceSchedule.is_active == is_active)
        if due_from is not None:
            stmt = stmt.where(MaintenanceSchedule.next_due_on >= due_from)
            count_stmt = count_stmt.where(MaintenanceSchedule.next_due_on >= due_from)
        if due_to is not None:
            stmt = stmt.where(MaintenanceSchedule.next_due_on <= due_to)
            count_stmt = count_stmt.where(MaintenanceSchedule.next_due_on <= due_to)

        stmt = stmt.order_by(MaintenanceSchedule.next_due_on.asc(), MaintenanceSchedule.id.asc()).offset(offset).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())

        annotated_items = []
        for s in items:
            is_overdue = s.is_active and s.next_due_on < local_today
            annotated_items.append((s, is_overdue))

        return annotated_items, total

    async def get_schedule_by_id(self, schedule_id: uuid.UUID) -> tuple[MaintenanceSchedule, bool]:
        stmt = select(MaintenanceSchedule).where(MaintenanceSchedule.id == schedule_id)
        sched = (await self.session.execute(stmt)).scalar_one_or_none()
        if sched is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Schedule Not Found",
                detail=f"Maintenance schedule with id '{schedule_id}' does not exist.",
            )
        local_today = get_local_today()
        is_overdue = sched.is_active and sched.next_due_on < local_today
        return sched, is_overdue
