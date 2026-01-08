"""Tests for workspaces API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestWorkspaces:
    """Tests for workspace CRUD operations."""

    async def test_create_workspace(self, authenticated_client: AsyncClient):
        """Test creating a workspace."""
        response = await authenticated_client.post(
            "/v1/workspaces",
            json={
                "name": "Test Workspace",
                "slug": "test-workspace",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workspace"
        assert data["slug"] == "test-workspace"
        assert "id" in data

    async def test_create_workspace_duplicate_slug(self, authenticated_client: AsyncClient):
        """Test creating workspace with duplicate slug."""
        # Create first workspace
        await authenticated_client.post(
            "/v1/workspaces",
            json={
                "name": "First Workspace",
                "slug": "unique-slug",
            },
        )

        # Try to create another with same slug
        response = await authenticated_client.post(
            "/v1/workspaces",
            json={
                "name": "Second Workspace",
                "slug": "unique-slug",
            },
        )
        assert response.status_code == 400

    async def test_list_workspaces(self, authenticated_client: AsyncClient):
        """Test listing workspaces."""
        # Create a workspace first
        await authenticated_client.post(
            "/v1/workspaces",
            json={
                "name": "List Test",
                "slug": "list-test",
            },
        )

        response = await authenticated_client.get("/v1/workspaces")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_workspace(self, authenticated_client: AsyncClient):
        """Test getting a specific workspace."""
        # Create workspace
        create_response = await authenticated_client.post(
            "/v1/workspaces",
            json={
                "name": "Get Test",
                "slug": "get-test",
            },
        )
        workspace_id = create_response.json()["id"]

        # Get workspace
        response = await authenticated_client.get(f"/v1/workspaces/{workspace_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workspace_id
        assert data["name"] == "Get Test"

    async def test_update_workspace(self, authenticated_client: AsyncClient):
        """Test updating a workspace."""
        # Create workspace
        create_response = await authenticated_client.post(
            "/v1/workspaces",
            json={
                "name": "Update Test",
                "slug": "update-test",
            },
        )
        workspace_id = create_response.json()["id"]

        # Update workspace
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_delete_workspace(self, authenticated_client: AsyncClient):
        """Test deleting a workspace."""
        # Create workspace
        create_response = await authenticated_client.post(
            "/v1/workspaces",
            json={
                "name": "Delete Test",
                "slug": "delete-test",
            },
        )
        workspace_id = create_response.json()["id"]

        # Delete workspace
        response = await authenticated_client.delete(f"/v1/workspaces/{workspace_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(f"/v1/workspaces/{workspace_id}")
        assert get_response.status_code == 404

    async def test_workspace_unauthorized(self, client: AsyncClient):
        """Test accessing workspaces without auth."""
        response = await client.get("/v1/workspaces")
        assert response.status_code == 401
