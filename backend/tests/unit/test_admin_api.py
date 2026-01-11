"""Unit tests for admin API endpoints."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException


def create_mock_user(**kwargs):
    """Create a mock user."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.email = kwargs.get("email", "test@example.com")
    mock.name = kwargs.get("name", "Test User")
    mock.is_active = kwargs.get("is_active", True)
    mock.is_superuser = kwargs.get("is_superuser", False)
    mock.email_verified = kwargs.get("email_verified", False)
    mock.telegram_id = kwargs.get("telegram_id", None)
    mock.telegram_username = kwargs.get("telegram_username", None)
    mock.preferred_language = kwargs.get("preferred_language", "ru")
    mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mock.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    return mock


def create_mock_admin(**kwargs):
    """Create a mock admin user."""
    mock = create_mock_user(**kwargs)
    mock.is_superuser = True
    return mock


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    @pytest.mark.asyncio
    async def test_require_admin_success(self):
        """Test admin user passes check."""
        from app.api.v1.admin import require_admin

        admin_user = create_mock_admin()

        result = await require_admin(admin_user)

        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_not_superuser(self):
        """Test non-admin user is rejected."""
        from app.api.v1.admin import require_admin

        regular_user = create_mock_user(is_superuser=False)

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(regular_user)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail


class TestGetAdminStats:
    """Tests for get_admin_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Test getting admin stats."""
        from app.api.v1.admin import get_admin_stats

        mock_admin = create_mock_admin()
        mock_db = MagicMock()

        # Mock all scalar calls with MagicMock that returns coroutine
        async def mock_scalar(query):
            # Return appropriate values for different queries
            return 100

        mock_db.scalar = mock_scalar

        result = await get_admin_stats(admin=mock_admin, db=mock_db)

        assert result.total_users == 100


class TestGetUser:
    """Tests for get_user endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """Test getting user details."""
        from app.api.v1.admin import get_user

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        user_id = str(uuid4())
        mock_user = create_mock_user(id=user_id)

        async def mock_get(model, id):
            return mock_user

        async def mock_scalar(query):
            return 5

        mock_db.get = mock_get
        mock_db.scalar = mock_scalar

        result = await get_user(admin=mock_admin, db=mock_db, user_id=user_id)

        assert result.email == mock_user.email
        assert result.workspaces_count == 5

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """Test getting non-existent user."""
        from app.api.v1.admin import get_user

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        user_id = str(uuid4())

        async def mock_get(model, id):
            return None

        mock_db.get = mock_get

        with pytest.raises(HTTPException) as exc_info:
            await get_user(admin=mock_admin, db=mock_db, user_id=user_id)

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail


class TestUpdateUser:
    """Tests for update_user endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Test updating non-existent user."""
        from app.api.v1.admin import UpdateUserRequest, update_user

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        user_id = str(uuid4())
        data = UpdateUserRequest(is_active=False)

        async def mock_get(model, id):
            return None

        mock_db.get = mock_get

        with pytest.raises(HTTPException) as exc_info:
            await update_user(admin=mock_admin, db=mock_db, user_id=user_id, data=data)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_cannot_remove_own_admin(self):
        """Test admin cannot remove their own admin status."""
        from app.api.v1.admin import UpdateUserRequest, update_user

        admin_id = uuid4()
        mock_admin = create_mock_admin(id=admin_id)
        mock_db = MagicMock()
        mock_user = create_mock_user(id=admin_id, is_superuser=True)

        data = UpdateUserRequest(is_superuser=False)

        async def mock_get(model, id):
            return mock_user

        mock_db.get = mock_get

        with pytest.raises(HTTPException) as exc_info:
            await update_user(admin=mock_admin, db=mock_db, user_id=str(admin_id), data=data)

        assert exc_info.value.status_code == 400
        assert "Cannot remove your own admin status" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_user_success(self):
        """Test successfully updating a user."""
        from app.api.v1.admin import UpdateUserRequest, update_user

        admin_id = uuid4()
        mock_admin = create_mock_admin(id=admin_id)
        mock_db = MagicMock()
        user_id = uuid4()  # Different user
        mock_user = create_mock_user(id=user_id, is_active=True)

        data = UpdateUserRequest(is_active=False)

        async def mock_get(model, id):
            return mock_user

        async def mock_commit():
            pass

        async def mock_refresh(obj):
            pass

        mock_db.get = mock_get
        mock_db.commit = mock_commit
        mock_db.refresh = mock_refresh

        result = await update_user(admin=mock_admin, db=mock_db, user_id=str(user_id), data=data)

        assert result["message"] == "User updated successfully"


class TestListUsers:
    """Tests for list_users endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_success(self):
        """Test listing users."""
        from app.api.v1.admin import list_users

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        mock_users = [create_mock_user(), create_mock_user()]

        async def mock_scalar(query):
            return 2

        async def mock_execute(query):
            result = MagicMock()
            result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_users)))
            return result

        mock_db.scalar = mock_scalar
        mock_db.execute = mock_execute

        result = await list_users(admin=mock_admin, db=mock_db, page=1, page_size=20, search=None)

        assert result.total == 2
        assert len(result.users) == 2

    @pytest.mark.asyncio
    async def test_list_users_with_search(self):
        """Test listing users with search."""
        from app.api.v1.admin import list_users

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        mock_users = [create_mock_user(email="search@example.com")]

        async def mock_scalar(query):
            return 1

        async def mock_execute(query):
            result = MagicMock()
            result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_users)))
            return result

        mock_db.scalar = mock_scalar
        mock_db.execute = mock_execute

        result = await list_users(admin=mock_admin, db=mock_db, page=1, page_size=20, search="search")

        assert result.total == 1


