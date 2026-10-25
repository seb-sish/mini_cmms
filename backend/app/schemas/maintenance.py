from datetime import date, datetime, timezone
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator
from app.db.models.maintenance_plan import PlanScope


class ChecklistTemplateItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=300, pattern=r"\S")
    required: bool
    order: int = Field(ge=0, le=999)


# Backwards compatibility alias
ChecklistItemTemplate = ChecklistTemplateItemInput


class ChecklistTemplateItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    title: str = Field(min_length=2, max_length=300, pattern=r"\S")
    required: bool
    order: int = Field(ge=0, le=999)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            item_id = data.get("id") or uuid.uuid4()
            title = data.get("title") or data.get("description", "")
            req = data.get("required") if data.get("required") is not None else data.get("is_required", True)
            order = data.get("order", 0)
            return {"id": item_id, "title": title, "required": req, "order": order}
        return data


class MaintenancePlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200, pattern=r"\S")
    scope: PlanScope
    equipment_id: Optional[uuid.UUID] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100, pattern=r"\S")
    interval_days: int = Field(ge=1, le=3650)
    first_due_on: date
    checklist: list[ChecklistTemplateItemInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_scope_fields(self) -> "MaintenancePlanCreate":
        if self.scope == PlanScope.EQUIPMENT:
            if not self.equipment_id:
                raise ValueError("equipment_id is required when scope is EQUIPMENT")
            if self.category is not None:
                raise ValueError("category must be null when scope is EQUIPMENT")
        elif self.scope == PlanScope.CATEGORY:
            if not self.category or not self.category.strip():
                raise ValueError("category is required when scope is CATEGORY")
            if self.equipment_id is not None:
                raise ValueError("equipment_id must be null when scope is CATEGORY")
        return self


class MaintenancePlanPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=2, max_length=200, pattern=r"\S")
    interval_days: Optional[int] = Field(default=None, ge=1, le=3650)
    enabled: Optional[bool] = None
    checklist: Optional[list[ChecklistTemplateItemInput]] = Field(default=None, min_length=1, max_length=100)

    @field_validator("name", "interval_days", "enabled", "checklist", mode="before")
    @classmethod
    def validate_not_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Field cannot be null")
        return v

    @model_validator(mode="after")
    def validate_not_empty(self) -> "MaintenancePlanPatch":
        if self.name is None and self.interval_days is None and self.enabled is None and self.checklist is None:
            raise ValueError("At least one property must be specified in PATCH")
        return self


MaintenancePlanUpdate = MaintenancePlanPatch


class MaintenancePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    name: str
    scope: PlanScope
    equipment_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    interval_days: int
    first_due_on: date
    enabled: bool = True
    checklist: list[ChecklistTemplateItem]
    created_at: datetime
    updated_at: datetime
    version: int

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "MaintenancePlanRead":
        if hasattr(obj, "is_active") and not hasattr(obj, "enabled"):
            setattr(obj, "enabled", getattr(obj, "is_active"))
        return super().model_validate(obj, **kwargs)


class MaintenanceScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    plan_id: uuid.UUID
    equipment_id: uuid.UUID
    last_completed_on: Optional[date] = None
    next_due_on: date
    is_overdue: bool = False
    has_current_work_order: bool = False
    active: bool = True
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "MaintenanceScheduleRead":
        if hasattr(obj, "is_active") and not hasattr(obj, "active"):
            setattr(obj, "active", getattr(obj, "is_active"))
        return super().model_validate(obj, **kwargs)
