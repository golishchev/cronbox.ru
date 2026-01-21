"""Tests for task scheduler module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.workers.scheduler import TaskScheduler


class TestTaskScheduler:
    """Tests for TaskScheduler class."""

    def test_init(self):
        """Test scheduler initialization."""
        scheduler = TaskScheduler()

        assert scheduler.redis_pool is None
        assert scheduler.running is False

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test scheduler stop."""
        scheduler = TaskScheduler()
        scheduler.running = True
        scheduler.redis_pool = AsyncMock()

        await scheduler.stop()

        assert scheduler.running is False
        scheduler.redis_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_without_redis_pool(self):
        """Test scheduler stop when redis pool is None."""
        scheduler = TaskScheduler()
        scheduler.running = True

        await scheduler.stop()

        assert scheduler.running is False


class TestSchedulerPolling:
    """Tests for scheduler polling methods."""

    @pytest.mark.asyncio
    async def test_poll_cron_tasks_stops_when_not_running(self):
        """Test cron task polling stops when scheduler not running."""
        scheduler = TaskScheduler()
        scheduler.running = False

        # Should complete immediately
        await scheduler._poll_cron_tasks()

    @pytest.mark.asyncio
    async def test_poll_delayed_tasks_stops_when_not_running(self):
        """Test delayed task polling stops when scheduler not running."""
        scheduler = TaskScheduler()
        scheduler.running = False

        # Should complete immediately
        await scheduler._poll_delayed_tasks()

    @pytest.mark.asyncio
    async def test_update_next_run_times_stops_when_not_running(self):
        """Test next run time update stops when scheduler not running."""
        scheduler = TaskScheduler()
        scheduler.running = False

        # Should complete immediately
        await scheduler._update_next_run_times()

    @pytest.mark.asyncio
    async def test_check_subscriptions_stops_when_not_running(self):
        """Test subscription check stops when scheduler not running."""
        scheduler = TaskScheduler()
        scheduler.running = False

        # Should complete immediately
        await scheduler._check_subscriptions()

    @pytest.mark.asyncio
    async def test_poll_cron_tasks_handles_error(self):
        """Test cron task polling handles errors gracefully."""
        scheduler = TaskScheduler()
        scheduler.running = True

        # Mock to raise error on first call, then stop
        call_count = 0

        async def mock_process():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            scheduler.running = False

        scheduler._process_due_cron_tasks = mock_process

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await scheduler._poll_cron_tasks()

        # Should have processed error and continued
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_poll_delayed_tasks_handles_error(self):
        """Test delayed task polling handles errors gracefully."""
        scheduler = TaskScheduler()
        scheduler.running = True

        call_count = 0

        async def mock_process():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            scheduler.running = False

        scheduler._process_due_delayed_tasks = mock_process

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await scheduler._poll_delayed_tasks()

        assert call_count >= 1


