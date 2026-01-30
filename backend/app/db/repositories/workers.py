from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.worker import Worker, WorkerStatus


class WorkerRepository(BaseRepository[Worker]):
    """Repository for worker operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Worker, db)

    async def get_by_workspace(self, workspace_id: UUID) -> list[Worker]:
        """Get all workers for a workspace."""
        stmt = select(Worker).where(Worker.workspace_id == workspace_id).order_by(Worker.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_by_prefix(self, prefix: str) -> list[Worker]:
        """Get active workers by API key prefix."""
        stmt = select(Worker).where(Worker.api_key_prefix == prefix).where(Worker.is_active == True)  # noqa: E712
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_offline_by_heartbeat(self, cutoff: datetime) -> int:
        """Mark workers as offline if last heartbeat is before cutoff time.

        Returns the number of workers marked offline.
        """
        stmt = (
            update(Worker)
            .where(Worker.status != WorkerStatus.OFFLINE)
            .where(Worker.last_heartbeat < cutoff)
            .values(status=WorkerStatus.OFFLINE)
        )
        result = await self.db.execute(stmt)
        return result.rowcount or 0
