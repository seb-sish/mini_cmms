from datetime import date, datetime, timezone
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator
from app.db.models.equipment import EquipmentStatus


class EquipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200, pattern=r"\S")
    inventory_number: str = Field(min_length=1, max_length=64, pattern=r"\S")
    category: str = Field(min_length=1, max_length=100, pattern=r"\S")
    location: str = Field(min_length=1, max_length=200, pattern=r"\S")
    commissioned_on: date
    status: Optional[EquipmentStatus] = Field(default=EquipmentStatus.OPERATIONAL)


class EquipmentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=200, pattern=r"\S")
    inventory_number: Optional[str] = Field(default=None, min_length=1, max_length=64, pattern=r"\S")
    category: Optional[str] = Field(default=None, min_length=1, max_length=100, pattern=r"\S")
    location: Optional[str] = Field(default=None, min_length=1, max_length=200, pattern=r"\S")
    commissioned_on: Optional[date] = None
    status: Optional[EquipmentStatus] = None

    @field_validator("name", "inventory_number", "category", "location", "commissioned_on", "status", mode="before")
    @classmethod
    def validate_not_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Field cannot be null")
        return v

    @model_validator(mode="after")
    def validate_not_empty(self) -> "EquipmentPatch":
        fields = [self.name, self.inventory_number, self.category, self.location, self.commissioned_on, self.status]
        if all(f is None for f in fields):
            raise ValueError("At least one property must be specified in PATCH")
        return self


EquipmentUpdate = EquipmentPatch


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    name: str
    inventory_number: str
    category: str
    location: str
    commissioned_on: date
    status: EquipmentStatus
    archived_at: Optional[datetime] = None
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

    @field_serializer("archived_at")
    def serialize_archived_at(self, dt: Optional[datetime], _info) -> Optional[str]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
