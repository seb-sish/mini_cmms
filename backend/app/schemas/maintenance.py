from datetime import date, datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.db.models.maintenance_plan import PlanScope

class ChecklistItemTemplate(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[uuid.UUID] = None
    order: int = Field(default=0, ge=0, le=999)
    title: str = Field(default="", min_length=0, max_length=300)
    description: Optional[str] = Field(default=None, max_length=500)
    required: bool = True
    is_required: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # title vs description
            t = data.get("title")
            d = data.get("description")
            if not t and d:
                data["title"] = d
            elif not d and t:
                data["description"] = t
            elif not t and not d:
                data["title"] = "Check item"
                data["description"] = "Check item"

            # required vs is_required
            req = data.get("required")
            is_req = data.get("is_required")
            if req is not None and is_req is None:
                data["is_required"] = req
            elif is_req is not None and req is None:
                data["required"] = is_req
            elif req is None and is_req is None:
                data["required"] = True
                data["is_required"] = True
        return data

class MaintenancePlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: Optional[str] = None
    scope: PlanScope
    equipment_id: Optional[uuid.UUID] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    interval_days: int = Field(ge=1, le=3650)
    first_due_on: date
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    checklist: list[ChecklistItemTemplate] = Field(default_factory=list, min_length=1, max_length=100)

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

class MaintenancePlanUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    interval_days: Optional[int] = Field(default=None, ge=1, le=3650)
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    checklist: Optional[list[ChecklistItemTemplate]] = Field(default=None, min_length=1, max_length=100)

class MaintenancePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    scope: PlanScope
    equipment_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    interval_days: int
    first_due_on: date
    enabled: bool = True
    is_active: bool = True
    checklist: list[ChecklistItemTemplate]
    version: int
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_enabled(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("enabled", data.get("is_active", True))
            data["enabled"] = val
            data["is_active"] = val
        elif hasattr(data, "is_active"):
            val = getattr(data, "is_active")
            # If data is an ORM instance, Pydantic from_attributes will check attributes
            # We can return data and define properties, or use dictionary
        return data

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "MaintenancePlanRead":
        if hasattr(obj, "is_active") and not hasattr(obj, "enabled"):
            setattr(obj, "enabled", getattr(obj, "is_active"))
        return super().model_validate(obj, **kwargs)

class MaintenanceScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    equipment_id: uuid.UUID
    next_due_on: date
    last_completed_on: Optional[date] = None
    active: bool = True
    is_active: bool = True
    is_overdue: bool = False
    has_current_work_order: bool = False
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj: Any, **kwargs) -> "MaintenanceScheduleRead":
        if hasattr(obj, "is_active") and not hasattr(obj, "active"):
            setattr(obj, "active", getattr(obj, "is_active"))
        return super().model_validate(obj, **kwargs)
