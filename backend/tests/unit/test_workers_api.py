"""Unit tests for workers API endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def create_mock_worker(**kwargs):
    """Create a mock worker."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.workspace_id = kwargs.get("workspace_id", uuid4())
    mock.name = kwargs.get("name", "Test Worker")
    mock.description = kwargs.get("description", "Test description")
    mock.region = kwargs.get("region", "us-east")
    mock.api_key_prefix = kwargs.get("api_key_prefix", "wk_abc12")
    mock.status = kwargs.get("status", "online")
    mock.last_heartbeat = kwargs.get("last_heartbeat", datetime.now(timezone.utc))
    mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mock.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return mock


def create_mock_workspace(**kwargs):
    """Create a mock workspace."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "Test Workspace")
    return mock


class TestListWorkers:
    """Tests for list_workers endpoint."""

    @pytest.mark.asyncio
    async def test_list_workers_success(self):
        """Test listing workers."""
        from app.api.v1.workers import list_workers

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_workers = [create_mock_worker(), create_mock_worker()]

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_workers_by_workspace = AsyncMock(return_value=mock_workers)

            result = await list_workers(workspace=mock_workspace, db=mock_db)

            assert len(result) == 2
            mock_service.get_workers_by_workspace.assert_called_once_with(
                mock_db, mock_workspace.id
            )


class TestCreateWorker:
    """Tests for create_worker endpoint."""

    @pytest.mark.asyncio
    async def test_create_worker_success(self):
        """Test creating a worker."""
        from app.api.v1.workers import create_worker
        from app.schemas.worker import WorkerCreate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_worker = create_mock_worker(workspace_id=mock_workspace.id)
        api_key = "wk_test123456"

        data = WorkerCreate(name="New Worker", description="New worker desc")

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.create_worker = AsyncMock(return_value=(mock_worker, api_key))

            result = await create_worker(
                workspace=mock_workspace,
                data=data,
                db=mock_db,
            )

            assert result.api_key == api_key
            mock_service.create_worker.assert_called_once()


class TestGetWorker:
    """Tests for get_worker endpoint."""

    @pytest.mark.asyncio
    async def test_get_worker_success(self):
        """Test getting a worker."""
        from app.api.v1.workers import get_worker

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_worker = create_mock_worker(workspace_id=mock_workspace.id)

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=mock_worker)

            result = await get_worker(
                workspace=mock_workspace,
                worker_id=mock_worker.id,
                db=mock_db,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_worker_not_found(self):
        """Test getting a non-existent worker."""
        from fastapi import HTTPException

        from app.api.v1.workers import get_worker

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        worker_id = uuid4()

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_worker(
                    workspace=mock_workspace,
                    worker_id=worker_id,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestUpdateWorker:
    """Tests for update_worker endpoint."""

    @pytest.mark.asyncio
    async def test_update_worker_success(self):
        """Test updating a worker."""
        from app.api.v1.workers import update_worker
        from app.schemas.worker import WorkerUpdate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_worker = create_mock_worker(workspace_id=mock_workspace.id)
        updated_worker = create_mock_worker(name="Updated Worker")

        data = WorkerUpdate(name="Updated Worker")

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=mock_worker)
            mock_service.update_worker = AsyncMock(return_value=updated_worker)

            result = await update_worker(
                workspace=mock_workspace,
                data=data,
                worker_id=mock_worker.id,
                db=mock_db,
            )

            assert result is not None
            mock_service.update_worker.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_worker_not_found(self):
        """Test updating a non-existent worker."""
        from fastapi import HTTPException

        from app.api.v1.workers import update_worker
        from app.schemas.worker import WorkerUpdate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        worker_id = uuid4()
        data = WorkerUpdate(name="Updated")

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await update_worker(
                    workspace=mock_workspace,
                    data=data,
                    worker_id=worker_id,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestDeleteWorker:
    """Tests for delete_worker endpoint."""

    @pytest.mark.asyncio
    async def test_delete_worker_success(self):
        """Test deleting a worker."""
        from app.api.v1.workers import delete_worker

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_worker = create_mock_worker(workspace_id=mock_workspace.id)

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=mock_worker)
            mock_service.delete_worker = AsyncMock()

            result = await delete_worker(
                workspace=mock_workspace,
                worker_id=mock_worker.id,
                db=mock_db,
            )

            assert result is None
            mock_service.delete_worker.assert_called_once_with(mock_db, mock_worker)

    @pytest.mark.asyncio
    async def test_delete_worker_not_found(self):
        """Test deleting a non-existent worker."""
        from fastapi import HTTPException

        from app.api.v1.workers import delete_worker

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        worker_id = uuid4()

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await delete_worker(
                    workspace=mock_workspace,
                    worker_id=worker_id,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestRegenerateWorkerKey:
    """Tests for regenerate_worker_key endpoint."""

    @pytest.mark.asyncio
    async def test_regenerate_key_success(self):
        """Test regenerating worker API key."""
        from app.api.v1.workers import regenerate_worker_key

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        mock_worker = create_mock_worker(workspace_id=mock_workspace.id)
        new_api_key = "wk_new123456"

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=mock_worker)
            mock_service.regenerate_api_key = AsyncMock(return_value=new_api_key)

            result = await regenerate_worker_key(
                workspace=mock_workspace,
                worker_id=mock_worker.id,
                db=mock_db,
            )

            assert result.api_key == new_api_key

    @pytest.mark.asyncio
    async def test_regenerate_key_not_found(self):
        """Test regenerating key for non-existent worker."""
        from fastapi import HTTPException

        from app.api.v1.workers import regenerate_worker_key

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        worker_id = uuid4()

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.get_worker_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await regenerate_worker_key(
                    workspace=mock_workspace,
                    worker_id=worker_id,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestWorkerHeartbeat:
    """Tests for worker_heartbeat endpoint."""

    @pytest.mark.asyncio
    async def test_heartbeat_success(self):
        """Test worker heartbeat."""
        from app.api.v1.workers import worker_heartbeat
        from app.models.worker import WorkerStatus
        from app.schemas.worker import WorkerHeartbeat

        mock_db = AsyncMock()
        mock_worker = create_mock_worker()
        heartbeat = WorkerHeartbeat(status=WorkerStatus.ONLINE)

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.update_heartbeat = AsyncMock()

            result = await worker_heartbeat(
                worker=mock_worker,
                heartbeat=heartbeat,
                db=mock_db,
            )

            assert result.acknowledged is True
            assert result.server_time is not None


class TestPollTasks:
    """Tests for poll_tasks endpoint."""

    @pytest.mark.asyncio
    async def test_poll_tasks_success(self):
        """Test polling tasks."""
        from app.api.v1.workers import poll_tasks
        from app.schemas.worker import WorkerTaskInfo

        mock_worker = create_mock_worker()
        mock_tasks = [
            WorkerTaskInfo(
                task_id=uuid4(),
                task_type="cron",
                url="https://example.com/api",
                method="GET",
                headers={},
                body=None,
                timeout_seconds=30,
                workspace_id=uuid4(),
            ),
            WorkerTaskInfo(
                task_id=uuid4(),
                task_type="delayed",
                url="https://example.com/webhook",
                method="POST",
                headers={"Content-Type": "application/json"},
                body='{"key": "value"}',
                timeout_seconds=60,
                workspace_id=uuid4(),
            ),
        ]

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.poll_tasks = AsyncMock(return_value=mock_tasks)

            result = await poll_tasks(worker=mock_worker, max_tasks=10)

            assert len(result.tasks) == 2
            assert result.poll_interval_seconds == 5

    @pytest.mark.asyncio
    async def test_poll_tasks_empty(self):
        """Test polling tasks when none available."""
        from app.api.v1.workers import poll_tasks

        mock_worker = create_mock_worker()

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.poll_tasks = AsyncMock(return_value=[])

            result = await poll_tasks(worker=mock_worker, max_tasks=10)

            assert len(result.tasks) == 0


class TestSubmitTaskResult:
    """Tests for submit_task_result endpoint."""

    @pytest.mark.asyncio
    async def test_submit_result_success(self):
        """Test submitting task result."""
        from app.api.v1.workers import submit_task_result
        from app.schemas.worker import WorkerTaskResult

        mock_db = AsyncMock()
        mock_worker = create_mock_worker()
        task_id = uuid4()

        result_data = WorkerTaskResult(
            task_id=task_id,
            task_type="cron",
            status_code=200,
            response_body='{"ok": true}',
            response_headers={"Content-Type": "application/json"},
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            duration_ms=100,
            error=None,
        )

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.process_task_result = AsyncMock(return_value=True)

            result = await submit_task_result(
                worker=mock_worker,
                result=result_data,
                db=mock_db,
            )

            assert result["status"] == "ok"
            assert result["task_id"] == str(task_id)

    @pytest.mark.asyncio
    async def test_submit_result_failure(self):
        """Test submitting task result when processing fails."""
        from fastapi import HTTPException

        from app.api.v1.workers import submit_task_result
        from app.schemas.worker import WorkerTaskResult

        mock_db = AsyncMock()
        mock_worker = create_mock_worker()

        result_data = WorkerTaskResult(
            task_id=uuid4(),
            task_type="cron",
            status_code=200,
            response_body="",
            response_headers={},
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            duration_ms=100,
            error=None,
        )

        with patch("app.api.v1.workers.worker_service") as mock_service:
            mock_service.process_task_result = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await submit_task_result(
                    worker=mock_worker,
                    result=result_data,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 500


class TestGetWorkerInfo:
    """Tests for get_worker_info endpoint."""

    @pytest.mark.asyncio
    async def test_get_worker_info_success(self):
        """Test getting worker info."""
        from app.api.v1.workers import get_worker_info

        mock_worker = create_mock_worker()

        result = await get_worker_info(worker=mock_worker)

        assert result is not None