class TestProcessDueCronTasks:
    """Tests for processing due cron tasks."""

    @pytest.mark.asyncio
    async def test_process_due_cron_tasks_no_tasks(self):
        """Test processing when no due tasks."""
        scheduler = TaskScheduler()
        scheduler.redis_pool = AsyncMock()

        # Mock the database session and repository
        mock_cron_repo = AsyncMock()
        mock_cron_repo.get_due_tasks.return_value = []

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.CronTaskRepository", return_value=mock_cron_repo):
                await scheduler._process_due_cron_tasks()

        # Should have checked for tasks
        mock_cron_repo.get_due_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_due_cron_task_cloud_worker(self):
        """Test processing cron task for cloud worker."""
        scheduler = TaskScheduler()
        scheduler.redis_pool = AsyncMock()

        # Create mock task (no worker_id = cloud worker)
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.name = "Test Task"
        mock_task.worker_id = None
        mock_task.timezone = "UTC"
        mock_task.schedule = "* * * * *"
        mock_task.url = "https://example.com"
        mock_task.method = MagicMock(value="GET")
        mock_task.headers = {}
        mock_task.body = None
        mock_task.timeout_seconds = 30
        mock_task.retry_count = 0
        mock_task.retry_delay_seconds = 60
        # Overlap prevention fields
        mock_task.overlap_policy = "allow"
        mock_task.running_instances = 0
        mock_task.max_instances = 1

        mock_cron_repo = AsyncMock()
        mock_cron_repo.get_due_tasks.side_effect = [[mock_task], []]

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.CronTaskRepository", return_value=mock_cron_repo):
                await scheduler._process_due_cron_tasks()

        # Should have enqueued job
        scheduler.redis_pool.enqueue_job.assert_called_once()
        call_args = scheduler.redis_pool.enqueue_job.call_args
        assert call_args[0][0] == "execute_cron_task"

    @pytest.mark.asyncio
    async def test_process_due_cron_task_external_worker(self):
        """Test processing cron task for external worker."""
        scheduler = TaskScheduler()
        scheduler.redis_pool = AsyncMock()

        worker_id = uuid4()

        # Create mock task (with worker_id = external worker)
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.name = "Test Task"
        mock_task.worker_id = worker_id
        mock_task.workspace_id = uuid4()
        mock_task.timezone = "UTC"
        mock_task.schedule = "* * * * *"
        mock_task.url = "https://example.com"
        mock_task.method = MagicMock(value="GET")
        mock_task.headers = {}
        mock_task.body = None
        mock_task.timeout_seconds = 30
        mock_task.retry_count = 0
        mock_task.retry_delay_seconds = 60
        # Overlap prevention fields
        mock_task.overlap_policy = "allow"
        mock_task.running_instances = 0
        mock_task.max_instances = 1

        mock_cron_repo = AsyncMock()
        mock_cron_repo.get_due_tasks.side_effect = [[mock_task], []]

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.CronTaskRepository", return_value=mock_cron_repo):
                with patch("app.workers.scheduler.worker_service") as mock_worker_service:
                    mock_worker_service.enqueue_task_for_worker = AsyncMock()
                    await scheduler._process_due_cron_tasks()

                    # Should have enqueued for external worker
                    mock_worker_service.enqueue_task_for_worker.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_due_cron_task_error_handling(self):
        """Test error handling during cron task processing."""
        scheduler = TaskScheduler()
        scheduler.redis_pool = AsyncMock()
        scheduler.redis_pool.enqueue_job.side_effect = Exception("Queue error")

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.name = "Test Task"
        mock_task.worker_id = None
        mock_task.timezone = "UTC"
        mock_task.schedule = "* * * * *"

        mock_cron_repo = AsyncMock()
        mock_cron_repo.get_due_tasks.side_effect = [[mock_task], []]

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.CronTaskRepository", return_value=mock_cron_repo):
                # Should not raise
                await scheduler._process_due_cron_tasks()

        # Should have rolled back
        mock_session.rollback.assert_called()


class TestProcessDueDelayedTasks:
    """Tests for processing due delayed tasks."""

    @pytest.mark.asyncio
    async def test_process_due_delayed_tasks_no_tasks(self):
        """Test processing when no due delayed tasks."""
        scheduler = TaskScheduler()
        scheduler.redis_pool = AsyncMock()

        mock_delayed_repo = AsyncMock()
        mock_delayed_repo.get_due_tasks.return_value = []

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.DelayedTaskRepository", return_value=mock_delayed_repo):
                await scheduler._process_due_delayed_tasks()

        mock_delayed_repo.get_due_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_due_delayed_task_cloud_worker(self):
        """Test processing delayed task for cloud worker."""
        scheduler = TaskScheduler()
        scheduler.redis_pool = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.name = "Delayed Task"
        mock_task.worker_id = None
        mock_task.workspace_id = uuid4()
        mock_task.url = "https://example.com"
        mock_task.method = MagicMock(value="POST")
        mock_task.headers = {}
        mock_task.body = '{"data": "test"}'
        mock_task.timeout_seconds = 30
        mock_task.retry_count = 0
        mock_task.retry_delay_seconds = 60

        mock_delayed_repo = AsyncMock()
        mock_delayed_repo.get_due_tasks.side_effect = [[mock_task], []]

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.DelayedTaskRepository", return_value=mock_delayed_repo):
                await scheduler._process_due_delayed_tasks()

        scheduler.redis_pool.enqueue_job.assert_called_once()
        call_args = scheduler.redis_pool.enqueue_job.call_args
        assert call_args[0][0] == "execute_delayed_task"


class TestCalculateNextRunTimes:
    """Tests for calculating next run times."""

    @pytest.mark.asyncio
    async def test_calculate_next_run_times(self):
        """Test calculating next run times for tasks."""
        scheduler = TaskScheduler()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.timezone = "UTC"
        mock_task.schedule = "0 * * * *"  # Every hour

        mock_cron_repo = AsyncMock()
        mock_cron_repo.get_tasks_needing_next_run_update.return_value = [mock_task]

        mock_chain_repo = AsyncMock()
        mock_chain_repo.get_chains_needing_next_run_update.return_value = []

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.CronTaskRepository", return_value=mock_cron_repo):
                with patch("app.workers.scheduler.TaskChainRepository", return_value=mock_chain_repo):
                    await scheduler._calculate_next_run_times()

        # Should have set next_run_at
        assert mock_task.next_run_at is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_next_run_times_handles_error(self):
        """Test error handling when calculating next run times."""
        scheduler = TaskScheduler()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.timezone = "Invalid/Timezone"  # Invalid timezone
        mock_task.schedule = "0 * * * *"

        mock_cron_repo = AsyncMock()
        mock_cron_repo.get_tasks_needing_next_run_update.return_value = [mock_task]

        mock_chain_repo = AsyncMock()
        mock_chain_repo.get_chains_needing_next_run_update.return_value = []

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch("app.workers.scheduler.CronTaskRepository", return_value=mock_cron_repo):
                with patch("app.workers.scheduler.TaskChainRepository", return_value=mock_chain_repo):
                    # Should not raise
                    await scheduler._calculate_next_run_times()

        # Should still commit
        mock_session.commit.assert_called_once()


class TestSubscriptionChecks:
    """Tests for subscription expiration checks."""

    @pytest.mark.asyncio
    async def test_process_subscription_checks(self):
        """Test processing subscription expiration checks."""
        scheduler = TaskScheduler()

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            # billing_service and notification_service are imported inside the method
            with patch("app.services.billing.billing_service") as mock_billing:
                mock_billing.get_subscriptions_with_scheduled_changes = AsyncMock(return_value=[])
                mock_billing.apply_scheduled_plan_change = AsyncMock(return_value=True)
                mock_billing.get_subscriptions_for_renewal = AsyncMock(return_value=[])
                mock_billing.auto_renew_subscription = AsyncMock(return_value=None)
                mock_billing.check_expired_subscriptions = AsyncMock(return_value=[])
                mock_billing.get_expiring_subscriptions = AsyncMock(return_value=[])

                with patch("app.services.notifications.notification_service") as mock_notif:
                    mock_notif.send_subscription_expired = AsyncMock()
                    mock_notif.send_subscription_expiring = AsyncMock()
                    mock_notif.send_subscription_renewed = AsyncMock()

                    await scheduler._process_subscription_checks()

                    # Should have checked for scheduled changes, renewals, and expirations
                    mock_billing.get_subscriptions_with_scheduled_changes.assert_called_once()
                    mock_billing.get_subscriptions_for_renewal.assert_called_once()
                    mock_billing.check_expired_subscriptions.assert_called_once()
                    assert mock_billing.get_expiring_subscriptions.call_count == 2  # 7 days and 1 day


