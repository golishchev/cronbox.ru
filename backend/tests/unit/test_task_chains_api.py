"""Unit tests for task chains API."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.task_chain import ChainStatus, TriggerType


class TestCalculateNextRun:
    """Tests for calculate_next_run helper function."""

    def test_calculate_next_run_utc(self):
        """Test next run calculation with UTC timezone."""
        from app.api.v1.task_chains import calculate_next_run

        result = calculate_next_run("0 * * * *", "UTC")  # Every hour

        # Should be a datetime
        assert isinstance(result, datetime)
        # Should be in the future
        assert result > datetime.utcnow()

    def test_calculate_next_run_different_timezone(self):
        """Test next run calculation with different timezone."""
        from app.api.v1.task_chains import calculate_next_run

        result = calculate_next_run("30 12 * * *", "Europe/Moscow")  # 12:30 Moscow time

        assert isinstance(result, datetime)


class TestCalculateMinIntervalMinutes:
    """Tests for calculate_min_interval_minutes helper function."""

    def test_hourly_schedule(self):
        """Test minimum interval for hourly schedule."""
        from app.api.v1.task_chains import calculate_min_interval_minutes

        result = calculate_min_interval_minutes("0 * * * *", "UTC")

        assert result == 60  # 60 minutes

    def test_every_5_minutes_schedule(self):
        """Test minimum interval for every 5 minutes."""
        from app.api.v1.task_chains import calculate_min_interval_minutes

        result = calculate_min_interval_minutes("*/5 * * * *", "UTC")

        assert result == 5  # 5 minutes

    def test_daily_schedule(self):
        """Test minimum interval for daily schedule."""
        from app.api.v1.task_chains import calculate_min_interval_minutes

        result = calculate_min_interval_minutes("0 0 * * *", "UTC")  # Midnight daily

        assert result == 1440  # 24 hours = 1440 minutes


class TestListTaskChains:
    """Tests for list_task_chains endpoint."""

    @pytest.mark.asyncio
    async def test_list_chains_success(self):
        """Test listing task chains."""
        from app.api.v1.task_chains import list_task_chains

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.workspace_id = mock_workspace.id
        mock_chain.name = "Test Chain"
        mock_chain.description = "Test description"
        mock_chain.tags = []
        mock_chain.trigger_type = TriggerType.MANUAL
        mock_chain.schedule = None
        mock_chain.timezone = "UTC"
        mock_chain.execute_at = None
        mock_chain.is_active = True
        mock_chain.is_paused = False
        mock_chain.stop_on_failure = True
        mock_chain.timeout_seconds = 30
        mock_chain.worker_id = None
        mock_chain.notify_on_failure = True
        mock_chain.notify_on_success = False
        mock_chain.notify_on_partial = False
        mock_chain.last_run_at = None
        mock_chain.last_status = None
        mock_chain.next_run_at = None
        mock_chain.consecutive_failures = 0
        mock_chain.created_at = datetime.now(timezone.utc)
        mock_chain.updated_at = datetime.now(timezone.utc)
        # Overlap prevention fields
        mock_chain.overlap_policy = "allow"
        mock_chain.max_instances = 1
        mock_chain.max_queue_size = 10
        mock_chain.execution_timeout = None
        mock_chain.running_instances = 0

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_workspace = AsyncMock(return_value=[mock_chain])
            mock_repo.count_by_workspace = AsyncMock(return_value=1)
            MockRepo.return_value = mock_repo

            result = await list_task_chains(
                workspace=mock_workspace,
                db=mock_db,
                page=1,
                limit=20,
                is_active=None,
            )

            assert len(result.chains) == 1
            assert result.pagination.total == 1


class TestCreateTaskChain:
    """Tests for create_task_chain endpoint."""

    @pytest.mark.asyncio
    async def test_create_chain_plan_not_allow_chains(self):
        """Test creating chain when plan doesn't allow chains."""
        from app.api.v1.task_chains import create_task_chain
        from app.schemas.task_chain import ChainStepBase, TaskChainCreate

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_plan = MagicMock()
        mock_plan.max_task_chains = 0  # No chains allowed
        mock_plan.max_chain_steps = 5
        mock_plan.min_chain_interval_minutes = 5

        data = TaskChainCreate(
            name="Test Chain",
            trigger_type=TriggerType.MANUAL,
            steps=[
                ChainStepBase(
                    name="Step 1",
                    url="https://example.com/api",
                    method="GET",
                )
            ],
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_task_chain(
                data=data,
                workspace=mock_workspace,
                user_plan=mock_plan,
                db=mock_db,
            )

        assert exc_info.value.status_code == 403
        assert "not available on your plan" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_chain_limit_reached(self):
        """Test creating chain when limit reached."""
        from app.api.v1.task_chains import create_task_chain
        from app.schemas.task_chain import ChainStepBase, TaskChainCreate

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_plan = MagicMock()
        mock_plan.max_task_chains = 3
        mock_plan.max_chain_steps = 5
        mock_plan.min_chain_interval_minutes = 5

        data = TaskChainCreate(
            name="Test Chain",
            trigger_type=TriggerType.MANUAL,
            steps=[
                ChainStepBase(
                    name="Step 1",
                    url="https://example.com/api",
                    method="GET",
                )
            ],
        )

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.count_by_workspace = AsyncMock(return_value=3)  # Already at limit
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_task_chain(
                    data=data,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
            assert "limit reached" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_chain_too_many_steps(self):
        """Test creating chain with too many steps."""
        from app.api.v1.task_chains import create_task_chain
        from app.schemas.task_chain import ChainStepBase, TaskChainCreate

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10
        mock_plan.max_chain_steps = 2  # Only 2 steps allowed
        mock_plan.min_chain_interval_minutes = 5

        data = TaskChainCreate(
            name="Test Chain",
            trigger_type=TriggerType.MANUAL,
            steps=[
                ChainStepBase(name="Step 1", url="https://example.com/1", method="GET"),
                ChainStepBase(name="Step 2", url="https://example.com/2", method="GET"),
                ChainStepBase(name="Step 3", url="https://example.com/3", method="GET"),  # Exceeds limit
            ],
        )

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.count_by_workspace = AsyncMock(return_value=0)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_task_chain(
                    data=data,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
            assert "Too many steps" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_cron_chain_no_schedule(self):
        """Test creating cron chain without schedule."""
        from app.api.v1.task_chains import create_task_chain
        from app.schemas.task_chain import ChainStepBase, TaskChainCreate

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10
        mock_plan.max_chain_steps = 10
        mock_plan.min_chain_interval_minutes = 5

        data = TaskChainCreate(
            name="Test Chain",
            trigger_type=TriggerType.CRON,
            schedule=None,  # Missing schedule
            steps=[
                ChainStepBase(name="Step 1", url="https://example.com/1", method="GET"),
            ],
        )

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.count_by_workspace = AsyncMock(return_value=0)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_task_chain(
                    data=data,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "Schedule is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_cron_chain_interval_too_frequent(self):
        """Test creating cron chain with too frequent interval."""
        from app.api.v1.task_chains import create_task_chain
        from app.schemas.task_chain import ChainStepBase, TaskChainCreate

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10
        mock_plan.max_chain_steps = 10
        mock_plan.min_chain_interval_minutes = 10  # Minimum 10 minutes

        data = TaskChainCreate(
            name="Test Chain",
            trigger_type=TriggerType.CRON,
            schedule="*/1 * * * *",  # Every minute - too frequent
            steps=[
                ChainStepBase(name="Step 1", url="https://example.com/1", method="GET"),
            ],
        )

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.count_by_workspace = AsyncMock(return_value=0)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_task_chain(
                    data=data,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
            assert "interval too frequent" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_delayed_chain_no_execute_at(self):
        """Test creating delayed chain without execute_at."""
        from app.api.v1.task_chains import create_task_chain
        from app.schemas.task_chain import ChainStepBase, TaskChainCreate

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10
        mock_plan.max_chain_steps = 10
        mock_plan.min_chain_interval_minutes = 5

        data = TaskChainCreate(
            name="Test Chain",
            trigger_type=TriggerType.DELAYED,
            execute_at=None,  # Missing execute_at
            steps=[
                ChainStepBase(name="Step 1", url="https://example.com/1", method="GET"),
            ],
        )

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.count_by_workspace = AsyncMock(return_value=0)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_task_chain(
                    data=data,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "execute_at is required" in exc_info.value.detail


class TestGetTaskChain:
    """Tests for get_task_chain endpoint."""

    @pytest.mark.asyncio
    async def test_get_chain_not_found(self):
        """Test getting non-existent chain."""
        from app.api.v1.task_chains import get_task_chain

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_steps = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_task_chain(
                    chain_id=uuid4(),
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_chain_wrong_workspace(self):
        """Test getting chain from wrong workspace."""
        from app.api.v1.task_chains import get_task_chain

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        mock_chain = MagicMock()
        mock_chain.workspace_id = uuid4()  # Different workspace

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_steps = AsyncMock(return_value=mock_chain)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_task_chain(
                    chain_id=uuid4(),
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestDeleteTaskChain:
    """Tests for delete_task_chain endpoint."""

    @pytest.mark.asyncio
    async def test_delete_chain_not_found(self):
        """Test deleting non-existent chain."""
        from app.api.v1.task_chains import delete_task_chain

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await delete_task_chain(
                    chain_id=uuid4(),
                    workspace=mock_workspace,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


class TestRunTaskChain:
    """Tests for run_task_chain endpoint."""

    @pytest.mark.asyncio
    async def test_run_chain_not_found(self):
        """Test running non-existent chain."""
        from app.api.v1.task_chains import run_task_chain

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()
        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_steps = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await run_task_chain(
                    chain_id=uuid4(),
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_run_inactive_chain(self):
        """Test running inactive chain."""
        from app.api.v1.task_chains import run_task_chain

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id
        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.workspace_id = workspace_id
        mock_chain.is_active = False  # Inactive

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_steps = AsyncMock(return_value=mock_chain)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await run_task_chain(
                    chain_id=mock_chain.id,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "inactive" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_run_chain_without_steps(self):
        """Test running chain without steps."""
        from app.api.v1.task_chains import run_task_chain

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id
        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.workspace_id = workspace_id
        mock_chain.is_active = True
        mock_chain.steps = []  # No steps

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_steps = AsyncMock(return_value=mock_chain)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await run_task_chain(
                    chain_id=mock_chain.id,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "no steps" in exc_info.value.detail.lower()


class TestCopyTaskChain:
    """Tests for copy_task_chain endpoint."""

    @pytest.mark.asyncio
    async def test_copy_chain_not_found(self):
        """Test copying non-existent chain."""
        from app.api.v1.task_chains import copy_task_chain

        mock_db = AsyncMock()
        mock_workspace = MagicMock()
        mock_workspace.id = uuid4()
        mock_plan = MagicMock()
        mock_plan.max_task_chains = 10

        with patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_with_steps = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await copy_task_chain(
                    chain_id=uuid4(),
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_copy_chain_limit_reached(self):
        """Test copying chain when limit reached."""
        from app.api.v1.task_chains import copy_task_chain

        mock_db = AsyncMock()
        workspace_id = uuid4()
        mock_workspace = MagicMock()
        mock_workspace.id = workspace_id
        mock_plan = MagicMock()
        mock_plan.max_task_chains = 3

        mock_chain = MagicMock()
        mock_chain.id = uuid4()
        mock_chain.workspace_id = workspace_id
        mock_chain.name = "Original Chain"

        with (
            patch("app.api.v1.task_chains.TaskChainRepository") as MockRepo,
            patch("app.api.v1.task_chains.WorkspaceRepository") as MockWorkspaceRepo,
        ):
            mock_repo = MagicMock()
            mock_repo.get_with_steps = AsyncMock(return_value=mock_chain)
            mock_repo.count_by_workspace = AsyncMock(return_value=3)  # At limit
            MockRepo.return_value = mock_repo

            mock_workspace_repo = MagicMock()
            mock_workspace_repo.get_active_chain_count = AsyncMock(return_value=3)
            MockWorkspaceRepo.return_value = mock_workspace_repo

            with pytest.raises(HTTPException) as exc_info:
                await copy_task_chain(
                    chain_id=mock_chain.id,
                    workspace=mock_workspace,
                    user_plan=mock_plan,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
            assert "limit reached" in exc_info.value.detail
