"""Tests for repository layer."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.cron_task import TaskStatus


class TestDelayedTaskRepository:
    """Tests for DelayedTaskRepository."""

    @pytest.mark.asyncio
    async def test_get_by_workspace(self):
        """Test getting delayed tasks by workspace."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        workspace_id = uuid4()
        mock_task = MagicMock()
        mock_task.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db.execute.return_value = mock_result

        tasks = await repo.get_by_workspace(workspace_id)

        assert len(tasks) == 1
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_workspace_with_status_filter(self):
        """Test filtering delayed tasks by status."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        tasks = await repo.get_by_workspace(workspace_id, status=TaskStatus.PENDING)

        assert len(tasks) == 0
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_workspace(self):
        """Test counting delayed tasks by workspace."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_db.execute.return_value = mock_result

        count = await repo.count_by_workspace(workspace_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_by_idempotency_key(self):
        """Test getting task by idempotency key."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        workspace_id = uuid4()
        mock_task = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute.return_value = mock_result

        task = await repo.get_by_idempotency_key(workspace_id, "unique-key")

        assert task == mock_task

    @pytest.mark.asyncio
    async def test_get_by_idempotency_key_not_found(self):
        """Test idempotency key not found returns None."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        task = await repo.get_by_idempotency_key(uuid4(), "non-existent")

        assert task is None

    @pytest.mark.asyncio
    async def test_get_due_tasks(self):
        """Test getting due tasks."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        now = datetime.now(timezone.utc)
        mock_task = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db.execute.return_value = mock_result

        tasks = await repo.get_due_tasks(now)

        assert len(tasks) == 1
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_count_this_month(self):
        """Test counting pending tasks this month."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        workspace_id = uuid4()
        month_start = datetime.now(timezone.utc).replace(day=1)

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        mock_db.execute.return_value = mock_result

        count = await repo.get_pending_count_this_month(workspace_id, month_start)

        assert count == 10

    @pytest.mark.asyncio
    async def test_mark_running(self):
        """Test marking task as running."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.status = TaskStatus.PENDING

        result = await repo.mark_running(mock_task)

        assert result.status == TaskStatus.RUNNING
        mock_db.flush.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_task)

    @pytest.mark.asyncio
    async def test_mark_completed(self):
        """Test marking task as completed."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        mock_task = MagicMock()
        executed_at = datetime.now(timezone.utc)

        result = await repo.mark_completed(mock_task, TaskStatus.SUCCESS, executed_at)

        assert result.status == TaskStatus.SUCCESS
        assert result.executed_at == executed_at
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_retry(self):
        """Test incrementing retry counter."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.retry_attempt = 0

        result = await repo.increment_retry(mock_task)

        assert result.retry_attempt == 1
        assert result.status == TaskStatus.PENDING
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self):
        """Test cancelling a pending task."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.status = TaskStatus.PENDING

        result = await repo.cancel(mock_task)

        assert result.status == TaskStatus.CANCELLED
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_non_pending_task(self):
        """Test cancelling a non-pending task does nothing."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.status = TaskStatus.SUCCESS

        result = await repo.cancel(mock_task)

        assert result.status == TaskStatus.SUCCESS
        mock_db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_update(self):
        """Test updating a delayed task."""
        from app.db.repositories.delayed_tasks import DelayedTaskRepository

        mock_db = AsyncMock()
        repo = DelayedTaskRepository(mock_db)

        mock_task = MagicMock()
        new_execute_at = datetime.now(timezone.utc) + timedelta(hours=2)

        result = await repo.update(
            mock_task,
            name="Updated Name",
            url="https://new.example.com",
            execute_at=new_execute_at,
        )

        assert result.name == "Updated Name"
        assert result.url == "https://new.example.com"
        assert result.execute_at == new_execute_at
        mock_db.flush.assert_called_once()


class TestCronTaskRepository:
    """Tests for CronTaskRepository."""

    @pytest.mark.asyncio
    async def test_get_by_workspace(self):
        """Test getting cron tasks by workspace."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        mock_db = AsyncMock()
        repo = CronTaskRepository(mock_db)

        workspace_id = uuid4()
        mock_task = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db.execute.return_value = mock_result

        tasks = await repo.get_by_workspace(workspace_id)

        assert len(tasks) == 1
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_workspace(self):
        """Test counting cron tasks by workspace."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        mock_db = AsyncMock()
        repo = CronTaskRepository(mock_db)

        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 3
        mock_db.execute.return_value = mock_result

        count = await repo.count_by_workspace(workspace_id)

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_due_tasks(self):
        """Test getting due cron tasks."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        mock_db = AsyncMock()
        repo = CronTaskRepository(mock_db)

        now = datetime.now(timezone.utc)
        mock_task = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db.execute.return_value = mock_result

        tasks = await repo.get_due_tasks(now)

        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_update_last_run(self):
        """Test updating last run status."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        mock_db = AsyncMock()
        repo = CronTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.consecutive_failures = 0
        run_at = datetime.now(timezone.utc)
        next_run_at = run_at + timedelta(minutes=5)

        await repo.update_last_run(mock_task, TaskStatus.SUCCESS, run_at, next_run_at)

        assert mock_task.last_run_at == run_at
        assert mock_task.next_run_at == next_run_at
        assert mock_task.last_status == TaskStatus.SUCCESS
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_run_failure(self):
        """Test updating last run status on failure."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        mock_db = AsyncMock()
        repo = CronTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.consecutive_failures = 2
        run_at = datetime.now(timezone.utc)
        next_run_at = run_at + timedelta(minutes=5)

        await repo.update_last_run(mock_task, TaskStatus.FAILED, run_at, next_run_at)

        assert mock_task.consecutive_failures == 3
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause(self):
        """Test pausing a cron task."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        mock_db = AsyncMock()
        repo = CronTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.is_paused = False

        await repo.pause(mock_task)

        assert mock_task.is_paused is True
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume(self):
        """Test resuming a cron task."""
        from app.db.repositories.cron_tasks import CronTaskRepository

        mock_db = AsyncMock()
        repo = CronTaskRepository(mock_db)

        mock_task = MagicMock()
        mock_task.is_paused = True
        next_run_at = datetime.now(timezone.utc) + timedelta(minutes=5)

        await repo.resume(mock_task, next_run_at)

        assert mock_task.is_paused is False
        assert mock_task.next_run_at == next_run_at
        mock_db.flush.assert_called_once()


class TestExecutionRepository:
    """Tests for ExecutionRepository."""

    @pytest.mark.asyncio
    async def test_create_execution(self):
        """Test creating an execution record."""
        from app.db.repositories.executions import ExecutionRepository

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is synchronous in SQLAlchemy
        repo = ExecutionRepository(mock_db)

        workspace_id = uuid4()
        task_id = uuid4()

        result = await repo.create_execution(
            workspace_id=workspace_id,
            task_type="cron",
            task_id=task_id,
            task_name="Test Task",
            request_url="https://api.example.com",
            request_method="GET",
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_execution(self):
        """Test completing an execution."""
        from app.db.repositories.executions import ExecutionRepository

        mock_db = AsyncMock()
        repo = ExecutionRepository(mock_db)

        # Use naive datetime to match what the repository expects
        mock_execution = MagicMock()
        mock_execution.started_at = datetime.utcnow()

        await repo.complete_execution(
            execution=mock_execution,
            status=TaskStatus.SUCCESS,
            response_status_code=200,
            response_headers={"content-type": "application/json"},
            response_body='{"ok": true}',
            response_size_bytes=12,
        )

        assert mock_execution.status == TaskStatus.SUCCESS
        assert mock_execution.response_status_code == 200
        assert mock_execution.completed_at is not None
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_workspace(self):
        """Test getting executions by workspace."""
        from app.db.repositories.executions import ExecutionRepository

        mock_db = AsyncMock()
        repo = ExecutionRepository(mock_db)

        workspace_id = uuid4()
        mock_execution = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_execution]
        mock_db.execute.return_value = mock_result

        executions = await repo.get_by_workspace(workspace_id)

        assert len(executions) == 1

    @pytest.mark.asyncio
    async def test_count_by_workspace(self):
        """Test counting executions by workspace."""
        from app.db.repositories.executions import ExecutionRepository

        mock_db = AsyncMock()
        repo = ExecutionRepository(mock_db)

        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 100
        mock_db.execute.return_value = mock_result

        count = await repo.count_by_workspace(workspace_id)

        assert count == 100

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting execution statistics."""
        from app.db.repositories.executions import ExecutionRepository

        mock_db = AsyncMock()
        repo = ExecutionRepository(mock_db)

        workspace_id = uuid4()

        # Mock the multiple execute calls
        mock_result1 = MagicMock()
        mock_result1.scalar_one.return_value = 100  # total

        mock_result2 = MagicMock()
        mock_result2.scalar_one.return_value = 80  # success

        mock_result3 = MagicMock()
        mock_result3.scalar_one.return_value = 20  # failed

        mock_result4 = MagicMock()
        mock_result4.scalar_one.return_value = 150.5  # avg_duration

        mock_db.execute.side_effect = [mock_result1, mock_result2, mock_result3, mock_result4]

        stats = await repo.get_stats(workspace_id)

        assert stats["total"] == 100
        assert stats["success"] == 80
        assert stats["failed"] == 20


class TestWorkspaceRepository:
    """Tests for WorkspaceRepository."""

    @pytest.mark.asyncio
    async def test_get_by_owner(self):
        """Test getting workspaces by owner."""
        from app.db.repositories.workspaces import WorkspaceRepository

        mock_db = AsyncMock()
        repo = WorkspaceRepository(mock_db)

        user_id = uuid4()
        mock_workspace = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_workspace]
        mock_db.execute.return_value = mock_result

        workspaces = await repo.get_by_owner(user_id)

        assert len(workspaces) == 1

    @pytest.mark.asyncio
    async def test_slug_exists(self):
        """Test checking if slug exists for owner."""
        from uuid import uuid4

        from app.db.repositories.workspaces import WorkspaceRepository

        mock_db = AsyncMock()
        repo = WorkspaceRepository(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        owner_id = uuid4()
        exists = await repo.slug_exists("test-slug", owner_id=owner_id)

        assert exists is True

    @pytest.mark.asyncio
    async def test_slug_not_exists(self):
        """Test slug doesn't exist for owner."""
        from uuid import uuid4

        from app.db.repositories.workspaces import WorkspaceRepository

        mock_db = AsyncMock()
        repo = WorkspaceRepository(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        owner_id = uuid4()
        exists = await repo.slug_exists("non-existent", owner_id=owner_id)

        assert exists is False


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_email_exists(self):
        """Test checking if email exists."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        repo = UserRepository(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        exists = await repo.email_exists("test@example.com")

        assert exists is True

    @pytest.mark.asyncio
    async def test_email_not_exists(self):
        """Test email doesn't exist."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        repo = UserRepository(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        exists = await repo.email_exists("non-existent@example.com")

        assert exists is False

    @pytest.mark.asyncio
    async def test_get_by_email(self):
        """Test getting user by email."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        repo = UserRepository(mock_db)

        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        user = await repo.get_by_email("test@example.com")

        assert user == mock_user

    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test creating a user."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is synchronous in SQLAlchemy
        repo = UserRepository(mock_db)

        with patch("app.db.repositories.users.User") as mock_user_class:
            mock_user = MagicMock()
            mock_user_class.return_value = mock_user

            result = await repo.create_user(
                email="new@example.com",
                password_hash="hash",
                name="New User",
            )

            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_password(self):
        """Test updating user password."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        repo = UserRepository(mock_db)

        mock_user = MagicMock()
        mock_user.password_hash = "old_hash"

        result = await repo.update_password(mock_user, "new_hash")

        assert result.password_hash == "new_hash"
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email(self):
        """Test verifying user email."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        repo = UserRepository(mock_db)

        mock_user = MagicMock()
        mock_user.email_verified = False

        result = await repo.verify_email(mock_user)

        assert result.email_verified is True
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_telegram_id(self):
        """Test getting user by Telegram ID."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        repo = UserRepository(mock_db)

        mock_user = MagicMock()
        mock_user.telegram_id = 12345678

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        user = await repo.get_by_telegram_id(12345678)

        assert user == mock_user

    @pytest.mark.asyncio
    async def test_update_telegram(self):
        """Test updating user Telegram info."""
        from app.db.repositories.users import UserRepository

        mock_db = AsyncMock()
        repo = UserRepository(mock_db)

        mock_user = MagicMock()
        mock_user.telegram_id = None

        result = await repo.update_telegram(mock_user, 12345678, "testuser")

        assert result.telegram_id == 12345678
        assert result.telegram_username == "testuser"
        mock_db.flush.assert_called_once()
