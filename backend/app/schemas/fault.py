from datetime import date, datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.db.models.fault import FaultSeverity, FaultStatus

class FaultCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    equipment_id: uuid.UUID
    description: str = Field(min_length=5, max_length=2000)
    detected_on: date
    severity: FaultSeverity

class FaultPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: Optional[str] = Field(default=None, min_length=5, max_length=2000)
    severity: Optional[FaultSeverity] = None
    detected_on: Optional[date] = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "FaultPatch":
        if self.description is None and self.severity is None and self.detected_on is None:
            raise ValueError("At least one property must be specified in PATCH")
        return self

FaultUpdate = FaultPatch

class FaultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_id: uuid.UUID
    description: str
    detected_on: date
    severity: FaultSeverity
    status: FaultStatus
    author_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime
