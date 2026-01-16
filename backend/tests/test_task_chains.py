"""Tests for task chains API."""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Chain Test Workspace",
            "slug": "chain-test",
        },
    )
    return response.json()


class TestTaskChains:
    """Tests for task chain CRUD operations."""

    async def test_create_chain(self, authenticated_client: AsyncClient, workspace):
        """Test creating a task chain."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Test Chain",
                "description": "A test chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Chain"
        assert data["description"] == "A test chain"
        assert data["trigger_type"] == "manual"
        assert data["is_active"] is True
        assert len(data["steps"]) == 1

    async def test_create_chain_with_cron_trigger(self, authenticated_client: AsyncClient, workspace):
        """Test creating a chain with cron trigger."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Cron Chain",
                "trigger_type": "cron",
                "schedule": "0 * * * *",
                "timezone": "Europe/Moscow",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "POST",
                    }
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["trigger_type"] == "cron"
        assert data["schedule"] == "0 * * * *"
        assert data["next_run_at"] is not None

    async def test_create_chain_with_delayed_trigger(self, authenticated_client: AsyncClient, workspace):
        """Test creating a chain with delayed trigger."""
        execute_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Delayed Chain",
                "trigger_type": "delayed",
                "execute_at": execute_at,
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["trigger_type"] == "delayed"
        assert data["execute_at"] is not None

    async def test_create_chain_with_multiple_steps(self, authenticated_client: AsyncClient, workspace):
        """Test creating a chain with multiple steps."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Multi-Step Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Get Token",
                        "url": "https://example.com/api/auth",
                        "method": "POST",
                        "headers": {"Content-Type": "application/json"},
                        "body": '{"user": "test"}',
                        "extract_variables": {"token": "$.access_token"},
                    },
                    {
                        "name": "Use Token",
                        "url": "https://example.com/api/data",
                        "method": "GET",
                        "headers": {"Authorization": "Bearer {{token}}"},
                    },
                ],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["steps"]) == 2
        assert data["steps"][0]["name"] == "Get Token"
        assert data["steps"][1]["name"] == "Use Token"

    async def test_create_chain_invalid_cron_schedule(self, authenticated_client: AsyncClient, workspace):
        """Test creating a chain with invalid cron schedule."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Invalid Chain",
                "trigger_type": "cron",
                "schedule": "invalid cron",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        assert response.status_code == 422

    async def test_create_chain_no_steps(self, authenticated_client: AsyncClient, workspace):
        """Test creating a chain without steps."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Empty Chain",
                "trigger_type": "manual",
                "steps": [],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["steps"]) == 0

    async def test_list_chains(self, authenticated_client: AsyncClient, workspace):
        """Test listing chains."""
        # Create a chain first
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "List Test Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )

        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/chains"
        )
        assert response.status_code == 200
        data = response.json()
        assert "chains" in data
        assert len(data["chains"]) >= 1

    async def test_get_chain(self, authenticated_client: AsyncClient, workspace):
        """Test getting a specific chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Get Test Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Get chain
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chain_id
        assert data["name"] == "Get Test Chain"

    async def test_update_chain(self, authenticated_client: AsyncClient, workspace):
        """Test updating a chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Update Test Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Update chain
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}",
            json={
                "name": "Updated Chain Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Chain Name"
        assert data["description"] == "Updated description"

    async def test_pause_chain(self, authenticated_client: AsyncClient, workspace):
        """Test pausing a chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Pause Test Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Pause chain
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/pause"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is True

    async def test_resume_chain(self, authenticated_client: AsyncClient, workspace):
        """Test resuming a paused chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Resume Test Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Pause then resume
        await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/pause"
        )
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/resume"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is False

    async def test_delete_chain(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Delete Test Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Delete chain
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}"
        )
        assert response.status_code == 204

        # Verify deleted
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}"
        )
        assert get_response.status_code == 404

    async def test_run_chain(self, authenticated_client: AsyncClient, workspace):
        """Test manually running a chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Run Test Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://httpbin.org/post",
                        "method": "POST",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Run chain
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/run"
        )
        assert response.status_code == 202

    async def test_run_inactive_chain(self, authenticated_client: AsyncClient, workspace):
        """Test running an inactive chain fails."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Inactive Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Deactivate chain
        await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}",
            json={"is_active": False},
        )

        # Try to run
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/run"
        )
        assert response.status_code == 400

    async def test_run_chain_without_steps(self, authenticated_client: AsyncClient, workspace):
        """Test running a chain without steps fails."""
        # Create chain without steps
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Empty Chain",
                "trigger_type": "manual",
                "steps": [],
            },
        )
        chain_id = create_response.json()["id"]

        # Try to run
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/run"
        )
        assert response.status_code == 400

    async def test_copy_chain(self, authenticated_client: AsyncClient, workspace):
        """Test copying a chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Original Chain",
                "description": "Original description",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Copy chain
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/copy"
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Original Chain (copy)"
        assert data["id"] != chain_id
        assert len(data["steps"]) == 1

    async def test_get_nonexistent_chain(self, authenticated_client: AsyncClient, workspace):
        """Test getting a non-existent chain."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/chains/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_update_nonexistent_chain(self, authenticated_client: AsyncClient, workspace):
        """Test updating a non-existent chain."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/chains/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 404

    async def test_delete_nonexistent_chain(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a non-existent chain."""
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/chains/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestChainSteps:
    """Tests for chain step operations."""

    async def test_add_step_to_chain(self, authenticated_client: AsyncClient, workspace):
        """Test adding a step to an existing chain."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Chain for Steps",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # Add step
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/steps",
            json={
                "name": "Step 2",
                "url": "https://example.com/api/step2",
                "method": "POST",
                "step_order": 1,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Step 2"

    async def test_update_step(self, authenticated_client: AsyncClient, workspace):
        """Test updating a chain step."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Chain for Step Update",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Original Step",
                        "url": "https://example.com/api/original",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]
        step_id = create_response.json()["steps"][0]["id"]

        # Update step
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/steps/{step_id}",
            json={
                "name": "Updated Step",
                "url": "https://example.com/api/updated",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Step"
        assert data["url"] == "https://example.com/api/updated"

    async def test_delete_step(self, authenticated_client: AsyncClient, workspace):
        """Test deleting a chain step."""
        # Create chain with two steps
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Chain for Step Delete",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api/step1",
                        "method": "GET",
                    },
                    {
                        "name": "Step 2",
                        "url": "https://example.com/api/step2",
                        "method": "GET",
                    },
                ],
            },
        )
        chain_id = create_response.json()["id"]
        step_id = create_response.json()["steps"][0]["id"]

        # Delete step
        response = await authenticated_client.delete(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/steps/{step_id}"
        )
        assert response.status_code == 204

        # Verify chain has one step
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}"
        )
        assert len(get_response.json()["steps"]) == 1

    async def test_reorder_steps(self, authenticated_client: AsyncClient, workspace):
        """Test reordering chain steps."""
        # Create chain with multiple steps
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Chain for Reorder",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step A",
                        "url": "https://example.com/api/a",
                        "method": "GET",
                    },
                    {
                        "name": "Step B",
                        "url": "https://example.com/api/b",
                        "method": "GET",
                    },
                    {
                        "name": "Step C",
                        "url": "https://example.com/api/c",
                        "method": "GET",
                    },
                ],
            },
        )
        chain_id = create_response.json()["id"]
        steps = create_response.json()["steps"]
        step_ids = [s["id"] for s in steps]

        # Reorder: C, A, B (new orders: 0, 1, 2)
        # Format: {step_id: new_order}
        response = await authenticated_client.put(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/steps/reorder",
            json={
                "step_orders": [
                    {step_ids[2]: 0},  # C -> 0
                    {step_ids[0]: 1},  # A -> 1
                    {step_ids[1]: 2},  # B -> 2
                ],
            },
        )
        assert response.status_code == 200

        # Verify order
        get_response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}"
        )
        reordered_steps = get_response.json()["steps"]
        assert reordered_steps[0]["name"] == "Step C"
        assert reordered_steps[1]["name"] == "Step A"
        assert reordered_steps[2]["name"] == "Step B"


class TestChainPlanLimits:
    """Tests for plan limit enforcement."""

    async def test_chain_limit_exceeded(self, authenticated_client: AsyncClient, workspace):
        """Test that chain limit is enforced."""
        # Free plan allows 3 chains - create 3
        for i in range(3):
            response = await authenticated_client.post(
                f"/v1/workspaces/{workspace['id']}/chains",
                json={
                    "name": f"Chain {i}",
                    "trigger_type": "manual",
                    "steps": [
                        {
                            "name": "Step 1",
                            "url": "https://example.com/api",
                            "method": "GET",
                        }
                    ],
                },
            )
            assert response.status_code == 201

        # 4th chain should fail
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Chain 4",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api",
                        "method": "GET",
                    }
                ],
            },
        )
        assert response.status_code == 403
        assert "limit" in response.json()["detail"].lower()

    async def test_step_limit_exceeded(self, authenticated_client: AsyncClient, workspace):
        """Test that step limit per chain is enforced."""
        # Free plan allows 5 steps - try to create chain with 6 steps
        steps = [
            {
                "name": f"Step {i}",
                "url": "https://example.com/api",
                "method": "GET",
            }
            for i in range(6)
        ]
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Chain with too many steps",
                "trigger_type": "manual",
                "steps": steps,
            },
        )
        assert response.status_code == 403
        assert "step" in response.json()["detail"].lower()

    async def test_cron_interval_too_frequent(self, authenticated_client: AsyncClient, workspace):
        """Test that cron interval limit is enforced."""
        # Free plan requires min 5 minutes - try every minute
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Frequent Chain",
                "trigger_type": "cron",
                "schedule": "* * * * *",  # Every minute
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://example.com/api",
                        "method": "GET",
                    }
                ],
            },
        )
        assert response.status_code == 403
        assert "interval" in response.json()["detail"].lower()


class TestChainRateLimiting:
    """Tests for manual run rate limiting."""

    async def test_run_rate_limit(self, authenticated_client: AsyncClient, workspace):
        """Test that manual runs respect rate limit."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Rate Limited Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://httpbin.org/post",
                        "method": "POST",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # First run - may succeed (202) or fail if Redis not available (503)
        response1 = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/run"
        )

        if response1.status_code == 503:
            # Redis/arq not available in test env, skip rate limit test
            import pytest
            pytest.skip("Redis/arq worker not available for rate limit test")

        assert response1.status_code == 202

        # Immediate second run should fail (rate limited)
        response2 = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/run"
        )
        assert response2.status_code == 429
        assert "interval" in response2.json()["detail"].lower()


class TestChainExecutions:
    """Tests for chain execution history."""

    async def test_list_chain_executions(self, authenticated_client: AsyncClient, workspace):
        """Test listing chain executions."""
        # Create chain
        create_response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/chains",
            json={
                "name": "Execution History Chain",
                "trigger_type": "manual",
                "steps": [
                    {
                        "name": "Step 1",
                        "url": "https://httpbin.org/get",
                        "method": "GET",
                    }
                ],
            },
        )
        chain_id = create_response.json()["id"]

        # List executions (may be empty)
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/chains/{chain_id}/executions"
        )
        assert response.status_code == 200
        data = response.json()
        assert "executions" in data
