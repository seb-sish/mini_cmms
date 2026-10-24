from datetime import date, datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.fault import FaultStatus

class FaultCreate(BaseModel):
    equipment_id: uuid.UUID
    description: str = Field(min_length=1, max_length=1000)
    detected_on: date

class FaultUpdate(BaseModel):
    description: str = Field(min_length=1, max_length=1000)

class FaultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_id: uuid.UUID
    description: str
    detected_on: date
    status: FaultStatus
    author_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime
