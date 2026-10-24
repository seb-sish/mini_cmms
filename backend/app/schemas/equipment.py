from datetime import date, datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.db.models.equipment import EquipmentStatus

class EquipmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    inventory_number: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=100)
    commissioned_on: date

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, min_length=1, max_length=100)
    status: Optional[EquipmentStatus] = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "EquipmentPatch":
        if self.name is None and self.category is None and self.location is None and self.status is None:
            raise ValueError("At least one property must be specified in PATCH")
        return self

EquipmentUpdate = EquipmentPatch

class EquipmentRead(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: EquipmentStatus
    archived_at: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime
