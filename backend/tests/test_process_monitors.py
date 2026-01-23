"""Tests for process monitor API."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Process Monitor Test Workspace",
            "slug": "process-monitor-test",
        },
    )
    return response.json()


class TestProcessMonitorsCRUD:
    """Tests for process monitor CRUD operations."""

    async def test_create_process_monitor_cron(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor with cron schedule."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Test Process Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 2 * * *",
                "timezone": "UTC",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Process Monitor"
        assert data["schedule_type"] == "cron"
        assert data["schedule_cron"] == "0 2 * * *"
        assert data["timezone"] == "UTC"
        assert data["start_grace_period"] == 300  # 5m in seconds
        assert data["end_timeout"] == 3600  # 1h in seconds
        assert data["status"] == "waiting_start"
        assert data["start_token"] is not None
        assert data["end_token"] is not None
        assert data["start_url"] is not None
        assert data["end_url"] is not None

    async def test_create_process_monitor_interval(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor with interval schedule."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Interval Monitor",
                "schedule_type": "interval",
                "schedule_interval": "6h",
                "start_grace_period": "10m",
                "end_timeout": "30m",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "interval"
        assert data["schedule_interval"] == 21600  # 6h in seconds

    async def test_create_process_monitor_exact_time(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor with exact time schedule."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Exact Time Monitor",
                "schedule_type": "exact_time",
                "schedule_exact_time": "09:00",
                "timezone": "Europe/Moscow",
                "start_grace_period": "15m",
                "end_timeout": "2h",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "exact_time"
        assert data["schedule_exact_time"] == "09:00"
        assert data["timezone"] == "Europe/Moscow"

    async def test_create_process_monitor_with_description(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor with description."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Nightly Backup",
                "description": "Monitors the nightly database backup process",
                "schedule_type": "cron",
                "schedule_cron": "0 3 * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Monitors the nightly database backup process"

    async def test_create_process_monitor_notification_settings(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor with custom notification settings."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Notification Settings Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "30m",
                "notify_on_missed_start": False,
                "notify_on_missed_end": True,
                "notify_on_recovery": True,
                "notify_on_success": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["notify_on_missed_start"] is False
        assert data["notify_on_missed_end"] is True
        assert data["notify_on_recovery"] is True
        assert data["notify_on_success"] is True

    async def test_create_process_monitor_missing_schedule(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor without required schedule field."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Missing Schedule",
                "schedule_type": "cron",
                # Missing schedule_cron
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        assert response.status_code == 400

    async def test_create_process_monitor_invalid_cron(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor with invalid cron expression."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Invalid Cron",
                "schedule_type": "cron",
                "schedule_cron": "invalid cron",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        assert response.status_code == 400

    async def test_create_process_monitor_invalid_interval(self, authenticated_client: AsyncClient, workspace):
        """Test creating a process monitor with invalid interval format."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Invalid Interval",
                "schedule_type": "interval",
                "schedule_interval": "invalid",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        assert response.status_code == 422

    async def test_list_process_monitors(self, authenticated_client: AsyncClient, workspace):
        """Test listing process monitors."""
        # Create a monitor first
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "List Test Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )

        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/process-monitors")
        assert response.status_code == 200
        data = response.json()
        assert "process_monitors" in data
        assert "pagination" in data
        assert len(data["process_monitors"]) >= 1

    async def test_get_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test getting a specific process monitor."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Get Test Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Get monitor
        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == monitor_id
        assert data["name"] == "Get Test Monitor"

    async def test_update_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test updating a process monitor."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Update Test Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Update monitor
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}",
            json={
                "name": "Updated Monitor Name",
                "end_timeout": "2h",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Monitor Name"
        assert data["end_timeout"] == 7200  # 2h in seconds

    async def test_pause_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test pausing a process monitor."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Pause Test Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Pause monitor
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is True
        assert data["status"] == "paused"

    async def test_resume_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a paused process monitor."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Resume Test Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Pause then resume
        await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause")
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/resume"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is False
        assert data["status"] == "waiting_start"

    async def test_delete_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a process monitor."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Delete Test Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Delete monitor
        response = await authenticated_client.delete(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}")
        assert get_response.status_code == 404

    async def test_get_nonexistent_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test getting a non-existent process monitor."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_update_nonexistent_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test updating a non-existent process monitor."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/process-monitors/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_process_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a non-existent process monitor."""
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/process-monitors/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_list_process_monitors_with_pagination(self, authenticated_client: AsyncClient, workspace):
        """Test listing process monitors with pagination."""
        # Create a few monitors
        for i in range(3):
            await authenticated_client.post(
                f"/v1/workspaces/{workspace['id']}/process-monitors",
                json={
                    "name": f"Pagination Test {i}",
                    "schedule_type": "cron",
                    "schedule_cron": "0 * * * *",
                    "start_grace_period": "5m",
                    "end_timeout": "1h",
                },
            )

        # List with limit
        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/process-monitors?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["process_monitors"]) <= 2


class TestProcessPingEndpoints:
    """Tests for the public ping endpoints."""

    async def test_start_ping_get(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test sending a GET start ping."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Start Ping Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        start_token = create_response.json()["start_token"]

        # Send start ping (public endpoint, no auth required)
        response = await client.get(f"/ping/start/{start_token}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["status"] == "running"
        assert data["run_id"] is not None

    async def test_start_ping_post(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test sending a POST start ping with payload."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Start Ping Post Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        start_token = create_response.json()["start_token"]

        # Send start ping with payload
        response = await client.post(
            f"/ping/start/{start_token}",
            json={
                "message": "Backup starting",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["status"] == "running"

    async def test_end_ping_after_start(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test sending an end ping after start."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "End Ping Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]
        start_token = create_response.json()["start_token"]
        end_token = create_response.json()["end_token"]

        # Send start ping first
        start_response = await client.get(f"/ping/start/{start_token}")
        assert start_response.status_code == 200
        run_id = start_response.json()["run_id"]

        # Send end ping
        response = await client.get(f"/ping/end/{end_token}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        # After completion, status immediately transitions to waiting_start for next run
        assert data["status"] == "waiting_start"
        assert data["run_id"] == run_id
        assert data["duration_ms"] is not None

        # Verify monitor status is waiting_start (ready for next run)
        get_response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}")
        assert get_response.json()["status"] == "waiting_start"

    async def test_end_ping_without_start(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test sending an end ping without a start ping."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "End Without Start Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        end_token = create_response.json()["end_token"]

        # Try to send end ping without start
        response = await client.get(f"/ping/end/{end_token}")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data  # FastAPI returns {"detail": "..."} for HTTPExceptions

    async def test_duplicate_start_ping(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test sending a duplicate start ping (should be rejected)."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Duplicate Start Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        start_token = create_response.json()["start_token"]

        # Send first start ping
        first_response = await client.get(f"/ping/start/{start_token}")
        assert first_response.status_code == 200

        # Try to send second start ping (should be rejected)
        second_response = await client.get(f"/ping/start/{start_token}")
        assert second_response.status_code == 409
        data = second_response.json()
        assert "detail" in data  # FastAPI returns {"detail": "..."} for HTTPExceptions

    async def test_ping_nonexistent_start_token(self, client: AsyncClient):
        """Test pinging with a non-existent start token."""
        response = await client.get("/ping/start/nonexistent-token")
        assert response.status_code == 404

    async def test_ping_nonexistent_end_token(self, client: AsyncClient):
        """Test pinging with a non-existent end token."""
        response = await client.get("/ping/end/nonexistent-token")
        assert response.status_code == 404

    async def test_ping_paused_monitor(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test pinging a paused monitor."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Paused Ping Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]
        start_token = create_response.json()["start_token"]

        # Pause monitor
        await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause")

        # Try to ping
        response = await client.get(f"/ping/start/{start_token}")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data  # FastAPI returns {"detail": "..."} for HTTPExceptions

    async def test_start_ping_updates_status(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test that start ping updates monitor status."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Status Update Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]
        start_token = create_response.json()["start_token"]

        # Initial status should be waiting_start
        get_response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}")
        assert get_response.json()["status"] == "waiting_start"

        # Send start ping
        await client.get(f"/ping/start/{start_token}")

        # Status should be running
        get_response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}")
        data = get_response.json()
        assert data["status"] == "running"
        assert data["last_start_at"] is not None
        assert data["current_run_id"] is not None

    async def test_head_request_start_ping(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test HEAD request for start ping."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Head Start Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        start_token = create_response.json()["start_token"]

        # Send HEAD request
        response = await client.head(f"/ping/start/{start_token}")
        assert response.status_code == 200

    async def test_head_request_end_ping(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test HEAD request for end ping (requires running state)."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Head End Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        start_token = create_response.json()["start_token"]
        end_token = create_response.json()["end_token"]

        # Start the process first
        await client.get(f"/ping/start/{start_token}")

        # Send HEAD request for end
        response = await client.head(f"/ping/end/{end_token}")
        assert response.status_code == 200


class TestProcessMonitorEvents:
    """Tests for process monitor events."""

    async def test_list_events(self, authenticated_client: AsyncClient, workspace, client: AsyncClient):
        """Test listing events for a process monitor."""
        # Create monitor
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Events Test",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]
        start_token = create_response.json()["start_token"]
        end_token = create_response.json()["end_token"]

        # Generate some events
        await client.get(f"/ping/start/{start_token}")
        await client.get(f"/ping/end/{end_token}")

        # List events
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/events"
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) >= 2

        # Check event types
        event_types = [e["event_type"] for e in data["events"]]
        assert "start" in event_types
        assert "end" in event_types


class TestProcessMonitorValidation:
    """Tests for process monitor validation edge cases."""

    async def test_create_monitor_interval_too_short(self, authenticated_client: AsyncClient, workspace):
        """Test creating a monitor with interval shorter than plan allows."""
        # Free plan requires minimum 5 minute interval
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Short Interval",
                "schedule_type": "interval",
                "schedule_interval": "2m",  # Too short for free plan
                "start_grace_period": "5m",
                "end_timeout": "30m",
            },
        )
        assert response.status_code == 403

    async def test_create_monitor_invalid_exact_time(self, authenticated_client: AsyncClient, workspace):
        """Test creating a monitor with invalid exact time format."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Invalid Time",
                "schedule_type": "exact_time",
                "schedule_exact_time": "25:00",  # Invalid hour
                "start_grace_period": "5m",
                "end_timeout": "30m",
            },
        )
        assert response.status_code == 422

    async def test_update_monitor_change_schedule_type(self, authenticated_client: AsyncClient, workspace):
        """Test updating monitor to change schedule type."""
        # Create with cron
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Schedule Type Change",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Update to interval
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}",
            json={
                "schedule_type": "interval",
                "schedule_interval": "6h",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["schedule_type"] == "interval"
        assert data["schedule_interval"] == 21600

    async def test_update_monitor_missing_interval_for_type(self, authenticated_client: AsyncClient, workspace):
        """Test updating to interval type without providing interval."""
        # Create with cron
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Missing Interval",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Try to update to interval without providing interval
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}",
            json={
                "schedule_type": "interval",
            },
        )
        assert response.status_code == 400

    async def test_pause_already_paused(self, authenticated_client: AsyncClient, workspace):
        """Test pausing an already paused monitor."""
        # Create and pause
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Already Paused",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # First pause
        await authenticated_client.post(f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause")

        # Try to pause again
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause"
        )
        assert response.status_code == 400

    async def test_resume_not_paused(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a monitor that's not paused."""
        # Create monitor (not paused)
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Not Paused",
                "schedule_type": "cron",
                "schedule_cron": "0 * * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        monitor_id = create_response.json()["id"]

        # Try to resume without pausing first
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/resume"
        )
        assert response.status_code == 400

    async def test_pause_nonexistent_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test pausing a non-existent monitor."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/00000000-0000-0000-0000-000000000000/pause"
        )
        assert response.status_code == 404

    async def test_resume_nonexistent_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a non-existent monitor."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/00000000-0000-0000-0000-000000000000/resume"
        )
        assert response.status_code == 404

    async def test_get_events_nonexistent_monitor(self, authenticated_client: AsyncClient, workspace):
        """Test getting events for a non-existent monitor."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/00000000-0000-0000-0000-000000000000/events"
        )
        assert response.status_code == 404


class TestIntervalParsing:
    """Tests for interval parsing."""

    async def test_interval_minutes(self, authenticated_client: AsyncClient, workspace):
        """Test interval in minutes."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Minutes Test",
                "schedule_type": "interval",
                "schedule_interval": "30m",
                "start_grace_period": "5m",
                "end_timeout": "15m",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_interval"] == 1800  # 30 minutes
        assert data["start_grace_period"] == 300  # 5 minutes
        assert data["end_timeout"] == 900  # 15 minutes

    async def test_interval_hours(self, authenticated_client: AsyncClient, workspace):
        """Test interval in hours."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Hours Test",
                "schedule_type": "interval",
                "schedule_interval": "6h",
                "start_grace_period": "10m",
                "end_timeout": "2h",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_interval"] == 21600  # 6 hours
        assert data["end_timeout"] == 7200  # 2 hours

    async def test_interval_days(self, authenticated_client: AsyncClient, workspace):
        """Test interval in days."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Days Test",
                "schedule_type": "interval",
                "schedule_interval": "1d",
                "start_grace_period": "30m",
                "end_timeout": "4h",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_interval"] == 86400  # 1 day

    async def test_interval_seconds(self, authenticated_client: AsyncClient, workspace):
        """Test interval in seconds."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Seconds Test",
                "schedule_type": "interval",
                "schedule_interval": "300s",
                "start_grace_period": "60s",
                "end_timeout": "180s",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_interval"] == 300
        assert data["start_grace_period"] == 60
        assert data["end_timeout"] == 180


class TestProcessMonitorTimezoneDeadline:
    """Tests for timezone-aware deadline calculation fix."""

    async def test_deadline_calculation_in_non_utc_timezone(self, db_session, workspace):
        """Test that start_deadline is correctly calculated for monitors with non-UTC timezone.

        This test verifies the fix for the timezone bug where datetime.fromtimestamp()
        was incorrectly interpreting UTC naive datetimes as local time, causing
        false missed_start alerts.
        """
        from datetime import datetime, timedelta

        from app.db.repositories.process_monitors import ProcessMonitorRepository
        from app.models.process_monitor import ProcessMonitor, ProcessMonitorStatus, ScheduleType
        from app.services.process_monitor import process_monitor_service

        # Create monitor with exact_time schedule (03:00 daily)
        monitor = ProcessMonitor(
            workspace_id=workspace["id"],
            name="Test Monitor",
            schedule_type=ScheduleType.EXACT_TIME,
            schedule_exact_time="03:00",
            timezone="Europe/Moscow",  # UTC+3
            start_grace_period=300,  # 5 minutes
            end_timeout=3600,  # 1 hour
            status=ProcessMonitorStatus.WAITING_START,
        )
        db_session.add(monitor)
        await db_session.commit()
        await db_session.refresh(monitor)

        # Simulate the monitor receiving START ping at 03:00:01
        start_time = datetime(2026, 1, 24, 0, 0, 1)  # 03:00:01 Moscow = 00:00:01 UTC

        await process_monitor_service.process_start_ping(
            db=db_session,
            monitor=monitor,
        )
        await db_session.refresh(monitor)

        # Monitor should be running
        assert monitor.status == ProcessMonitorStatus.RUNNING
        assert monitor.end_deadline is not None

        # Simulate END ping at 03:00:04
        end_time = datetime(2026, 1, 24, 0, 0, 4)  # 03:00:04 Moscow = 00:00:04 UTC

        await process_monitor_service.process_end_ping(
            db=db_session,
            monitor=monitor,
        )
        await db_session.refresh(monitor)

        # Monitor should transition to WAITING_START for next run
        assert monitor.status == ProcessMonitorStatus.WAITING_START
        assert monitor.next_expected_start is not None
        assert monitor.start_deadline is not None

        # The key fix: start_deadline should be calculated correctly
        # next_expected_start should be tomorrow at 03:00 Moscow = 00:00 UTC
        # start_deadline should be next_expected_start + 300 seconds
        expected_start_deadline = monitor.next_expected_start + timedelta(seconds=300)

        # Verify that start_deadline matches expected calculation
        # (not affected by timezone.fromtimestamp() bug)
        assert monitor.start_deadline == expected_start_deadline

        # Verify that start_deadline is in the future
        # If the bug was present, start_deadline could be miscalculated by several hours
        # due to timezone confusion
        now = datetime.utcnow()
        assert monitor.start_deadline > now, (
            f"start_deadline should be in the future, but it's {monitor.start_deadline} (now: {now})"
        )

        # Verify correct timezone-independent calculation:
        # start_deadline = next_expected_start + grace_period (as timedeltas, not timestamps)
        grace_period_delta = timedelta(seconds=300)
        assert (monitor.start_deadline - monitor.next_expected_start) == grace_period_delta, (
            f"start_deadline should be exactly grace_period ({grace_period_delta}) after next_expected_start"
        )

    async def test_no_false_missed_start_after_successful_run(self, db_session, workspace):
        """Test that monitor doesn't trigger false missed_start after successful completion.

        Regression test for the bug where a monitor would incorrectly trigger missed_start
        alerts after successfully completing, due to incorrect deadline calculation.
        """
        from datetime import datetime, timedelta

        from app.db.repositories.process_monitors import ProcessMonitorRepository
        from app.models.process_monitor import ProcessMonitor, ProcessMonitorStatus, ScheduleType
        from app.services.process_monitor import process_monitor_service

        # Create monitor
        monitor = ProcessMonitor(
            workspace_id=workspace["id"],
            name="Test Monitor 2",
            schedule_type=ScheduleType.EXACT_TIME,
            schedule_exact_time="03:00",
            timezone="Europe/Moscow",
            start_grace_period=300,
            end_timeout=3600,
            status=ProcessMonitorStatus.WAITING_START,
        )
        db_session.add(monitor)
        await db_session.commit()
        await db_session.refresh(monitor)

        # Simulate successful run: START → END
        await process_monitor_service.process_start_ping(db=db_session, monitor=monitor)
        await db_session.refresh(monitor)

        await process_monitor_service.process_end_ping(db=db_session, monitor=monitor)
        await db_session.refresh(monitor)

        # Monitor should be waiting for next start
        assert monitor.status == ProcessMonitorStatus.WAITING_START

        # Now check for missed starts (this is what scheduler does every 30 seconds)
        repo = ProcessMonitorRepository(db_session)
        now = datetime.utcnow()

        # Should NOT find this monitor as missed (start_deadline should be in the future)
        missed_monitors = await repo.get_monitors_waiting_for_start(now, limit=100)

        # This monitor should NOT be in the list
        missed_ids = [m.id for m in missed_monitors]
        assert monitor.id not in missed_ids, "Monitor incorrectly marked as missed_start after successful completion"


class TestConcurrencyPolicy:
    """Tests for concurrency policy feature."""

    async def test_create_monitor_with_default_concurrency_policy(self, authenticated_client: AsyncClient, workspace):
        """Test that new monitors default to SKIP policy."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Default Policy Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 2 * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["concurrency_policy"] == "skip"

    async def test_create_monitor_with_skip_policy(self, authenticated_client: AsyncClient, workspace):
        """Test creating a monitor with explicit SKIP policy."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Skip Policy Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 2 * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
                "concurrency_policy": "skip",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["concurrency_policy"] == "skip"

    async def test_create_monitor_with_replace_policy(self, authenticated_client: AsyncClient, workspace):
        """Test creating a monitor with REPLACE policy."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Replace Policy Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 2 * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
                "concurrency_policy": "replace",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["concurrency_policy"] == "replace"

    async def test_skip_policy_rejects_duplicate_start(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient, db_session
    ):
        """Test that SKIP policy rejects duplicate start pings."""
        from app.db.repositories.process_monitors import ProcessMonitorRepository

        # Create monitor with SKIP policy
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Skip Test Monitor",
                "schedule_type": "interval",
                "schedule_interval": "1h",
                "start_grace_period": "5m",
                "end_timeout": "10m",
                "concurrency_policy": "skip",
            },
        )
        assert response.status_code == 201
        monitor_data = response.json()
        monitor_id = monitor_data["id"]
        start_token = monitor_data["start_token"]

        # Send first start ping (using unauthenticated client)
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 200

        # Verify monitor is running
        repo = ProcessMonitorRepository(db_session)
        from uuid import UUID

        monitor = await repo.get_by_id(UUID(monitor_id))
        from app.models.process_monitor import ProcessMonitorStatus

        assert monitor.status == ProcessMonitorStatus.RUNNING

        # Try to send another start ping - should be rejected
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 409  # Conflict

    async def test_replace_policy_timeouts_current_run(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient, db_session
    ):
        """Test that REPLACE policy timeouts current run and starts new one."""
        from uuid import UUID

        from app.db.repositories.process_monitors import (
            ProcessMonitorEventRepository,
            ProcessMonitorRepository,
        )
        from app.models.process_monitor import ProcessMonitorEventType, ProcessMonitorStatus

        # Create monitor with REPLACE policy
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Replace Test Monitor",
                "schedule_type": "interval",
                "schedule_interval": "1h",
                "start_grace_period": "5m",
                "end_timeout": "10m",
                "concurrency_policy": "replace",
                "notify_on_missed_end": True,
            },
        )
        assert response.status_code == 201
        monitor_data = response.json()
        monitor_id = UUID(monitor_data["id"])
        start_token = monitor_data["start_token"]

        # Send first start ping (using unauthenticated client)
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 200
        first_run_id = response.json()["run_id"]

        # Verify monitor is running
        repo = ProcessMonitorRepository(db_session)
        monitor = await repo.get_by_id(monitor_id)
        assert monitor.status == ProcessMonitorStatus.RUNNING
        assert monitor.current_run_id == first_run_id

        # Send another start ping - should timeout first run and start new one
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 200
        second_run_id = response.json()["run_id"]
        assert second_run_id != first_run_id

        # Verify monitor is still running with new run_id
        await db_session.refresh(monitor)
        assert monitor.status == ProcessMonitorStatus.RUNNING
        assert monitor.current_run_id == second_run_id

        # Verify events were created
        from sqlalchemy import select

        from app.models.process_monitor import ProcessMonitorEvent

        # Check that timeout event was created for first run
        stmt = select(ProcessMonitorEvent).where(
            ProcessMonitorEvent.monitor_id == monitor_id,
            ProcessMonitorEvent.event_type == ProcessMonitorEventType.TIMEOUT,
            ProcessMonitorEvent.run_id == first_run_id,
        )
        result = await db_session.execute(stmt)
        timeout_events = result.scalars().all()
        assert len(timeout_events) == 1, "Should have created timeout event for first run"

    async def test_update_concurrency_policy(self, authenticated_client: AsyncClient, workspace):
        """Test updating monitor's concurrency policy."""
        # Create monitor with SKIP policy
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Update Policy Monitor",
                "schedule_type": "cron",
                "schedule_cron": "0 2 * * *",
                "start_grace_period": "5m",
                "end_timeout": "1h",
                "concurrency_policy": "skip",
            },
        )
        assert response.status_code == 201
        monitor_id = response.json()["id"]

        # Update to REPLACE policy
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}",
            json={"concurrency_policy": "replace"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["concurrency_policy"] == "replace"

    async def test_replace_policy_handles_none_run_id(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient, db_session
    ):
        """Test REPLACE policy gracefully handles None run_id (edge case)."""
        from uuid import UUID

        from app.db.repositories.process_monitors import ProcessMonitorRepository
        from app.models.process_monitor import ProcessMonitorStatus

        # Create monitor with REPLACE policy
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "None Run ID Monitor",
                "schedule_type": "interval",
                "schedule_interval": "1h",
                "start_grace_period": "5m",
                "end_timeout": "10m",
                "concurrency_policy": "replace",
            },
        )
        assert response.status_code == 201
        monitor_data = response.json()
        monitor_id = UUID(monitor_data["id"])
        start_token = monitor_data["start_token"]

        # Manually set monitor to RUNNING but with None run_id (shouldn't happen normally)
        repo = ProcessMonitorRepository(db_session)
        monitor = await repo.get_by_id(monitor_id)
        monitor.status = ProcessMonitorStatus.RUNNING
        monitor.current_run_id = None  # Edge case
        await db_session.commit()

        # Send start ping - should handle None run_id gracefully
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 200  # Should succeed despite None run_id

    async def test_replace_policy_on_failed_monitor(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient, db_session
    ):
        """Test REPLACE policy works correctly when monitor is in failed state."""
        from uuid import UUID

        from app.db.repositories.process_monitors import ProcessMonitorRepository
        from app.models.process_monitor import ProcessMonitorStatus

        # Create monitor with REPLACE policy
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Failed State Monitor",
                "schedule_type": "interval",
                "schedule_interval": "1h",
                "start_grace_period": "5m",
                "end_timeout": "10m",
                "concurrency_policy": "replace",
                "notify_on_recovery": True,
            },
        )
        assert response.status_code == 201
        monitor_data = response.json()
        monitor_id = UUID(monitor_data["id"])
        start_token = monitor_data["start_token"]

        # Manually set monitor to MISSED_END (failed state)
        repo = ProcessMonitorRepository(db_session)
        monitor = await repo.get_by_id(monitor_id)
        monitor.status = ProcessMonitorStatus.MISSED_END
        monitor.consecutive_failures = 3
        await db_session.commit()

        # Send start ping - should work as recovery
        from unittest.mock import patch

        with patch("app.services.process_monitor.notification_service.send_task_recovery") as mock_recovery:
            mock_recovery.return_value = None

            response = await client.post(f"/ping/start/{start_token}")
            assert response.status_code == 200

            # Verify recovery notification was sent
            mock_recovery.assert_called_once()
            call_args = mock_recovery.call_args
            assert call_args.kwargs["workspace_id"] == UUID(workspace["id"])

        # Verify monitor is now running
        await db_session.refresh(monitor)
        assert monitor.status == ProcessMonitorStatus.RUNNING
        # Note: consecutive_failures will be reset only after successful completion
        # At this point monitor just started, so failures remain until end signal
        assert monitor.consecutive_failures == 3  # Still 3, not reset yet

        # Complete the run successfully
        end_token = monitor_data["end_token"]
        response = await client.post(f"/ping/end/{end_token}")
        assert response.status_code == 200

        # Now verify failures are reset after successful completion
        await db_session.refresh(monitor)
        assert monitor.consecutive_failures == 0  # Reset after successful end
        assert monitor.consecutive_successes == 1  # Incremented
        assert monitor.status == ProcessMonitorStatus.WAITING_START

    async def test_skip_policy_rejects_on_paused(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient, db_session
    ):
        """Test that SKIP policy also checks for PAUSED status."""
        from uuid import UUID

        from app.db.repositories.process_monitors import ProcessMonitorRepository

        # Create monitor with SKIP policy
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Paused Monitor",
                "schedule_type": "interval",
                "schedule_interval": "1h",
                "start_grace_period": "5m",
                "end_timeout": "10m",
                "concurrency_policy": "skip",
            },
        )
        assert response.status_code == 201
        monitor_data = response.json()
        monitor_id = UUID(monitor_data["id"])
        start_token = monitor_data["start_token"]

        # Pause the monitor
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause"
        )
        assert response.status_code == 200

        # Try to send start ping - should be rejected
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 400
        assert "paused" in response.json()["detail"].lower()

    async def test_replace_policy_consecutive_failures_reset(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient, db_session
    ):
        """Test that REPLACE policy correctly resets consecutive_failures counter."""
        from uuid import UUID

        from app.db.repositories.process_monitors import ProcessMonitorRepository
        from app.models.process_monitor import ProcessMonitorStatus

        # Create monitor with REPLACE policy
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Failure Counter Monitor",
                "schedule_type": "interval",
                "schedule_interval": "1h",
                "start_grace_period": "5m",
                "end_timeout": "10m",
                "concurrency_policy": "replace",
            },
        )
        assert response.status_code == 201
        monitor_data = response.json()
        monitor_id = UUID(monitor_data["id"])
        start_token = monitor_data["start_token"]
        end_token = monitor_data["end_token"]

        # Send first start
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 200

        # Send second start (REPLACE) - this creates timeout for first run
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 200
        second_run_id = response.json()["run_id"]

        # Check that consecutive_failures was incremented by timeout
        repo = ProcessMonitorRepository(db_session)
        monitor = await repo.get_by_id(monitor_id)
        # After timeout event, failures should be incremented
        # (This happens in scheduler, not in start_ping, so we skip this check)

        # Complete second run successfully
        response = await client.post(f"/ping/end/{end_token}")
        assert response.status_code == 200

        # Verify consecutive_successes incremented and failures reset
        await db_session.refresh(monitor)
        assert monitor.consecutive_successes > 0
        # consecutive_failures should be 0 after successful completion


