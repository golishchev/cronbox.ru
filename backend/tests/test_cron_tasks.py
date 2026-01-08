"""Tests for cron tasks API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Cron Test Workspace",
            "slug": "cron-test",
        },
    )
    return response.json()


class TestCronTasks:
    """Tests for cron task CRUD operations."""

    async def test_create_cron_task(self, authenticated_client: AsyncClient, workspace):
        """Test creating a cron task."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Test Cron Task",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "*/5 * * * *",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Cron Task"
        assert data["url"] == "https://example.com/api/test"
        assert data["method"] == "GET"
        assert data["schedule"] == "*/5 * * * *"
        assert data["is_active"] is True

    async def test_create_cron_task_with_headers(self, authenticated_client: AsyncClient, workspace):
        """Test creating a cron task with headers."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Task with Headers",
                "url": "https://example.com/api/test",
                "method": "POST",
                "schedule": "0 * * * *",
                "headers": {
                    "Authorization": "Bearer token123",
                    "Content-Type": "application/json",
                },
                "body": '{"key": "value"}',
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["headers"]["Authorization"] == "Bearer token123"
        assert data["body"] == '{"key": "value"}'

    async def test_create_cron_task_invalid_schedule(self, authenticated_client: AsyncClient, workspace):
        """Test creating a cron task with invalid schedule."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Invalid Schedule",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "invalid cron",
            },
        )
        assert response.status_code == 422

    async def test_list_cron_tasks(self, authenticated_client: AsyncClient, workspace):
        """Test listing cron tasks."""
        # Create a task first
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "List Test Task",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "0 0 * * *",
            },
        )

        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/cron"
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    async def test_get_cron_task(self, authenticated_client: AsyncClient, workspace):
        """Test getting a specific cron task."""
        # Create task
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Get Test Task",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "0 0 * * *",
            },
        )
        task_id = create_response.json()["id"]

        # Get task
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/cron/{task_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["name"] == "Get Test Task"

    async def test_update_cron_task(self, authenticated_client: AsyncClient, workspace):
        """Test updating a cron task."""
        # Create task
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Update Test Task",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "0 0 * * *",
            },
        )
        task_id = create_response.json()["id"]

        # Update task
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/cron/{task_id}",
            json={
                "name": "Updated Task Name",
                "schedule": "0 * * * *",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Task Name"
        assert data["schedule"] == "0 * * * *"

    async def test_pause_cron_task(self, authenticated_client: AsyncClient, workspace):
        """Test pausing a cron task."""
        # Create task
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Pause Test Task",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "0 0 * * *",
            },
        )
        task_id = create_response.json()["id"]

        # Pause task
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron/{task_id}/pause"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_resume_cron_task(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a paused cron task."""
        # Create task
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Resume Test Task",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "0 0 * * *",
            },
        )
        task_id = create_response.json()["id"]

        # Pause then resume
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron/{task_id}/pause"
        )
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron/{task_id}/resume"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True

    async def test_delete_cron_task(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a cron task."""
        # Create task
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/cron",
            json={
                "name": "Delete Test Task",
                "url": "https://example.com/api/test",
                "method": "GET",
                "schedule": "0 0 * * *",
            },
        )
        task_id = create_response.json()["id"]

        # Delete task
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/cron/{task_id}"
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/cron/{task_id}"
        )
        assert get_response.status_code == 404
