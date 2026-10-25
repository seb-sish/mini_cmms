import uuid
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.db.models.work_order import WorkOrderPriority, WorkOrderStatus, WorkOrderType
from app.db.models.work_order_event import WorkOrderEventType
from app.schemas.base import Trimmed


def _serialize_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.isoformat().replace("+00:00", "Z")


class WorkChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    title: str
    required: bool
    order: int
    checked: bool
    comment: str | None = None
    checked_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            item_id = data.get("id") or uuid.uuid4()
            title = data.get("title") or data.get("description", "")
            req = data.get("required") if data.get("required") is not None else data.get("is_required", True)
            order = data.get("order", 0)
            checked = data.get("checked") if data.get("checked") is not None else data.get("is_done", False)
            return {
                "id": item_id,
                "title": title,
                "required": req,
                "order": order,
                "checked": checked,
                "comment": data.get("comment"),
                "checked_at": data.get("checked_at"),
            }
        return data

    @field_serializer("checked_at")
    def serialize_checked_at(self, dt: datetime | None, _info) -> str | None:
        return _serialize_dt(dt)


class ChecklistItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checked: bool
    comment: str | None = Field(default=None, max_length=1000)


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: WorkOrderType
    equipment_id: uuid.UUID
    fault_id: uuid.UUID | None = None
    schedule_id: uuid.UUID | None = None
    title: Trimmed(3, 200) = Field(pattern=r"\S")
    description: Trimmed(5, 2000) = Field(pattern=r"\S")
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
    model_config = ConfigDict(extra="forbid")

    title: Trimmed(3, 200) | None = Field(default=None, pattern=r"\S")
    description: Trimmed(5, 2000) | None = Field(default=None, pattern=r"\S")
    priority: WorkOrderPriority | None = None

    @field_validator("title", "description", "priority", mode="before")
    @classmethod
    def validate_not_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Field cannot be null")
        return v

    @model_validator(mode="after")
    def validate_not_empty(self) -> "WorkOrderPatch":
        if self.title is None and self.description is None and self.priority is None:
            raise ValueError("At least one field must be provided in PATCH")
        return self


class WorkOrderAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignee_id: uuid.UUID


AssignRequest = WorkOrderAssign


class WorkOrderComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: Trimmed(1, 4000) = Field(pattern=r"\S")
    replaced_parts: list[Trimmed(1, 200)] = Field(default_factory=list, max_length=100)


class CancelWorkOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000, pattern=r"\S")


class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    number: str
    type: WorkOrderType
    equipment_id: uuid.UUID
    fault_id: uuid.UUID | None = None
    schedule_id: uuid.UUID | None = None
    planned_due_on: date | None = None
    title: str
    description: str
    priority: WorkOrderPriority
    status: WorkOrderStatus
    author_id: uuid.UUID
    assignee_id: uuid.UUID | None = None
    checklist: list[WorkChecklistItemRead] = Field(default_factory=list)
    result: str | None = None
    replaced_parts: list[str] = Field(default_factory=list)
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    version: int
    cancelled_at: datetime | None = None
    cancelled_by: uuid.UUID | None = None
    cancellation_reason: str | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_req_datetime(self, dt: datetime, _info) -> str:
        res = _serialize_dt(dt)
        assert res is not None
        return res

    @field_serializer("completed_at", "closed_at", "cancelled_at")
    def serialize_opt_datetime(self, dt: datetime | None, _info) -> str | None:
        return _serialize_dt(dt)


class WorkOrderPage(BaseModel):
    items: list[WorkOrderRead]
    total: int
    limit: int
    offset: int


class WorkOrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    work_order_id: uuid.UUID
    event_type: WorkOrderEventType
    actor_id: uuid.UUID
    occurred_at: datetime
    from_status: WorkOrderStatus | None = None
    to_status: WorkOrderStatus | None = None
    old_assignee_id: uuid.UUID | None = None
    new_assignee_id: uuid.UUID | None = None
    details: str | None = None

    @field_serializer("occurred_at")
    def serialize_occurred_at(self, dt: datetime, _info) -> str:
        res = _serialize_dt(dt)
        assert res is not None
        return res


class WorkOrderEventPage(BaseModel):
    items: list[WorkOrderEventRead]
    total: int
    limit: int
    offset: int


class WorkHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    work_order_id: uuid.UUID
    equipment_id: uuid.UUID
    plan_id: uuid.UUID | None = None
    fault_id: uuid.UUID | None = None
    technician_id: uuid.UUID
    completed_at: datetime
    closed_at: datetime
    result: str
    replaced_parts: list[str] = Field(default_factory=list)
    created_at: datetime

    @field_serializer("completed_at", "closed_at", "created_at")
    def serialize_history_datetime(self, dt: datetime, _info) -> str:
        res = _serialize_dt(dt)
        assert res is not None
        return res


class WorkHistoryPage(BaseModel):
    items: list[WorkHistoryRead]
    total: int
    limit: int
    offset: int
