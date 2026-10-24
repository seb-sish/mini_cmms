from datetime import date, datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.db.models.work_order import WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.db.models.work_order_event import WorkOrderEventType

class WorkChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    required: bool
    order: int
    checked: bool
    comment: Optional[str] = None
    checked_at: Optional[datetime] = None

class ChecklistItemUpdate(BaseModel):
    checked: bool
    comment: Optional[str] = None

class WorkOrderCreate(BaseModel):
    type: WorkOrderType
    equipment_id: uuid.UUID
    fault_id: Optional[uuid.UUID] = None
    schedule_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=2000)
    priority: WorkOrderPriority

    @model_validator(mode="after")
    def validate_type_dependencies(self) -> "WorkOrderCreate":
        if self.type == WorkOrderType.REPAIR:
            if self.schedule_id is not None:
                raise ValueError("schedule_id is forbidden for REPAIR work orders")
        elif self.type == WorkOrderType.PLANNED:
            if self.schedule_id is None:
                raise ValueError("schedule_id is required for PLANNED work orders")
            if self.fault_id is not None:
                raise ValueError("fault_id is forbidden for PLANNED work orders")
        return self

class WorkOrderPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=5, max_length=2000)
    priority: Optional[WorkOrderPriority] = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "WorkOrderPatch":
        if self.title is None and self.description is None and self.priority is None:
            raise ValueError("At least one field must be provided in PATCH")
        return self

class WorkOrderAssign(BaseModel):
    assignee_id: uuid.UUID

class WorkOrderComplete(BaseModel):
    result: str = Field(min_length=1, max_length=4000)
    replaced_parts: list[str] = Field(default_factory=list, max_length=100)

class CancelWorkOrderRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)

class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    type: WorkOrderType
    equipment_id: uuid.UUID
    fault_id: Optional[uuid.UUID] = None
    schedule_id: Optional[uuid.UUID] = None
    planned_due_on: Optional[date] = None
    title: str
    description: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    author_id: uuid.UUID
    assignee_id: Optional[uuid.UUID] = None
    checklist: list[WorkChecklistItemRead] = Field(default_factory=list)
    result: Optional[str] = None
    replaced_parts: list[str] = Field(default_factory=list)
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    version: int
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[uuid.UUID] = None
    cancellation_reason: Optional[str] = None

class WorkOrderPage(BaseModel):
    items: list[WorkOrderRead]
    total: int
    limit: int
    offset: int

class WorkOrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    work_order_id: uuid.UUID
    event_type: WorkOrderEventType
    actor_id: uuid.UUID
    occurred_at: datetime
    from_status: Optional[WorkOrderStatus] = None
    to_status: Optional[WorkOrderStatus] = None
    old_assignee_id: Optional[uuid.UUID] = None
    new_assignee_id: Optional[uuid.UUID] = None
    details: Optional[str] = None

class WorkOrderEventPage(BaseModel):
    items: list[WorkOrderEventRead]
    total: int
    limit: int
    offset: int

class WorkHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    work_order_id: uuid.UUID
    equipment_id: uuid.UUID
    plan_id: Optional[uuid.UUID] = None
    fault_id: Optional[uuid.UUID] = None
    technician_id: uuid.UUID
    completed_at: datetime
    closed_at: datetime
    result: str
    replaced_parts: list[str] = Field(default_factory=list)
    created_at: datetime
