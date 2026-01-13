from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for decoded token payload."""

    sub: str  # user_id
    email: str | None = None
    exp: int
    type: str  # "access" or "refresh"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class RegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)


class RegisterResponse(BaseModel):
    """Schema for registration response."""

    user: UserResponse
    tokens: TokenResponse


class LoginResponse(BaseModel):
    """Schema for login response."""

    user: UserResponse
    tokens: TokenResponse


class PasswordChangeRequest(BaseModel):
    """Schema for password change."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str


class TelegramConnectRequest(BaseModel):
    """Schema for generating Telegram link code."""

    pass  # No fields needed, uses current user


class TelegramConnectResponse(BaseModel):
    """Schema for Telegram connect response."""

    code: str
    expires_in: int  # seconds
    bot_username: str


class TelegramLinkRequest(BaseModel):
    """Schema for linking Telegram account (from bot)."""

    code: str
    telegram_id: int
    telegram_username: str | None = None


class DeleteAccountRequest(BaseModel):
    """Schema for account deletion confirmation."""

    confirmation: str = Field(..., description="Must be 'delete' to confirm account deletion")
