from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.db.models.user import UserRole, UserStatus

class UserCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    login: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)
    role: UserRole
    full_name: Optional[str] = Field(default=None, max_length=100)

class UserPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    new_password: Optional[str] = Field(default=None, min_length=12, max_length=128)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_at_least_one(self) -> "UserPatch":
        if self.role is None and self.status is None and self.new_password is None and self.full_name is None:
            raise ValueError("At least one property must be specified in PATCH")
        return self

# Backwards compatibility aliases
UserUpdate = UserPatch

class PasswordUpdate(BaseModel):
    password: str = Field(min_length=12, max_length=128)

class StatusUpdate(BaseModel):
    status: UserStatus

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    login: str
    role: UserRole
    status: UserStatus
    version: int
    created_at: datetime
    updated_at: datetime
    full_name: Optional[str] = None
