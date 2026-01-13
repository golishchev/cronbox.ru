import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status

from app.api.deps import DB, CurrentUser
from app.config import settings
from app.db.repositories.users import UserRepository
from app.schemas.auth import (
    DeleteAccountRequest,
    EmailVerificationRequest,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TelegramConnectResponse,
    TokenResponse,
)
from app.schemas.user import UserLogin, UserResponse, UserUpdate
from app.services.auth import TELEGRAM_LINK_EXPIRE, AuthService
from app.services.email import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Avatar upload settings
UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads" / "avatars"
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(data: RegisterRequest, db: DB):
    """Register a new user account."""
    auth_service = AuthService(db)
    user, tokens = await auth_service.register(
        email=data.email,
        password=data.password,
        name=data.name,
    )

    return RegisterResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post("/login", response_model=LoginResponse)
async def login(data: UserLogin, db: DB):
    """Login with email and password."""
    auth_service = AuthService(db)
    user, tokens = await auth_service.login(
        email=data.email,
        password=data.password,
    )

    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: DB):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_tokens(data.refresh_token)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get current authenticated user profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(data: UserUpdate, current_user: CurrentUser, db: DB):
    """Update current user profile."""
    user_repo = UserRepository(db)

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return UserResponse.model_validate(current_user)

    updated_user = await user_repo.update(current_user, **update_data)
    return UserResponse.model_validate(updated_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: PasswordChangeRequest,
    current_user: CurrentUser,
    db: DB,
):
    """Change current user's password."""
    auth_service = AuthService(db)
    await auth_service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: CurrentUser):
    """Logout current user.

    Note: With JWT tokens, logout is handled client-side by removing the token.
    This endpoint can be used to invalidate refresh tokens if needed.
    """
    # In a more sophisticated implementation, you could:
    # 1. Add the refresh token to a blacklist in Redis
    # 2. Invalidate all user sessions
    # For now, this is a no-op since JWT is stateless
    pass


@router.post("/send-verification", status_code=status.HTTP_204_NO_CONTENT)
async def send_verification_email(
    current_user: CurrentUser,
    db: DB,
    background_tasks: BackgroundTasks,
):
    """Send email verification link to current user."""
    if current_user.email_verified:
        return  # Already verified, no action needed

    auth_service = AuthService(db)
    token = await auth_service.send_email_verification(current_user)

    # Send email in background
    verification_url = f"{settings.frontend_url}/#/verify-email?token={token}"

    async def send_email():
        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Подтверждение email</h2>
            <p>Здравствуйте, {current_user.name}!</p>
            <p>Для подтверждения вашего email перейдите по ссылке:</p>
            <a href="{verification_url}" style="display: inline-block; padding: 12px 24px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px;">
                Подтвердить email
            </a>
            <p style="margin-top: 16px; color: #666;">
                Или скопируйте ссылку: {verification_url}
            </p>
            <p style="margin-top: 24px; color: #666; font-size: 12px;">
                Ссылка действительна 24 часа. Если вы не запрашивали это письмо, просто проигнорируйте его.
            </p>
        </div>
        """
        await email_service.send_email(
            to=current_user.email,
            subject="[CronBox] Подтверждение email",
            html=html,
        )

    background_tasks.add_task(send_email)


@router.post("/verify-email", response_model=UserResponse)
async def verify_email(data: EmailVerificationRequest, db: DB):
    """Verify email using token from verification link."""
    auth_service = AuthService(db)
    user = await auth_service.verify_email(data.token)
    return UserResponse.model_validate(user)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(
    data: PasswordResetRequest,
    db: DB,
    background_tasks: BackgroundTasks,
):
    """Request password reset. Sends email if user exists."""
    auth_service = AuthService(db)
    token = await auth_service.request_password_reset(data.email)

    if token:
        # Send email in background (only if user exists)
        reset_url = f"{settings.cors_origins[0]}/#/reset-password?token={token}"

        async def send_email():
            html = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Сброс пароля</h2>
                <p>Вы запросили сброс пароля для вашего аккаунта CronBox.</p>
                <p>Для установки нового пароля перейдите по ссылке:</p>
                <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px;">
                    Сбросить пароль
                </a>
                <p style="margin-top: 16px; color: #666;">
                    Или скопируйте ссылку: {reset_url}
                </p>
                <p style="margin-top: 24px; color: #666; font-size: 12px;">
                    Ссылка действительна 1 час. Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
                </p>
            </div>
            """
            await email_service.send_email(
                to=data.email,
                subject="[CronBox] Сброс пароля",
                html=html,
            )

        background_tasks.add_task(send_email)

    # Always return success to prevent email enumeration


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: PasswordResetConfirm, db: DB):
    """Reset password using token from reset link."""
    auth_service = AuthService(db)
    await auth_service.reset_password(data.token, data.new_password)


@router.post("/telegram/connect", response_model=TelegramConnectResponse)
async def telegram_connect(current_user: CurrentUser, db: DB):
    """Generate a code for linking Telegram account."""
    auth_service = AuthService(db)
    code = await auth_service.generate_telegram_link_code(current_user)

    # Get bot username from token (format: 123456:ABC...)
    bot_username = "cronbox_bot"  # Default fallback
    if settings.telegram_bot_token:
        # We can't get username from token directly, should be configured
        pass

    return TelegramConnectResponse(
        code=code,
        expires_in=TELEGRAM_LINK_EXPIRE,
        bot_username=bot_username,
    )


@router.delete("/telegram/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def telegram_disconnect(current_user: CurrentUser, db: DB):
    """Unlink Telegram account from current user."""
    auth_service = AuthService(db)
    await auth_service.unlink_telegram(current_user)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile,
    current_user: CurrentUser,
    db: DB,
):
    """Upload user avatar image.

    Accepts JPEG, PNG, GIF, WebP images up to 2 MB.
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: JPEG, PNG, GIF, WebP",
        )

    # Read file and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 2 MB",
        )

    # Create upload directory if not exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Delete old avatar if exists
    if current_user.avatar_url:
        old_filename = current_user.avatar_url.split("/")[-1]
        old_path = UPLOAD_DIR / old_filename
        if old_path.exists():
            os.remove(old_path)

    # Generate unique filename
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = UPLOAD_DIR / filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Update user avatar_url
    avatar_url = f"/uploads/avatars/{filename}"
    user_repo = UserRepository(db)
    updated_user = await user_repo.update(current_user, avatar_url=avatar_url)

    return UserResponse.model_validate(updated_user)


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
async def delete_avatar(current_user: CurrentUser, db: DB):
    """Delete user avatar."""
    if not current_user.avatar_url:
        return  # No avatar to delete

    # Delete file
    filename = current_user.avatar_url.split("/")[-1]
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        os.remove(file_path)

    # Update user
    user_repo = UserRepository(db)
    await user_repo.update(current_user, avatar_url=None)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    data: DeleteAccountRequest,
    current_user: CurrentUser,
    db: DB,
):
    """Soft-delete user account.

    Requires typing 'delete' as confirmation.
    This deactivates the account but preserves data.
    """
    if data.confirmation.lower() != "delete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type 'delete' to confirm account deletion",
        )

    user_repo = UserRepository(db)
    await user_repo.update(current_user, is_active=False)
