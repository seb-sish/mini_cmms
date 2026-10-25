import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import parse_if_match_version, require_role
from app.db.models.maintenance_plan import PlanScope
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.common import PaginatedResponse
from app.schemas.maintenance import MaintenancePlanCreate, MaintenancePlanRead, MaintenancePlanUpdate
from app.services.maintenance_service import MaintenanceService

plans_router = APIRouter(prefix="/maintenance-plans", tags=["Maintenance Plans"])


@plans_router.get("", response_model=PaginatedResponse)
async def list_plans(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER", "TECHNICIAN"))],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scope: PlanScope | None = None,
    is_active: bool | None = None,
    q: str | None = None,
    category: str | None = None,
    equipment_id: uuid.UUID | None = None,
    enabled: bool | None = None,
) -> PaginatedResponse:
    service = MaintenanceService(db)
    items, total = await service.list_plans(
        current_user=current_user,
        limit=limit,
        offset=offset,
        scope=scope,
        is_active=is_active,
        q=q,
        category=category,
        equipment_id=equipment_id,
        enabled=enabled,
    )
    return PaginatedResponse(
        items=[MaintenancePlanRead.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@plans_router.post("", response_model=MaintenancePlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: MaintenancePlanCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER"))],
) -> MaintenancePlanRead:
    service = MaintenanceService(db)
    plan = await service.create_plan(payload)
    response.headers["Location"] = f"/api/v1/maintenance-plans/{plan.id}"
    response.headers["ETag"] = f'"{plan.id}:{plan.version}"'
    return MaintenancePlanRead.model_validate(plan)


@plans_router.get("/{plan_id}", response_model=MaintenancePlanRead)
async def get_plan(
    plan_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER", "TECHNICIAN"))],
) -> MaintenancePlanRead:
    service = MaintenanceService(db)
    plan = await service.get_plan_by_id(plan_id, current_user=current_user)
    response.headers["ETag"] = f'"{plan.id}:{plan.version}"'
    return MaintenancePlanRead.model_validate(plan)


@plans_router.patch("/{plan_id}", response_model=MaintenancePlanRead)
async def update_plan(
    plan_id: uuid.UUID,
    payload: MaintenancePlanUpdate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER"))],
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> MaintenancePlanRead:
    expected_version = parse_if_match_version(if_match, str(plan_id))
    service = MaintenanceService(db)
    plan = await service.update_plan(plan_id, expected_version, payload)
    response.headers["ETag"] = f'"{plan.id}:{plan.version}"'
    return MaintenancePlanRead.model_validate(plan)
