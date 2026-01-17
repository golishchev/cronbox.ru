import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
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
OTP_PREFIX = "otp:"
OTP_ATTEMPTS_PREFIX = "otp_attempts:"
OTP_COOLDOWN_PREFIX = "otp_cooldown:"

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
        """
        Authenticate user and return tokens.

        Security features:
        - Account lockout after repeated failed attempts
        - Timing-safe password comparison
        - Failed attempt tracking
        """
        user = await self.user_repo.get_by_email(email)

        # Check if account is locked (even if user doesn't exist, continue to prevent enumeration)
        if user and user.is_locked():
            remaining_minutes = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60) + 1
            logger.warning(
                "Login attempt on locked account",
                email=email,
                locked_until=user.locked_until.isoformat() if user.locked_until else None,
            )
            raise UnauthorizedError(f"Account is temporarily locked. Try again in {remaining_minutes} minutes.")

        # Verify password (timing-safe via bcrypt)
        password_valid = user is not None and verify_password(password, user.password_hash)

        if not password_valid:
            # Track failed login attempt
            if user:
                await self._handle_failed_login(user)
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        # Successful login - reset failed attempts and update last login
        if user.failed_login_attempts > 0:
            await self._reset_failed_attempts(user)

        # Update last login timestamp
        await self._update_last_login(user)

        # Generate tokens
        tokens = self._create_tokens(user)

        logger.info("User logged in successfully", user_id=str(user.id))
        return user, tokens

    async def _handle_failed_login(self, user: User) -> None:
        """Handle failed login attempt - increment counter and possibly lock account."""
        user.failed_login_attempts += 1

        # Check if we should lock the account
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.account_lockout_minutes)
            logger.warning(
                "Account locked due to too many failed attempts",
                user_id=str(user.id),
                failed_attempts=user.failed_login_attempts,
                locked_until=user.locked_until.isoformat(),
            )
        else:
            logger.info(
                "Failed login attempt",
                user_id=str(user.id),
                failed_attempts=user.failed_login_attempts,
                max_attempts=settings.max_failed_login_attempts,
            )

        await self.db.commit()

    async def _reset_failed_attempts(self, user: User) -> None:
        """Reset failed login attempts after successful login."""
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.db.commit()

    async def _update_last_login(self, user: User) -> None:
        """Update user's last login timestamp."""
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)

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

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Change user's password."""
        if not verify_password(current_password, user.password_hash):
            raise BadRequestError("Current password is incorrect")

        password_hash = get_password_hash(new_password)
        await self.user_repo.update_password(user, password_hash)

    async def link_telegram_by_code(self, code: str, telegram_id: int, telegram_username: str | None) -> User | None:
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

    async def request_password_reset(self, email: str) -> tuple[str, User] | None:
        """Request password reset and return (token, user) tuple (or None if user not found)."""
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
        return token, user

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

    async def request_otp(self, email: str) -> tuple[str, int, User | None]:
        """
        Request OTP code for passwordless login.

        Returns (code, expires_in, user) tuple.
        User is returned if exists (for language preference), None otherwise.
        Code should be sent via email to the user.
        Raises BadRequestError if rate limited.
        """
        email_lower = email.lower()

        # Check cooldown (rate limiting)
        cooldown_key = f"{OTP_COOLDOWN_PREFIX}{email_lower}"
        if await redis_client.exists(cooldown_key):
            ttl = await redis_client.ttl(cooldown_key)
            raise BadRequestError(f"Please wait {ttl} seconds before requesting a new code")

        # Try to get existing user for language preference
        user = await self.user_repo.get_by_email(email_lower)

        # Generate OTP code
        code = "".join([str(secrets.randbelow(10)) for _ in range(settings.otp_code_length)])

        # Store OTP in Redis
        otp_key = f"{OTP_PREFIX}{email_lower}"
        expire_seconds = settings.otp_expire_minutes * 60
        await redis_client.set(otp_key, code, expire=expire_seconds)

        # Reset attempts counter
        attempts_key = f"{OTP_ATTEMPTS_PREFIX}{email_lower}"
        await redis_client.delete(attempts_key)

        # Set cooldown
        await redis_client.set(cooldown_key, "1", expire=settings.otp_request_cooldown_seconds)

        logger.info("OTP code generated", email=email_lower)
        return code, expire_seconds, user

    async def verify_otp(self, email: str, code: str) -> tuple[User, TokenResponse]:
        """
        Verify OTP code and login/register user.

        Returns user and tokens on success.
        Raises UnauthorizedError on invalid/expired code.
        """
        email_lower = email.lower()
        otp_key = f"{OTP_PREFIX}{email_lower}"
        attempts_key = f"{OTP_ATTEMPTS_PREFIX}{email_lower}"

        # Check attempts
        attempts = await redis_client.get(attempts_key)
        current_attempts = int(attempts) if attempts else 0

        if current_attempts >= settings.otp_max_attempts:
            # Delete the OTP to force requesting a new one
            await redis_client.delete(otp_key)
            await redis_client.delete(attempts_key)
            raise UnauthorizedError("Too many failed attempts. Please request a new code.")

        # Get stored OTP
        stored_code = await redis_client.get(otp_key)

        if not stored_code:
            raise UnauthorizedError("Invalid or expired code")

        # Timing-safe comparison
        if not secrets.compare_digest(code, stored_code):
            # Increment attempts
            await redis_client.incr(attempts_key)
            await redis_client.expire(attempts_key, settings.otp_expire_minutes * 60)
            remaining = settings.otp_max_attempts - current_attempts - 1
            logger.warning(
                "Invalid OTP attempt",
                email=email_lower,
                attempts=current_attempts + 1,
                remaining=remaining,
            )
            raise UnauthorizedError(f"Invalid code. {remaining} attempts remaining.")

        # OTP is valid - delete it (one-time use)
        await redis_client.delete(otp_key)
        await redis_client.delete(attempts_key)

        # Get or create user
        user = await self.user_repo.get_by_email(email_lower)

        if not user:
            # Create new user (passwordless registration)
            # Generate a random password hash (user won't know it, OTP-only login)
            random_password = secrets.token_urlsafe(32)
            password_hash = get_password_hash(random_password)

            # Extract name from email (before @)
            name = email_lower.split("@")[0].replace(".", " ").title()

            user = await self.user_repo.create_user(
                email=email_lower,
                password_hash=password_hash,
                name=name,
            )
            logger.info("New user created via OTP", user_id=str(user.id))

        if not user.is_active:
            raise UnauthorizedError("Account is disabled")

        # Auto-verify email since they received the OTP
        if not user.email_verified:
            user = await self.user_repo.verify_email(user)

        # Update last login timestamp
        await self._update_last_login(user)

        # Generate tokens
        tokens = self._create_tokens(user)

        logger.info("User logged in via OTP", user_id=str(user.id))
        return user, tokens

    def _create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
