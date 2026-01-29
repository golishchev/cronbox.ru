"""Task scheduler for processing due tasks.

This scheduler runs as a separate process and periodically checks for
due cron and delayed tasks, enqueueing them to the arq worker queue.

Tasks can be executed by:
1. Cloud workers (arq) - default, if no worker_id is set
2. External workers - if task has worker_id, enqueue to worker's polling queue
"""

import asyncio
import signal
from datetime import datetime

import pytz
import structlog
from arq import create_pool
from croniter import croniter

from app.db.database import async_session_factory
from app.db.repositories.cron_tasks import CronTaskRepository
from app.db.repositories.delayed_tasks import DelayedTaskRepository
from app.db.repositories.task_chains import TaskChainRepository
from app.models.cron_task import CronTask, OverlapPolicy, TaskStatus
from app.models.task_chain import TaskChain, TriggerType
from app.schemas.worker import WorkerTaskInfo
from app.services.overlap import OverlapAction, overlap_service
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
            self._poll_task_chains(),
            self._poll_heartbeats(),
            self._poll_ssl_monitors(),
            self._poll_process_monitors(),
            self._update_next_run_times(),
            self._check_subscriptions(),
            self._check_pending_payments(),
            self._cleanup_stale_instances(),
            self._cleanup_old_executions(),
            self._process_task_queue(),
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

    async def _poll_task_chains(self):
        """Poll for due task chains every 5 seconds."""
        while self.running:
            try:
                await self._process_due_chains()
            except Exception as e:
                logger.error("Error processing task chains", error=str(e))

            await asyncio.sleep(5)

    async def _poll_heartbeats(self):
        """Poll for overdue heartbeat monitors every 30 seconds."""
        while self.running:
            try:
                await self._process_heartbeat_checks()
            except Exception as e:
                logger.error("Error processing heartbeat checks", error=str(e))

            await asyncio.sleep(30)

    async def _process_heartbeat_checks(self):
        """Check for overdue heartbeat monitors and send alerts."""
        from app.services.heartbeat import heartbeat_service

        async with async_session_factory() as db:
            # Check for late heartbeats (grace period expired)
            late_count = await heartbeat_service.check_overdue_heartbeats(db)
            if late_count > 0:
                logger.info(f"Marked {late_count} heartbeat(s) as late")

            # Check for dead heartbeats (3+ consecutive misses)
            dead_count = await heartbeat_service.check_dead_heartbeats(db)
            if dead_count > 0:
                logger.info(f"Marked {dead_count} heartbeat(s) as dead")

    async def _poll_process_monitors(self):
        """Poll for process monitors with missed starts/ends every 30 seconds."""
        while self.running:
            try:
                await self._process_process_monitor_checks()
            except Exception as e:
                logger.error("Error processing process monitor checks", error=str(e))

            await asyncio.sleep(30)

    async def _process_process_monitor_checks(self):
        """Check for process monitors with missed starts and missed ends."""
        from app.services.process_monitor import process_monitor_service

        async with async_session_factory() as db:
            # Check for missed starts (past start deadline)
            missed_starts = await process_monitor_service.check_missed_starts(db)
            if missed_starts > 0:
                logger.info(f"Marked {missed_starts} process monitor(s) as missed start")

            # Check for missed ends (past end deadline while running)
            missed_ends = await process_monitor_service.check_missed_ends(db)
            if missed_ends > 0:
                logger.info(f"Marked {missed_ends} process monitor(s) as missed end (timeout)")

    async def _poll_ssl_monitors(self):
        """Poll for SSL monitors due for check every 5 minutes."""
        while self.running:
            try:
                await self._process_ssl_monitor_checks()
            except Exception as e:
                logger.error("Error processing SSL monitor checks", error=str(e))

            await asyncio.sleep(300)  # Every 5 minutes

    async def _process_ssl_monitor_checks(self):
        """Check SSL certificates for due monitors."""
        from app.services.ssl_monitor import ssl_monitor_service

        async with async_session_factory() as db:
            # Check monitors due for regular daily check
            checked_count = await ssl_monitor_service.check_due_monitors(db)
            if checked_count > 0:
                logger.info(f"Checked {checked_count} SSL monitor(s)")

            # Check monitors due for retry
            retry_count = await ssl_monitor_service.check_due_retries(db)
            if retry_count > 0:
                logger.info(f"Retried {retry_count} SSL monitor(s)")

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

    async def _check_pending_payments(self):
        """Check and update old pending payments every 5 minutes."""
        while self.running:
            try:
                from app.services.billing import billing_service

                async with async_session_factory() as db:
                    updated = await billing_service.check_pending_payments(db)
                    if updated:
                        logger.info("Checked pending payments", updated=updated)
            except Exception as e:
                logger.error("Error checking pending payments", error=str(e))

            # Check every 5 minutes
            await asyncio.sleep(300)

    async def _process_subscription_checks(self):
        """Process subscription expiration checks, auto-renewals, and notifications."""
        from app.services.billing import billing_service
        from app.services.notifications import notification_service

        async with async_session_factory() as db:
            # 0. Apply scheduled plan changes (downgrades, yearly→monthly)
            scheduled_changes = await billing_service.get_subscriptions_with_scheduled_changes(db)
            applied_count = 0
            for subscription in scheduled_changes:
                success = await billing_service.apply_scheduled_plan_change(db, subscription)
                if success:
                    applied_count += 1
            if applied_count:
                logger.info("Applied scheduled plan changes", count=applied_count)

            # 1. Try to auto-renew expiring subscriptions (due today or already expired)
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

            # 2. Check and process expired subscriptions (those that couldn't be auto-renewed)
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

            # 3. Send notifications for subscriptions expiring in 7 days
            expiring_7d = await billing_service.get_expiring_subscriptions(db, days_before=7)
            for subscription in expiring_7d:
                expiration_date = subscription.current_period_end.strftime("%d.%m.%Y")
                await notification_service.send_subscription_expiring(
                    db=db,
                    user_id=subscription.user_id,
                    days_remaining=7,
                    expiration_date=expiration_date,
                )
            if expiring_7d:
                logger.info(
                    "Sent 7-day expiration notifications",
                    count=len(expiring_7d),
                )

            # 4. Send notifications for subscriptions expiring in 1 day
            expiring_1d = await billing_service.get_expiring_subscriptions(db, days_before=1)
            for subscription in expiring_1d:
                expiration_date = subscription.current_period_end.strftime("%d.%m.%Y")
                await notification_service.send_subscription_expiring(
                    db=db,
                    user_id=subscription.user_id,
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

                    # Check overlap prevention policy
                    if task.overlap_policy != OverlapPolicy.ALLOW:
                        overlap_result = await overlap_service.check_cron_task_overlap(db, task)
                        if not overlap_result.should_execute:
                            if overlap_result.action == OverlapAction.QUEUE:
                                logger.info(
                                    "Cron task queued due to overlap",
                                    task_id=str(task.id),
                                    task_name=task.name,
                                    queue_position=overlap_result.queue_position,
                                )
                            else:
                                logger.info(
                                    "Cron task skipped due to overlap",
                                    task_id=str(task.id),
                                    task_name=task.name,
                                    reason=overlap_result.message,
                                )
                            await db.commit()
                            processed += 1
                            continue

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
        """Calculate next_run_at for tasks and chains that don't have it set."""
        async with async_session_factory() as db:
            # Update cron tasks
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
                        "Updated next_run_at for cron task",
                        task_id=str(task.id),
                        next_run_at=next_run_utc.isoformat(),
                    )
                except Exception as e:
                    logger.error(
                        "Error calculating next run time for cron task",
                        task_id=str(task.id),
                        error=str(e),
                    )

            # Update task chains
            chain_repo = TaskChainRepository(db)
            chains = await chain_repo.get_chains_needing_next_run_update(limit=100)

            for chain in chains:
                try:
                    tz = pytz.timezone(chain.timezone)
                    now_tz = datetime.now(tz)
                    cron = croniter(chain.schedule, now_tz)
                    next_run = cron.get_next(datetime)
                    next_run_utc = next_run.astimezone(pytz.UTC).replace(tzinfo=None)

                    chain.next_run_at = next_run_utc

                    logger.debug(
                        "Updated next_run_at for chain",
                        chain_id=str(chain.id),
                        next_run_at=next_run_utc.isoformat(),
                    )
                except Exception as e:
                    logger.error(
                        "Error calculating next run time for chain",
                        chain_id=str(chain.id),
                        error=str(e),
                    )

            await db.commit()

    async def _process_due_chains(self):
        """Find and enqueue due task chains.

        Each chain is processed in a separate transaction to ensure
        FOR UPDATE lock is held until commit for that specific chain.
        """
        now = datetime.utcnow()
        processed = 0
        max_chains_per_cycle = 50

        while processed < max_chains_per_cycle:
            async with async_session_factory() as db:
                chain_repo = TaskChainRepository(db)
                # Fetch ONE chain at a time with row lock
                due_chains = await chain_repo.get_due_chains(now, limit=1)

                if not due_chains:
                    break  # No more due chains

                chain = due_chains[0]
                try:
                    # Calculate next run time for cron chains
                    next_run_utc = None
                    if chain.trigger_type == TriggerType.CRON and chain.schedule:
                        tz = pytz.timezone(chain.timezone)
                        now_tz = datetime.now(tz)
                        cron = croniter(chain.schedule, now_tz)
                        next_run = cron.get_next(datetime)
                        next_run_utc = next_run.astimezone(pytz.UTC).replace(tzinfo=None)
                        chain.next_run_at = next_run_utc
                    elif chain.trigger_type == TriggerType.DELAYED:
                        # Delayed chains run once and deactivate
                        chain.next_run_at = None

                    # Check overlap prevention policy
                    if chain.overlap_policy != OverlapPolicy.ALLOW:
                        overlap_result = await overlap_service.check_chain_overlap(db, chain)
                        if not overlap_result.should_execute:
                            if overlap_result.action == OverlapAction.QUEUE:
                                logger.info(
                                    "Chain queued due to overlap",
                                    chain_id=str(chain.id),
                                    chain_name=chain.name,
                                    queue_position=overlap_result.queue_position,
                                )
                            else:
                                logger.info(
                                    "Chain skipped due to overlap",
                                    chain_id=str(chain.id),
                                    chain_name=chain.name,
                                    reason=overlap_result.message,
                                )
                            await db.commit()
                            processed += 1
                            continue

                    # Enqueue chain for execution
                    # Note: External workers for chains are not supported yet
                    await self.redis_pool.enqueue_job(
                        "execute_chain",
                        chain_id=str(chain.id),
                        initial_variables={},
                    )

                    logger.info(
                        "Enqueued task chain for execution",
                        chain_id=str(chain.id),
                        chain_name=chain.name,
                        trigger_type=chain.trigger_type.value,
                        next_run_at=next_run_utc.isoformat() if next_run_utc else None,
                    )

                    # Commit releases the row lock after successful enqueue
                    await db.commit()
                    processed += 1

                except Exception as e:
                    await db.rollback()
                    logger.error(
                        "Error processing task chain",
                        chain_id=str(chain.id),
                        error=str(e),
                    )
                    # Continue to next chain on error

        if processed > 0:
            logger.info(f"Processed {processed} task chains")

    async def _cleanup_stale_instances(self):
        """Cleanup stale running instances every 5 minutes."""
        while self.running:
            try:
                async with async_session_factory() as db:
                    cleaned = await overlap_service.cleanup_stale_instances(db)
                    if cleaned:
                        await db.commit()
                        logger.info("Cleaned up stale running instances", count=cleaned)
            except Exception as e:
                logger.error("Error cleaning up stale instances", error=str(e))

            await asyncio.sleep(300)  # Every 5 minutes

    async def _cleanup_old_executions(self):
        """Cleanup old execution history based on plan limits every hour."""
        from datetime import timedelta

        from app.db.repositories.chain_executions import ChainExecutionRepository
        from app.db.repositories.executions import ExecutionRepository
        from app.db.repositories.workspaces import WorkspaceRepository
        from app.services.billing import billing_service

        while self.running:
            try:
                async with async_session_factory() as db:
                    workspace_repo = WorkspaceRepository(db)
                    execution_repo = ExecutionRepository(db)
                    chain_execution_repo = ChainExecutionRepository(db)

                    # Get all workspaces grouped by owner
                    owner_workspaces = await workspace_repo.get_all_workspace_ids_grouped_by_owner()

                    total_deleted = 0
                    total_chain_deleted = 0

                    for owner_id, workspace_ids in owner_workspaces:
                        try:
                            # Get owner's plan
                            plan = await billing_service.get_user_plan(db, owner_id)
                            retention_days = plan.max_execution_history_days

                            # Calculate cutoff date
                            cutoff = datetime.utcnow() - timedelta(days=retention_days)

                            # Delete old executions for each workspace
                            for workspace_id in workspace_ids:
                                deleted = await execution_repo.cleanup_old_executions(workspace_id, cutoff)
                                total_deleted += deleted

                                chain_deleted = await chain_execution_repo.delete_old_executions(
                                    workspace_id, retention_days
                                )
                                total_chain_deleted += chain_deleted

                        except Exception as e:
                            logger.error(
                                "Error cleaning up executions for owner",
                                owner_id=str(owner_id),
                                error=str(e),
                            )
                            continue

                    await db.commit()

                    if total_deleted > 0 or total_chain_deleted > 0:
                        logger.info(
                            "Cleaned up old executions",
                            executions_deleted=total_deleted,
                            chain_executions_deleted=total_chain_deleted,
                        )

            except Exception as e:
                logger.error("Error in execution cleanup job", error=str(e))

            # Run every hour
            await asyncio.sleep(3600)

    async def _process_task_queue(self):
        """Process queued tasks when slots become available every 10 seconds."""
        while self.running:
            try:
                await self._check_and_execute_queued_tasks()
            except Exception as e:
                logger.error("Error processing task queue", error=str(e))

            await asyncio.sleep(10)

    async def _check_and_execute_queued_tasks(self):
        """Check for queued tasks that can now be executed."""

        async with async_session_factory() as db:
            # Get cron tasks with queue policy and available slots
            CronTaskRepository(db)
            TaskChainRepository(db)

            # Find cron tasks with available slots
            from sqlalchemy import select

            result = await db.execute(
                select(CronTask).where(
                    CronTask.overlap_policy == OverlapPolicy.QUEUE,
                    CronTask.is_active == True,  # noqa: E712
                    CronTask.is_paused == False,  # noqa: E712
                    CronTask.running_instances < CronTask.max_instances,
                )
            )
            available_cron_tasks = result.scalars().all()

            for task in available_cron_tasks:
                # Check if there are queued executions
                queued = await overlap_service._pop_from_queue(db, "cron", task.id)
                if queued:
                    # Increment running instances
                    await overlap_service._increment_running_instances(db, "cron", task.id)

                    # Enqueue the task
                    if task.worker_id:
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
                    else:
                        await self.redis_pool.enqueue_job(
                            "execute_cron_task",
                            task_id=str(task.id),
                            retry_attempt=queued.retry_attempt,
                        )

                    logger.info(
                        "Executed queued cron task",
                        task_id=str(task.id),
                        task_name=task.name,
                    )

            # Find chains with available slots
            chain_result = await db.execute(
                select(TaskChain).where(
                    TaskChain.overlap_policy == OverlapPolicy.QUEUE,
                    TaskChain.is_active == True,  # noqa: E712
                    TaskChain.is_paused == False,  # noqa: E712
                    TaskChain.running_instances < TaskChain.max_instances,
                )
            )
            available_chains = chain_result.scalars().all()

            for chain in available_chains:
                queued = await overlap_service._pop_from_queue(db, "chain", chain.id)
                if queued:
                    # Increment running instances
                    await overlap_service._increment_running_instances(db, "chain", chain.id)

                    # Enqueue the chain
                    await self.redis_pool.enqueue_job(
                        "execute_chain",
                        chain_id=str(chain.id),
                        initial_variables=queued.initial_variables or {},
                    )

                    logger.info(
                        "Executed queued chain",
                        chain_id=str(chain.id),
                        chain_name=chain.name,
                    )

            await db.commit()


async def run_scheduler():
    """Run the scheduler until interrupted."""
    scheduler = TaskScheduler()
    loop = asyncio.get_running_loop()

    # Setup signal handlers for graceful shutdown
    def handle_signal(sig: signal.Signals) -> None:
        logger.info("Received signal, initiating graceful shutdown...", signal=sig.name)
        scheduler.running = False

    # Register signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal, sig)

    try:
        await scheduler.start()
    except asyncio.CancelledError:
        logger.info("Scheduler cancelled")
    except Exception as e:
        logger.error("Scheduler error", error=str(e))
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(run_scheduler())