class TestCleanupOldExecutions:
    """Tests for old execution history cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_old_executions_stops_when_not_running(self):
        """Test cleanup stops when scheduler not running."""
        scheduler = TaskScheduler()
        scheduler.running = False

        # Should complete immediately
        await scheduler._cleanup_old_executions()

    @pytest.mark.asyncio
    async def test_cleanup_old_executions_deletes_based_on_plan(self):
        """Test cleanup deletes executions based on plan retention days."""
        scheduler = TaskScheduler()
        scheduler.running = True

        owner_id = uuid4()
        workspace_id = uuid4()

        # Mock plan with 7 days retention
        mock_plan = MagicMock()
        mock_plan.max_execution_history_days = 7

        # Mock workspace repository
        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_all_workspace_ids_grouped_by_owner.return_value = [
            (owner_id, [workspace_id])
        ]

        # Mock execution repository
        mock_execution_repo = AsyncMock()
        mock_execution_repo.cleanup_old_executions.return_value = 5

        # Mock chain execution repository
        mock_chain_repo = AsyncMock()
        mock_chain_repo.delete_old_executions.return_value = 3

        async def stop_scheduler(*args, **kwargs):
            scheduler.running = False

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.workspaces.WorkspaceRepository",
                return_value=mock_workspace_repo,
            ):
                with patch(
                    "app.db.repositories.executions.ExecutionRepository",
                    return_value=mock_execution_repo,
                ):
                    with patch(
                        "app.db.repositories.chain_executions.ChainExecutionRepository",
                        return_value=mock_chain_repo,
                    ):
                        with patch(
                            "app.services.billing.billing_service"
                        ) as mock_billing:
                            mock_billing.get_user_plan = AsyncMock(return_value=mock_plan)

                            with patch("asyncio.sleep", side_effect=stop_scheduler):
                                await scheduler._cleanup_old_executions()

        # Should have cleaned up executions
        mock_execution_repo.cleanup_old_executions.assert_called_once()
        mock_chain_repo.delete_old_executions.assert_called_once_with(workspace_id, 7)

    @pytest.mark.asyncio
    async def test_cleanup_old_executions_handles_error(self):
        """Test cleanup handles errors gracefully."""
        scheduler = TaskScheduler()
        scheduler.running = True

        async def stop_scheduler(*args, **kwargs):
            scheduler.running = False

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__.side_effect = Exception("DB error")

            with patch("asyncio.sleep", side_effect=stop_scheduler):
                # Should not raise
                await scheduler._cleanup_old_executions()

    @pytest.mark.asyncio
    async def test_cleanup_old_executions_multiple_workspaces(self):
        """Test cleanup handles multiple workspaces for same owner."""
        scheduler = TaskScheduler()
        scheduler.running = True

        owner_id = uuid4()
        workspace_id_1 = uuid4()
        workspace_id_2 = uuid4()

        mock_plan = MagicMock()
        mock_plan.max_execution_history_days = 30

        mock_workspace_repo = AsyncMock()
        mock_workspace_repo.get_all_workspace_ids_grouped_by_owner.return_value = [
            (owner_id, [workspace_id_1, workspace_id_2])
        ]

        mock_execution_repo = AsyncMock()
        mock_execution_repo.cleanup_old_executions.return_value = 10

        mock_chain_repo = AsyncMock()
        mock_chain_repo.delete_old_executions.return_value = 5

        async def stop_scheduler(*args, **kwargs):
            scheduler.running = False

        with patch("app.workers.scheduler.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__.return_value = mock_session

            with patch(
                "app.db.repositories.workspaces.WorkspaceRepository",
                return_value=mock_workspace_repo,
            ):
                with patch(
                    "app.db.repositories.executions.ExecutionRepository",
                    return_value=mock_execution_repo,
                ):
                    with patch(
                        "app.db.repositories.chain_executions.ChainExecutionRepository",
                        return_value=mock_chain_repo,
                    ):
                        with patch(
                            "app.services.billing.billing_service"
                        ) as mock_billing:
                            mock_billing.get_user_plan = AsyncMock(return_value=mock_plan)

                            with patch("asyncio.sleep", side_effect=stop_scheduler):
                                await scheduler._cleanup_old_executions()

        # Should have called cleanup for both workspaces
        assert mock_execution_repo.cleanup_old_executions.call_count == 2
        assert mock_chain_repo.delete_old_executions.call_count == 2
