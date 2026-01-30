from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.subscription import Subscription, SubscriptionStatus


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for subscription operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Subscription, db)

    async def get_expiring_today(self, start_of_day: datetime, end_of_day: datetime) -> list[Subscription]:
        """Get active subscriptions expiring today."""
        stmt = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end >= start_of_day,
            Subscription.current_period_end < end_of_day,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_renewal(self, renewal_window: datetime) -> list[Subscription]:
        """Get active subscriptions pending auto-renewal."""
        stmt = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end <= renewal_window,
            Subscription.yookassa_payment_method_id.isnot(None),
            Subscription.cancel_at_period_end.is_(False),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_active(self, now: datetime) -> list[Subscription]:
        """Get active subscriptions that have expired."""
        stmt = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.current_period_end < now,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_scheduled_plan_change(self, now: datetime) -> list[Subscription]:
        """Get active subscriptions with scheduled plan changes."""
        stmt = select(Subscription).where(
            Subscription.scheduled_plan_id.isnot(None),
            Subscription.current_period_end <= now,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
