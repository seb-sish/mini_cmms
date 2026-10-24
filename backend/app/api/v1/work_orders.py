from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import parse_if_match_version, require_role
from app.db.models.user import User
from app.db.models.work_order import WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.db.session import get_session
from app.errors.handlers import AppException
from app.schemas.work_order import (
    CancelWorkOrderRequest,
    ChecklistItemUpdate,
    WorkChecklistItemRead,
    WorkOrderAssign,
    WorkOrderComplete,
    WorkOrderCreate,
    WorkOrderEventPage,
    WorkOrderPage,
    WorkOrderPatch,
    WorkOrderRead,
)
from app.services.work_order_service import WorkOrderService

work_orders_router = APIRouter(prefix="/work-orders", tags=["Work Orders"])

@work_orders_router.get(
    "",
    response_model=WorkOrderPage,
    status_code=status.HTTP_200_OK,
)
async def list_work_orders(
    equipment_id: Optional[uuid.UUID] = Query(None),
    type: Optional[WorkOrderType] = Query(None),
    status_filter: Optional[WorkOrderStatus] = Query(None, alias="status"),
    priority: Optional[WorkOrderPriority] = Query(None),
    assignee_id: Optional[uuid.UUID] = Query(None),
    fault_id: Optional[uuid.UUID] = Query(None),
    schedule_id: Optional[uuid.UUID] = Query(None),
    q: Optional[str] = Query(None, min_length=1, max_length=200),
    sort: str = Query("-created_at"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "TECHNICIAN", "OPERATOR")),
):
    if sort not in ("created_at", "-created_at", "status", "-status"):
        raise AppException(422, "VALIDATION_ERROR", f"Invalid sort parameter: {sort}")

    items, total = await WorkOrderService.list_work_orders(
        session=session,
        current_user=current_user,
        equipment_id=equipment_id,
        type=type,
        status=status_filter,
        priority=priority,
        assignee_id=assignee_id,
        fault_id=fault_id,
        schedule_id=schedule_id,
        q=q,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return WorkOrderPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )

@work_orders_router.post(
    "",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_order(
    payload: WorkOrderCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "OPERATOR")),
):
    wo = await WorkOrderService.create_work_order(session, current_user, payload)
    etag = f'"{wo.id}:{wo.version}"'
    response.headers["ETag"] = etag
    response.headers["Location"] = f"/api/v1/work-orders/{wo.id}"
    return wo

@work_orders_router.get(
    "/{work_order_id}",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def get_work_order(
    work_order_id: uuid.UUID,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "TECHNICIAN", "OPERATOR")),
):
    wo = await WorkOrderService.get_work_order(session, current_user, work_order_id)
    etag = f'"{wo.id}:{wo.version}"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.patch(
    "/{work_order_id}",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def patch_work_order(
    work_order_id: uuid.UUID,
    payload: WorkOrderPatch,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER")),
):
    expected_version = parse_if_match_version(if_match, str(work_order_id))
    wo = await WorkOrderService.patch_work_order(session, current_user, work_order_id, expected_version, payload)
    etag = f'"{wo.id}:{wo.version}"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.post(
    "/{work_order_id}/assign",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def assign_work_order(
    work_order_id: uuid.UUID,
    payload: WorkOrderAssign,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER")),
):
    wo = await WorkOrderService.assign_work_order(
        session, current_user, work_order_id, payload.assignee_id
    )
    etag = f'"{wo.id}:{wo.version}"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.post(
    "/{work_order_id}/reassign",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def reassign_work_order(
    work_order_id: uuid.UUID,
    payload: WorkOrderAssign,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER")),
):
    wo = await WorkOrderService.reassign_work_order(
        session, current_user, work_order_id, payload.assignee_id
    )
    etag = f'"{wo.id}:{wo.version}"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.post(
    "/{work_order_id}/start",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def start_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("TECHNICIAN")),
):
    raw_body = await request.body()
    if raw_body and raw_body.strip():
        raise AppException(422, "VALIDATION_ERROR", "Unexpected body in command")

    wo = await WorkOrderService.start_work_order(session, current_user, work_order_id)
    etag = f'\"{wo.id}:{wo.version}\"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.patch(
    "/{work_order_id}/checklist/{item_id}",
    response_model=WorkChecklistItemRead,
    status_code=status.HTTP_200_OK,
)
async def patch_checklist_item(
    work_order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: ChecklistItemUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("TECHNICIAN")),
):
    item, wo = await WorkOrderService.check_item(
        session=session,
        current_user=current_user,
        work_order_id=work_order_id,
        item_id=item_id,
        checked=payload.checked,
        comment=payload.comment,
        if_match=if_match,
    )
    etag = f'\"{wo.id}:{wo.version}\"'
    response.headers["ETag"] = etag
    return item

@work_orders_router.post(
    "/{work_order_id}/complete",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def complete_work_order(
    work_order_id: uuid.UUID,
    payload: WorkOrderComplete,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("TECHNICIAN")),
):
    wo = await WorkOrderService.complete_work_order(
        session=session,
        current_user=current_user,
        work_order_id=work_order_id,
        result=payload.result,
        replaced_parts=payload.replaced_parts,
    )
    etag = f'\"{wo.id}:{wo.version}\"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.post(
    "/{work_order_id}/close",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def close_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER")),
):
    raw_body = await request.body()
    if raw_body and raw_body.strip():
        raise AppException(422, "VALIDATION_ERROR", "Unexpected body in command")

    wo = await WorkOrderService.close_work_order(
        session=session,
        current_user=current_user,
        work_order_id=work_order_id,
    )
    etag = f'\"{wo.id}:{wo.version}\"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.post(
    "/{work_order_id}/cancel",
    response_model=WorkOrderRead,
    status_code=status.HTTP_200_OK,
)
async def cancel_work_order(
    work_order_id: uuid.UUID,
    payload: CancelWorkOrderRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER")),
):
    wo = await WorkOrderService.cancel_work_order(
        session, current_user, work_order_id, payload.reason
    )
    etag = f'\"{wo.id}:{wo.version}\"'
    response.headers["ETag"] = etag
    return wo

@work_orders_router.get(
    "/{work_order_id}/events",
    response_model=WorkOrderEventPage,
    status_code=status.HTTP_200_OK,
)
async def get_work_order_events(
    work_order_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "TECHNICIAN", "OPERATOR")),
):
    items, total = await WorkOrderService.list_events(
        session=session,
        current_user=current_user,
        work_order_id=work_order_id,
        limit=limit,
        offset=offset,
    )
    return WorkOrderEventPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
