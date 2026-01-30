from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.payment import Payment, PaymentStatus


class PaymentRepository(BaseRepository[Payment]):
    """Repository for payment operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Payment, db)

    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Payment]:
        """Get payment history for a user."""
        stmt = (
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_old_pending(self, cutoff_time: datetime) -> list[Payment]:
        """Get old pending payments created before cutoff time."""
        stmt = select(Payment).where(
            Payment.status == PaymentStatus.PENDING,
            Payment.created_at < cutoff_time,
            Payment.yookassa_payment_id.isnot(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
