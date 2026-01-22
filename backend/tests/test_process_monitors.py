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
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}"
        )
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
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause"
        )
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
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}"
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}"
        )
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
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors?limit=2"
        )
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
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}"
        )
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
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause"
        )

        # Try to ping
        response = await client.get(f"/ping/start/{start_token}")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data  # FastAPI returns {"detail": "..."} for HTTPExceptions

    async def test_start_ping_updates_status(
        self, authenticated_client: AsyncClient, workspace, client: AsyncClient
    ):
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
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}"
        )
        assert get_response.json()["status"] == "waiting_start"

        # Send start ping
        await client.get(f"/ping/start/{start_token}")

        # Status should be running
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}"
        )
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

    async def test_update_monitor_change_schedule_type(
        self, authenticated_client: AsyncClient, workspace
    ):
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

    async def test_update_monitor_missing_interval_for_type(
        self, authenticated_client: AsyncClient, workspace
    ):
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
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/process-monitors/{monitor_id}/pause"
        )

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
