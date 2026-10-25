from datetime import date, datetime, timezone
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator
from app.db.models.fault import FaultSeverity, FaultStatus


class FaultCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment_id: uuid.UUID
    description: str = Field(min_length=5, max_length=2000, pattern=r"\S")
    detected_on: date
    severity: FaultSeverity


class FaultPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Optional[str] = Field(default=None, min_length=5, max_length=2000, pattern=r"\S")
    severity: Optional[FaultSeverity] = None
    detected_on: Optional[date] = None

    @field_validator("description", "severity", "detected_on", mode="before")
    @classmethod
    def validate_not_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Field cannot be null")
        return v

    @model_validator(mode="after")
    def validate_not_empty(self) -> "FaultPatch":
        if self.description is None and self.severity is None and self.detected_on is None:
            raise ValueError("At least one property must be specified in PATCH")
        return self


FaultUpdate = FaultPatch


class FaultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

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

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
