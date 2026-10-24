from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.user import UserRead

class LoginRequest(BaseModel):
    login: str = Field(min_length=1)
    password: str = Field(min_length=1)

class AuthResponse(BaseModel):
    token: str = Field(description="Opaque bearer authentication token")
    expires_at: datetime = Field(description="Token expiration timestamp in UTC")
    user: UserRead
