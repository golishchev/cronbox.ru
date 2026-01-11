"""Unit tests for delayed tasks API endpoints."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.cron_task import TaskStatus


def create_mock_workspace(**kwargs):
    """Create a mock workspace."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "Test Workspace")
    mock.delayed_tasks_this_month = kwargs.get("delayed_tasks_this_month", 0)
    return mock


def create_mock_task(**kwargs):
    """Create a mock delayed task."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.workspace_id = kwargs.get("workspace_id", uuid4())
    mock.worker_id = kwargs.get("worker_id", None)
    mock.name = kwargs.get("name", "Test Task")
    mock.idempotency_key = kwargs.get("idempotency_key", None)
    mock.tags = kwargs.get("tags", [])
    mock.url = kwargs.get("url", "https://example.com/api")
    mock.method = kwargs.get("method", "GET")
    mock.headers = kwargs.get("headers", {})
    mock.body = kwargs.get("body", None)
    mock.execute_at = kwargs.get("execute_at", datetime.now(timezone.utc) + timedelta(hours=1))
    mock.timeout_seconds = kwargs.get("timeout_seconds", 30)
    mock.retry_count = kwargs.get("retry_count", 0)
    mock.retry_delay_seconds = kwargs.get("retry_delay_seconds", 60)
    mock.callback_url = kwargs.get("callback_url", None)
    mock.status = kwargs.get("status", TaskStatus.PENDING)
    mock.executed_at = kwargs.get("executed_at", None)
    mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mock.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return mock


def create_mock_plan(**kwargs):
    """Create a mock plan."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.max_delayed_tasks_per_month = kwargs.get("max_delayed_tasks_per_month", 100)
    return mock


class TestListDelayedTasks:
    """Tests for list_delayed_tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_tasks_success(self):
        """Test listing delayed tasks."""
        from app.api.v1.delayed_tasks import list_delayed_tasks

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_tasks = [create_mock_task(), create_mock_task()]

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_workspace = AsyncMock(return_value=mock_tasks)
            mock_repo.count_by_workspace = AsyncMock(return_value=2)
            mock_repo_class.return_value = mock_repo

            result = await list_delayed_tasks(
                workspace=mock_workspace,
                db=mock_db,
                page=1,
                limit=20,
                status=None,
            )

            assert len(result.tasks) == 2
            assert result.pagination.total == 2


class TestGetDelayedTask:
    """Tests for get_delayed_task endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_success(self):
        """Test getting a delayed task."""
        from app.api.v1.delayed_tasks import get_delayed_task

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = create_mock_task(workspace_id=workspace_id)

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            result = await get_delayed_task(
                task_id=mock_task.id,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test getting non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import get_delayed_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_delayed_task(
                    task_id=task_id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestCreateDelayedTask:
    """Tests for create_delayed_task endpoint."""

    @pytest.mark.asyncio
    async def test_create_with_idempotency_key_existing(self):
        """Test creating task with existing idempotency key returns existing."""
        from app.api.v1.delayed_tasks import create_delayed_task
        from app.schemas.delayed_task import DelayedTaskCreate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        existing_task = create_mock_task()

        data = DelayedTaskCreate(
            name="New Task",
            url="https://example.com/api",
            method="GET",
            execute_at=datetime.now(timezone.utc) + timedelta(hours=1),
            idempotency_key="unique-key-123",
        )

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_idempotency_key = AsyncMock(return_value=existing_task)
            mock_repo_class.return_value = mock_repo

            with patch("app.api.v1.delayed_tasks.WorkspaceRepository"):
                with patch("app.api.v1.delayed_tasks.PlanRepository"):
                    result = await create_delayed_task(
                        data=data,
                        workspace=mock_workspace,
                        db=mock_db,
                    )

                    # Should return existing task without creating new
                    mock_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_limit_reached(self):
        """Test creating task when monthly limit reached."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import create_delayed_task
        from app.schemas.delayed_task import DelayedTaskCreate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace(delayed_tasks_this_month=100)
        mock_plan = create_mock_plan(max_delayed_tasks_per_month=100)
        mock_workspace_with_plan = MagicMock()
        mock_workspace_with_plan.plan = mock_plan

        data = DelayedTaskCreate(
            name="New Task",
            url="https://example.com/api",
            method="GET",
            execute_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            mock_delayed_repo = MagicMock()
            mock_delayed_repo.get_by_idempotency_key = AsyncMock(return_value=None)
            mock_delayed_repo_class.return_value = mock_delayed_repo

            with patch("app.api.v1.delayed_tasks.WorkspaceRepository") as mock_ws_repo_class:
                mock_ws_repo = MagicMock()
                mock_ws_repo.get_with_plan = AsyncMock(return_value=mock_workspace_with_plan)
                mock_ws_repo_class.return_value = mock_ws_repo

                with patch("app.api.v1.delayed_tasks.PlanRepository"):
                    with pytest.raises(HTTPException) as exc_info:
                        await create_delayed_task(
                            data=data,
                            workspace=mock_workspace,
                            db=mock_db,
                        )

                    assert exc_info.value.status_code == 403
                    assert "limit reached" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_execute_at_in_past(self):
        """Test creating task with execute_at in the past."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import create_delayed_task
        from app.schemas.delayed_task import DelayedTaskCreate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_workspace_with_plan = MagicMock()
        mock_workspace_with_plan.plan = None

        data = DelayedTaskCreate(
            name="New Task",
            url="https://example.com/api",
            method="GET",
            execute_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Past
        )

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_delayed_repo_class:
            mock_delayed_repo = MagicMock()
            mock_delayed_repo.get_by_idempotency_key = AsyncMock(return_value=None)
            mock_delayed_repo_class.return_value = mock_delayed_repo

            with patch("app.api.v1.delayed_tasks.WorkspaceRepository") as mock_ws_repo_class:
                mock_ws_repo = MagicMock()
                mock_ws_repo.get_with_plan = AsyncMock(return_value=mock_workspace_with_plan)
                mock_ws_repo_class.return_value = mock_ws_repo

                with patch("app.api.v1.delayed_tasks.PlanRepository"):
                    with pytest.raises(HTTPException) as exc_info:
                        await create_delayed_task(
                            data=data,
                            workspace=mock_workspace,
                            db=mock_db,
                        )

                    assert exc_info.value.status_code == 400
                    assert "future" in exc_info.value.detail


class TestUpdateDelayedTask:
    """Tests for update_delayed_task endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_not_found(self):
        """Test updating non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import update_delayed_task
        from app.schemas.delayed_task import DelayedTaskUpdate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()
        data = DelayedTaskUpdate(name="Updated Name")

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await update_delayed_task(
                    task_id=task_id,
                    data=data,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_non_pending_task(self):
        """Test updating non-pending task fails."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import update_delayed_task
        from app.models.cron_task import TaskStatus
        from app.schemas.delayed_task import DelayedTaskUpdate

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = MagicMock()
        mock_task.workspace_id = workspace_id
        mock_task.status = TaskStatus.RUNNING

        data = DelayedTaskUpdate(name="Updated Name")

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await update_delayed_task(
                    task_id=uuid4(),
                    data=data,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "pending" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_update_execute_at_in_past(self):
        """Test updating execute_at to past fails."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import update_delayed_task
        from app.models.cron_task import TaskStatus
        from app.schemas.delayed_task import DelayedTaskUpdate

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = MagicMock()
        mock_task.workspace_id = workspace_id
        mock_task.status = TaskStatus.PENDING

        data = DelayedTaskUpdate(
            execute_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Past
        )

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await update_delayed_task(
                    task_id=uuid4(),
                    data=data,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "future" in exc_info.value.detail


class TestCancelDelayedTask:
    """Tests for cancel_delayed_task endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test canceling non-existent task."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import cancel_delayed_task

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await cancel_delayed_task(
                    task_id=task_id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_non_pending_task(self):
        """Test canceling non-pending task fails."""
        from fastapi import HTTPException

        from app.api.v1.delayed_tasks import cancel_delayed_task
        from app.models.cron_task import TaskStatus

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = MagicMock()
        mock_task.workspace_id = workspace_id
        mock_task.status = TaskStatus.SUCCESS

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await cancel_delayed_task(
                    task_id=uuid4(),
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "pending" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cancel_pending_task_success(self):
        """Test successfully canceling pending task."""
        from app.api.v1.delayed_tasks import cancel_delayed_task
        from app.models.cron_task import TaskStatus

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_task = MagicMock()
        mock_task.workspace_id = workspace_id
        mock_task.status = TaskStatus.PENDING

        with patch("app.api.v1.delayed_tasks.DelayedTaskRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_task)
            mock_repo.cancel = AsyncMock()
            mock_repo_class.return_value = mock_repo

            result = await cancel_delayed_task(
                task_id=uuid4(),
                workspace=mock_workspace,
                db=mock_db,
            )

            mock_repo.cancel.assert_called_once_with(mock_task)
            mock_db.commit.assert_called_once()
