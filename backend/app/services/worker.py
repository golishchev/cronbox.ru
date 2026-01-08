"""Worker service for external task execution."""
import json
from datetime import datetime, timezone
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import get_password_hash, verify_password
from app.models.cron_task import CronTask, TaskStatus
from app.models.delayed_task import DelayedTask
from app.models.execution import Execution
from app.models.worker import Worker, WorkerStatus
from app.schemas.worker import (
    WorkerCreate,
    WorkerHeartbeat,
    WorkerTaskInfo,
    WorkerTaskResult,
    WorkerUpdate,
)

logger = structlog.get_logger()

# Redis keys
WORKER_TASKS_KEY = "worker:{worker_id}:tasks"  # List of pending tasks for worker
WORKER_TASK_DATA_KEY = "worker:task:{task_id}"  # Task data hash


class WorkerService:
    """Service for managing external workers and their tasks."""

    async def create_worker(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        data: WorkerCreate,
    ) -> tuple[Worker, str]:
        """
        Create a new worker and return it with the API key.

        The API key is only returned once at creation time.
        """
        # Generate API key
        api_key = Worker.generate_api_key()
        api_key_hash = get_password_hash(api_key)
        api_key_prefix = Worker.get_key_prefix(api_key)

        worker = Worker(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description,
            region=data.region,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            status=WorkerStatus.OFFLINE,
        )

        db.add(worker)
        await db.commit()
        await db.refresh(worker)

        logger.info("Worker created", worker_id=str(worker.id), workspace_id=str(workspace_id))

        return worker, api_key

    async def get_worker_by_id(
        self,
        db: AsyncSession,
        worker_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Worker | None:
        """Get worker by ID, optionally filtered by workspace."""
        query = select(Worker).where(Worker.id == worker_id)
        if workspace_id:
            query = query.where(Worker.workspace_id == workspace_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_workers_by_workspace(
        self,
        db: AsyncSession,
        workspace_id: UUID,
    ) -> list[Worker]:
        """Get all workers for a workspace."""
        result = await db.execute(
            select(Worker)
            .where(Worker.workspace_id == workspace_id)
            .order_by(Worker.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_worker(
        self,
        db: AsyncSession,
        worker: Worker,
        data: WorkerUpdate,
    ) -> Worker:
        """Update worker settings."""
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(worker, field, value)

        await db.commit()
        await db.refresh(worker)

        return worker

    async def delete_worker(
        self,
        db: AsyncSession,
        worker: Worker,
    ) -> None:
        """Delete a worker."""
        await db.delete(worker)
        await db.commit()

        logger.info("Worker deleted", worker_id=str(worker.id))

    async def regenerate_api_key(
        self,
        db: AsyncSession,
        worker: Worker,
    ) -> str:
        """Regenerate API key for a worker."""
        api_key = Worker.generate_api_key()
        worker.api_key_hash = get_password_hash(api_key)
        worker.api_key_prefix = Worker.get_key_prefix(api_key)

        await db.commit()

        logger.info("Worker API key regenerated", worker_id=str(worker.id))

        return api_key

    async def authenticate_worker(
        self,
        db: AsyncSession,
        api_key: str,
    ) -> Worker | None:
        """Authenticate a worker by API key."""
        # Get prefix to narrow down search
        prefix = Worker.get_key_prefix(api_key)

        result = await db.execute(
            select(Worker)
            .where(Worker.api_key_prefix == prefix)
            .where(Worker.is_active == True)  # noqa: E712
        )
        workers = result.scalars().all()

        # Verify full API key
        for worker in workers:
            if verify_password(api_key, worker.api_key_hash):
                return worker

        return None

    async def update_heartbeat(
        self,
        db: AsyncSession,
        worker: Worker,
        heartbeat: WorkerHeartbeat,
    ) -> None:
        """Update worker heartbeat and status."""
        worker.last_heartbeat = datetime.now(timezone.utc)
        worker.status = heartbeat.status

        await db.commit()

    # === Task queue management ===

    async def enqueue_task_for_worker(
        self,
        worker_id: UUID,
        task_info: WorkerTaskInfo,
    ) -> None:
        """Add a task to the worker's queue."""
        redis: Redis = await get_redis()

        # Store task data
        task_key = WORKER_TASK_DATA_KEY.format(task_id=task_info.task_id)
        await redis.set(
            task_key,
            task_info.model_dump_json(),
            ex=3600 * 24,  # 24 hour TTL
        )

        # Add to worker's task list
        queue_key = WORKER_TASKS_KEY.format(worker_id=worker_id)
        await redis.rpush(queue_key, str(task_info.task_id))

        logger.info(
            "Task enqueued for worker",
            worker_id=str(worker_id),
            task_id=str(task_info.task_id),
        )

    async def poll_tasks(
        self,
        worker_id: UUID,
        max_tasks: int = 10,
    ) -> list[WorkerTaskInfo]:
        """Get pending tasks for a worker."""
        redis: Redis = await get_redis()
        queue_key = WORKER_TASKS_KEY.format(worker_id=worker_id)

        tasks = []

        # Pop tasks from queue
        for _ in range(max_tasks):
            task_id = await redis.lpop(queue_key)
            if not task_id:
                break

            # Get task data
            task_key = WORKER_TASK_DATA_KEY.format(task_id=task_id.decode())
            task_data = await redis.get(task_key)

            if task_data:
                tasks.append(WorkerTaskInfo.model_validate_json(task_data))
                # Delete task data after retrieval
                await redis.delete(task_key)

        return tasks

    async def process_task_result(
        self,
        db: AsyncSession,
        worker: Worker,
        result: WorkerTaskResult,
    ) -> bool:
        """Process task execution result from worker."""
        try:
            # Determine success/failure
            is_success = result.error is None and result.status_code is not None

            # Create execution record
            execution = Execution(
                workspace_id=worker.workspace_id,
                cron_task_id=result.task_id if result.task_type == "cron" else None,
                delayed_task_id=result.task_id if result.task_type == "delayed" else None,
                status=TaskStatus.SUCCESS if is_success else TaskStatus.FAILED,
                started_at=result.started_at,
                finished_at=result.finished_at,
                duration_ms=result.duration_ms,
                request_url="",  # Will be set from task
                request_method="",  # Will be set from task
                response_status=result.status_code,
                response_body=result.response_body[:10000] if result.response_body else None,
                response_headers=result.response_headers,
                error_message=result.error,
            )

            # Update task based on type
            if result.task_type == "cron":
                task = await db.get(CronTask, result.task_id)
                if task:
                    execution.request_url = task.url
                    execution.request_method = task.method.value
                    task.last_run_at = result.finished_at
                    task.last_status = TaskStatus.SUCCESS if is_success else TaskStatus.FAILED
                    if is_success:
                        task.consecutive_failures = 0
                    else:
                        task.consecutive_failures += 1

            elif result.task_type == "delayed":
                task = await db.get(DelayedTask, result.task_id)
                if task:
                    execution.request_url = task.url
                    execution.request_method = task.method.value
                    task.status = TaskStatus.SUCCESS if is_success else TaskStatus.FAILED
                    task.executed_at = result.finished_at

            db.add(execution)

            # Update worker stats
            if is_success:
                worker.tasks_completed += 1
            else:
                worker.tasks_failed += 1

            await db.commit()

            logger.info(
                "Task result processed",
                worker_id=str(worker.id),
                task_id=str(result.task_id),
                success=is_success,
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to process task result",
                worker_id=str(worker.id),
                task_id=str(result.task_id),
                error=str(e),
            )
            await db.rollback()
            return False

    async def mark_offline_workers(
        self,
        db: AsyncSession,
        timeout_seconds: int = 60,
    ) -> int:
        """Mark workers as offline if they haven't sent a heartbeat recently."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)

        result = await db.execute(
            update(Worker)
            .where(Worker.status != WorkerStatus.OFFLINE)
            .where(Worker.last_heartbeat < cutoff)
            .values(status=WorkerStatus.OFFLINE)
        )

        await db.commit()

        return result.rowcount


from datetime import timedelta  # noqa: E402

# Singleton instance
worker_service = WorkerService()
