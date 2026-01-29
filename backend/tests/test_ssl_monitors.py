"""Tests for SSL monitor API."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "SSL Test Workspace",
            "slug": "ssl-test",
        },
    )
    return response.json()


class TestSSLMonitors:
    """Tests for SSL monitor CRUD operations."""

    async def test_create_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test creating an SSL monitor."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Test SSL Monitor",
                "domain": "example.com",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test SSL Monitor"
        assert data["domain"] == "example.com"
        assert data["port"] == 443  # default port
        # Status is updated after immediate check
        assert data["status"] in ["pending", "valid", "expiring", "expired", "invalid", "error"]

    async def test_create_ssl_monitor_with_port(self, authenticated_client: AsyncClient, workspace):
        """Test creating an SSL monitor with custom port."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Custom Port SSL",
                "domain": "example.com",
                "port": 8443,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["port"] == 8443

    async def test_create_ssl_monitor_with_description(self, authenticated_client: AsyncClient, workspace):
        """Test creating an SSL monitor with description."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Production API",
                "description": "Main production API endpoint",
                "domain": "api.example.com",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Production API"
        assert data["description"] == "Main production API endpoint"

    async def test_create_ssl_monitor_with_notification_settings(self, authenticated_client: AsyncClient, workspace):
        """Test creating an SSL monitor with notification settings."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Notified SSL",
                "domain": "notify.example.com",
                "notify_on_expiring": True,
                "notify_on_error": False,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["notify_on_expiring"] is True
        assert data["notify_on_error"] is False

    async def test_create_ssl_monitor_missing_name(self, authenticated_client: AsyncClient, workspace):
        """Test creating an SSL monitor without name fails."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "domain": "example.com",
            },
        )
        assert response.status_code == 422

    async def test_create_ssl_monitor_missing_domain(self, authenticated_client: AsyncClient, workspace):
        """Test creating an SSL monitor without domain fails."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "No Domain",
            },
        )
        assert response.status_code == 422

    async def test_create_ssl_monitor_invalid_port(self, authenticated_client: AsyncClient, workspace):
        """Test creating an SSL monitor with invalid port fails."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Invalid Port",
                "domain": "example.com",
                "port": 70000,  # > 65535
            },
        )
        assert response.status_code == 422

    async def test_list_ssl_monitors(self, authenticated_client: AsyncClient, workspace):
        """Test listing SSL monitors."""
        # Create an SSL monitor first
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "List Test SSL",
                "domain": "list.example.com",
            },
        )

        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/ssl-monitors")
        assert response.status_code == 200
        data = response.json()
        assert "monitors" in data
        assert "pagination" in data
        assert len(data["monitors"]) >= 1

    async def test_get_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test getting a specific SSL monitor."""
        # Create SSL monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Get Test SSL",
                "domain": "get.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        # Get SSL monitor
        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == monitor_id
        assert data["name"] == "Get Test SSL"

    async def test_update_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test updating an SSL monitor."""
        # Create SSL monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Update Test SSL",
                "domain": "update.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        # Update SSL monitor
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}",
            json={
                "name": "Updated SSL Name",
                "description": "Now with description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated SSL Name"
        assert data["description"] == "Now with description"
        # Domain should not change
        assert data["domain"] == "update.example.com"

    async def test_update_ssl_monitor_port(self, authenticated_client: AsyncClient, workspace):
        """Test updating SSL monitor port."""
        # Create SSL monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Port Update Test",
                "domain": "port.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        # Update port
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}",
            json={
                "port": 8443,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["port"] == 8443

    async def test_pause_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test pausing an SSL monitor."""
        # Create SSL monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Pause Test SSL",
                "domain": "pause.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        # Pause SSL monitor
        response = await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    async def test_resume_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a paused SSL monitor."""
        # Create SSL monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Resume Test SSL",
                "domain": "resume.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        # Pause then resume
        await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/pause")
        response = await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

    async def test_check_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test manual SSL check."""
        # Create SSL monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Check Test SSL",
                "domain": "google.com",  # Use a real domain for check
            },
        )
        monitor_id = create_response.json()["id"]

        # Trigger manual check
        response = await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/check")
        assert response.status_code == 200
        data = response.json()
        # Should have checked the certificate
        assert data["last_check_at"] is not None
        # Status should be updated (valid, expiring, expired, or error)
        assert data["status"] in ["valid", "expiring", "expired", "invalid", "error"]

    async def test_delete_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test deleting an SSL monitor."""
        # Create SSL monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Delete Test SSL",
                "domain": "delete.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        # Delete SSL monitor
        response = await authenticated_client.delete(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}")
        assert get_response.status_code == 404

    async def test_get_nonexistent_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test getting a non-existent SSL monitor."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_update_nonexistent_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test updating a non-existent SSL monitor."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_ssl_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a non-existent SSL monitor."""
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_list_ssl_monitors_with_pagination(self, authenticated_client: AsyncClient, workspace):
        """Test listing SSL monitors with pagination."""
        # Create a few SSL monitors
        for i in range(3):
            await authenticated_client.post(
                f"/v1/workspaces/{workspace['id']}/ssl-monitors",
                json={
                    "name": f"Pagination Test {i}",
                    "domain": f"page{i}.example.com",
                },
            )

        # List with limit
        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/ssl-monitors?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["monitors"]) <= 2


class TestSSLMonitorDuplicates:
    """Tests for duplicate domain handling."""

    async def test_create_duplicate_domain(self, authenticated_client: AsyncClient, workspace):
        """Test creating SSL monitor with duplicate domain."""
        # Create first monitor
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "First SSL",
                "domain": "duplicate.example.com",
            },
        )

        # Try to create duplicate
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Second SSL",
                "domain": "duplicate.example.com",
            },
        )
        assert response.status_code == 400

    async def test_create_same_domain_different_port(self, authenticated_client: AsyncClient, workspace):
        """Test creating SSL monitor with same domain but different port is rejected."""
        # Create first monitor
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Port 443 SSL",
                "domain": "multiport.example.com",
                "port": 443,
            },
        )

        # Try to create second with different port - should fail (domain uniqueness per workspace)
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Port 8443 SSL",
                "domain": "multiport.example.com",
                "port": 8443,
            },
        )
        assert response.status_code == 400


class TestSSLMonitorPausedState:
    """Tests for paused SSL monitor behavior."""

    async def test_check_paused_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test that checking a paused monitor returns error."""
        # Create and pause
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Paused Check SSL",
                "domain": "paused.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/pause")

        # Try to check
        response = await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/check")
        assert response.status_code == 400

    async def test_pause_already_paused(self, authenticated_client: AsyncClient, workspace):
        """Test pausing an already paused monitor returns error."""
        # Create and pause
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Double Pause SSL",
                "domain": "doublepause.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/pause")

        # Pause again - should return error
        response = await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/pause")
        assert response.status_code == 400

    async def test_resume_not_paused(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a monitor that is not paused."""
        # Create (not paused)
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/ssl-monitors",
            json={
                "name": "Not Paused SSL",
                "domain": "notpaused.example.com",
            },
        )
        monitor_id = create_response.json()["id"]

        # Try to resume
        response = await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/ssl-monitors/{monitor_id}/resume")
        assert response.status_code == 400
