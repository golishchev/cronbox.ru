import secrets
import structlog
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, UnauthorizedError
from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.repositories.users import UserRepository
from app.models.user import User
from app.schemas.auth import TokenResponse

logger = structlog.get_logger()

# Redis key prefixes
EMAIL_VERIFY_PREFIX = "email_verify:"
PASSWORD_RESET_PREFIX = "password_reset:"
TELEGRAM_LINK_PREFIX = "telegram_link:"

# Token expiration times (in seconds)
EMAIL_VERIFY_EXPIRE = 24 * 60 * 60  # 24 hours
PASSWORD_RESET_EXPIRE = 60 * 60  # 1 hour
TELEGRAM_LINK_EXPIRE = 10 * 60  # 10 minutes


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, email: str, password: str, name: str) -> tuple[User, TokenResponse]:
        """Register a new user."""
        # Check if email already exists
        if await self.user_repo.email_exists(email):
            raise ConflictError("Email already registered")

        # Create user
        password_hash = get_password_hash(password)
        user = await self.user_repo.create_user(
            email=email,
            password_hash=password_hash,
            name=name,
        )

        # Generate tokens
        tokens = self._create_tokens(user)

        return user, tokens

    async def login(self, email: str, password: str) -> tuple[User, TokenResponse]:
        """Authenticate user and return tokens."""
        user = await self.user_repo.get_by_email(email)

        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        # Generate tokens
        tokens = self._create_tokens(user)

        return user, tokens

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        payload = decode_token(refresh_token)

        if payload is None:
            raise UnauthorizedError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        user_id = UUID(payload["sub"])
        user = await self.user_repo.get_by_id(user_id)

        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        return self._create_tokens(user)

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """Change user's password."""
        if not verify_password(current_password, user.password_hash):
            raise BadRequestError("Current password is incorrect")

        password_hash = get_password_hash(new_password)
        await self.user_repo.update_password(user, password_hash)

    async def link_telegram_by_code(
        self, code: str, telegram_id: int, telegram_username: str | None
    ) -> User | None:
        """Link Telegram account by verification code."""
        # Get user_id from Redis
        redis_key = f"{TELEGRAM_LINK_PREFIX}{code}"
        user_id_str = await redis_client.get(redis_key)

        if not user_id_str:
            logger.warning("Invalid or expired Telegram link code", code=code)
            return None

        # Delete the code (one-time use)
        await redis_client.delete(redis_key)

        # Get user and update Telegram info
        user_id = UUID(user_id_str)
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            logger.error("User not found for Telegram link", user_id=user_id_str)
            return None

        # Check if Telegram already linked to another account
        existing = await self.user_repo.get_by_telegram_id(telegram_id)
        if existing and existing.id != user.id:
            logger.warning(
                "Telegram already linked to another account",
                telegram_id=telegram_id,
                existing_user_id=str(existing.id),
            )
            return None

        # Update user's Telegram info
        user = await self.user_repo.update_telegram(user, telegram_id, telegram_username)
        logger.info(
            "Telegram account linked successfully",
            user_id=str(user.id),
            telegram_id=telegram_id,
        )
        return user

    async def generate_telegram_link_code(self, user: User) -> str:
        """Generate a code for linking Telegram account."""
        # Generate 6-digit code
        code = "".join([str(secrets.randbelow(10)) for _ in range(6)])

        # Store in Redis: code -> user_id
        redis_key = f"{TELEGRAM_LINK_PREFIX}{code}"
        await redis_client.set(redis_key, str(user.id), expire=TELEGRAM_LINK_EXPIRE)

        logger.info("Generated Telegram link code", user_id=str(user.id))
        return code

    async def send_email_verification(self, user: User) -> str:
        """Generate and send email verification token."""
        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Store in Redis: token -> user_id
        redis_key = f"{EMAIL_VERIFY_PREFIX}{token}"
        await redis_client.set(redis_key, str(user.id), expire=EMAIL_VERIFY_EXPIRE)

        logger.info("Generated email verification token", user_id=str(user.id))
        return token

    async def verify_email(self, token: str) -> User:
        """Verify email using token."""
        redis_key = f"{EMAIL_VERIFY_PREFIX}{token}"
        user_id_str = await redis_client.get(redis_key)

        if not user_id_str:
            raise BadRequestError("Invalid or expired verification token")

        # Delete the token (one-time use)
        await redis_client.delete(redis_key)

        # Get and update user
        user_id = UUID(user_id_str)
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        if user.email_verified:
            raise BadRequestError("Email already verified")

        user = await self.user_repo.verify_email(user)
        logger.info("Email verified successfully", user_id=str(user.id))
        return user

    async def request_password_reset(self, email: str) -> str | None:
        """Request password reset and return token (or None if user not found)."""
        user = await self.user_repo.get_by_email(email)

        if not user:
            # Don't reveal if user exists
            logger.info("Password reset requested for non-existent email", email=email)
            return None

        if not user.is_active:
            logger.warning("Password reset requested for inactive user", email=email)
            return None

        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Store in Redis: token -> user_id
        redis_key = f"{PASSWORD_RESET_PREFIX}{token}"
        await redis_client.set(redis_key, str(user.id), expire=PASSWORD_RESET_EXPIRE)

        logger.info("Generated password reset token", user_id=str(user.id))
        return token

    async def reset_password(self, token: str, new_password: str) -> User:
        """Reset password using token."""
        redis_key = f"{PASSWORD_RESET_PREFIX}{token}"
        user_id_str = await redis_client.get(redis_key)

        if not user_id_str:
            raise BadRequestError("Invalid or expired reset token")

        # Delete the token (one-time use)
        await redis_client.delete(redis_key)

        # Get and update user
        user_id = UUID(user_id_str)
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundError("User not found")

        if not user.is_active:
            raise BadRequestError("Account is disabled")

        password_hash = get_password_hash(new_password)
        user = await self.user_repo.update_password(user, password_hash)
        logger.info("Password reset successfully", user_id=str(user.id))
        return user

    async def unlink_telegram(self, user: User) -> User:
        """Unlink Telegram account from user."""
        if not user.telegram_id:
            raise BadRequestError("No Telegram account linked")

        user = await self.user_repo.update(user, telegram_id=None, telegram_username=None)
        logger.info("Telegram account unlinked", user_id=str(user.id))
        return user

    def _create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
