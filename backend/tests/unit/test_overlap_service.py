"""Tests for OverlapService."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.cron_task import OverlapPolicy
from app.services.overlap import OverlapAction, OverlapResult, OverlapService


class TestOverlapResult:
    """Tests for OverlapResult."""

    def test_allow_should_execute(self):
        """Test that ALLOW action should execute."""
        result = OverlapResult(OverlapAction.ALLOW)
        assert result.should_execute is True
        assert result.skipped_reason is None

    def test_skip_should_not_execute(self):
        """Test that SKIP action should not execute."""
        result = OverlapResult(OverlapAction.SKIP, "Task already running")
        assert result.should_execute is False
        assert result.skipped_reason == "overlap_skipped"

    def test_queue_should_not_execute(self):
        """Test that QUEUE action should not execute immediately."""
        result = OverlapResult(OverlapAction.QUEUE, "Added to queue", queue_position=3)
        assert result.should_execute is False
        assert result.skipped_reason is None
        assert result.queue_position == 3

    def test_queued_full_should_not_execute(self):
        """Test that QUEUED_FULL action should not execute."""
        result = OverlapResult(OverlapAction.QUEUED_FULL, "Queue full")
        assert result.should_execute is False
        assert result.skipped_reason == "queue_full"


class TestOverlapServiceCheckCronTaskOverlap:
    """Tests for OverlapService.check_cron_task_overlap."""

    @pytest.mark.asyncio
    async def test_allow_policy_always_executes(self):
        """Test that ALLOW policy always allows execution."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.overlap_policy = OverlapPolicy.ALLOW
        mock_task.running_instances = 5

        with patch.object(service, "_increment_running_instances", new_callable=AsyncMock):
            result = await service.check_cron_task_overlap(mock_db, mock_task)

        assert result.action == OverlapAction.ALLOW
        assert result.should_execute is True

    @pytest.mark.asyncio
    async def test_skip_policy_under_max_instances(self):
        """Test SKIP policy allows when under max_instances."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.overlap_policy = OverlapPolicy.SKIP
        mock_task.running_instances = 0
        mock_task.max_instances = 2

        with patch.object(service, "_increment_running_instances", new_callable=AsyncMock):
            result = await service.check_cron_task_overlap(mock_db, mock_task)

        assert result.action == OverlapAction.ALLOW
        assert result.should_execute is True

    @pytest.mark.asyncio
    async def test_skip_policy_at_max_instances(self):
        """Test SKIP policy skips when at max_instances."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.overlap_policy = OverlapPolicy.SKIP
        mock_task.running_instances = 2
        mock_task.max_instances = 2

        with patch.object(service, "_increment_skipped_count", new_callable=AsyncMock):
            result = await service.check_cron_task_overlap(mock_db, mock_task)

        assert result.action == OverlapAction.SKIP
        assert result.should_execute is False

    @pytest.mark.asyncio
    async def test_queue_policy_under_max_instances(self):
        """Test QUEUE policy allows when under max_instances."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.overlap_policy = OverlapPolicy.QUEUE
        mock_task.running_instances = 0
        mock_task.max_instances = 1

        with patch.object(service, "_increment_running_instances", new_callable=AsyncMock):
            result = await service.check_cron_task_overlap(mock_db, mock_task)

        assert result.action == OverlapAction.ALLOW
        assert result.should_execute is True

    @pytest.mark.asyncio
    async def test_queue_policy_at_max_instances_queue_available(self):
        """Test QUEUE policy queues when at max_instances and queue has space."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.overlap_policy = OverlapPolicy.QUEUE
        mock_task.running_instances = 1
        mock_task.max_instances = 1
        mock_task.max_queue_size = 10

        with patch.object(service, "_add_to_queue", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = OverlapResult(OverlapAction.QUEUE, queue_position=1)
            result = await service.check_cron_task_overlap(mock_db, mock_task)

        assert result.action == OverlapAction.QUEUE
        assert result.should_execute is False

    @pytest.mark.asyncio
    async def test_queue_policy_at_max_instances_queue_full(self):
        """Test QUEUE policy skips when queue is full."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.workspace_id = uuid4()
        mock_task.name = "Test Task"
        mock_task.overlap_policy = OverlapPolicy.QUEUE
        mock_task.running_instances = 1
        mock_task.max_instances = 1
        mock_task.max_queue_size = 5

        with patch.object(service, "_add_to_queue", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = OverlapResult(OverlapAction.QUEUED_FULL, "Queue full")
            result = await service.check_cron_task_overlap(mock_db, mock_task)

        assert result.action == OverlapAction.QUEUED_FULL
        assert result.should_execute is False


class TestOverlapServiceCheckChainOverlap:
    """Tests for OverlapService.check_chain_overlap."""

    @pytest.mark.asyncio
    async def test_allow_policy_always_executes(self):
        """Test that ALLOW policy always allows chain execution."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.overlap_policy = OverlapPolicy.ALLOW
        mock_chain.running_instances = 3

        with patch.object(service, "_increment_running_instances", new_callable=AsyncMock):
            result = await service.check_chain_overlap(mock_db, mock_chain)

        assert result.action == OverlapAction.ALLOW
        assert result.should_execute is True

    @pytest.mark.asyncio
    async def test_skip_policy_skips_chain(self):
        """Test SKIP policy skips chain when at max_instances."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.workspace_id = uuid4()
        mock_chain.name = "Test Chain"
        mock_chain.overlap_policy = OverlapPolicy.SKIP
        mock_chain.running_instances = 1
        mock_chain.max_instances = 1

        with patch.object(service, "_increment_skipped_count", new_callable=AsyncMock):
            result = await service.check_chain_overlap(mock_db, mock_chain)

        assert result.action == OverlapAction.SKIP
        assert result.should_execute is False

    @pytest.mark.asyncio
    async def test_queue_policy_with_variables(self):
        """Test QUEUE policy stores initial variables."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.workspace_id = uuid4()
        mock_chain.name = "Test Chain"
        mock_chain.overlap_policy = OverlapPolicy.QUEUE
        mock_chain.running_instances = 1
        mock_chain.max_instances = 1
        mock_chain.max_queue_size = 10

        initial_variables = {"key": "value"}

        with patch.object(service, "_add_to_queue", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = OverlapResult(OverlapAction.QUEUE, queue_position=1)
            result = await service.check_chain_overlap(
                mock_db, mock_chain, initial_variables=initial_variables
            )

        mock_add.assert_called_once()
        call_kwargs = mock_add.call_args[1]
        assert call_kwargs["initial_variables"] == initial_variables


class TestOverlapServiceRelease:
    """Tests for OverlapService release methods."""

    @pytest.mark.asyncio
    async def test_release_cron_task_decrements(self):
        """Test releasing cron task decrements running instances."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.overlap_policy = OverlapPolicy.SKIP

        with patch.object(
            service, "_decrement_running_instances", new_callable=AsyncMock
        ) as mock_dec:
            await service.release_cron_task(mock_db, mock_task)

        mock_dec.assert_called_once_with(mock_db, "cron", mock_task.id)

    @pytest.mark.asyncio
    async def test_release_cron_task_checks_queue(self):
        """Test releasing cron task checks for queued items."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.overlap_policy = OverlapPolicy.QUEUE

        with patch.object(
            service, "_decrement_running_instances", new_callable=AsyncMock
        ):
            with patch.object(
                service, "_pop_from_queue", new_callable=AsyncMock
            ) as mock_pop:
                mock_pop.return_value = None
                await service.release_cron_task(mock_db, mock_task)

        mock_pop.assert_called_once_with(db=mock_db, task_type="cron", task_id=mock_task.id)

    @pytest.mark.asyncio
    async def test_release_chain_returns_queued_item(self):
        """Test releasing chain returns queued item if present."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.overlap_policy = OverlapPolicy.QUEUE

        mock_queued = MagicMock()

        with patch.object(
            service, "_decrement_running_instances", new_callable=AsyncMock
        ):
            with patch.object(
                service, "_pop_from_queue", new_callable=AsyncMock
            ) as mock_pop:
                mock_pop.return_value = mock_queued
                result = await service.release_chain(mock_db, mock_chain)

        assert result == mock_queued


class TestOverlapServiceQueueManagement:
    """Tests for queue management methods."""

    @pytest.mark.asyncio
    async def test_get_queue_size(self):
        """Test getting queue size."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        size = await service.get_queue_size(mock_db, "cron", uuid4())

        assert size == 5

    @pytest.mark.asyncio
    async def test_get_queue_size_empty(self):
        """Test getting queue size when empty."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        size = await service.get_queue_size(mock_db, "cron", uuid4())

        assert size == 0

    @pytest.mark.asyncio
    async def test_get_queued_tasks(self):
        """Test getting queued tasks."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_items = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_items
        mock_db.execute.return_value = mock_result

        items = await service.get_queued_tasks(mock_db, uuid4())

        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_remove_from_queue_found(self):
        """Test removing item from queue when found."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_item = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        result = await service.remove_from_queue(mock_db, uuid4())

        assert result is True
        mock_db.delete.assert_called_once_with(mock_item)

    @pytest.mark.asyncio
    async def test_remove_from_queue_not_found(self):
        """Test removing item from queue when not found."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.remove_from_queue(mock_db, uuid4())

        assert result is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_task_queue(self):
        """Test clearing task queue."""
        service = OverlapService()
        mock_db = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3

        # First call is count, second is delete
        mock_db.execute.side_effect = [mock_count_result, MagicMock()]

        count = await service.clear_task_queue(mock_db, "cron", uuid4())

        assert count == 3
        assert mock_db.execute.call_count == 2


class TestOverlapServiceAddToQueue:
    """Tests for _add_to_queue method."""

    @pytest.mark.asyncio
    async def test_add_to_queue_success(self):
        """Test adding to queue when space available."""
        service = OverlapService()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        with patch.object(service, "get_queue_size", new_callable=AsyncMock) as mock_size:
            mock_size.return_value = 3
            with patch.object(
                service, "_increment_queued_count", new_callable=AsyncMock
            ):
                result = await service._add_to_queue(
                    db=mock_db,
                    workspace_id=uuid4(),
                    task_type="cron",
                    task_id=uuid4(),
                    task_name="Test Task",
                    max_queue_size=10,
                )

        assert result.action == OverlapAction.QUEUE
        assert result.queue_position == 4
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_queue_full(self):
        """Test adding to queue when full."""
        service = OverlapService()
        mock_db = AsyncMock()

        with patch.object(service, "get_queue_size", new_callable=AsyncMock) as mock_size:
            mock_size.return_value = 10
            with patch.object(
                service, "_increment_skipped_count", new_callable=AsyncMock
            ):
                result = await service._add_to_queue(
                    db=mock_db,
                    workspace_id=uuid4(),
                    task_type="cron",
                    task_id=uuid4(),
                    task_name="Test Task",
                    max_queue_size=10,
                )

        assert result.action == OverlapAction.QUEUED_FULL
        assert result.should_execute is False


class TestOverlapServiceCleanup:
    """Tests for cleanup_stale_instances."""

    @pytest.mark.asyncio
    async def test_cleanup_stale_instances_cron(self):
        """Test cleanup of stale cron task instances."""
        service = OverlapService()
        mock_db = AsyncMock()

        # Create a stale task (last_run_at + execution_timeout < now)
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.running_instances = 2
        mock_task.execution_timeout = 60  # 60 seconds
        mock_task.last_run_at = datetime.utcnow() - timedelta(seconds=120)  # 2 minutes ago

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]

        # Empty chains
        mock_chain_result = MagicMock()
        mock_chain_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_result, mock_chain_result]

        cleaned = await service.cleanup_stale_instances(mock_db)

        assert cleaned == 1
        assert mock_task.running_instances == 0

    @pytest.mark.asyncio
    async def test_cleanup_stale_instances_not_stale(self):
        """Test no cleanup when instances are not stale."""
        service = OverlapService()
        mock_db = AsyncMock()

        # Create a non-stale task
        mock_task = MagicMock()
        mock_task.id = uuid4()
        mock_task.running_instances = 1
        mock_task.execution_timeout = 300  # 5 minutes
        mock_task.last_run_at = datetime.utcnow() - timedelta(seconds=60)  # 1 minute ago

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]

        mock_chain_result = MagicMock()
        mock_chain_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_result, mock_chain_result]

        cleaned = await service.cleanup_stale_instances(mock_db)

        assert cleaned == 0
        assert mock_task.running_instances == 1  # Unchanged
