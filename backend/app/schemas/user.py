from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: EmailStr | None = None
    preferred_language: str | None = Field(None, pattern="^(en|ru)$")


class UserResponse(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_id: int | None = None
    telegram_username: str | None = None
    email_verified: bool
    is_active: bool
    preferred_language: str = "ru"
    created_at: datetime
    updated_at: datetime


class UserInDB(UserResponse):
    """Schema for user in database (includes password hash)."""

    password_hash: str
    is_superuser: bool
