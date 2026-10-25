import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.db.models.notification import NotificationType
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.notification import NotificationPage, NotificationRead
from app.services.notification_service import NotificationService

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get(
    "",
    response_model=NotificationPage,
    status_code=status.HTTP_200_OK,
)
async def list_notifications(
    type: NotificationType | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "TECHNICIAN")),
):
    items, total = await NotificationService.list_notifications(
        session=session,
        current_user=current_user,
        type=type,
        limit=limit,
        offset=offset,
    )
    return NotificationPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@notifications_router.get(
    "/{notification_id}",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
)
async def get_notification(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "TECHNICIAN")),
):
    return await NotificationService.get_notification(
        session=session,
        current_user=current_user,
        notification_id=notification_id,
    )
