from datetime import date, datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.db.models.maintenance_plan import PlanScope

class ChecklistItemTemplate(BaseModel):
    order: int = Field(ge=1)
    description: str = Field(min_length=1, max_length=500)
    is_required: bool = True

class MaintenancePlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    scope: PlanScope
    equipment_id: Optional[uuid.UUID] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    interval_days: int = Field(ge=1, le=3650)
    first_due_on: date
    checklist: list[ChecklistItemTemplate] = Field(default_factory=list)

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
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    interval_days: Optional[int] = Field(default=None, ge=1, le=3650)
    is_active: Optional[bool] = None
    checklist: Optional[list[ChecklistItemTemplate]] = None

class MaintenancePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    scope: PlanScope
    equipment_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    interval_days: int
    first_due_on: date
    is_active: bool
    checklist: list[ChecklistItemTemplate]
    version: int
    created_at: datetime
    updated_at: datetime

class MaintenanceScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    equipment_id: uuid.UUID
    next_due_on: date
    last_completed_on: Optional[date] = None
    is_active: bool
    is_overdue: bool = False
    version: int
    created_at: datetime
    updated_at: datetime
