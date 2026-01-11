"""Unit tests for workspaces API endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def create_mock_user(**kwargs):
    """Create a mock user."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.email = kwargs.get("email", "test@example.com")
    mock.name = kwargs.get("name", "Test User")
    return mock


def create_mock_workspace(**kwargs):
    """Create a mock workspace."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "Test Workspace")
    mock.slug = kwargs.get("slug", "test-workspace")
    mock.owner_id = kwargs.get("owner_id", uuid4())
    mock.plan_id = kwargs.get("plan_id", uuid4())
    mock.cron_tasks_count = kwargs.get("cron_tasks_count", 0)
    mock.delayed_tasks_this_month = kwargs.get("delayed_tasks_this_month", 0)
    mock.default_timezone = kwargs.get("default_timezone", "UTC")
    mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mock.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return mock


def create_mock_plan(**kwargs):
    """Create a mock plan."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "free")
    mock.display_name = kwargs.get("display_name", "Free Plan")
    mock.max_workspaces = kwargs.get("max_workspaces", 3)
    mock.max_cron_tasks = kwargs.get("max_cron_tasks", 5)
    return mock


class TestListWorkspaces:
    """Tests for list_workspaces endpoint."""

    @pytest.mark.asyncio
    async def test_list_workspaces_success(self):
        """Test listing workspaces."""
        from app.api.v1.workspaces import list_workspaces

        mock_db = AsyncMock()
        mock_user = create_mock_user()
        mock_workspaces = [create_mock_workspace(), create_mock_workspace()]

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_owner = AsyncMock(return_value=mock_workspaces)
            mock_repo_class.return_value = mock_repo

            result = await list_workspaces(
                current_user=mock_user,
                db=mock_db,
                page=1,
                limit=20,
            )

            assert len(result) == 2
            mock_repo.get_by_owner.assert_called_once_with(
                owner_id=mock_user.id,
                skip=0,
                limit=20,
            )

    @pytest.mark.asyncio
    async def test_list_workspaces_with_pagination(self):
        """Test listing workspaces with pagination."""
        from app.api.v1.workspaces import list_workspaces

        mock_db = AsyncMock()
        mock_user = create_mock_user()
        mock_workspaces = [create_mock_workspace()]

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_owner = AsyncMock(return_value=mock_workspaces)
            mock_repo_class.return_value = mock_repo

            result = await list_workspaces(
                current_user=mock_user,
                db=mock_db,
                page=2,
                limit=10,
            )

            assert len(result) == 1
            mock_repo.get_by_owner.assert_called_once_with(
                owner_id=mock_user.id,
                skip=10,  # (page-1) * limit = (2-1) * 10 = 10
                limit=10,
            )


class TestCreateWorkspace:
    """Tests for create_workspace endpoint."""

    @pytest.mark.asyncio
    async def test_create_workspace_slug_exists(self):
        """Test creating workspace with existing slug."""
        from fastapi import HTTPException

        from app.api.v1.workspaces import create_workspace
        from app.schemas.workspace import WorkspaceCreate

        mock_db = AsyncMock()
        mock_user = create_mock_user()
        data = WorkspaceCreate(name="Test", slug="existing-slug")

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.slug_exists = AsyncMock(return_value=True)
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await create_workspace(data=data, current_user=mock_user, db=mock_db)

            assert exc_info.value.status_code == 400
            assert "slug already exists" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_workspace_limit_reached(self):
        """Test creating workspace when limit reached."""
        from fastapi import HTTPException

        from app.api.v1.workspaces import create_workspace
        from app.schemas.workspace import WorkspaceCreate

        mock_db = AsyncMock()
        mock_user = create_mock_user()
        mock_plan = create_mock_plan(max_workspaces=1)
        data = WorkspaceCreate(name="Test", slug="new-slug")

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_ws_repo_class:
            mock_ws_repo = MagicMock()
            mock_ws_repo.slug_exists = AsyncMock(return_value=False)
            mock_ws_repo.count_by_owner = AsyncMock(return_value=1)  # Already at limit
            mock_ws_repo_class.return_value = mock_ws_repo

            with patch("app.api.v1.workspaces.PlanRepository") as mock_plan_repo_class:
                mock_plan_repo = MagicMock()
                mock_plan_repo.ensure_free_plan_exists = AsyncMock(return_value=mock_plan)
                mock_plan_repo_class.return_value = mock_plan_repo

                with pytest.raises(HTTPException) as exc_info:
                    await create_workspace(data=data, current_user=mock_user, db=mock_db)

                assert exc_info.value.status_code == 403
                assert "limit reached" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_workspace_success(self):
        """Test successful workspace creation."""
        from app.api.v1.workspaces import create_workspace
        from app.schemas.workspace import WorkspaceCreate

        mock_db = AsyncMock()
        mock_user = create_mock_user()
        mock_plan = create_mock_plan(max_workspaces=5)
        mock_workspace = create_mock_workspace(
            name="New Workspace",
            slug="new-workspace",
            owner_id=mock_user.id,
        )
        data = WorkspaceCreate(name="New Workspace", slug="new-workspace")

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_ws_repo_class:
            mock_ws_repo = MagicMock()
            mock_ws_repo.slug_exists = AsyncMock(return_value=False)
            mock_ws_repo.count_by_owner = AsyncMock(return_value=1)
            mock_ws_repo.create = AsyncMock(return_value=mock_workspace)
            mock_ws_repo_class.return_value = mock_ws_repo

            with patch("app.api.v1.workspaces.PlanRepository") as mock_plan_repo_class:
                mock_plan_repo = MagicMock()
                mock_plan_repo.ensure_free_plan_exists = AsyncMock(return_value=mock_plan)
                mock_plan_repo_class.return_value = mock_plan_repo

                result = await create_workspace(data=data, current_user=mock_user, db=mock_db)

                assert result is not None
                mock_db.commit.assert_called_once()


