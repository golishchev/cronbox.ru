"""Task scheduler for processing due tasks.

This scheduler runs as a separate process and periodically checks for
due cron and delayed tasks, enqueueing them to the arq worker queue.

Tasks can be executed by:
1. Cloud workers (arq) - default, if no worker_id is set
2. External workers - if task has worker_id, enqueue to worker's polling queue
"""

import asyncio
from datetime import datetime

import structlog
from arq import create_pool
from croniter import croniter
import pytz

from app.config import settings
from app.db.database import async_session_factory
from app.db.repositories.cron_tasks import CronTaskRepository
from app.db.repositories.delayed_tasks import DelayedTaskRepository
from app.schemas.worker import WorkerTaskInfo
from app.services.worker import worker_service
from app.workers.settings import get_redis_settings

logger = structlog.get_logger()


class TaskScheduler:
    """Scheduler that polls for due tasks and enqueues them."""

    def __init__(self):
        self.redis_pool = None
        self.running = False

    async def start(self):
        """Start the scheduler."""
        self.running = True
        self.redis_pool = await create_pool(get_redis_settings())

        logger.info("Scheduler started")

        # Run both polling loops concurrently
        await asyncio.gather(
            self._poll_cron_tasks(),
            self._poll_delayed_tasks(),
            self._update_next_run_times(),
        )

    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.redis_pool:
            await self.redis_pool.close()
        logger.info("Scheduler stopped")

    async def _poll_cron_tasks(self):
        """Poll for due cron tasks every 10 seconds."""
        while self.running:
            try:
                await self._process_due_cron_tasks()
            except Exception as e:
                logger.error("Error processing cron tasks", error=str(e))

            await asyncio.sleep(10)

    async def _poll_delayed_tasks(self):
        """Poll for due delayed tasks every 5 seconds."""
        while self.running:
            try:
                await self._process_due_delayed_tasks()
            except Exception as e:
                logger.error("Error processing delayed tasks", error=str(e))

            await asyncio.sleep(5)

    async def _update_next_run_times(self):
        """Update next_run_at for tasks that need it, every minute."""
        while self.running:
            try:
                await self._calculate_next_run_times()
            except Exception as e:
                logger.error("Error updating next run times", error=str(e))

            await asyncio.sleep(60)

    async def _process_due_cron_tasks(self):
        """Find and enqueue due cron tasks."""
        now = datetime.utcnow()

        async with async_session_factory() as db:
            cron_repo = CronTaskRepository(db)
            due_tasks = await cron_repo.get_due_tasks(now, limit=100)

            if due_tasks:
                logger.info(f"Found {len(due_tasks)} due cron tasks")

            for task in due_tasks:
                # Calculate next run time immediately to prevent re-enqueueing
                tz = pytz.timezone(task.timezone)
                now_tz = datetime.now(tz)
                cron = croniter(task.schedule, now_tz)
                next_run = cron.get_next(datetime)
                next_run_utc = next_run.astimezone(pytz.UTC).replace(tzinfo=None)

                # Update next_run_at to prevent re-processing
                task.next_run_at = next_run_utc
                await db.commit()

                # Check if task is assigned to an external worker
                if task.worker_id:
                    # Enqueue for external worker (polling)
                    task_info = WorkerTaskInfo(
                        task_id=task.id,
                        task_type="cron",
                        url=task.url,
                        method=task.method.value,
                        headers=task.headers or {},
                        body=task.body,
                        timeout_seconds=task.timeout_seconds,
                        retry_count=task.retry_count,
                        retry_delay_seconds=task.retry_delay_seconds,
                        workspace_id=task.workspace_id,
                        task_name=task.name,
                    )
                    await worker_service.enqueue_task_for_worker(task.worker_id, task_info)

                    logger.info(
                        "Enqueued cron task for external worker",
                        task_id=str(task.id),
                        task_name=task.name,
                        worker_id=str(task.worker_id),
                        next_run_at=next_run_utc.isoformat(),
                    )
                else:
                    # Enqueue for cloud worker (arq)
                    await self.redis_pool.enqueue_job(
                        "execute_cron_task",
                        task_id=str(task.id),
                        retry_attempt=0,
                    )

                    logger.info(
                        "Enqueued cron task for cloud worker",
                        task_id=str(task.id),
                        task_name=task.name,
                        next_run_at=next_run_utc.isoformat(),
                    )

    async def _process_due_delayed_tasks(self):
        """Find and enqueue due delayed tasks."""
        now = datetime.utcnow()

        async with async_session_factory() as db:
            delayed_repo = DelayedTaskRepository(db)
            due_tasks = await delayed_repo.get_due_tasks(now, limit=100)

            if due_tasks:
                logger.info(f"Found {len(due_tasks)} due delayed tasks")

            for task in due_tasks:
                # Check if task is assigned to an external worker
                if task.worker_id:
                    # Enqueue for external worker (polling)
                    task_info = WorkerTaskInfo(
                        task_id=task.id,
                        task_type="delayed",
                        url=task.url,
                        method=task.method.value,
                        headers=task.headers or {},
                        body=task.body,
                        timeout_seconds=task.timeout_seconds,
                        retry_count=task.retry_count,
                        retry_delay_seconds=task.retry_delay_seconds,
                        workspace_id=task.workspace_id,
                        task_name=task.name,
                    )
                    await worker_service.enqueue_task_for_worker(task.worker_id, task_info)

                    logger.info(
                        "Enqueued delayed task for external worker",
                        task_id=str(task.id),
                        task_name=task.name,
                        worker_id=str(task.worker_id),
                    )
                else:
                    # Enqueue for cloud worker (arq)
                    await self.redis_pool.enqueue_job(
                        "execute_delayed_task",
                        task_id=str(task.id),
                        retry_attempt=0,
                    )

                    logger.info(
                        "Enqueued delayed task for cloud worker",
                        task_id=str(task.id),
                        task_name=task.name,
                    )

    async def _calculate_next_run_times(self):
        """Calculate next_run_at for tasks that don't have it set."""
        async with async_session_factory() as db:
            cron_repo = CronTaskRepository(db)
            tasks = await cron_repo.get_tasks_needing_next_run_update(limit=100)

            for task in tasks:
                try:
                    tz = pytz.timezone(task.timezone)
                    now_tz = datetime.now(tz)
                    cron = croniter(task.schedule, now_tz)
                    next_run = cron.get_next(datetime)
                    next_run_utc = next_run.astimezone(pytz.UTC).replace(tzinfo=None)

                    task.next_run_at = next_run_utc

                    logger.debug(
                        "Updated next_run_at",
                        task_id=str(task.id),
                        next_run_at=next_run_utc.isoformat(),
                    )
                except Exception as e:
                    logger.error(
                        "Error calculating next run time",
                        task_id=str(task.id),
                        error=str(e),
                    )

            await db.commit()


async def run_scheduler():
    """Run the scheduler until interrupted."""
    scheduler = TaskScheduler()

    try:
        await scheduler.start()
    except asyncio.CancelledError:
        await scheduler.stop()
    except KeyboardInterrupt:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(run_scheduler())
