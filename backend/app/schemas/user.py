from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.user import UserRole, UserStatus

class UserBase(BaseModel):
    login: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: str = Field(min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.OPERATOR)

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)

class PasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)

class StatusUpdate(BaseModel):
    status: UserStatus

class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: UserStatus
    version: int
    created_at: datetime
    updated_at: datetime
