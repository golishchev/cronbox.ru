"""Tests for heartbeat monitor API."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Heartbeat Test Workspace",
            "slug": "heartbeat-test",
        },
    )
    return response.json()


class TestHeartbeats:
    """Tests for heartbeat monitor CRUD operations."""

    async def test_create_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test creating a heartbeat monitor."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Test Heartbeat",
                "expected_interval": "1h",
                "grace_period": "10m",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Heartbeat"
        assert data["expected_interval"] == 3600  # 1h in seconds
        assert data["grace_period"] == 600  # 10m in seconds
        assert data["status"] == "waiting"
        assert data["ping_url"] is not None
        assert data["ping_token"] is not None

    async def test_create_heartbeat_with_description(self, authenticated_client: AsyncClient, workspace):
        """Test creating a heartbeat monitor with description."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Nightly Backup",
                "description": "Monitors the nightly backup job",
                "expected_interval": "1d",
                "grace_period": "30m",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Nightly Backup"
        assert data["description"] == "Monitors the nightly backup job"
        assert data["expected_interval"] == 86400  # 1d in seconds
        assert data["grace_period"] == 1800  # 30m in seconds

    async def test_create_heartbeat_invalid_interval(self, authenticated_client: AsyncClient, workspace):
        """Test creating a heartbeat with invalid interval format."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Invalid Interval",
                "expected_interval": "invalid",
            },
        )
        assert response.status_code == 422

    async def test_create_heartbeat_too_short_interval(self, authenticated_client: AsyncClient, workspace):
        """Test creating a heartbeat with too short interval."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Too Short",
                "expected_interval": "30s",  # Less than 60s
            },
        )
        assert response.status_code == 422

    async def test_list_heartbeats(self, authenticated_client: AsyncClient, workspace):
        """Test listing heartbeat monitors."""
        # Create a heartbeat first
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "List Test Heartbeat",
                "expected_interval": "1h",
            },
        )

        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/heartbeats")
        assert response.status_code == 200
        data = response.json()
        assert "heartbeats" in data
        assert "pagination" in data
        assert len(data["heartbeats"]) >= 1

    async def test_get_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test getting a specific heartbeat monitor."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Get Test Heartbeat",
                "expected_interval": "30m",
            },
        )
        heartbeat_id = create_response.json()["id"]

        # Get heartbeat
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == heartbeat_id
        assert data["name"] == "Get Test Heartbeat"

    async def test_update_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test updating a heartbeat monitor."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Update Test Heartbeat",
                "expected_interval": "1h",
            },
        )
        heartbeat_id = create_response.json()["id"]

        # Update heartbeat
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}",
            json={
                "name": "Updated Heartbeat Name",
                "expected_interval": "2h",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Heartbeat Name"
        assert data["expected_interval"] == 7200  # 2h in seconds

    async def test_pause_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test pausing a heartbeat monitor."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Pause Test Heartbeat",
                "expected_interval": "1h",
            },
        )
        heartbeat_id = create_response.json()["id"]

        # Pause heartbeat
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}/pause"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is True
        assert data["status"] == "paused"

    async def test_resume_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a paused heartbeat monitor."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Resume Test Heartbeat",
                "expected_interval": "1h",
            },
        )
        heartbeat_id = create_response.json()["id"]

        # Pause then resume
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}/pause"
        )
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}/resume"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is False
        assert data["status"] == "waiting"

    async def test_delete_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a heartbeat monitor."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Delete Test Heartbeat",
                "expected_interval": "1h",
            },
        )
        heartbeat_id = create_response.json()["id"]

        # Delete heartbeat
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}"
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}"
        )
        assert get_response.status_code == 404

    async def test_get_nonexistent_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test getting a non-existent heartbeat monitor."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/heartbeats/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_update_nonexistent_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test updating a non-existent heartbeat monitor."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/heartbeats/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_heartbeat(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a non-existent heartbeat monitor."""
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/heartbeats/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_list_heartbeats_with_pagination(self, authenticated_client: AsyncClient, workspace):
        """Test listing heartbeat monitors with pagination."""
        # Create a few heartbeats
        for i in range(3):
            await authenticated_client.post(
                f"/v1/workspaces/{workspace['id']}/heartbeats",
                json={
                    "name": f"Pagination Test {i}",
                    "expected_interval": "1h",
                },
            )

        # List with limit
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/heartbeats?limit=2"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["heartbeats"]) <= 2


class TestPingEndpoint:
    """Tests for the public ping endpoint."""

    async def test_ping_get(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test sending a GET ping."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Ping Test Heartbeat",
                "expected_interval": "1h",
            },
        )
        ping_token = create_response.json()["ping_token"]

        # Send ping (public endpoint, no auth required)
        response = await client.get(f"/ping/{ping_token}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["message"] == "pong"
        assert data["status"] == "healthy"

    async def test_ping_post_with_payload(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient
    ):
        """Test sending a POST ping with payload."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Ping Post Test",
                "expected_interval": "1h",
            },
        )
        ping_token = create_response.json()["ping_token"]

        # Send ping with payload
        response = await client.post(
            f"/ping/{ping_token}",
            json={
                "duration_ms": 4523,
                "status": "ok",
                "message": "Backup completed successfully",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["status"] == "healthy"

    async def test_ping_nonexistent_token(self, client: AsyncClient):
        """Test pinging with a non-existent token."""
        response = await client.get("/ping/nonexistent-token")
        assert response.status_code == 404

    async def test_ping_paused_heartbeat(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient
    ):
        """Test pinging a paused heartbeat."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Paused Ping Test",
                "expected_interval": "1h",
            },
        )
        heartbeat_id = create_response.json()["id"]
        ping_token = create_response.json()["ping_token"]

        # Pause heartbeat
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}/pause"
        )

        # Try to ping
        response = await client.get(f"/ping/{ping_token}")
        assert response.status_code == 400

    async def test_ping_updates_status(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient
    ):
        """Test that ping updates heartbeat status."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Status Update Test",
                "expected_interval": "1h",
            },
        )
        heartbeat_id = create_response.json()["id"]
        ping_token = create_response.json()["ping_token"]

        # Initial status should be waiting
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}"
        )
        assert get_response.json()["status"] == "waiting"

        # Send ping
        await client.get(f"/ping/{ping_token}")

        # Status should be healthy
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}"
        )
        assert get_response.json()["status"] == "healthy"
        assert get_response.json()["last_ping_at"] is not None

    async def test_list_heartbeat_pings(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient
    ):
        """Test listing ping history for a heartbeat."""
        # Create heartbeat
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Ping History Test",
                "expected_interval": "1h",
            },
        )
        heartbeat_id = create_response.json()["id"]
        ping_token = create_response.json()["ping_token"]

        # Send a few pings
        for _ in range(3):
            await client.get(f"/ping/{ping_token}")

        # List pings
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/heartbeats/{heartbeat_id}/pings"
        )
        assert response.status_code == 200
        data = response.json()
        assert "pings" in data
        assert len(data["pings"]) >= 3


class TestHeartbeatIntervals:
    """Tests for interval parsing."""

    async def test_interval_minutes(self, authenticated_client: AsyncClient, workspace):
        """Test interval in minutes."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Minutes Test",
                "expected_interval": "30m",
            },
        )
        assert response.status_code == 201
        assert response.json()["expected_interval"] == 1800  # 30 minutes

    async def test_interval_hours(self, authenticated_client: AsyncClient, workspace):
        """Test interval in hours."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Hours Test",
                "expected_interval": "6h",
            },
        )
        assert response.status_code == 201
        assert response.json()["expected_interval"] == 21600  # 6 hours

    async def test_interval_days(self, authenticated_client: AsyncClient, workspace):
        """Test interval in days."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Days Test",
                "expected_interval": "1d",
            },
        )
        assert response.status_code == 201
        assert response.json()["expected_interval"] == 86400  # 1 day

    async def test_grace_period_parsing(self, authenticated_client: AsyncClient, workspace):
        """Test grace period interval parsing."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/heartbeats",
            json={
                "name": "Grace Period Test",
                "expected_interval": "1h",
                "grace_period": "15m",
            },
        )
        assert response.status_code == 201
        assert response.json()["grace_period"] == 900  # 15 minutes
