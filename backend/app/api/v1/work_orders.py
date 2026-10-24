import uuid
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrderStatus
from app.db.session import get_session
from app.errors.handlers import AppException
from app.schemas.work_order import WorkOrderCreate, WorkOrderPatch, WorkOrderRead
from app.services.work_order_service import WorkOrderService

work_orders_router = APIRouter(prefix="/work-orders", tags=["Work Orders"])

@work_orders_router.post(
    "",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_work_order(
    payload: WorkOrderCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    if not if_match:
        raise AppException(428, "PRECONDITION_REQUIRED", "If-Match header is required")

    if current_user.role not in (UserRole.ADMIN, UserRole.ENGINEER):
        raise AppException(403, "ACCESS_DENIED", "Only engineer or admin can modify work order")

    wo = await WorkOrderService.get_work_order(session, current_user, work_order_id)

    expected_etag = f'"{wo.id}:{wo.version}"'
    cleaned_if_match = if_match.strip('"')
    cleaned_expected = expected_etag.strip('"')
    if cleaned_if_match != cleaned_expected:
        raise AppException(412, "VERSION_CONFLICT", "ETag mismatch")

    if wo.status != WorkOrderStatus.CREATED:
        raise AppException(409, "INVALID_WORK_ORDER_STATE", "Cannot patch work order after assignment")

    if payload.title is not None:
        wo.title = payload.title
    if payload.description is not None:
        wo.description = payload.description
    if payload.priority is not None:
        wo.priority = payload.priority

    wo.version += 1
    session.add(wo)
    await session.commit()
    await session.refresh(wo)

    etag = f'"{wo.id}:{wo.version}"'
    response.headers["ETag"] = etag
    return wo
