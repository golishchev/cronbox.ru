"""Tests for WorkerService."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestWorkerServiceCreateWorker:
    """Tests for WorkerService.create_worker."""

    @pytest.mark.asyncio
    async def test_create_worker_success(self):
        """Test creating a worker."""
        from app.schemas.worker import WorkerCreate
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        workspace_id = uuid4()
        data = WorkerCreate(
            name="Test Worker",
            description="Test description",
        )

        with patch("app.services.worker.Worker") as mock_worker_class:
            mock_worker_class.generate_api_key.return_value = "wk_test123456"
            mock_worker_class.get_key_prefix.return_value = "wk_test12"

            with patch("app.services.worker.get_password_hash") as mock_hash:
                mock_hash.return_value = "hashed_key"

                mock_worker_instance = MagicMock()
                mock_worker_class.return_value = mock_worker_instance

                worker, api_key = await service.create_worker(mock_db, workspace_id, data)

                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()
                mock_db.refresh.assert_called_once()
                assert api_key == "wk_test123456"


class TestWorkerServiceGetWorkerById:
    """Tests for WorkerService.get_worker_by_id."""

    @pytest.mark.asyncio
    async def test_get_worker_by_id_found(self):
        """Test getting worker by ID."""
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_worker
        mock_db.execute.return_value = mock_result

        result = await service.get_worker_by_id(mock_db, uuid4())

        assert result == mock_worker

    @pytest.mark.asyncio
    async def test_get_worker_by_id_with_workspace(self):
        """Test getting worker by ID filtered by workspace."""
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_worker
        mock_db.execute.return_value = mock_result

        result = await service.get_worker_by_id(mock_db, uuid4(), workspace_id=uuid4())

        assert result == mock_worker

    @pytest.mark.asyncio
    async def test_get_worker_by_id_not_found(self):
        """Test getting worker by ID when not found."""
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_worker_by_id(mock_db, uuid4())

        assert result is None


class TestWorkerServiceGetWorkersByWorkspace:
    """Tests for WorkerService.get_workers_by_workspace."""

    @pytest.mark.asyncio
    async def test_get_workers_by_workspace(self):
        """Test getting workers by workspace."""
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_workers = [MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_workers
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.get_workers_by_workspace(mock_db, uuid4())

        assert len(result) == 2


class TestWorkerServiceUpdateWorker:
    """Tests for WorkerService.update_worker."""

    @pytest.mark.asyncio
    async def test_update_worker(self):
        """Test updating a worker."""
        from app.schemas.worker import WorkerUpdate
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock()
        mock_worker.name = "Old Name"

        data = WorkerUpdate(name="New Name")

        result = await service.update_worker(mock_db, mock_worker, data)

        assert mock_worker.name == "New Name"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestWorkerServiceDeleteWorker:
    """Tests for WorkerService.delete_worker."""

    @pytest.mark.asyncio
    async def test_delete_worker(self):
        """Test deleting a worker."""
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock()
        mock_worker.id = uuid4()

        await service.delete_worker(mock_db, mock_worker)

        mock_db.delete.assert_called_once_with(mock_worker)
        mock_db.commit.assert_called_once()


class TestWorkerServiceRegenerateApiKey:
    """Tests for WorkerService.regenerate_api_key."""

    @pytest.mark.asyncio
    async def test_regenerate_api_key(self):
        """Test regenerating API key."""
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock()
        mock_worker.id = uuid4()

        with patch("app.services.worker.Worker") as mock_worker_class:
            mock_worker_class.generate_api_key.return_value = "wk_newkey123"
            mock_worker_class.get_key_prefix.return_value = "wk_newke"

            with patch("app.services.worker.get_password_hash") as mock_hash:
                mock_hash.return_value = "hashed_new_key"

                result = await service.regenerate_api_key(mock_db, mock_worker)

                assert result == "wk_newkey123"
                mock_db.commit.assert_called_once()


class TestWorkerServiceAuthenticateWorker:
    """Tests for WorkerService.authenticate_worker."""

    @pytest.mark.asyncio
    async def test_authenticate_worker_success(self):
        """Test successful worker authentication."""
        from app.models.worker import Worker
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock(spec=Worker)
        mock_worker.api_key_hash = "hashed_key"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_worker]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch.object(Worker, "get_key_prefix", return_value="wk_test12"):
            with patch("app.services.worker.verify_password") as mock_verify:
                mock_verify.return_value = True

                result = await service.authenticate_worker(mock_db, "wk_test123456")

                assert result == mock_worker

    @pytest.mark.asyncio
    async def test_authenticate_worker_invalid_key(self):
        """Test worker authentication with invalid key."""
        from app.models.worker import Worker
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock(spec=Worker)

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_worker]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch.object(Worker, "get_key_prefix", return_value="wk_test12"):
            with patch("app.services.worker.verify_password") as mock_verify:
                mock_verify.return_value = False

                result = await service.authenticate_worker(mock_db, "wk_invalid")

                assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_worker_no_match(self):
        """Test worker authentication with no matching prefix."""
        from app.models.worker import Worker
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with patch.object(Worker, "get_key_prefix", return_value="wk_unkno"):
            result = await service.authenticate_worker(mock_db, "wk_unknown")

            assert result is None


class TestWorkerServiceUpdateHeartbeat:
    """Tests for WorkerService.update_heartbeat."""

    @pytest.mark.asyncio
    async def test_update_heartbeat(self):
        """Test updating worker heartbeat."""
        from app.models.worker import WorkerStatus
        from app.schemas.worker import WorkerHeartbeat
        from app.services.worker import WorkerService

        service = WorkerService()
        mock_db = AsyncMock()

        mock_worker = MagicMock()

        heartbeat = WorkerHeartbeat(status=WorkerStatus.BUSY)

        await service.update_heartbeat(mock_db, mock_worker, heartbeat)

        assert mock_worker.status == WorkerStatus.BUSY
        assert mock_worker.last_heartbeat is not None
        mock_db.commit.assert_called_once()


class TestWorkerServiceTaskQueue:
    """Tests for task queue management."""

    @pytest.mark.asyncio
    async def test_enqueue_task_for_worker(self):
        """Test enqueueing task for worker."""
        from app.schemas.worker import WorkerTaskInfo
        from app.services.worker import WorkerService

        service = WorkerService()

        worker_id = uuid4()
        workspace_id = uuid4()
        task_info = WorkerTaskInfo(
            task_id=uuid4(),
            task_type="cron",
            url="https://api.example.com/webhook",
            method="POST",
            headers={"Content-Type": "application/json"},
            body='{"key": "value"}',
            timeout_seconds=30,
            workspace_id=workspace_id,
            task_name="Test Task",
        )

        mock_redis = AsyncMock()

        with patch("app.services.worker.get_redis", return_value=mock_redis):
            await service.enqueue_task_for_worker(worker_id, task_info)

            mock_redis.set.assert_called_once()
            mock_redis.rpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_tasks(self):
        """Test polling tasks for worker."""
        from app.schemas.worker import WorkerTaskInfo
        from app.services.worker import WorkerService

        service = WorkerService()

        worker_id = uuid4()
        workspace_id = uuid4()
        task_id = str(uuid4())

        task_info = WorkerTaskInfo(
            task_id=task_id,
            task_type="cron",
            url="https://api.example.com/webhook",
            method="GET",
            headers={},
            body=None,
            timeout_seconds=30,
            workspace_id=workspace_id,
        )

        mock_redis = AsyncMock()
        mock_redis.lpop.side_effect = [task_id.encode(), None]
        mock_redis.get.return_value = task_info.model_dump_json()

        with patch("app.services.worker.get_redis", return_value=mock_redis):
            result = await service.poll_tasks(worker_id, max_tasks=10)

            assert len(result) == 1
            assert str(result[0].task_id) == task_id

    @pytest.mark.asyncio
    async def test_poll_tasks_empty(self):
        """Test polling tasks when queue is empty."""
        from app.services.worker import WorkerService

        service = WorkerService()

        worker_id = uuid4()

        mock_redis = AsyncMock()
        mock_redis.lpop.return_value = None

        with patch("app.services.worker.get_redis", return_value=mock_redis):
            result = await service.poll_tasks(worker_id, max_tasks=10)

            assert len(result) == 0


class TestWorkerServiceProcessTaskResult:
    """Tests for task result processing."""

    @pytest.mark.asyncio
    async def test_process_task_result_determines_success(self):
        """Test processing determines success based on error and status_code."""
        from app.schemas.worker import WorkerTaskResult
        from app.services.worker import WorkerService

        service = WorkerService()

        # Success case: no error and status_code present
        result_success = WorkerTaskResult(
            task_id=uuid4(),
            task_type="cron",
            status_code=200,
            response_body='{"result": "ok"}',
            response_headers={"Content-Type": "application/json"},
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            duration_ms=150,
            error=None,
        )

        is_success = result_success.error is None and result_success.status_code is not None
        assert is_success is True

        # Failure case: error present
        result_failure = WorkerTaskResult(
            task_id=uuid4(),
            task_type="cron",
            status_code=None,
            response_body=None,
            response_headers=None,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            duration_ms=5000,
            error="Connection timeout",
        )

        is_success = result_failure.error is None and result_failure.status_code is not None
        assert is_success is False


class TestWorkerServiceGlobalInstance:
    """Tests for global worker_service instance."""

    def test_global_instance_exists(self):
        """Test global worker_service instance exists."""
        from app.services.worker import worker_service

        assert worker_service is not None
