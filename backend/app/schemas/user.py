import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.db.models.user import UserRole, UserStatus


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)
    role: UserRole


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    status: UserStatus | None = None
    new_password: str | None = Field(default=None, min_length=12, max_length=128)

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Role cannot be null")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Status cannot be null")
        return v

    @field_validator("new_password", mode="before")
    @classmethod
    def validate_new_password(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("New password cannot be null")
        return v

    @model_validator(mode="after")
    def validate_at_least_one(self) -> "UserPatch":
        if self.role is None and self.status is None and self.new_password is None:
            raise ValueError("At least one property must be specified in PATCH")
        return self


# Backwards compatibility aliases
UserUpdate = UserPatch


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    login: str
    role: UserRole
    status: UserStatus
    version: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            dt = dt.astimezone(UTC)
        return dt.isoformat().replace("+00:00", "Z")
