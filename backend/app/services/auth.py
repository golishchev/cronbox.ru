from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
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
        """Link Telegram account by verification code.

        This method should validate the code from Redis and link the account.
        For now, it's a placeholder.
        """
        # TODO: Implement code validation from Redis
        # The code should be stored in Redis with user_id as value
        # After validation, update user's telegram_id and telegram_username
        return None

    def _create_tokens(self, user: User) -> TokenResponse:
        """Create access and refresh tokens for user."""
        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
