"""Tests for Task Queue API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status


class TestListQueuedTasks:
    """Tests for list_queued_tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_queued_tasks_success(self):
        """Test listing queued tasks."""
        from app.api.v1.task_queue import list_queued_tasks
        from app.models.task_queue import TaskQueue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_items = [
            MagicMock(
                id=uuid4(),
                workspace_id=mock_workspace.id,
                task_type="cron",
                task_id=uuid4(),
                task_name="Test Task",
                priority=0,
                queued_at=datetime.utcnow(),
                scheduled_for=None,
                retry_attempt=0,
                initial_variables={},
                created_at=datetime.utcnow(),
            )
        ]

        with patch("app.api.v1.task_queue.overlap_service") as mock_service:
            mock_service.get_queued_tasks = AsyncMock(return_value=mock_items)

            # Mock count query
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_db.execute.return_value = mock_result

            result = await list_queued_tasks(
                workspace=mock_workspace, db=mock_db, limit=50
            )

        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_list_queued_tasks_empty(self):
        """Test listing queued tasks when empty."""
        from app.api.v1.task_queue import list_queued_tasks

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        with patch("app.api.v1.task_queue.overlap_service") as mock_service:
            mock_service.get_queued_tasks = AsyncMock(return_value=[])

            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_db.execute.return_value = mock_result

            result = await list_queued_tasks(
                workspace=mock_workspace, db=mock_db, limit=50
            )

        assert result.total == 0
        assert len(result.items) == 0


class TestRemoveFromQueue:
    """Tests for remove_from_queue endpoint."""

    @pytest.mark.asyncio
    async def test_remove_from_queue_success(self):
        """Test removing item from queue."""
        from app.api.v1.task_queue import remove_from_queue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        queue_id = uuid4()
        mock_item = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_item
        mock_db.execute.return_value = mock_result

        # Should not raise
        await remove_from_queue(workspace=mock_workspace, queue_id=queue_id, db=mock_db)

        mock_db.delete.assert_called_once_with(mock_item)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_from_queue_not_found(self):
        """Test removing item from queue when not found."""
        from fastapi import HTTPException

        from app.api.v1.task_queue import remove_from_queue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        queue_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await remove_from_queue(workspace=mock_workspace, queue_id=queue_id, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestClearWorkspaceQueue:
    """Tests for clear_workspace_queue endpoint."""

    @pytest.mark.asyncio
    async def test_clear_workspace_queue_success(self):
        """Test clearing workspace queue."""
        from app.api.v1.task_queue import clear_workspace_queue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        # Should not raise
        await clear_workspace_queue(workspace=mock_workspace, db=mock_db)

        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


class TestGetOverlapStats:
    """Tests for get_overlap_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_overlap_stats_success(self):
        """Test getting overlap statistics."""
        from app.api.v1.task_queue import get_overlap_stats

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()
        mock_workspace.executions_skipped = 10
        mock_workspace.executions_queued = 20

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        result = await get_overlap_stats(workspace=mock_workspace, db=mock_db)

        assert result.executions_skipped == 10
        assert result.executions_queued == 20
        assert result.current_queue_size == 5
        assert result.overlap_rate == 33.33  # 10 / (10+20) * 100

    @pytest.mark.asyncio
    async def test_get_overlap_stats_no_overlaps(self):
        """Test getting overlap stats when no overlaps occurred."""
        from app.api.v1.task_queue import get_overlap_stats

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()
        mock_workspace.executions_skipped = 0
        mock_workspace.executions_queued = 0

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await get_overlap_stats(workspace=mock_workspace, db=mock_db)

        assert result.executions_skipped == 0
        assert result.executions_queued == 0
        assert result.current_queue_size == 0
        assert result.overlap_rate == 0.0


class TestClearTaskQueue:
    """Tests for clear task queue endpoints."""

    @pytest.mark.asyncio
    async def test_clear_cron_task_queue(self):
        """Test clearing cron task queue."""
        from app.api.v1.task_queue import clear_cron_task_queue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        task_id = uuid4()

        with patch("app.api.v1.task_queue.overlap_service") as mock_service:
            mock_service.clear_task_queue = AsyncMock(return_value=3)

            await clear_cron_task_queue(
                workspace=mock_workspace, task_id=task_id, db=mock_db
            )

        mock_service.clear_task_queue.assert_called_once_with(mock_db, "cron", task_id)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_chain_queue(self):
        """Test clearing chain queue."""
        from app.api.v1.task_queue import clear_chain_queue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        chain_id = uuid4()

        with patch("app.api.v1.task_queue.overlap_service") as mock_service:
            mock_service.clear_task_queue = AsyncMock(return_value=2)

            await clear_chain_queue(
                workspace=mock_workspace, chain_id=chain_id, db=mock_db
            )

        mock_service.clear_task_queue.assert_called_once_with(mock_db, "chain", chain_id)
        mock_db.commit.assert_called_once()


class TestGetTaskQueue:
    """Tests for get task queue endpoints."""

    @pytest.mark.asyncio
    async def test_get_cron_task_queue(self):
        """Test getting cron task queue."""
        from app.api.v1.task_queue import get_cron_task_queue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()
        task_id = uuid4()

        mock_items = [
            MagicMock(
                id=uuid4(),
                workspace_id=mock_workspace.id,
                task_type="cron",
                task_id=task_id,
                task_name="Test Task",
                priority=0,
                queued_at=datetime.utcnow(),
                scheduled_for=None,
                retry_attempt=0,
                initial_variables={},
                created_at=datetime.utcnow(),
            )
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_items
        mock_db.execute.return_value = mock_result

        result = await get_cron_task_queue(
            workspace=mock_workspace, task_id=task_id, db=mock_db
        )

        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_get_chain_queue(self):
        """Test getting chain queue."""
        from app.api.v1.task_queue import get_chain_queue

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()
        chain_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await get_chain_queue(
            workspace=mock_workspace, chain_id=chain_id, db=mock_db
        )

        assert result.total == 0
        assert len(result.items) == 0
