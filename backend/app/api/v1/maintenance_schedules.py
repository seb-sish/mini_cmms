import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.common import PaginatedResponse
from app.schemas.maintenance import MaintenanceScheduleRead
from app.services.maintenance_service import MaintenanceService

schedules_router = APIRouter(prefix="/maintenance-schedules", tags=["Maintenance Schedules"])


@schedules_router.get("", response_model=PaginatedResponse)
async def list_schedules(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER", "TECHNICIAN"))],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    plan_id: uuid.UUID | None = None,
    equipment_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
) -> PaginatedResponse:
    service = MaintenanceService(db)
    items, total = await service.list_schedules(
        current_user=current_user,
        limit=limit,
        offset=offset,
        plan_id=plan_id,
        equipment_id=equipment_id,
        is_active=is_active,
        due_from=due_from,
        due_to=due_to,
    )
    result_items = []
    for sched, is_overdue, has_current in items:
        dto = MaintenanceScheduleRead.model_validate(sched)
        dto.is_overdue = is_overdue
        dto.has_current_work_order = has_current
        result_items.append(dto)

    return PaginatedResponse(
        items=result_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@schedules_router.get("/{schedule_id}", response_model=MaintenanceScheduleRead)
async def get_schedule(
    schedule_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER", "TECHNICIAN"))],
) -> MaintenanceScheduleRead:
    service = MaintenanceService(db)
    sched, is_overdue, has_current = await service.get_schedule_by_id(schedule_id, current_user=current_user)
    response.headers["ETag"] = f'"{sched.id}:{sched.version}"'
    dto = MaintenanceScheduleRead.model_validate(sched)
    dto.is_overdue = is_overdue
    dto.has_current_work_order = has_current
    return dto
