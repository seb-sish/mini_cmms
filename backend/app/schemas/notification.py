import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.notification import NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_id: uuid.UUID
    plan_id: uuid.UUID
    schedule_id: uuid.UUID
    equipment_id: uuid.UUID
    planned_due_on: date
    type: NotificationType
    message: str
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    total: int
    limit: int
    offset: int
