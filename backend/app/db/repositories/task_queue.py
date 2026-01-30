from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.task_queue import TaskQueue


class TaskQueueRepository(BaseRepository[TaskQueue]):
    """Repository for task queue operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(TaskQueue, db)

    async def count_by_task(self, task_type: str, task_id: UUID) -> int:
        """Count queued items for a specific task."""
        stmt = select(func.count(TaskQueue.id)).where(
            TaskQueue.task_type == task_type,
            TaskQueue.task_id == task_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_by_workspace(self, workspace_id: UUID, limit: int = 100) -> list[TaskQueue]:
        """Get queued tasks for a workspace, ordered by priority and time."""
        stmt = (
            select(TaskQueue)
            .where(TaskQueue.workspace_id == workspace_id)
            .order_by(TaskQueue.priority.desc(), TaskQueue.queued_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_task(self, task_type: str, task_id: UUID) -> int:
        """Delete all queued items for a task.

        Returns the number of items deleted.
        """
        # Count items first
        count = await self.count_by_task(task_type, task_id)

        # Delete all items
        stmt = delete(TaskQueue).where(
            TaskQueue.task_type == task_type,
            TaskQueue.task_id == task_id,
        )
        await self.db.execute(stmt)

        return count

    async def get_next_by_task(self, task_type: str, task_id: UUID) -> TaskQueue | None:
        """Get and remove next item from queue for a specific task."""
        stmt = (
            select(TaskQueue)
            .where(
                TaskQueue.task_type == task_type,
                TaskQueue.task_id == task_id,
            )
            .order_by(TaskQueue.priority.desc(), TaskQueue.queued_at.asc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()

        if item:
            await self.db.delete(item)

        return item

    async def delete_by_id(self, queue_item_id: UUID) -> bool:
        """Delete a queue item by ID.

        Returns True if item was deleted, False if not found.
        """
        stmt = select(TaskQueue).where(TaskQueue.id == queue_item_id)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()

        if item:
            await self.db.delete(item)
            return True

        return False