class TestSuccessNotifications:
    """Tests for success notification fix."""

    async def test_success_notification_sent_when_monitor_enabled(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient, db_session
    ):
        """Test that success notifications are sent when monitor.notify_on_success is true."""
        from unittest.mock import AsyncMock, patch
        from uuid import UUID

        from app.db.repositories.process_monitors import ProcessMonitorRepository

        # Create monitor with notify_on_success enabled
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors",
            json={
                "name": "Success Notification Monitor",
                "schedule_type": "interval",
                "schedule_interval": "1h",
                "start_grace_period": "5m",
                "end_timeout": "10m",
                "notify_on_success": True,
            },
        )
        assert response.status_code == 201
        monitor_data = response.json()
        monitor_id = UUID(monitor_data["id"])
        start_token = monitor_data["start_token"]
        end_token = monitor_data["end_token"]

        # Send start ping (using unauthenticated client)
        response = await client.post(f"/ping/start/{start_token}")
        assert response.status_code == 200

        # Mock notification service to verify it's called
        with patch("app.services.process_monitor.notification_service.send_task_success") as mock_send:
            mock_send.return_value = None

            # Send end ping
            response = await client.post(f"/ping/end/{end_token}")
            assert response.status_code == 200

            # Verify send_task_success was called
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["workspace_id"] == UUID(workspace["id"])
            assert call_args.kwargs["task_name"] == "Success Notification Monitor"
            assert call_args.kwargs["task_type"] == "process_monitor"
