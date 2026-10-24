from datetime import date, datetime, timedelta, timezone
from typing import Optional
import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.equipment import Equipment
from app.db.models.maintenance_plan import MaintenancePlan, PlanScope
from app.db.models.maintenance_schedule import MaintenanceSchedule
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderStatus
from app.errors.exceptions import AppException
from app.schemas.maintenance import ChecklistItemTemplate, MaintenancePlanCreate, MaintenancePlanUpdate
from app.services.equipment_service import get_company_today

def validate_checklist_items(checklist: list[ChecklistItemTemplate]) -> list[dict]:
    seen_orders = set()
    seen_titles = set()
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
        item_title = item.title or item.description or ""
        norm_title = " ".join(item_title.strip().split())
        if not norm_title:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail="Checklist item title cannot be empty.",
            )
        if norm_title.lower() in seen_titles:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail=f"Checklist item title '{item_title}' is duplicated.",
            )
        seen_titles.add(norm_title.lower())
        item_id = str(item.id) if item.id else str(uuid.uuid4())
        is_req = item.required if item.required is not None else (item.is_required if item.is_required is not None else True)
        cleaned.append({
            "id": item_id,
            "order": item.order,
            "title": norm_title,
            "required": is_req,
            # Legacy compatibility
            "description": norm_title,
            "is_required": is_req,
        })
    cleaned.sort(key=lambda x: x["order"])
    return cleaned

class MaintenanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_plans(
        self,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
        scope: Optional[PlanScope] = None,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
    ) -> tuple[list[MaintenancePlan], int]:
        stmt = select(MaintenancePlan)
        count_stmt = select(func.count(MaintenancePlan.id))

        if current_user.role == UserRole.TECHNICIAN:
            # Technician sees only plans associated with their assigned work orders
            assigned_plans_subq = (
                select(MaintenanceSchedule.plan_id)
                .join(WorkOrder, WorkOrder.schedule_id == MaintenanceSchedule.id)
                .where(WorkOrder.assignee_id == current_user.id)
                .scalar_subquery()
            )
            stmt = stmt.where(MaintenancePlan.id.in_(assigned_plans_subq))
            count_stmt = count_stmt.where(MaintenancePlan.id.in_(assigned_plans_subq))

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

    async def get_plan_by_id(self, plan_id: uuid.UUID, current_user: Optional[User] = None) -> MaintenancePlan:
        stmt = select(MaintenancePlan).where(MaintenancePlan.id == plan_id)
        plan = (await self.session.execute(stmt)).scalar_one_or_none()
        if plan is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Plan Not Found",
                detail=f"Maintenance plan with id '{plan_id}' does not exist.",
            )

        if current_user and current_user.role == UserRole.TECHNICIAN:
            has_assigned = (
                await self.session.execute(
                    select(func.count(WorkOrder.id))
                    .join(MaintenanceSchedule, WorkOrder.schedule_id == MaintenanceSchedule.id)
                    .where(
                        MaintenanceSchedule.plan_id == plan.id,
                        WorkOrder.assignee_id == current_user.id,
                    )
                )
            ).scalar_one() > 0
            if not has_assigned:
                raise AppException(
                    status=404,
                    code="NOT_FOUND",
                    title="Plan Not Found",
                    detail=f"Maintenance plan with id '{plan_id}' does not exist.",
                )

        return plan

    async def create_plan(self, payload: MaintenancePlanCreate) -> MaintenancePlan:
        company_today = get_company_today()
        cleaned_checklist = validate_checklist_items(payload.checklist)

        enabled = payload.enabled if payload.enabled is not None else (
            payload.is_active if payload.is_active is not None else True
        )

        plan = MaintenancePlan(
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            scope=payload.scope,
            equipment_id=payload.equipment_id,
            category=payload.category.strip() if payload.category else None,
            interval_days=payload.interval_days,
            first_due_on=payload.first_due_on,
            is_active=enabled,
            checklist=cleaned_checklist,
        )
        self.session.add(plan)
        await self.session.flush()

        initial_due = max(payload.first_due_on, company_today)

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
                is_active=enabled,
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
                    is_active=enabled,
                )
                self.session.add(sched)

        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def generate_schedules_for_new_equipment(self, eq: Equipment) -> None:
        company_today = get_company_today()
        plans_q = select(MaintenancePlan).where(
            MaintenancePlan.scope == PlanScope.CATEGORY,
            MaintenancePlan.category == eq.category,
            MaintenancePlan.is_active == True,
        )
        plans = (await self.session.execute(plans_q)).scalars().all()
        for plan in plans:
            initial_due = max(plan.first_due_on, company_today)
            sched = MaintenanceSchedule(
                plan_id=plan.id,
                equipment_id=eq.id,
                next_due_on=initial_due,
                last_completed_on=None,
                is_active=True,
            )
            self.session.add(sched)
        await self.session.commit()

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

        new_enabled = payload.enabled if payload.enabled is not None else payload.is_active
        if new_enabled is not None and new_enabled != plan.is_active:
            plan.is_active = new_enabled
            has_changes = True
            # Update all attached schedules
            await self.session.execute(
                update(MaintenanceSchedule)
                .where(MaintenanceSchedule.plan_id == plan.id)
                .values(is_active=new_enabled)
            )

        if payload.interval_days is not None and payload.interval_days != plan.interval_days:
            # Check Q16: Cannot change interval if there are active work orders for this plan
            active_wo_q = (
                select(func.count(WorkOrder.id))
                .join(MaintenanceSchedule, WorkOrder.schedule_id == MaintenanceSchedule.id)
                .where(
                    MaintenanceSchedule.plan_id == plan.id,
                    WorkOrder.status.in_([
                        WorkOrderStatus.CREATED,
                        WorkOrderStatus.ASSIGNED,
                        WorkOrderStatus.IN_PROGRESS,
                        WorkOrderStatus.COMPLETED,
                    ]),
                )
            )
            active_wo_count = (await self.session.execute(active_wo_q)).scalar_one()
            if active_wo_count > 0:
                raise AppException(
                    status=409,
                    code="ACTIVE_MAINTENANCE_WORK",
                    title="Active Maintenance Work",
                    detail="Cannot change interval while there are active maintenance work orders for this plan.",
                )

            # Recalculate schedules where last_completed_on is set
            sched_stmt = select(MaintenanceSchedule).where(MaintenanceSchedule.plan_id == plan.id)
            schedules = (await self.session.execute(sched_stmt)).scalars().all()

            for s in schedules:
                if s.last_completed_on is not None:
                    new_due = s.last_completed_on + timedelta(days=payload.interval_days)
                    # Non-advancing check: new_due must be strictly > last closed work order's planned_due_on
                    last_closed_q = select(func.max(WorkOrder.planned_due_on)).where(
                        WorkOrder.schedule_id == s.id,
                        WorkOrder.status == WorkOrderStatus.CLOSED,
                    )
                    last_closed = (await self.session.execute(last_closed_q)).scalar_one_or_none()
                    if last_closed is not None and new_due <= last_closed:
                        raise AppException(
                            status=409,
                            code="NON_ADVANCING_DUE_DATE",
                            title="Non Advancing Due Date",
                            detail=f"Calculated next_due_on {new_due} must be strictly after last closed maintenance date {last_closed}.",
                        )
                    s.next_due_on = new_due
                    s.version += 1

            plan.interval_days = payload.interval_days
            has_changes = True

        if has_changes:
            plan.version += 1
            await self.session.commit()
            await self.session.refresh(plan)

        return plan

    async def list_schedules(
        self,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
        plan_id: Optional[uuid.UUID] = None,
        equipment_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
    ) -> tuple[list[tuple[MaintenanceSchedule, bool, bool]], int]:
        if due_from and due_to and due_from > due_to:
            raise AppException(
                status=422,
                code="INVALID_DATE_RANGE",
                title="Invalid Date Range",
                detail="due_from cannot be greater than due_to.",
            )

        company_today = get_company_today()
        stmt = select(MaintenanceSchedule)
        count_stmt = select(func.count(MaintenanceSchedule.id))

        if current_user.role == UserRole.TECHNICIAN:
            assigned_scheds_subq = (
                select(WorkOrder.schedule_id)
                .where(
                    WorkOrder.assignee_id == current_user.id,
                    WorkOrder.schedule_id.is_not(None),
                )
                .scalar_subquery()
            )
            stmt = stmt.where(MaintenanceSchedule.id.in_(assigned_scheds_subq))
            count_stmt = count_stmt.where(MaintenanceSchedule.id.in_(assigned_scheds_subq))

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

        active_pairs = set()
        if items:
            sched_ids = [s.id for s in items]
            active_orders_q = select(WorkOrder.schedule_id, WorkOrder.planned_due_on).where(
                WorkOrder.schedule_id.in_(sched_ids),
                WorkOrder.status.in_([
                    WorkOrderStatus.CREATED,
                    WorkOrderStatus.ASSIGNED,
                    WorkOrderStatus.IN_PROGRESS,
                    WorkOrderStatus.COMPLETED,
                ]),
            )
            active_pairs = set((await self.session.execute(active_orders_q)).all())

        annotated_items = []
        for s in items:
            is_overdue = s.is_active and s.next_due_on < company_today
            has_current = (s.id, s.next_due_on) in active_pairs
            annotated_items.append((s, is_overdue, has_current))

        return annotated_items, total

    async def get_schedule_by_id(self, schedule_id: uuid.UUID, current_user: Optional[User] = None) -> tuple[MaintenanceSchedule, bool, bool]:
        stmt = select(MaintenanceSchedule).where(MaintenanceSchedule.id == schedule_id)
        sched = (await self.session.execute(stmt)).scalar_one_or_none()
        if sched is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Schedule Not Found",
                detail=f"Maintenance schedule with id '{schedule_id}' does not exist.",
            )

        if current_user and current_user.role == UserRole.TECHNICIAN:
            has_assigned = (
                await self.session.execute(
                    select(func.count(WorkOrder.id)).where(
                        WorkOrder.schedule_id == sched.id,
                        WorkOrder.assignee_id == current_user.id,
                    )
                )
            ).scalar_one() > 0
            if not has_assigned:
                raise AppException(
                    status=404,
                    code="NOT_FOUND",
                    title="Schedule Not Found",
                    detail=f"Maintenance schedule with id '{schedule_id}' does not exist.",
                )

        company_today = get_company_today()
        is_overdue = sched.is_active and sched.next_due_on < company_today

        has_current_q = select(func.count(WorkOrder.id)).where(
            WorkOrder.schedule_id == sched.id,
            WorkOrder.planned_due_on == sched.next_due_on,
            WorkOrder.status.in_([
                WorkOrderStatus.CREATED,
                WorkOrderStatus.ASSIGNED,
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.COMPLETED,
            ]),
        )
        has_current = (await self.session.execute(has_current_q)).scalar_one() > 0

        return sched, is_overdue, has_current
