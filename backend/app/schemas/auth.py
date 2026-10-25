from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(min_length=32, max_length=256, description="Opaque bearer authentication token")
    token_type: str = Field(default="Bearer", description="OAuth2 token type")
    expires_at: datetime = Field(description="Token expiration timestamp in UTC")
    user: UserRead

    @field_serializer("expires_at")
    def serialize_expires_at(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


AuthResponse = TokenResponse
