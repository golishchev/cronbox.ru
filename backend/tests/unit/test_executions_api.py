"""Unit tests for executions API endpoints."""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.cron_task import TaskStatus


def create_mock_workspace(**kwargs):
    """Create a mock workspace."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "Test Workspace")
    return mock


def create_mock_execution(**kwargs):
    """Create a mock execution."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.workspace_id = kwargs.get("workspace_id", uuid4())
    mock.task_id = kwargs.get("task_id", uuid4())
    mock.task_type = kwargs.get("task_type", "cron")
    mock.task_name = kwargs.get("task_name", "Test Task")
    mock.status = kwargs.get("status", TaskStatus.SUCCESS)
    mock.started_at = kwargs.get("started_at", datetime.now(timezone.utc))
    mock.finished_at = kwargs.get("finished_at", datetime.now(timezone.utc))
    mock.duration_ms = kwargs.get("duration_ms", 100)
    mock.request_url = kwargs.get("request_url", "https://example.com/api")
    mock.request_method = kwargs.get("request_method", "GET")
    mock.request_headers = kwargs.get("request_headers", {})
    mock.request_body = kwargs.get("request_body", None)
    mock.response_status_code = kwargs.get("response_status_code", 200)
    mock.response_headers = kwargs.get("response_headers", {})
    mock.response_body = kwargs.get("response_body", '{"ok": true}')
    mock.error = kwargs.get("error", None)
    mock.error_message = kwargs.get("error_message", None)
    mock.error_type = kwargs.get("error_type", None)
    mock.retry_attempt = kwargs.get("retry_attempt", 0)
    mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    return mock


class TestListExecutions:
    """Tests for list_executions endpoint."""

    @pytest.mark.asyncio
    async def test_list_executions_success(self):
        """Test listing executions."""
        from app.api.v1.executions import list_executions

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_executions = [
            create_mock_execution(workspace_id=workspace_id),
            create_mock_execution(workspace_id=workspace_id),
        ]

        with patch("app.api.v1.executions.ExecutionRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_workspace = AsyncMock(return_value=mock_executions)
            mock_repo.count_by_workspace = AsyncMock(return_value=2)
            mock_repo_class.return_value = mock_repo

            result = await list_executions(
                workspace=mock_workspace,
                db=mock_db,
                page=1,
                limit=20,
                task_type=None,
                task_id=None,
                status=None,
                start_date=None,
                end_date=None,
            )

            assert len(result.executions) == 2
            assert result.pagination.total == 2

    @pytest.mark.asyncio
    async def test_list_executions_with_filters(self):
        """Test listing executions with filters."""
        from app.api.v1.executions import list_executions

        mock_db = AsyncMock()
        workspace_id = uuid4()
        task_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_executions = [create_mock_execution(workspace_id=workspace_id)]

        with patch("app.api.v1.executions.ExecutionRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_workspace = AsyncMock(return_value=mock_executions)
            mock_repo.count_by_workspace = AsyncMock(return_value=1)
            mock_repo_class.return_value = mock_repo

            result = await list_executions(
                workspace=mock_workspace,
                db=mock_db,
                page=1,
                limit=10,
                task_type="cron",
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc),
            )

            assert len(result.executions) == 1
            mock_repo.get_by_workspace.assert_called_once()


class TestGetExecutionStats:
    """Tests for get_execution_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Test getting execution stats."""
        from app.api.v1.executions import get_execution_stats

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_stats = {
            "total": 100,
            "success": 95,
            "failed": 5,
            "success_rate": 95.0,
            "avg_duration_ms": 150.0,
        }

        with patch("app.api.v1.executions.ExecutionRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_stats = AsyncMock(return_value=mock_stats)
            mock_repo_class.return_value = mock_repo

            result = await get_execution_stats(
                workspace=mock_workspace,
                db=mock_db,
                task_id=None,
                start_date=None,
                end_date=None,
            )

            assert result.total == 100
            assert result.success == 95

    @pytest.mark.asyncio
    async def test_get_stats_with_task_id(self):
        """Test getting execution stats for specific task."""
        from app.api.v1.executions import get_execution_stats

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        task_id = uuid4()
        mock_stats = {
            "total": 50,
            "success": 48,
            "failed": 2,
            "success_rate": 96.0,
            "avg_duration_ms": 120.0,
        }

        with patch("app.api.v1.executions.ExecutionRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_stats = AsyncMock(return_value=mock_stats)
            mock_repo_class.return_value = mock_repo

            result = await get_execution_stats(
                workspace=mock_workspace,
                db=mock_db,
                task_id=task_id,
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc),
            )

            assert result.total == 50
            mock_repo.get_stats.assert_called_once()


class TestGetExecution:
    """Tests for get_execution endpoint."""

    @pytest.mark.asyncio
    async def test_get_execution_success(self):
        """Test getting a specific execution."""
        from app.api.v1.executions import get_execution

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = create_mock_workspace(id=workspace_id)
        mock_execution = create_mock_execution(workspace_id=workspace_id)

        with patch("app.api.v1.executions.ExecutionRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_execution)
            mock_repo_class.return_value = mock_repo

            result = await get_execution(
                execution_id=mock_execution.id,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_execution_not_found(self):
        """Test getting a non-existent execution."""
        from app.api.v1.executions import get_execution
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        execution_id = uuid4()

        with patch("app.api.v1.executions.ExecutionRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_execution(
                    execution_id=execution_id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_execution_wrong_workspace(self):
        """Test getting execution from wrong workspace."""
        from app.api.v1.executions import get_execution
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_execution = create_mock_execution(workspace_id=uuid4())  # Different workspace

        with patch("app.api.v1.executions.ExecutionRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_execution)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_execution(
                    execution_id=mock_execution.id,
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
