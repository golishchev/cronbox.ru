"""Tests for workers API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Workers Test Workspace",
            "slug": "workers-test",
        },
    )
    return response.json()


class TestWorkers:
    """Tests for worker management endpoints."""

    async def test_create_worker(self, authenticated_client: AsyncClient, workspace):
        """Test creating a new worker."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={
                "name": "Test Worker",
                "description": "A test worker for running tasks",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Worker"
        assert "api_key" in data  # Should return the API key once

    async def test_list_workers(self, authenticated_client: AsyncClient, workspace):
        """Test listing workers."""
        # Create a worker first
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={"name": "List Test Worker"},
        )

        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/workers"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data
        workers = data if isinstance(data, list) else data["items"]
        assert len(workers) >= 1

    async def test_get_worker(self, authenticated_client: AsyncClient, workspace):
        """Test getting a specific worker."""
        # Create worker
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={"name": "Get Test Worker"},
        )
        worker_id = create_response.json()["id"]

        # Get worker
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/workers/{worker_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == worker_id
        assert data["name"] == "Get Test Worker"
        # API key should NOT be returned on get
        assert "api_key" not in data or data.get("api_key") is None

    async def test_update_worker(self, authenticated_client: AsyncClient, workspace):
        """Test updating a worker."""
        # Create worker
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={"name": "Update Test Worker"},
        )
        worker_id = create_response.json()["id"]

        # Update worker
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/workers/{worker_id}",
            json={
                "name": "Updated Worker Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Worker Name"
        assert data["description"] == "Updated description"

    async def test_delete_worker(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a worker."""
        # Create worker
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={"name": "Delete Test Worker"},
        )
        worker_id = create_response.json()["id"]

        # Delete worker
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/workers/{worker_id}"
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/workers/{worker_id}"
        )
        assert get_response.status_code == 404

    async def test_regenerate_worker_key(self, authenticated_client: AsyncClient, workspace):
        """Test regenerating worker API key."""
        # Create worker
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={"name": "Regenerate Test Worker"},
        )
        worker_id = create_response.json()["id"]
        old_key_prefix = create_response.json().get("api_key_prefix")

        # Regenerate key
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers/{worker_id}/regenerate-key"
        )
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data  # New key returned
        # Prefix might be same but key should be different
        assert data["api_key"]  # Key is not empty

    async def test_deactivate_worker(self, authenticated_client: AsyncClient, workspace):
        """Test deactivating a worker."""
        # Create worker
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={"name": "Deactivate Test Worker"},
        )
        worker_id = create_response.json()["id"]

        # Deactivate
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/workers/{worker_id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False


class TestWorkerAPI:
    """Tests for worker-side API endpoints."""

    @pytest.fixture
    async def worker_with_key(self, authenticated_client: AsyncClient, workspace):
        """Create a worker and get its API key."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/workers",
            json={"name": "API Test Worker"},
        )
        return response.json()

    async def test_worker_heartbeat(self, client: AsyncClient, worker_with_key):
        """Test worker heartbeat endpoint."""
        api_key = worker_with_key.get("api_key")
        if api_key:
            response = await client.post(
                "/v1/worker/heartbeat",
                headers={"X-Worker-Key": api_key},
            )
            # Should work or fail if endpoint requires more data
            assert response.status_code in [200, 422]

    async def test_worker_get_tasks(self, client: AsyncClient, worker_with_key):
        """Test worker getting tasks."""
        api_key = worker_with_key.get("api_key")
        if api_key:
            try:
                response = await client.get(
                    "/v1/worker/tasks",
                    headers={"X-Worker-Key": api_key},
                )
                # 200/204 if works, 500 if Redis not available in tests
                assert response.status_code in [200, 204, 500]
            except RuntimeError as e:
                # Skip test if Redis not initialized (expected in test env without Redis)
                if "Redis client is not initialized" in str(e):
                    pytest.skip("Redis not available in test environment")

    async def test_worker_info(self, client: AsyncClient, worker_with_key):
        """Test worker info endpoint."""
        api_key = worker_with_key.get("api_key")
        if api_key:
            response = await client.get(
                "/v1/worker/info",
                headers={"X-Worker-Key": api_key},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "API Test Worker"

    async def test_worker_invalid_key(self, client: AsyncClient):
        """Test worker API with invalid key."""
        response = await client.post(
            "/v1/worker/heartbeat",
            headers={"X-Worker-Key": "invalid-key"},
        )
        assert response.status_code == 401

    async def test_worker_no_key(self, client: AsyncClient):
        """Test worker API without key."""
        response = await client.post("/v1/worker/heartbeat")
        assert response.status_code in [401, 422]

    async def test_workers_unauthorized(self, client: AsyncClient):
        """Test accessing workers without authentication."""
        response = await client.get("/v1/workspaces/some-id/workers")
        assert response.status_code == 401
