from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.cron_task import CronTask, TaskStatus


class CronTaskRepository(BaseRepository[CronTask]):
    """Repository for cron task operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(CronTask, db)

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> list[CronTask]:
        """Get all cron tasks for a workspace."""
        stmt = (
            select(CronTask)
            .where(CronTask.workspace_id == workspace_id)
            .order_by(CronTask.created_at.desc())
        )
        if is_active is not None:
            stmt = stmt.where(CronTask.is_active == is_active)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_workspace(
        self,
        workspace_id: UUID,
        is_active: bool | None = None,
    ) -> int:
        """Count cron tasks for a workspace."""
        stmt = select(func.count()).select_from(CronTask).where(CronTask.workspace_id == workspace_id)
        if is_active is not None:
            stmt = stmt.where(CronTask.is_active == is_active)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_due_tasks(self, now: datetime, limit: int = 100) -> list[CronTask]:
        """Get tasks due for execution."""
        stmt = (
            select(CronTask)
            .where(
                and_(
                    CronTask.is_active == True,
                    CronTask.is_paused == False,
                    CronTask.next_run_at <= now,
                )
            )
            .order_by(CronTask.next_run_at)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tasks_needing_next_run_update(self, limit: int = 100) -> list[CronTask]:
        """Get active tasks that need next_run_at calculated."""
        stmt = (
            select(CronTask)
            .where(
                and_(
                    CronTask.is_active == True,
                    CronTask.is_paused == False,
                    CronTask.next_run_at == None,
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_last_run(
        self,
        task: CronTask,
        status: TaskStatus,
        run_at: datetime,
        next_run_at: datetime | None,
    ) -> CronTask:
        """Update task after execution."""
        task.last_run_at = run_at
        task.last_status = status
        task.next_run_at = next_run_at

        if status == TaskStatus.SUCCESS:
            task.consecutive_failures = 0
        elif status == TaskStatus.FAILED:
            task.consecutive_failures += 1

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def pause(self, task: CronTask) -> CronTask:
        """Pause a task."""
        task.is_paused = True
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def resume(self, task: CronTask, next_run_at: datetime) -> CronTask:
        """Resume a task."""
        task.is_paused = False
        task.next_run_at = next_run_at
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def deactivate(self, task: CronTask) -> CronTask:
        """Deactivate a task."""
        task.is_active = False
        task.next_run_at = None
        await self.db.flush()
        await self.db.refresh(task)
        return task
