"""Unit tests for cron tasks API endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def create_mock_workspace(**kwargs):
    """Create a mock workspace."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "Test Workspace")
    mock.default_timezone = kwargs.get("default_timezone", "UTC")
    return mock


def create_mock_task(**kwargs):
    """Create a mock cron task."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.workspace_id = kwargs.get("workspace_id", uuid4())
    mock.worker_id = kwargs.get("worker_id", None)
    mock.name = kwargs.get("name", "Test Task")
    mock.description = kwargs.get("description", None)
    mock.url = kwargs.get("url", "https://example.com/api")
    mock.method = kwargs.get("method", "GET")
    mock.headers = kwargs.get("headers", {})
    mock.body = kwargs.get("body", None)
    mock.schedule = kwargs.get("schedule", "0 * * * *")
    mock.timezone = kwargs.get("timezone", "UTC")
    mock.timeout_seconds = kwargs.get("timeout_seconds", 30)
    mock.retry_count = kwargs.get("retry_count", 0)
    mock.retry_delay_seconds = kwargs.get("retry_delay_seconds", 60)
    mock.is_active = kwargs.get("is_active", True)
    mock.is_paused = kwargs.get("is_paused", False)
    mock.status = kwargs.get("status", "idle")
    mock.last_status = kwargs.get("last_status", None)
    mock.notify_on_failure = kwargs.get("notify_on_failure", True)
    mock.notify_on_recovery = kwargs.get("notify_on_recovery", False)
    mock.next_run_at = kwargs.get("next_run_at", datetime.now(timezone.utc))
    mock.last_run_at = kwargs.get("last_run_at", None)
    mock.last_success_at = kwargs.get("last_success_at", None)
    mock.last_failure_at = kwargs.get("last_failure_at", None)
    mock.consecutive_failures = kwargs.get("consecutive_failures", 0)
    mock.total_runs = kwargs.get("total_runs", 0)
    mock.successful_runs = kwargs.get("successful_runs", 0)
    mock.failed_runs = kwargs.get("failed_runs", 0)
    mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mock.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return mock


def create_mock_plan(**kwargs):
    """Create a mock plan."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.max_cron_tasks = kwargs.get("max_cron_tasks", 10)
    mock.min_cron_interval_minutes = kwargs.get("min_cron_interval_minutes", 1)
    return mock


class TestCalculateNextRun:
    """Tests for calculate_next_run function."""

    def test_calculate_next_run(self):
        """Test calculating next run time."""
        from app.api.v1.cron_tasks import calculate_next_run

        next_run = calculate_next_run("0 * * * *", "UTC")

        assert next_run is not None
        assert isinstance(next_run, datetime)


class TestCalculateMinInterval:
    """Tests for calculate_min_interval_minutes function."""

    def test_calculate_min_interval_hourly(self):
        """Test calculating interval for hourly cron."""
        from app.api.v1.cron_tasks import calculate_min_interval_minutes

        interval = calculate_min_interval_minutes("0 * * * *", "UTC")

        assert interval == 60

    def test_calculate_min_interval_every_5_minutes(self):
        """Test calculating interval for every 5 minutes cron."""
        from app.api.v1.cron_tasks import calculate_min_interval_minutes

        interval = calculate_min_interval_minutes("*/5 * * * *", "UTC")

        assert interval == 5


