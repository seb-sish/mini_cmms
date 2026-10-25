import uuid
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import escape_like, locked, pairing_lock
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
        if norm_title in seen_titles:
            raise AppException(
                status=422,
                code="VALIDATION_ERROR",
                title="Validation Error",
                detail=f"Checklist item title '{item_title}' is duplicated.",
            )
        seen_titles.add(norm_title)
        raw_id = getattr(item, "id", None)
        item_id = str(raw_id) if raw_id else str(uuid.uuid4())
        is_req = getattr(item, "required", None)
        if is_req is None:
            is_req = getattr(item, "is_required", True)
        cleaned.append(
            {
                "id": item_id,
                "order": item.order,
                "title": norm_title,
                "required": is_req,
            }
        )
    cleaned.sort(key=lambda x: x["order"])
    return cleaned


def _checklist_content_equals(current: list[dict] | None, incoming: list[dict]) -> bool:
    """Сравнивает шаблоны checklist по содержанию, игнорируя генерируемые id."""
    if not current:
        return False

    def signature(items: list[dict]) -> list[tuple]:
        return sorted(
            (item.get("order"), item.get("title"), bool(item.get("required")))  # type: ignore[arg-type]
            for item in items
        )

    return signature(current) == signature(incoming)


class MaintenanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_plans(
        self,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
        scope: PlanScope | None = None,
        is_active: bool | None = None,
        q: str | None = None,
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
            term = f"%{escape_like(q.strip().lower())}%"
            stmt = stmt.where(func.lower(MaintenancePlan.name).like(term, escape="\\"))
            count_stmt = count_stmt.where(func.lower(MaintenancePlan.name).like(term, escape="\\"))

        stmt = stmt.order_by(MaintenancePlan.name.asc(), MaintenancePlan.id.asc()).offset(offset).limit(limit)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())
        return items, total

    async def get_plan_by_id(self, plan_id: uuid.UUID, current_user: User | None = None) -> MaintenancePlan:
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

    async def sync_equipment_schedules(self, equipment: Equipment) -> None:
        """
        Synchronizes all schedules for a given equipment across all relevant plans
        without performing internal commit (callers commit their own transaction).
        - Preserves existing schedule ID and next_due_on.
        - Sets is_active = (plan.is_active and equipment not archived and in scope).
        - Creates missing schedules for matching plans.
        """
        company_today = get_company_today()

        sched_plan_subq = (
            select(MaintenanceSchedule.plan_id)
            .where(MaintenanceSchedule.equipment_id == equipment.id)
            .scalar_subquery()
        )
        matching_plans_q = select(MaintenancePlan).where(
            or_(
                (MaintenancePlan.scope == PlanScope.CATEGORY) & (MaintenancePlan.category == equipment.category),
                (MaintenancePlan.scope == PlanScope.EQUIPMENT) & (MaintenancePlan.equipment_id == equipment.id),
                MaintenancePlan.id.in_(sched_plan_subq),
            )
        )
        plans = (await self.session.execute(matching_plans_q)).scalars().all()

        existing_sched_q = select(MaintenanceSchedule).where(MaintenanceSchedule.equipment_id == equipment.id)
        existing_scheds = {s.plan_id: s for s in (await self.session.execute(existing_sched_q)).scalars().all()}

        for plan in plans:
            in_scope = False
            if plan.scope == PlanScope.EQUIPMENT and plan.equipment_id == equipment.id:
                in_scope = True
            elif plan.scope == PlanScope.CATEGORY and plan.category == equipment.category:
                in_scope = True

            should_be_active = bool(plan.is_active and (equipment.archived_at is None) and in_scope)

            if plan.id in existing_scheds:
                sched = existing_scheds[plan.id]
                if sched.is_active != should_be_active:
                    sched.is_active = should_be_active
                    sched.version += 1
                    self.session.add(sched)
            else:
                if in_scope:
                    initial_due = max(plan.first_due_on, company_today)
                    sched = MaintenanceSchedule(
                        id=uuid.uuid4(),
                        plan_id=plan.id,
                        equipment_id=equipment.id,
                        next_due_on=initial_due,
                        last_completed_on=None,
                        is_active=should_be_active,
                        version=1,
                    )
                    self.session.add(sched)

    async def generate_schedules_for_new_equipment(self, eq: Equipment) -> None:
        await self.sync_equipment_schedules(eq)
        await self.session.commit()

    async def create_plan(self, payload: MaintenancePlanCreate) -> MaintenancePlan:
        await pairing_lock(self.session)
        cleaned_checklist = validate_checklist_items(payload.checklist)

        enabled = getattr(payload, "enabled", None)
        if enabled is None:
            enabled = getattr(payload, "is_active", True)
        if enabled is None:
            enabled = True

        desc = getattr(payload, "description", None)
        plan = MaintenancePlan(
            name=payload.name.strip(),
            description=desc.strip() if desc else None,
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

        if payload.scope == PlanScope.EQUIPMENT:
            eq = (
                await self.session.execute(select(Equipment).where(Equipment.id == payload.equipment_id))
            ).scalar_one_or_none()
            if eq is None or eq.archived_at is not None:
                raise AppException(
                    status=404,
                    code="NOT_FOUND",
                    title="Equipment Not Found",
                    detail="Target equipment does not exist or is archived.",
                )
            await self.sync_equipment_schedules(eq)
        elif payload.scope == PlanScope.CATEGORY:
            eq_stmt = select(Equipment).where(Equipment.category == payload.category.strip()).order_by(Equipment.id)
            equipments = (await self.session.execute(eq_stmt)).scalars().all()
            for eq in equipments:
                await self.sync_equipment_schedules(eq)

        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def update_plan(
        self, plan_id: uuid.UUID, expected_version: int, payload: MaintenancePlanUpdate
    ) -> MaintenancePlan:
        await pairing_lock(self.session)
        await self.get_plan_by_id(plan_id)
        stmt = locked(select(MaintenancePlan).where(MaintenancePlan.id == plan_id))
        res = await self.session.execute(stmt)
        plan = res.scalar_one_or_none()
        if plan is None:
            raise AppException(
                status=404,
                code="NOT_FOUND",
                title="Plan Not Found",
                detail=f"Plan with id '{plan_id}' does not exist.",
            )
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
        desc = getattr(payload, "description", None)
        if desc is not None:
            clean_desc = desc.strip() if desc else None
            if clean_desc != plan.description:
                plan.description = clean_desc
                has_changes = True

        if payload.checklist is not None:
            cleaned_checklist = validate_checklist_items(payload.checklist)
            # Тот же состав шаблона — no-op: id, версия и updated_at не меняются.
            if not _checklist_content_equals(plan.checklist, cleaned_checklist):
                plan.checklist = cleaned_checklist
                has_changes = True

        new_enabled = getattr(payload, "enabled", None)
        if new_enabled is None:
            new_enabled = getattr(payload, "is_active", None)
        if new_enabled is not None and new_enabled != plan.is_active:
            plan.is_active = new_enabled
            has_changes = True

            # Sync schedules for all associated equipment
            sched_eq_subq = (
                select(MaintenanceSchedule.equipment_id).where(MaintenanceSchedule.plan_id == plan.id).scalar_subquery()
            )
            eq_ids_q = (
                select(Equipment)
                .where(
                    or_(
                        Equipment.category == plan.category,
                        Equipment.id == plan.equipment_id,
                        Equipment.id.in_(sched_eq_subq),
                    )
                )
                .order_by(Equipment.id)
            )
            equipments = (await self.session.execute(eq_ids_q)).scalars().all()
            for eq in equipments:
                await self.sync_equipment_schedules(eq)

        if payload.interval_days is not None and payload.interval_days != plan.interval_days:
            # Канонический порядок блокировок: Equipment -> Schedule -> Plan.
            eq_ids_q = (
                select(MaintenanceSchedule.equipment_id)
                .where(MaintenanceSchedule.plan_id == plan.id)
                .distinct()
                .order_by(MaintenanceSchedule.equipment_id)
            )
            eq_ids = list((await self.session.execute(eq_ids_q)).scalars().all())
            if eq_ids:
                await self.session.execute(
                    locked(select(Equipment).where(Equipment.id.in_(eq_ids)).order_by(Equipment.id))
                )

            sched_stmt = locked(
                select(MaintenanceSchedule)
                .where(MaintenanceSchedule.plan_id == plan.id)
                .order_by(MaintenanceSchedule.id)
            )
            schedules = (await self.session.execute(sched_stmt)).scalars().all()

            # Check Q16: Cannot change interval if there are active work orders for this plan
            sched_ids = [s.id for s in schedules]
            if sched_ids:
                active_wo_q = select(func.count(WorkOrder.id)).where(
                    WorkOrder.schedule_id.in_(sched_ids),
                    WorkOrder.status.in_(
                        [
                            WorkOrderStatus.CREATED,
                            WorkOrderStatus.ASSIGNED,
                            WorkOrderStatus.IN_PROGRESS,
                            WorkOrderStatus.COMPLETED,
                        ]
                    ),
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
                        await self.session.rollback()
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
        plan_id: uuid.UUID | None = None,
        equipment_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        due_from: date | None = None,
        due_to: date | None = None,
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

        stmt = (
            stmt.order_by(MaintenanceSchedule.next_due_on.asc(), MaintenanceSchedule.id.asc())
            .offset(offset)
            .limit(limit)
        )

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())

        active_pairs = set()
        completed_pairs = set()
        if items:
            sched_ids = [s.id for s in items]
            active_orders_q = select(WorkOrder.schedule_id, WorkOrder.planned_due_on, WorkOrder.status).where(
                WorkOrder.schedule_id.in_(sched_ids),
                WorkOrder.status.in_(
                    [
                        WorkOrderStatus.CREATED,
                        WorkOrderStatus.ASSIGNED,
                        WorkOrderStatus.IN_PROGRESS,
                        WorkOrderStatus.COMPLETED,
                    ]
                ),
            )
            rows = (await self.session.execute(active_orders_q)).all()
            for sched_id_val, planned_due, status_val in rows:
                active_pairs.add((sched_id_val, planned_due))
                if status_val == WorkOrderStatus.COMPLETED:
                    completed_pairs.add((sched_id_val, planned_due))

        annotated_items = []
        for s in items:
            is_overdue, has_current = self.calculate_schedule_flags(s, company_today, active_pairs, completed_pairs)
            annotated_items.append((s, is_overdue, has_current))

        return annotated_items, total

    @staticmethod
    def calculate_schedule_flags(
        schedule: MaintenanceSchedule,
        company_today: date,
        active_due_pairs: set[tuple[uuid.UUID, date]],
        completed_due_pairs: set[tuple[uuid.UUID, date]],
    ) -> tuple[bool, bool]:
        has_current = (schedule.id, schedule.next_due_on) in active_due_pairs
        has_completed = (schedule.id, schedule.next_due_on) in completed_due_pairs
        is_overdue = bool(schedule.is_active and schedule.next_due_on < company_today and not has_completed)
        return is_overdue, has_current

    async def get_schedule_by_id(
        self, schedule_id: uuid.UUID, current_user: User | None = None
    ) -> tuple[MaintenanceSchedule, bool, bool]:
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

        orders_q = select(WorkOrder.planned_due_on, WorkOrder.status).where(
            WorkOrder.schedule_id == sched.id,
            WorkOrder.planned_due_on == sched.next_due_on,
            WorkOrder.status.in_(
                [
                    WorkOrderStatus.CREATED,
                    WorkOrderStatus.ASSIGNED,
                    WorkOrderStatus.IN_PROGRESS,
                    WorkOrderStatus.COMPLETED,
                ]
            ),
        )
        rows = (await self.session.execute(orders_q)).all()
        active_pairs = {(sched.id, r[0]) for r in rows}
        completed_pairs = {(sched.id, r[0]) for r in rows if r[1] == WorkOrderStatus.COMPLETED}

        is_overdue, has_current = self.calculate_schedule_flags(sched, company_today, active_pairs, completed_pairs)

        return sched, is_overdue, has_current
