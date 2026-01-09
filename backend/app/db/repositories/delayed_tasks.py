from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.cron_task import TaskStatus
from app.models.delayed_task import DelayedTask
from app.models.workspace import Workspace


class DelayedTaskRepository(BaseRepository[DelayedTask]):
    """Repository for delayed task operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(DelayedTask, db)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: TaskStatus | None = None,
    ) -> list[DelayedTask]:
        """Get all delayed tasks for a workspace."""
        stmt = (
            select(DelayedTask)
            .where(DelayedTask.workspace_id == workspace_id)
            .order_by(DelayedTask.execute_at.desc())
        )
        if status is not None:
            stmt = stmt.where(DelayedTask.status == status)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: UUID,
        status: TaskStatus | None = None,
    ) -> int:
        """Count delayed tasks for a workspace."""
        stmt = (
            select(func.count())
            .select_from(DelayedTask)
            .where(DelayedTask.workspace_id == workspace_id)
        )
        if status is not None:
            stmt = stmt.where(DelayedTask.status == status)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> DelayedTask | None:
        """Get task by idempotency key."""
        stmt = select(DelayedTask).where(
            and_(
                DelayedTask.workspace_id == workspace_id,
                DelayedTask.idempotency_key == idempotency_key,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_due_tasks(self, now: datetime, limit: int = 100) -> list[DelayedTask]:
        """Get tasks due for execution.

        Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
        when multiple scheduler instances are running.
        Excludes tasks from blocked workspaces.
        """
        stmt = (
            select(DelayedTask)
            .join(Workspace, DelayedTask.workspace_id == Workspace.id)
            .where(
                and_(
                    DelayedTask.status == TaskStatus.PENDING,
                    DelayedTask.execute_at <= now,
                    Workspace.is_blocked.is_(False),
                )
            )
            .order_by(DelayedTask.execute_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_count_this_month(
        self,
        workspace_id: UUID,
        month_start: datetime,
    ) -> int:
        """Count pending delayed tasks created this month."""
        stmt = (
            select(func.count())
            .select_from(DelayedTask)
            .where(
                and_(
                    DelayedTask.workspace_id == workspace_id,
                    DelayedTask.created_at >= month_start,
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def mark_running(self, task: DelayedTask) -> DelayedTask:
        """Mark task as running."""
        task.status = TaskStatus.RUNNING
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def mark_completed(
        self,
        task: DelayedTask,
        status: TaskStatus,
        executed_at: datetime,
    ) -> DelayedTask:
        """Mark task as completed (success or failed)."""
        task.status = status
        task.executed_at = executed_at
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def increment_retry(self, task: DelayedTask) -> DelayedTask:
        """Increment retry attempt counter."""
        task.retry_attempt += 1
        task.status = TaskStatus.PENDING
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def cancel(self, task: DelayedTask) -> DelayedTask:
        """Cancel a pending task."""
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            await self.db.flush()
            await self.db.refresh(task)
        return task

    async def update(
        self,
        task: DelayedTask,
        name: str | None = None,
        tags: list[str] | None = None,
        url: str | None = None,
        method: str | None = None,
        headers: dict | None = None,
        body: str | None = None,
        execute_at: datetime | None = None,
        timeout_seconds: int | None = None,
        retry_count: int | None = None,
        retry_delay_seconds: int | None = None,
        callback_url: str | None = None,
    ) -> DelayedTask:
        """Update a pending delayed task."""
        if name is not None:
            task.name = name
        if tags is not None:
            task.tags = tags
        if url is not None:
            task.url = url
        if method is not None:
            task.method = method
        if headers is not None:
            task.headers = headers
        if body is not None:
            task.body = body
        if execute_at is not None:
            task.execute_at = execute_at
        if timeout_seconds is not None:
            task.timeout_seconds = timeout_seconds
        if retry_count is not None:
            task.retry_count = retry_count
        if retry_delay_seconds is not None:
            task.retry_delay_seconds = retry_delay_seconds
        if callback_url is not None:
            task.callback_url = callback_url

        await self.db.flush()
        await self.db.refresh(task)
        return task