class TestListCronTasks:
    """Tests for list_cron_tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_tasks_success(self):
        """Test listing cron tasks."""
        from app.api.v1.cron_tasks import list_cron_tasks

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_tasks = [create_mock_task(), create_mock_task()]

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_workspace = AsyncMock(return_value=mock_tasks)
            mock_repo.count_by_workspace = AsyncMock(return_value=2)
            mock_repo_class.return_value = mock_repo

            result = await list_cron_tasks(
                workspace=mock_workspace,
                db=mock_db,
                page=1,
                limit=20,
                is_active=None,
            )

            assert len(result.tasks) == 2
            assert result.pagination.total == 2


class TestGetCronTask:
    """Tests for get_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_success(self):
        """Test getting a cron task."""
        from app.api.v1.cron_tasks import get_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            result = await get_cron_task(
                task_id=mock_task.id,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test getting a non-existent cron task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import get_cron_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_cron_task(
                    task_id=task_id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_task_wrong_workspace(self):
        """Test getting a task from wrong workspace."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import get_cron_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_task = create_mock_task(workspace_id=uuid4())  # Different workspace

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_cron_task(
                    task_id=mock_task.id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestCreateCronTask:
    """Tests for create_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_limit_reached(self):
        """Test creating task when limit reached."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import create_cron_task
        from app.schemas.cron_task import CronTaskCreate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_plan = create_mock_plan(max_cron_tasks=5)
        mock_workspace_with_plan = MagicMock()
        mock_workspace_with_plan.plan = mock_plan

        data = CronTaskCreate(
            name="New Task",
            url="https://example.com/api",
            method="GET",
            schedule="0 * * * *",
        )

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_cron_repo_class:
            mock_cron_repo = MagicMock()
            mock_cron_repo.count_by_workspace = AsyncMock(return_value=5)  # At limit
            mock_cron_repo_class.return_value = mock_cron_repo

            with patch("app.api.v1.cron_tasks.WorkspaceRepository") as mock_ws_repo_class:
                mock_ws_repo = MagicMock()
                mock_ws_repo.get_with_plan = AsyncMock(return_value=mock_workspace_with_plan)
                mock_ws_repo_class.return_value = mock_ws_repo

                with patch("app.api.v1.cron_tasks.PlanRepository"):
                    with pytest.raises(HTTPException) as exc_info:
                        await create_cron_task(data=data, workspace=mock_workspace, db=mock_db)

                    assert exc_info.value.status_code == 403
                    assert "limit reached" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_task_interval_too_frequent(self):
        """Test creating task with too frequent interval."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import create_cron_task
        from app.schemas.cron_task import CronTaskCreate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_plan = create_mock_plan(max_cron_tasks=10, min_cron_interval_minutes=60)
        mock_workspace_with_plan = MagicMock()
        mock_workspace_with_plan.plan = mock_plan

        data = CronTaskCreate(
            name="New Task",
            url="https://example.com/api",
            method="GET",
            schedule="*/5 * * * *",  # Every 5 minutes
        )

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_cron_repo_class:
            mock_cron_repo = MagicMock()
            mock_cron_repo.count_by_workspace = AsyncMock(return_value=1)
            mock_cron_repo_class.return_value = mock_cron_repo

            with patch("app.api.v1.cron_tasks.WorkspaceRepository") as mock_ws_repo_class:
                mock_ws_repo = MagicMock()
                mock_ws_repo.get_with_plan = AsyncMock(return_value=mock_workspace_with_plan)
                mock_ws_repo_class.return_value = mock_ws_repo

                with patch("app.api.v1.cron_tasks.PlanRepository"):
                    with pytest.raises(HTTPException) as exc_info:
                        await create_cron_task(data=data, workspace=mock_workspace, db=mock_db)

                    assert exc_info.value.status_code == 403
                    assert "too frequent" in exc_info.value.detail


class TestCreateCronTaskSuccess:
    """Tests for successful create_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_success(self):
        """Test successfully creating a cron task."""
        from app.api.v1.cron_tasks import create_cron_task
        from app.schemas.cron_task import CronTaskCreate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_plan = create_mock_plan(max_cron_tasks=10, min_cron_interval_minutes=1)
        mock_workspace_with_plan = MagicMock()
        mock_workspace_with_plan.plan = mock_plan
        created_task = create_mock_task(workspace_id=mock_workspace.id)

        data = CronTaskCreate(
            name="New Task",
            url="https://example.com/api",
            method="GET",
            schedule="0 * * * *",  # Every hour
        )

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_cron_repo_class:
            mock_cron_repo = MagicMock()
            mock_cron_repo.count_by_workspace = AsyncMock(return_value=1)
            mock_cron_repo.create = AsyncMock(return_value=created_task)
            mock_cron_repo_class.return_value = mock_cron_repo

            with patch("app.api.v1.cron_tasks.WorkspaceRepository") as mock_ws_repo_class:
                mock_ws_repo = MagicMock()
                mock_ws_repo.get_with_plan = AsyncMock(return_value=mock_workspace_with_plan)
                mock_ws_repo.update_cron_tasks_count = AsyncMock()
                mock_ws_repo_class.return_value = mock_ws_repo

                with patch("app.api.v1.cron_tasks.PlanRepository"):
                    result = await create_cron_task(data=data, workspace=mock_workspace, db=mock_db)

                    assert result is not None
                    mock_cron_repo.create.assert_called_once()
                    mock_db.commit.assert_called_once()


class TestDeleteCronTask:
    """Tests for delete_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_delete_task_success(self):
        """Test successfully deleting a cron task."""
        from app.api.v1.cron_tasks import delete_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_cron_repo_class:
            mock_cron_repo = MagicMock()
            mock_cron_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_cron_repo.delete = AsyncMock()
            mock_cron_repo_class.return_value = mock_cron_repo

            with patch("app.api.v1.cron_tasks.WorkspaceRepository") as mock_ws_repo_class:
                mock_ws_repo = MagicMock()
                mock_ws_repo.update_cron_tasks_count = AsyncMock()
                mock_ws_repo_class.return_value = mock_ws_repo

                result = await delete_cron_task(
                    task_id=mock_task.id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

                assert result is None
                mock_cron_repo.delete.assert_called_once_with(mock_task)
                mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self):
        """Test deleting non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import delete_cron_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with patch("app.api.v1.cron_tasks.WorkspaceRepository"):
                with pytest.raises(HTTPException) as exc_info:
                    await delete_cron_task(
                        task_id=task_id,
                        workspace=mock_workspace,
                        db=mock_db,
                    )

                assert exc_info.value.status_code == 404


class TestRunCronTask:
    """Tests for run_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_run_task_not_found(self):
        """Test running non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import run_cron_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await run_cron_task(
                    task_id=task_id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_run_inactive_task(self):
        """Test running inactive task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import run_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, is_active=False)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await run_cron_task(
                    task_id=mock_task.id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "inactive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_run_task_success(self):
        """Test successfully running a cron task."""
        from app.api.v1.cron_tasks import run_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, is_active=True)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with patch("arq.create_pool") as mock_create_pool:
                mock_redis = AsyncMock()
                mock_redis.enqueue_job = AsyncMock()
                mock_redis.close = AsyncMock()
                mock_create_pool.return_value = mock_redis

                result = await run_cron_task(
                    task_id=mock_task.id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

                assert result["message"] == "Task queued for execution"
                assert result["task_id"] == str(mock_task.id)
                mock_redis.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_task_enqueue_fails(self):
        """Test running task when enqueue fails."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import run_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, is_active=True)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with patch("arq.create_pool") as mock_create_pool:
                mock_create_pool.side_effect = Exception("Redis connection failed")

                with pytest.raises(HTTPException) as exc_info:
                    await run_cron_task(
                        task_id=mock_task.id,
                        workspace=mock_workspace,
                        db=mock_db,
                    )

                assert exc_info.value.status_code == 503
                assert "Failed to enqueue" in exc_info.value.detail


class TestPauseCronTask:
    """Tests for pause_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_pause_task_not_found(self):
        """Test pausing non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import pause_cron_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await pause_cron_task(
                    task_id=task_id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_pause_already_paused(self):
        """Test pausing already paused task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import pause_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, is_paused=True)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await pause_cron_task(
                    task_id=mock_task.id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "already paused" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_pause_task_success(self):
        """Test successfully pausing a cron task."""
        from app.api.v1.cron_tasks import pause_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, is_paused=False)
        paused_task = create_mock_task(workspace_id=workspace_id, is_paused=True)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo.pause = AsyncMock(return_value=paused_task)
            mock_repo_class.return_value = mock_repo

            result = await pause_cron_task(
                task_id=mock_task.id,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None
            mock_repo.pause.assert_called_once_with(mock_task)
            mock_db.commit.assert_called_once()


class TestResumeCronTask:
    """Tests for resume_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_resume_task_not_found(self):
        """Test resuming non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import resume_cron_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await resume_cron_task(
                    task_id=task_id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_resume_not_paused(self):
        """Test resuming task that is not paused."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import resume_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, is_paused=False)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await resume_cron_task(
                    task_id=mock_task.id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "not paused" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_resume_task_success(self):
        """Test successfully resuming a paused cron task."""
        from unittest.mock import ANY

        from app.api.v1.cron_tasks import resume_cron_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, is_paused=True)
        resumed_task = create_mock_task(workspace_id=workspace_id, is_paused=False)

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo.resume = AsyncMock(return_value=resumed_task)
            mock_repo_class.return_value = mock_repo

            result = await resume_cron_task(
                task_id=mock_task.id,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None
            # Resume is called with task and next_run_at datetime
            mock_repo.resume.assert_called_once_with(mock_task, ANY)
            mock_db.commit.assert_called_once()


class TestUpdateCronTask:
    """Tests for update_cron_task endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_not_found(self):
        """Test updating non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.cron_tasks import update_cron_task
        from app.schemas.cron_task import CronTaskUpdate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()
        data = CronTaskUpdate(name="Updated Name")

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await update_cron_task(
                    task_id=task_id,
                    data=data,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task_success(self):
        """Test successfully updating a cron task."""
        from app.api.v1.cron_tasks import update_cron_task
        from app.schemas.cron_task import CronTaskUpdate

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id)
        updated_task = create_mock_task(workspace_id=workspace_id, name="Updated Name")

        data = CronTaskUpdate(name="Updated Name")

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo.update = AsyncMock(return_value=updated_task)
            mock_repo_class.return_value = mock_repo

            result = await update_cron_task(
                task_id=mock_task.id,
                data=data,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None
            mock_repo.update.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_with_schedule_change(self):
        """Test updating a cron task with schedule change."""
        from app.api.v1.cron_tasks import update_cron_task
        from app.schemas.cron_task import CronTaskUpdate

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id, schedule="0 * * * *")
        updated_task = create_mock_task(workspace_id=workspace_id, schedule="30 * * * *")
        mock_plan = create_mock_plan(min_cron_interval_minutes=1)
        mock_workspace_with_plan = MagicMock()
        mock_workspace_with_plan.plan = mock_plan

        data = CronTaskUpdate(schedule="30 * * * *")

        with patch("app.api.v1.cron_tasks.CronTaskRepository") as mock_cron_repo_class:
            mock_cron_repo = MagicMock()
            mock_cron_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_cron_repo.update = AsyncMock(return_value=updated_task)
            mock_cron_repo_class.return_value = mock_cron_repo

            with patch("app.api.v1.cron_tasks.WorkspaceRepository") as mock_ws_repo_class:
                mock_ws_repo = MagicMock()
                mock_ws_repo.get_with_plan = AsyncMock(return_value=mock_workspace_with_plan)
                mock_ws_repo_class.return_value = mock_ws_repo

                result = await update_cron_task(
                    task_id=mock_task.id,
                    data=data,
                    workspace=mock_workspace,
                    db=mock_db,
                )

                assert result is not None
                mock_cron_repo.update.assert_called_once()
                mock_db.commit.assert_called_once()
