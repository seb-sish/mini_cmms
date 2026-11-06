from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.equipment_service import get_company_today
from app.services.notification_service import NotificationService


async def generate_maintenance_notifications(ctx: dict[str, Any]) -> int:
    session: AsyncSession = ctx.get("session")
    should_close = False
    if session is None:
        session_maker = ctx.get("session_maker")
        if session_maker:
            session = session_maker()
            should_close = True
        else:
            raise ValueError("No session or session_maker in worker context")

    try:
        created_count = await NotificationService.generate(session, get_company_today())
        if created_count > 0:
            await session.commit()

        return created_count

    finally:
        if should_close and session is not None:
            await session.close()
