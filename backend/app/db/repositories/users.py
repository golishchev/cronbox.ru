from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """Repository for user operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str, exclude_id: UUID | None = None) -> bool:
        """Check if email already exists."""
        stmt = select(User.id).where(User.email == email)
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_user(
        self,
        email: str,
        password_hash: str,
        name: str,
        is_active: bool = True,
        email_verified: bool = False,
    ) -> User:
        """Create a new user."""
        return await self.create(
            email=email,
            password_hash=password_hash,
            name=name,
            is_active=is_active,
            email_verified=email_verified,
        )

    async def update_telegram(
        self, user: User, telegram_id: int, telegram_username: str | None = None
    ) -> User:
        """Update user's Telegram info."""
        return await self.update(
            user,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
        )

    async def verify_email(self, user: User) -> User:
        """Mark user's email as verified."""
        return await self.update(user, email_verified=True)

    async def update_password(self, user: User, password_hash: str) -> User:
        """Update user's password."""
        return await self.update(user, password_hash=password_hash)