def create_mock_workspace(**kwargs):
    """Create a mock workspace."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock.name = kwargs.get("name", "Test Workspace")
    mock.slug = kwargs.get("slug", "test-workspace")
    mock.owner_id = kwargs.get("owner_id", uuid4())
    mock.default_timezone = kwargs.get("default_timezone", "UTC")
    mock.webhook_secret = kwargs.get("webhook_secret", None)
    mock.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
    mock.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
    # Add owner relation
    mock.owner = kwargs.get("owner", create_mock_user())
    return mock


def create_mock_subscription(**kwargs):
    """Create a mock subscription."""
    mock = MagicMock()
    mock.id = kwargs.get("id", uuid4())
    mock_plan = MagicMock()
    mock_plan.name = kwargs.get("plan_name", "free")
    mock.plan = mock_plan
    return mock


class TestListWorkspaces:
    """Tests for list_workspaces endpoint."""

    @pytest.mark.asyncio
    async def test_list_workspaces_success(self):
        """Test listing workspaces."""
        from app.api.v1.admin import list_workspaces

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        mock_workspaces = [create_mock_workspace(), create_mock_workspace()]
        mock_sub = create_mock_subscription()

        call_count = 0
        async def mock_scalar(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 2  # total count
            # For each workspace: cron, delayed, exec, subscription
            # So subscription is at 5, 9 (for 2 workspaces)
            if call_count in [5, 9]:
                return mock_sub
            return 5  # counts for cron/delayed/executions

        async def mock_execute(query):
            result = MagicMock()
            result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_workspaces)))
            return result

        mock_db.scalar = mock_scalar
        mock_db.execute = mock_execute

        result = await list_workspaces(admin=mock_admin, db=mock_db, page=1, page_size=20, search=None)

        assert result.total == 2

    @pytest.mark.asyncio
    async def test_list_workspaces_with_search(self):
        """Test listing workspaces with search filter."""
        from app.api.v1.admin import list_workspaces

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        mock_workspaces = [create_mock_workspace(name="SearchWorkspace")]
        mock_sub = create_mock_subscription()

        call_count = 0
        async def mock_scalar(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1  # total count
            if call_count == 5:  # subscription query for 1 workspace
                return mock_sub
            return 3  # counts for cron/delayed/executions

        async def mock_execute(query):
            result = MagicMock()
            result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_workspaces)))
            return result

        mock_db.scalar = mock_scalar
        mock_db.execute = mock_execute

        result = await list_workspaces(admin=mock_admin, db=mock_db, page=1, page_size=20, search="search")

        assert result.total == 1


class TestGetWorkspace:
    """Tests for get_workspace endpoint."""

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self):
        """Test getting non-existent workspace."""
        from app.api.v1.admin import get_workspace

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        workspace_id = str(uuid4())

        async def mock_execute(query):
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        mock_db.execute = mock_execute

        with pytest.raises(HTTPException) as exc_info:
            await get_workspace(admin=mock_admin, db=mock_db, workspace_id=workspace_id)

        assert exc_info.value.status_code == 404
        assert "Workspace not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_workspace_success(self):
        """Test getting workspace details."""
        from app.api.v1.admin import get_workspace

        mock_admin = create_mock_admin()
        mock_db = MagicMock()
        workspace_id = str(uuid4())
        mock_ws = create_mock_workspace(id=workspace_id)
        mock_sub = create_mock_subscription()

        call_count = 0
        async def mock_scalar(query):
            nonlocal call_count
            call_count += 1
            # Count queries: cron, delayed, exec, active_cron, pending_delayed, subscription
            if call_count == 6:  # subscription query
                return mock_sub
            return 10  # counts

        async def mock_execute(query):
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=mock_ws)
            return result

        mock_db.execute = mock_execute
        mock_db.scalar = mock_scalar

        result = await get_workspace(admin=mock_admin, db=mock_db, workspace_id=workspace_id)

        assert result.name == mock_ws.name
