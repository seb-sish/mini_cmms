from datetime import date
from typing import Annotated, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.common import PaginatedResponse
from app.schemas.maintenance import MaintenanceScheduleRead
from app.services.maintenance_service import MaintenanceService

schedules_router = APIRouter(prefix="/maintenance-schedules", tags=["Maintenance Schedules"])

@schedules_router.get("", response_model=PaginatedResponse)
async def list_schedules(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    plan_id: Optional[uuid.UUID] = None,
    equipment_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    due_from: Optional[date] = None,
    due_to: Optional[date] = None,
) -> PaginatedResponse:
    service = MaintenanceService(db)
    items, total = await service.list_schedules(
        limit=limit,
        offset=offset,
        plan_id=plan_id,
        equipment_id=equipment_id,
        is_active=is_active,
        due_from=due_from,
        due_to=due_to,
    )
    result_items = []
    for sched, is_overdue in items:
        dto = MaintenanceScheduleRead.model_validate(sched)
        dto.is_overdue = is_overdue
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
    current_user: Annotated[User, Depends(get_current_user)],
) -> MaintenanceScheduleRead:
    service = MaintenanceService(db)
    sched, is_overdue = await service.get_schedule_by_id(schedule_id)
    response.headers["ETag"] = f'"{sched.id}:{sched.version}"'
    dto = MaintenanceScheduleRead.model_validate(sched)
    dto.is_overdue = is_overdue
    return dto
