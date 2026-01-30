from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.notification_template import NotificationTemplate


class NotificationTemplateRepository(BaseRepository[NotificationTemplate]):
    """Repository for notification template operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(NotificationTemplate, db)

    async def get_by_code_and_language(
        self,
        code: str,
        language: str,
        channel: str,
    ) -> NotificationTemplate | None:
        """Get active template by code, language and channel."""
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.code == code,
            NotificationTemplate.language == language,
            NotificationTemplate.channel == channel,
            NotificationTemplate.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_ordered(self) -> list[NotificationTemplate]:
        """Get all templates ordered by code, language, channel."""
        stmt = select(NotificationTemplate).order_by(
            NotificationTemplate.code,
            NotificationTemplate.language,
            NotificationTemplate.channel,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_code_language_channel(
        self,
        code: str,
        language: str,
        channel: str,
    ) -> NotificationTemplate | None:
        """Find template by code, language and channel (regardless of active status)."""
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.code == code,
            NotificationTemplate.language == language,
            NotificationTemplate.channel == channel,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
