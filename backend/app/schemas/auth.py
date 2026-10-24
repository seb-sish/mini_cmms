from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserRead

class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)

class TokenResponse(BaseModel):
    access_token: str = Field(min_length=32, max_length=256, description="Opaque bearer authentication token")
    token_type: str = Field(default="Bearer", description="OAuth2 token type")
    expires_at: datetime = Field(description="Token expiration timestamp in UTC")
    user: UserRead
    token: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.token is None:
            self.token = self.access_token

AuthResponse = TokenResponse
