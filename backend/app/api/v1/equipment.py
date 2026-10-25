import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import parse_if_match_version, require_role
from app.db.models.equipment import EquipmentStatus
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.common import PaginatedResponse
from app.schemas.equipment import EquipmentCreate, EquipmentPatch, EquipmentRead
from app.services.equipment_service import EquipmentService

equipment_router = APIRouter(prefix="/equipment", tags=["Equipment"])


@equipment_router.get("", response_model=PaginatedResponse)
async def list_equipment(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER", "TECHNICIAN", "OPERATOR"))],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: str | None = None,
    location: str | None = None,
    status_filter: EquipmentStatus | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False),
    is_archived: bool | None = None,
    q: str | None = None,
) -> PaginatedResponse:
    effective_archived = include_archived or bool(is_archived)
    service = EquipmentService(db)
    items, total = await service.list_equipment(
        current_user=current_user,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
        category=category,
        location=location,
        include_archived=effective_archived,
        q=q,
    )
    return PaginatedResponse(
        items=[EquipmentRead.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@equipment_router.post("", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    payload: EquipmentCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER"))],
) -> EquipmentRead:
    service = EquipmentService(db)
    eq = await service.create_equipment(payload)
    response.headers["Location"] = f"/api/v1/equipment/{eq.id}"
    response.headers["ETag"] = f'"{eq.id}:{eq.version}"'
    return EquipmentRead.model_validate(eq)


@equipment_router.get("/{equipment_id}", response_model=EquipmentRead)
async def get_equipment(
    equipment_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER", "TECHNICIAN", "OPERATOR"))],
) -> EquipmentRead:
    service = EquipmentService(db)
    eq = await service.get_equipment_by_id(equipment_id, current_user)
    response.headers["ETag"] = f'"{eq.id}:{eq.version}"'
    return EquipmentRead.model_validate(eq)


@equipment_router.patch("/{equipment_id}", response_model=EquipmentRead)
async def update_equipment(
    equipment_id: uuid.UUID,
    payload: EquipmentPatch,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER"))],
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> EquipmentRead:
    expected_version = parse_if_match_version(if_match, str(equipment_id))
    service = EquipmentService(db)
    eq = await service.update_equipment(equipment_id, expected_version, payload, current_user)
    response.headers["ETag"] = f'"{eq.id}:{eq.version}"'
    return EquipmentRead.model_validate(eq)


@equipment_router.post("/{equipment_id}/archive", response_model=EquipmentRead)
async def archive_equipment(
    equipment_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER"))],
) -> EquipmentRead:
    service = EquipmentService(db)
    eq = await service.archive_equipment(equipment_id, current_user)
    response.headers["ETag"] = f'"{eq.id}:{eq.version}"'
    return EquipmentRead.model_validate(eq)


@equipment_router.post("/{equipment_id}/restore", response_model=EquipmentRead)
async def restore_equipment(
    equipment_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("ENGINEER"))],
) -> EquipmentRead:
    service = EquipmentService(db)
    eq = await service.restore_equipment(equipment_id, current_user)
    response.headers["ETag"] = f'"{eq.id}:{eq.version}"'
    return EquipmentRead.model_validate(eq)
