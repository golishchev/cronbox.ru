"""Unit tests for chain executions repository."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.db.repositories.chain_executions import (
    ChainExecutionRepository,
    StepExecutionRepository,
)
from app.models.chain_execution import StepStatus
from app.models.cron_task import HttpMethod
from app.models.task_chain import ChainStatus


class TestChainExecutionRepository:
    """Tests for ChainExecutionRepository."""

    def create_mock_execution(self, **kwargs):
        """Create a mock chain execution."""
        mock = MagicMock()
        mock.id = kwargs.get("id", uuid4())
        mock.workspace_id = kwargs.get("workspace_id", uuid4())
        mock.chain_id = kwargs.get("chain_id", uuid4())
        mock.status = kwargs.get("status", ChainStatus.RUNNING)
        mock.started_at = kwargs.get("started_at", datetime.utcnow())
        mock.finished_at = kwargs.get("finished_at", None)
        mock.duration_ms = kwargs.get("duration_ms", None)
        mock.total_steps = kwargs.get("total_steps", 3)
        mock.completed_steps = kwargs.get("completed_steps", 0)
        mock.failed_steps = kwargs.get("failed_steps", 0)
        mock.skipped_steps = kwargs.get("skipped_steps", 0)
        mock.variables = kwargs.get("variables", {})
        mock.error_message = kwargs.get("error_message", None)
        return mock

    @pytest.mark.asyncio
    async def test_get_by_chain(self):
        """Test getting executions by chain."""
        mock_db = AsyncMock()
        chain_id = uuid4()
        mock_executions = [self.create_mock_execution(chain_id=chain_id)]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_executions
        mock_db.execute.return_value = mock_result

        repo = ChainExecutionRepository(mock_db)
        result = await repo.get_by_chain(chain_id, skip=0, limit=100)

        assert len(result) == 1
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_workspace(self):
        """Test getting executions by workspace."""
        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_executions = [
            self.create_mock_execution(workspace_id=workspace_id),
            self.create_mock_execution(workspace_id=workspace_id),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_executions
        mock_db.execute.return_value = mock_result

        repo = ChainExecutionRepository(mock_db)
        result = await repo.get_by_workspace(workspace_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_count_by_chain(self):
        """Test counting executions by chain."""
        mock_db = AsyncMock()
        chain_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        mock_db.execute.return_value = mock_result

        repo = ChainExecutionRepository(mock_db)
        result = await repo.count_by_chain(chain_id)

        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_workspace(self):
        """Test counting executions by workspace."""
        mock_db = AsyncMock()
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 10
        mock_db.execute.return_value = mock_result

        repo = ChainExecutionRepository(mock_db)
        result = await repo.count_by_workspace(workspace_id)

        assert result == 10

    @pytest.mark.asyncio
    async def test_get_with_step_executions(self):
        """Test getting execution with step executions."""
        mock_db = AsyncMock()
        execution_id = uuid4()
        mock_execution = self.create_mock_execution(id=execution_id)
        mock_execution.step_executions = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_execution
        mock_db.execute.return_value = mock_result

        repo = ChainExecutionRepository(mock_db)
        result = await repo.get_with_step_executions(execution_id)

        assert result == mock_execution

    @pytest.mark.asyncio
    async def test_get_with_step_executions_not_found(self):
        """Test getting non-existent execution."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        repo = ChainExecutionRepository(mock_db)
        result = await repo.get_with_step_executions(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_create_execution(self):
        """Test creating a chain execution."""
        mock_db = AsyncMock()
        workspace_id = uuid4()
        chain_id = uuid4()

        with patch(
            "app.db.repositories.chain_executions.ChainExecution"
        ) as MockExecution:
            mock_execution = MagicMock()
            MockExecution.return_value = mock_execution

            repo = ChainExecutionRepository(mock_db)
            result = await repo.create_execution(
                workspace_id=workspace_id,
                chain_id=chain_id,
                total_steps=3,
                initial_variables={"key": "value"},
            )

            mock_db.add.assert_called_once_with(mock_execution)
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_execution_without_variables(self):
        """Test creating execution without initial variables."""
        mock_db = AsyncMock()

        with patch(
            "app.db.repositories.chain_executions.ChainExecution"
        ) as MockExecution:
            mock_execution = MagicMock()
            MockExecution.return_value = mock_execution

            repo = ChainExecutionRepository(mock_db)
            await repo.create_execution(
                workspace_id=uuid4(),
                chain_id=uuid4(),
                total_steps=2,
            )

            # Verify empty dict is used for variables
            call_kwargs = MockExecution.call_args[1]
            assert call_kwargs["variables"] == {}

    @pytest.mark.asyncio
    async def test_complete_execution(self):
        """Test completing a chain execution."""
        mock_db = AsyncMock()
        mock_execution = self.create_mock_execution()
        mock_execution.started_at = datetime.utcnow() - timedelta(seconds=5)

        repo = ChainExecutionRepository(mock_db)
        result = await repo.complete_execution(
            execution=mock_execution,
            status=ChainStatus.SUCCESS,
            error_message=None,
        )

        assert mock_execution.status == ChainStatus.SUCCESS
        assert mock_execution.finished_at is not None
        assert mock_execution.duration_ms is not None
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_execution_with_error(self):
        """Test completing execution with error."""
        mock_db = AsyncMock()
        mock_execution = self.create_mock_execution()
        mock_execution.started_at = datetime.utcnow()

        repo = ChainExecutionRepository(mock_db)
        await repo.complete_execution(
            execution=mock_execution,
            status=ChainStatus.FAILED,
            error_message="Connection timeout",
        )

        assert mock_execution.status == ChainStatus.FAILED
        assert mock_execution.error_message == "Connection timeout"

    @pytest.mark.asyncio
    async def test_update_step_counts(self):
        """Test updating step counts."""
        mock_db = AsyncMock()
        mock_execution = self.create_mock_execution()

        repo = ChainExecutionRepository(mock_db)
        result = await repo.update_step_counts(
            execution=mock_execution,
            completed=3,
            failed=1,
            skipped=2,
        )

        assert mock_execution.completed_steps == 3
        assert mock_execution.failed_steps == 1
        assert mock_execution.skipped_steps == 2
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_variables(self):
        """Test updating variables."""
        mock_db = AsyncMock()
        mock_execution = self.create_mock_execution()

        repo = ChainExecutionRepository(mock_db)
        new_vars = {"user_id": "123", "token": "abc"}
        result = await repo.update_variables(mock_execution, new_vars)

        assert mock_execution.variables == new_vars
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_old_executions(self):
        """Test deleting old executions."""
        mock_db = AsyncMock()
        workspace_id = uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_db.execute.return_value = mock_result

        repo = ChainExecutionRepository(mock_db)
        result = await repo.delete_old_executions(workspace_id, keep_days=7)

        assert result == 5
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()


class TestStepExecutionRepository:
    """Tests for StepExecutionRepository."""

    def create_mock_step_execution(self, **kwargs):
        """Create a mock step execution."""
        mock = MagicMock()
        mock.id = kwargs.get("id", uuid4())
        mock.chain_execution_id = kwargs.get("chain_execution_id", uuid4())
        mock.step_id = kwargs.get("step_id", uuid4())
        mock.step_order = kwargs.get("step_order", 0)
        mock.step_name = kwargs.get("step_name", "Test Step")
        mock.status = kwargs.get("status", StepStatus.RUNNING)
        mock.started_at = kwargs.get("started_at", datetime.utcnow())
        mock.finished_at = kwargs.get("finished_at", None)
        mock.request_url = kwargs.get("request_url", "https://example.com")
        mock.request_method = kwargs.get("request_method", HttpMethod.GET)
        return mock

    @pytest.mark.asyncio
    async def test_get_by_chain_execution(self):
        """Test getting step executions by chain execution."""
        mock_db = AsyncMock()
        chain_execution_id = uuid4()
        mock_steps = [
            self.create_mock_step_execution(
                chain_execution_id=chain_execution_id, step_order=0
            ),
            self.create_mock_step_execution(
                chain_execution_id=chain_execution_id, step_order=1
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_steps
        mock_db.execute.return_value = mock_result

        repo = StepExecutionRepository(mock_db)
        result = await repo.get_by_chain_execution(chain_execution_id)

        assert len(result) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_step_execution(self):
        """Test creating a step execution."""
        mock_db = AsyncMock()
        chain_execution_id = uuid4()
        step_id = uuid4()

        with patch(
            "app.db.repositories.chain_executions.StepExecution"
        ) as MockStepExecution:
            mock_step = MagicMock()
            MockStepExecution.return_value = mock_step

            repo = StepExecutionRepository(mock_db)
            result = await repo.create_step_execution(
                chain_execution_id=chain_execution_id,
                step_id=step_id,
                step_order=0,
                step_name="Step 1",
                request_url="https://example.com/api",
                request_method="GET",
                request_headers={"Authorization": "Bearer token"},
                request_body='{"data": "test"}',
            )

            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_step_execution_without_body(self):
        """Test creating step execution without body."""
        mock_db = AsyncMock()

        with patch(
            "app.db.repositories.chain_executions.StepExecution"
        ) as MockStepExecution:
            mock_step = MagicMock()
            MockStepExecution.return_value = mock_step

            repo = StepExecutionRepository(mock_db)
            await repo.create_step_execution(
                chain_execution_id=uuid4(),
                step_id=None,
                step_order=0,
                step_name="Step 1",
                request_url="https://example.com",
                request_method="GET",
            )

            call_kwargs = MockStepExecution.call_args[1]
            assert call_kwargs["request_headers"] is None
            assert call_kwargs["request_body"] is None

    @pytest.mark.asyncio
    async def test_complete_step_execution_success(self):
        """Test completing step execution successfully."""
        mock_db = AsyncMock()
        mock_step = self.create_mock_step_execution()
        mock_step.started_at = datetime.utcnow() - timedelta(milliseconds=500)

        repo = StepExecutionRepository(mock_db)
        result = await repo.complete_step_execution(
            step_execution=mock_step,
            status=StepStatus.SUCCESS,
            response_status_code=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"success": true}',
            response_size_bytes=100,
            extracted_variables={"result_id": "123"},
            condition_met=True,
            condition_details="Status code 200 in [200, 201]",
        )

        assert mock_step.status == StepStatus.SUCCESS
        assert mock_step.finished_at is not None
        assert mock_step.duration_ms is not None
        assert mock_step.response_status_code == 200
        assert mock_step.extracted_variables == {"result_id": "123"}
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_step_execution_failed(self):
        """Test completing step execution with failure."""
        mock_db = AsyncMock()
        mock_step = self.create_mock_step_execution()
        mock_step.started_at = datetime.utcnow()

        repo = StepExecutionRepository(mock_db)
        await repo.complete_step_execution(
            step_execution=mock_step,
            status=StepStatus.FAILED,
            response_status_code=500,
            error_message="Internal server error",
            error_type="HTTP_ERROR",
            retry_attempt=2,
        )

        assert mock_step.status == StepStatus.FAILED
        assert mock_step.error_message == "Internal server error"
        assert mock_step.error_type == "HTTP_ERROR"
        assert mock_step.retry_attempt == 2

    @pytest.mark.asyncio
    async def test_complete_step_execution_no_started_at(self):
        """Test completing step execution without started_at."""
        mock_db = AsyncMock()
        mock_step = self.create_mock_step_execution()
        mock_step.started_at = None

        repo = StepExecutionRepository(mock_db)
        await repo.complete_step_execution(
            step_execution=mock_step,
            status=StepStatus.SUCCESS,
        )

        # Should not set duration_ms when started_at is None
        assert mock_step.finished_at is not None

    @pytest.mark.asyncio
    async def test_mark_as_skipped(self):
        """Test marking step as skipped."""
        mock_db = AsyncMock()
        chain_execution_id = uuid4()

        with patch(
            "app.db.repositories.chain_executions.StepExecution"
        ) as MockStepExecution:
            mock_step = MagicMock()
            MockStepExecution.return_value = mock_step

            repo = StepExecutionRepository(mock_db)
            result = await repo.mark_as_skipped(
                chain_execution_id=chain_execution_id,
                step_id=uuid4(),
                step_order=1,
                step_name="Skipped Step",
                request_url="https://example.com",
                request_method="POST",
                condition_details="Condition not met: status code != 200",
            )

            call_kwargs = MockStepExecution.call_args[1]
            assert call_kwargs["status"] == StepStatus.SKIPPED
            assert call_kwargs["started_at"] is None
            assert call_kwargs["finished_at"] is None
            assert call_kwargs["condition_met"] is False
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
