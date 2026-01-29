"""Overlap Prevention Service for managing concurrent task executions."""

from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cron_task import CronTask, OverlapPolicy
from app.models.task_chain import TaskChain
from app.models.task_queue import TaskQueue
from app.models.workspace import Workspace

logger = structlog.get_logger()


class OverlapAction(str, Enum):
    """Result of overlap check."""

    ALLOW = "allow"  # Execution can proceed
    SKIP = "skip"  # Execution should be skipped
    QUEUE = "queue"  # Execution was added to queue
    QUEUED_FULL = "queued_full"  # Queue is full, execution skipped


class OverlapResult:
    """Result of overlap prevention check."""

    def __init__(
        self,
        action: OverlapAction,
        message: str | None = None,
        queue_position: int | None = None,
    ):
        self.action = action
        self.message = message
        self.queue_position = queue_position

    @property
    def should_execute(self) -> bool:
        return self.action == OverlapAction.ALLOW

    @property
    def skipped_reason(self) -> str | None:
        if self.action == OverlapAction.SKIP:
            return "overlap_skipped"
        elif self.action == OverlapAction.QUEUED_FULL:
            return "queue_full"
        return None


class OverlapService:
    """Service for managing overlap prevention."""

    async def check_cron_task_overlap(
        self,
        db: AsyncSession,
        task: CronTask,
    ) -> OverlapResult:
        """Check if cron task can be executed based on overlap policy.

        Args:
            db: Database session
            task: Cron task to check

        Returns:
            OverlapResult indicating whether execution should proceed
        """
        # Allow policy - always execute
        if task.overlap_policy == OverlapPolicy.ALLOW:
            await self._increment_running_instances(db, "cron", task.id)
            return OverlapResult(OverlapAction.ALLOW)

        # Check current running instances
        current_instances = task.running_instances

        # If under max_instances limit, allow execution
        if current_instances < task.max_instances:
            await self._increment_running_instances(db, "cron", task.id)
            return OverlapResult(
                OverlapAction.ALLOW,
                f"Running {current_instances + 1}/{task.max_instances} instances",
            )

        # Max instances reached - handle based on policy
        if task.overlap_policy == OverlapPolicy.SKIP:
            await self._increment_skipped_count(db, task.workspace_id)
            logger.info(
                "Skipping cron task due to overlap",
                task_id=str(task.id),
                task_name=task.name,
                running_instances=current_instances,
                max_instances=task.max_instances,
            )
            return OverlapResult(
                OverlapAction.SKIP,
                f"Task already running ({current_instances}/{task.max_instances} instances)",
            )

        # Queue policy - add to queue if not full
        if task.overlap_policy == OverlapPolicy.QUEUE:
            return await self._add_to_queue(
                db=db,
                workspace_id=task.workspace_id,
                task_type="cron",
                task_id=task.id,
                task_name=task.name,
                max_queue_size=task.max_queue_size,
            )

        return OverlapResult(OverlapAction.ALLOW)

    async def check_chain_overlap(
        self,
        db: AsyncSession,
        chain: TaskChain,
        initial_variables: dict | None = None,
    ) -> OverlapResult:
        """Check if task chain can be executed based on overlap policy.

        Args:
            db: Database session
            chain: Task chain to check
            initial_variables: Initial variables for chain execution

        Returns:
            OverlapResult indicating whether execution should proceed
        """
        # Allow policy - always execute
        if chain.overlap_policy == OverlapPolicy.ALLOW:
            await self._increment_running_instances(db, "chain", chain.id)
            return OverlapResult(OverlapAction.ALLOW)

        # Check current running instances
        current_instances = chain.running_instances

        # If under max_instances limit, allow execution
        if current_instances < chain.max_instances:
            await self._increment_running_instances(db, "chain", chain.id)
            return OverlapResult(
                OverlapAction.ALLOW,
                f"Running {current_instances + 1}/{chain.max_instances} instances",
            )

        # Max instances reached - handle based on policy
        if chain.overlap_policy == OverlapPolicy.SKIP:
            await self._increment_skipped_count(db, chain.workspace_id)
            logger.info(
                "Skipping chain due to overlap",
                chain_id=str(chain.id),
                chain_name=chain.name,
                running_instances=current_instances,
                max_instances=chain.max_instances,
            )
            return OverlapResult(
                OverlapAction.SKIP,
                f"Chain already running ({current_instances}/{chain.max_instances} instances)",
            )

        # Queue policy - add to queue if not full
        if chain.overlap_policy == OverlapPolicy.QUEUE:
            return await self._add_to_queue(
                db=db,
                workspace_id=chain.workspace_id,
                task_type="chain",
                task_id=chain.id,
                task_name=chain.name,
                max_queue_size=chain.max_queue_size,
                initial_variables=initial_variables,
            )

        return OverlapResult(OverlapAction.ALLOW)

    async def release_cron_task(
        self,
        db: AsyncSession,
        task: CronTask,
    ) -> None:
        """Release running instance slot for cron task and check queue.

        Args:
            db: Database session
            task: Cron task that finished execution
        """
        await self._decrement_running_instances(db, "cron", task.id)

        # Check if there are queued executions
        if task.overlap_policy == OverlapPolicy.QUEUE:
            queued_task = await self._pop_from_queue(
                db=db,
                task_type="cron",
                task_id=task.id,
            )
            if queued_task:
                logger.info(
                    "Processing queued cron task",
                    task_id=str(task.id),
                    queue_item_id=str(queued_task.id),
                )

    async def release_chain(
        self,
        db: AsyncSession,
        chain: TaskChain,
    ) -> TaskQueue | None:
        """Release running instance slot for chain and check queue.

        Args:
            db: Database session
            chain: Task chain that finished execution

        Returns:
            Queued task if one was found, None otherwise
        """
        await self._decrement_running_instances(db, "chain", chain.id)

        # Check if there are queued executions
        if chain.overlap_policy == OverlapPolicy.QUEUE:
            return await self._pop_from_queue(
                db=db,
                task_type="chain",
                task_id=chain.id,
            )
        return None

    async def get_queue_size(
        self,
        db: AsyncSession,
        task_type: str,
        task_id: UUID,
    ) -> int:
        """Get current queue size for a task.

        Args:
            db: Database session
            task_type: Type of task ('cron' or 'chain')
            task_id: Task ID

        Returns:
            Number of items in queue
        """
        from sqlalchemy import func

        result = await db.execute(
            select(func.count(TaskQueue.id)).where(
                TaskQueue.task_type == task_type,
                TaskQueue.task_id == task_id,
            )
        )
        return result.scalar() or 0

    async def get_queued_tasks(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        limit: int = 50,
    ) -> list[TaskQueue]:
        """Get all queued tasks for a workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            limit: Maximum number of items to return

        Returns:
            List of queued tasks
        """
        result = await db.execute(
            select(TaskQueue)
            .where(TaskQueue.workspace_id == workspace_id)
            .order_by(TaskQueue.priority.desc(), TaskQueue.queued_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def remove_from_queue(
        self,
        db: AsyncSession,
        queue_item_id: UUID,
    ) -> bool:
        """Remove a task from the queue.

        Args:
            db: Database session
            queue_item_id: Queue item ID

        Returns:
            True if item was removed, False if not found
        """
        result = await db.execute(select(TaskQueue).where(TaskQueue.id == queue_item_id))
        queue_item = result.scalar_one_or_none()
        if queue_item:
            await db.delete(queue_item)
            return True
        return False

    async def clear_task_queue(
        self,
        db: AsyncSession,
        task_type: str,
        task_id: UUID,
    ) -> int:
        """Clear all queued executions for a task.

        Args:
            db: Database session
            task_type: Type of task ('cron' or 'chain')
            task_id: Task ID

        Returns:
            Number of items removed
        """
        from sqlalchemy import delete, func

        # Count items first
        count_result = await db.execute(
            select(func.count(TaskQueue.id)).where(
                TaskQueue.task_type == task_type,
                TaskQueue.task_id == task_id,
            )
        )
        count = count_result.scalar() or 0

        # Delete all items
        await db.execute(
            delete(TaskQueue).where(
                TaskQueue.task_type == task_type,
                TaskQueue.task_id == task_id,
            )
        )

        return count

    async def cleanup_stale_instances(
        self,
        db: AsyncSession,
        timeout_threshold: datetime | None = None,
    ) -> int:
        """Cleanup stale running instances that exceed execution timeout.

        Args:
            db: Database session
            timeout_threshold: Datetime before which instances are considered stale.
                             If None, uses individual task timeouts.

        Returns:
            Number of instances cleaned up
        """
        cleaned = 0

        # Cleanup cron tasks with execution_timeout set
        if timeout_threshold is None:
            # Use individual task timeouts
            result = await db.execute(
                select(CronTask).where(
                    CronTask.running_instances > 0,
                    CronTask.execution_timeout.isnot(None),
                )
            )
            tasks = result.scalars().all()

            for task in tasks:
                if task.last_run_at:
                    timeout_at = task.last_run_at + timedelta(seconds=task.execution_timeout)
                    if datetime.utcnow() > timeout_at:
                        task.running_instances = 0
                        cleaned += 1
                        logger.warning(
                            "Reset stale running instances for cron task",
                            task_id=str(task.id),
                            last_run_at=task.last_run_at.isoformat(),
                            timeout_seconds=task.execution_timeout,
                        )

            # Cleanup chains with execution_timeout set
            chain_result = await db.execute(
                select(TaskChain).where(
                    TaskChain.running_instances > 0,
                    TaskChain.execution_timeout.isnot(None),
                )
            )
            chains = chain_result.scalars().all()

            for chain in chains:
                if chain.last_run_at:
                    timeout_at = chain.last_run_at + timedelta(seconds=chain.execution_timeout)
                    if datetime.utcnow() > timeout_at:
                        chain.running_instances = 0
                        cleaned += 1
                        logger.warning(
                            "Reset stale running instances for chain",
                            chain_id=str(chain.id),
                            last_run_at=chain.last_run_at.isoformat(),
                            timeout_seconds=chain.execution_timeout,
                        )

        return cleaned

    async def _increment_running_instances(
        self,
        db: AsyncSession,
        task_type: str,
        task_id: UUID,
    ) -> None:
        """Increment running instances counter."""
        if task_type == "cron":
            await db.execute(
                update(CronTask).where(CronTask.id == task_id).values(running_instances=CronTask.running_instances + 1)
            )
        elif task_type == "chain":
            await db.execute(
                update(TaskChain)
                .where(TaskChain.id == task_id)
                .values(running_instances=TaskChain.running_instances + 1)
            )

    async def _decrement_running_instances(
        self,
        db: AsyncSession,
        task_type: str,
        task_id: UUID,
    ) -> None:
        """Decrement running instances counter (minimum 0)."""
        if task_type == "cron":
            await db.execute(
                update(CronTask)
                .where(CronTask.id == task_id, CronTask.running_instances > 0)
                .values(running_instances=CronTask.running_instances - 1)
            )
        elif task_type == "chain":
            await db.execute(
                update(TaskChain)
                .where(TaskChain.id == task_id, TaskChain.running_instances > 0)
                .values(running_instances=TaskChain.running_instances - 1)
            )

    async def _increment_skipped_count(
        self,
        db: AsyncSession,
        workspace_id: UUID,
    ) -> None:
        """Increment skipped executions counter for workspace."""
        await db.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(executions_skipped=Workspace.executions_skipped + 1)
        )

    async def _increment_queued_count(
        self,
        db: AsyncSession,
        workspace_id: UUID,
    ) -> None:
        """Increment queued executions counter for workspace."""
        await db.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(executions_queued=Workspace.executions_queued + 1)
        )

    async def _add_to_queue(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        task_type: str,
        task_id: UUID,
        task_name: str | None,
        max_queue_size: int,
        initial_variables: dict | None = None,
    ) -> OverlapResult:
        """Add task execution to queue."""
        # Check current queue size
        queue_size = await self.get_queue_size(db, task_type, task_id)

        if queue_size >= max_queue_size:
            await self._increment_skipped_count(db, workspace_id)
            logger.info(
                "Queue full, skipping task",
                task_type=task_type,
                task_id=str(task_id),
                queue_size=queue_size,
                max_queue_size=max_queue_size,
            )
            return OverlapResult(
                OverlapAction.QUEUED_FULL,
                f"Queue full ({queue_size}/{max_queue_size})",
            )

        # Add to queue
        queue_item = TaskQueue(
            workspace_id=workspace_id,
            task_type=task_type,
            task_id=task_id,
            task_name=task_name,
            priority=0,
            queued_at=datetime.utcnow(),
            initial_variables=initial_variables or {},
        )
        db.add(queue_item)
        await self._increment_queued_count(db, workspace_id)

        logger.info(
            "Task added to queue",
            task_type=task_type,
            task_id=str(task_id),
            queue_position=queue_size + 1,
        )

        return OverlapResult(
            OverlapAction.QUEUE,
            f"Added to queue (position {queue_size + 1})",
            queue_position=queue_size + 1,
        )

    async def _pop_from_queue(
        self,
        db: AsyncSession,
        task_type: str,
        task_id: UUID,
    ) -> TaskQueue | None:
        """Get and remove next item from queue."""
        result = await db.execute(
            select(TaskQueue)
            .where(
                TaskQueue.task_type == task_type,
                TaskQueue.task_id == task_id,
            )
            .order_by(TaskQueue.priority.desc(), TaskQueue.queued_at.asc())
            .limit(1)
        )
        queue_item = result.scalar_one_or_none()

        if queue_item:
            await db.delete(queue_item)

        return queue_item


# Singleton instance
overlap_service = OverlapService()
