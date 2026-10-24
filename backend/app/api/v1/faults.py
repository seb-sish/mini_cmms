from datetime import date
from typing import Annotated, Optional
import uuid
from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, parse_if_match_version, require_role
from app.db.models.fault import FaultStatus
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.common import PaginatedResponse
from app.schemas.fault import FaultCreate, FaultRead, FaultUpdate
from app.services.fault_service import FaultService

faults_router = APIRouter(prefix="/faults", tags=["Faults"])

@faults_router.get("", response_model=PaginatedResponse)
async def list_faults(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    equipment_id: Optional[uuid.UUID] = None,
    status_filter: Optional[FaultStatus] = Query(default=None, alias="status"),
    author_id: Optional[uuid.UUID] = None,
    detected_from: Optional[date] = None,
    detected_to: Optional[date] = None,
    q: Optional[str] = None,
) -> PaginatedResponse:
    service = FaultService(db)
    items, total = await service.list_faults(
        current_user=current_user,
        limit=limit,
        offset=offset,
        equipment_id=equipment_id,
        status_filter=status_filter,
        author_id=author_id,
        detected_from=detected_from,
        detected_to=detected_to,
        q=q,
    )
    return PaginatedResponse(
        items=[FaultRead.model_validate(f) for f in items],
        total=total,
        limit=limit,
        offset=offset,
    )

@faults_router.post("", response_model=FaultRead, status_code=status.HTTP_201_CREATED)
async def create_fault(
    payload: FaultCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("OPERATOR", "ENGINEER"))],
) -> FaultRead:
    service = FaultService(db)
    fault = await service.create_fault(payload, current_user)
    response.headers["Location"] = f"/api/v1/faults/{fault.id}"
    response.headers["ETag"] = f'"{fault.id}:{fault.version}"'
    return FaultRead.model_validate(fault)

@faults_router.get("/{fault_id}", response_model=FaultRead)
async def get_fault(
    fault_id: uuid.UUID,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FaultRead:
    service = FaultService(db)
    fault = await service.get_fault_by_id(fault_id, current_user)
    response.headers["ETag"] = f'"{fault.id}:{fault.version}"'
    return FaultRead.model_validate(fault)

@faults_router.patch("/{fault_id}", response_model=FaultRead)
async def update_fault(
    fault_id: uuid.UUID,
    payload: FaultUpdate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(require_role("OPERATOR", "ENGINEER"))],
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
) -> FaultRead:
    expected_version = parse_if_match_version(if_match, str(fault_id))
    service = FaultService(db)
    fault = await service.update_fault(fault_id, expected_version, payload, current_user)
    response.headers["ETag"] = f'"{fault.id}:{fault.version}"'
    return FaultRead.model_validate(fault)
