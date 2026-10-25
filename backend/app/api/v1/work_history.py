import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_role
from app.db.models.user import User
from app.db.session import get_session
from app.schemas.work_order import WorkHistoryPage, WorkHistoryRead
from app.services.work_order_service import WorkHistoryService

work_history_router = APIRouter(prefix="/work-history", tags=["Work History"])


@work_history_router.get(
    "",
    response_model=WorkHistoryPage,
    status_code=status.HTTP_200_OK,
)
async def list_work_history(
    equipment_id: uuid.UUID | None = Query(None),
    technician_id: uuid.UUID | None = Query(None),
    completed_from: date | None = Query(None),
    completed_to: date | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "TECHNICIAN", "OPERATOR")),
):
    items, total = await WorkHistoryService.list_work_history(
        session=session,
        current_user=current_user,
        equipment_id=equipment_id,
        technician_id=technician_id,
        completed_from=completed_from,
        completed_to=completed_to,
        limit=limit,
        offset=offset,
    )
    return WorkHistoryPage(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@work_history_router.get(
    "/{history_id}",
    response_model=WorkHistoryRead,
    status_code=status.HTTP_200_OK,
)
async def get_work_history(
    history_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role("ENGINEER", "TECHNICIAN", "OPERATOR")),
):
    return await WorkHistoryService.get_work_history(session, current_user, history_id)
