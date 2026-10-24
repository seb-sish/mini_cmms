from datetime import date, datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.work_order import WorkOrderStatus, WorkOrderType

class WorkChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order: int
    description: str
    is_required: bool
    is_checked: bool
    checked_at: Optional[datetime] = None
    comment: Optional[str] = None

class WorkChecklistItemUpdate(BaseModel):
    is_checked: bool
    comment: Optional[str] = None

class WorkOrderCreate(BaseModel):
    type: WorkOrderType
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    equipment_id: Optional[uuid.UUID] = None
    fault_id: Optional[uuid.UUID] = None
    schedule_id: Optional[uuid.UUID] = None

class WorkOrderAssign(BaseModel):
    assignee_id: uuid.UUID

class WorkOrderComplete(BaseModel):
    result: str = Field(min_length=1)

class WorkOrderCancel(BaseModel):
    reason: str = Field(min_length=1)

class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    type: WorkOrderType
    status: WorkOrderStatus
    title: str
    description: Optional[str] = None
    equipment_id: uuid.UUID
    fault_id: Optional[uuid.UUID] = None
    schedule_id: Optional[uuid.UUID] = None
    planned_due_on: Optional[date] = None
    author_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None
    cancelled_reason: Optional[str] = None
    result: Optional[str] = None
    checklist: list[WorkChecklistItemRead] = Field(default_factory=list)
    version: int
    created_at: datetime
    updated_at: datetime

class WorkHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    work_order_id: uuid.UUID
    equipment_id: uuid.UUID
    type: WorkOrderType
    title: str
    completed_at: datetime
    closed_at: datetime
    assignee_id: uuid.UUID
    closed_by: uuid.UUID
    result: str
    checklist_snapshot: list[dict[str, Any]]
    created_at: datetime
