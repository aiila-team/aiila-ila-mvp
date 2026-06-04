from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str | None = None
    role: str | None = None
    is_active: bool = True
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