class TestGetWorkspace:
    """Tests for get_workspace endpoint."""

    @pytest.mark.asyncio
    async def test_get_workspace_with_stats(self):
        """Test getting workspace with statistics."""
        from app.api.v1.workspaces import get_workspace

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()

        mock_workspace_with_plan = MagicMock()
        mock_workspace_with_plan.slug = mock_workspace.slug
        mock_workspace_with_plan.plan = MagicMock()
        mock_workspace_with_plan.plan.display_name = "Pro Plan"

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_ws_repo_class:
            mock_ws_repo = MagicMock()
            mock_ws_repo.get_with_plan = AsyncMock(return_value=mock_workspace_with_plan)
            mock_ws_repo_class.return_value = mock_ws_repo

            with patch("app.db.repositories.cron_tasks.CronTaskRepository") as mock_cron_repo_class:
                mock_cron_repo = MagicMock()
                mock_cron_repo.count_by_workspace = AsyncMock(return_value=5)
                mock_cron_repo_class.return_value = mock_cron_repo

                with patch("app.db.repositories.delayed_tasks.DelayedTaskRepository") as mock_delayed_repo_class:
                    mock_delayed_repo = MagicMock()
                    mock_delayed_repo.count_by_workspace = AsyncMock(return_value=3)
                    mock_delayed_repo_class.return_value = mock_delayed_repo

                    with patch("app.db.repositories.executions.ExecutionRepository") as mock_exec_repo_class:
                        mock_exec_repo = MagicMock()
                        mock_exec_repo.count_by_workspace = AsyncMock(return_value=100)
                        mock_exec_repo.get_stats = AsyncMock(return_value={"success_rate": 95.0})
                        mock_exec_repo_class.return_value = mock_exec_repo

                        result = await get_workspace(workspace=mock_workspace, db=mock_db)

                        assert result is not None
                        assert result.active_cron_tasks == 5
                        assert result.pending_delayed_tasks == 3
                        assert result.executions_today == 100
                        assert result.success_rate_7d == 95.0


class TestUpdateWorkspace:
    """Tests for update_workspace endpoint."""

    @pytest.mark.asyncio
    async def test_update_workspace_no_changes(self):
        """Test updating workspace with no changes."""
        from app.api.v1.workspaces import update_workspace
        from app.schemas.workspace import WorkspaceUpdate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        data = WorkspaceUpdate()  # Empty update

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            result = await update_workspace(
                data=data,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_workspace_with_name(self):
        """Test updating workspace name."""
        from app.api.v1.workspaces import update_workspace
        from app.schemas.workspace import WorkspaceUpdate

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()
        updated_workspace = create_mock_workspace(name="Updated Name")
        data = WorkspaceUpdate(name="Updated Name")

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.update = AsyncMock(return_value=updated_workspace)
            mock_repo_class.return_value = mock_repo

            result = await update_workspace(
                data=data,
                workspace=mock_workspace,
                db=mock_db,
            )

            assert result is not None
            mock_repo.update.assert_called_once()
            mock_db.commit.assert_called_once()


class TestDeleteWorkspace:
    """Tests for delete_workspace endpoint."""

    @pytest.mark.asyncio
    async def test_delete_workspace_success(self):
        """Test deleting workspace."""
        from app.api.v1.workspaces import delete_workspace

        mock_db = AsyncMock()
        mock_workspace = create_mock_workspace()

        with patch("app.api.v1.workspaces.WorkspaceRepository") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.delete = AsyncMock()
            mock_repo_class.return_value = mock_repo

            result = await delete_workspace(workspace=mock_workspace, db=mock_db)

            assert result is None
            mock_repo.delete.assert_called_once_with(mock_workspace)
            mock_db.commit.assert_called_once()
