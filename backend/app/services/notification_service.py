from typing import Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification, NotificationType
from app.db.models.user import User, UserRole
from app.errors.handlers import AppException

class NotificationService:
    @classmethod
    async def list_notifications(
        cls,
        session: AsyncSession,
        current_user: User,
        type: Optional[NotificationType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        if current_user.role not in (UserRole.ENGINEER, UserRole.TECHNICIAN):
            raise AppException(403, "ACCESS_DENIED", "Access denied to notifications")

        conditions = [Notification.recipient_id == current_user.id]
        if type:
            conditions.append(Notification.type == type)

        count_q = select(func.count(Notification.id)).where(*conditions)
        total = (await session.execute(count_q)).scalar() or 0

        q = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = (await session.execute(q)).scalars().all()
        return list(items), total

    @classmethod
    async def get_notification(
        cls, session: AsyncSession, current_user: User, notification_id: uuid.UUID
    ) -> Notification:
        if current_user.role not in (UserRole.ENGINEER, UserRole.TECHNICIAN):
            raise AppException(403, "ACCESS_DENIED", "Access denied to notifications")

        notif = await session.get(Notification, notification_id)
        if not notif or notif.recipient_id != current_user.id:
            raise AppException(404, "NOT_FOUND", "Notification not found")

        return notif
