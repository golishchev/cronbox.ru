"""Task scheduler for processing due tasks.

This scheduler runs as a separate process and periodically checks for
due cron and delayed tasks, enqueueing them to the arq worker queue.

Tasks can be executed by:
1. Cloud workers (arq) - default, if no worker_id is set
2. External workers - if task has worker_id, enqueue to worker's polling queue
"""

import asyncio
from datetime import datetime

import pytz
import structlog
from arq import create_pool
from croniter import croniter

from app.db.database import async_session_factory
from app.db.repositories.cron_tasks import CronTaskRepository
from app.db.repositories.delayed_tasks import DelayedTaskRepository
from app.models.cron_task import TaskStatus
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

        # Run all polling loops concurrently
        await asyncio.gather(
            self._poll_cron_tasks(),
            self._poll_delayed_tasks(),
            self._update_next_run_times(),
            self._check_subscriptions(),
        )

    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.redis_pool:
            await self.redis_pool.close()
        logger.info("Scheduler stopped")

    async def _poll_cron_tasks(self):
        """Poll for due cron tasks every 2 seconds for improved accuracy."""
        while self.running:
            try:
                await self._process_due_cron_tasks()
            except Exception as e:
                logger.error("Error processing cron tasks", error=str(e))

            await asyncio.sleep(2)

    async def _poll_delayed_tasks(self):
        """Poll for due delayed tasks every 1 second for improved accuracy."""
        while self.running:
            try:
                await self._process_due_delayed_tasks()
            except Exception as e:
                logger.error("Error processing delayed tasks", error=str(e))

            await asyncio.sleep(1)

    async def _update_next_run_times(self):
        """Update next_run_at for tasks that need it, every minute."""
        while self.running:
            try:
                await self._calculate_next_run_times()
            except Exception as e:
                logger.error("Error updating next run times", error=str(e))

            await asyncio.sleep(60)

    async def _check_subscriptions(self):
        """Check for expired and expiring subscriptions every hour."""
        while self.running:
            try:
                await self._process_subscription_checks()
            except Exception as e:
                logger.error("Error checking subscriptions", error=str(e))

            # Check every hour
            await asyncio.sleep(3600)

    async def _process_subscription_checks(self):
        """Process subscription expiration checks, auto-renewals, and notifications."""
        from app.services.billing import billing_service
        from app.services.notifications import notification_service

        async with async_session_factory() as db:
            # 0. Try to auto-renew expiring subscriptions (due today or already expired)
            renewed_count = 0
            failed_renewals = []
            expiring_subscriptions = await billing_service.get_subscriptions_for_renewal(db)
            for subscription in expiring_subscriptions:
                payment = await billing_service.auto_renew_subscription(db, subscription)
                if payment:
                    renewed_count += 1
                    # Send success notification
                    await notification_service.send_subscription_renewed(
                        db=db,
                        user_id=subscription.user_id,
                        payment=payment,
                    )
                else:
                    failed_renewals.append(subscription.user_id)

            if renewed_count:
                logger.info("Auto-renewed subscriptions", count=renewed_count)

            # 1. Check and process expired subscriptions (those that couldn't be auto-renewed)
            expired_workspaces = await billing_service.check_expired_subscriptions(db)
            for user_id, tasks_paused, workspaces_blocked in expired_workspaces:
                await notification_service.send_subscription_expired(
                    db=db,
                    user_id=user_id,
                    tasks_paused=tasks_paused,
                    workspaces_blocked=workspaces_blocked,
                )
            if expired_workspaces:
                logger.info(
                    "Processed expired subscriptions",
                    count=len(expired_workspaces),
                )

            # 2. Send notifications for subscriptions expiring in 7 days
            expiring_7d = await billing_service.get_expiring_subscriptions(db, days_before=7)
            for subscription in expiring_7d:
                expiration_date = subscription.current_period_end.strftime("%d.%m.%Y")
                await notification_service.send_subscription_expiring(
                    db=db,
                    workspace_id=subscription.workspace_id,
                    days_remaining=7,
                    expiration_date=expiration_date,
                )
            if expiring_7d:
                logger.info(
                    "Sent 7-day expiration notifications",
                    count=len(expiring_7d),
                )

            # 3. Send notifications for subscriptions expiring in 1 day
            expiring_1d = await billing_service.get_expiring_subscriptions(db, days_before=1)
            for subscription in expiring_1d:
                expiration_date = subscription.current_period_end.strftime("%d.%m.%Y")
                await notification_service.send_subscription_expiring(
                    db=db,
                    workspace_id=subscription.workspace_id,
                    days_remaining=1,
                    expiration_date=expiration_date,
                )
            if expiring_1d:
                logger.info(
                    "Sent 1-day expiration notifications",
                    count=len(expiring_1d),
                )

    async def _process_due_cron_tasks(self):
        """Find and enqueue due cron tasks.

        Each task is processed in a separate transaction to ensure
        FOR UPDATE lock is held until commit for that specific task.
        """
        now = datetime.utcnow()
        processed = 0
        max_tasks_per_cycle = 100

        while processed < max_tasks_per_cycle:
            async with async_session_factory() as db:
                cron_repo = CronTaskRepository(db)
                # Fetch ONE task at a time with row lock
                due_tasks = await cron_repo.get_due_tasks(now, limit=1)

                if not due_tasks:
                    break  # No more due tasks

                task = due_tasks[0]
                try:
                    # Calculate next run time immediately to prevent re-enqueueing
                    tz = pytz.timezone(task.timezone)
                    now_tz = datetime.now(tz)
                    cron = croniter(task.schedule, now_tz)
                    next_run = cron.get_next(datetime)
                    next_run_utc = next_run.astimezone(pytz.UTC).replace(tzinfo=None)

                    # Update next_run_at in memory (row is still locked by FOR UPDATE)
                    task.next_run_at = next_run_utc

                    # Enqueue BEFORE commit to ensure task is queued while row is locked
                    # This prevents race conditions with other scheduler instances
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

                    # Commit releases the row lock after successful enqueue
                    await db.commit()
                    processed += 1

                except Exception as e:
                    await db.rollback()
                    logger.error(
                        "Error processing cron task",
                        task_id=str(task.id),
                        error=str(e),
                    )
                    # Continue to next task on error

        if processed > 0:
            logger.info(f"Processed {processed} cron tasks")

    async def _process_due_delayed_tasks(self):
        """Find and enqueue due delayed tasks.

        Each task is processed in a separate transaction to ensure
        FOR UPDATE lock is held until commit for that specific task.
        """
        now = datetime.utcnow()
        processed = 0
        max_tasks_per_cycle = 100

        while processed < max_tasks_per_cycle:
            async with async_session_factory() as db:
                delayed_repo = DelayedTaskRepository(db)
                # Fetch ONE task at a time with row lock
                due_tasks = await delayed_repo.get_due_tasks(now, limit=1)

                if not due_tasks:
                    break  # No more due tasks

                task = due_tasks[0]
                try:
                    # Mark task as running in memory (row is still locked by FOR UPDATE)
                    task.status = TaskStatus.RUNNING

                    # Enqueue BEFORE commit to ensure task is queued while row is locked
                    # This prevents race conditions with other scheduler instances
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

                    # Commit releases the row lock after successful enqueue
                    await db.commit()
                    processed += 1

                except Exception as e:
                    await db.rollback()
                    logger.error(
                        "Error processing delayed task",
                        task_id=str(task.id),
                        error=str(e),
                    )
                    # Continue to next task on error

        if processed > 0:
            logger.info(f"Processed {processed} delayed tasks")

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
