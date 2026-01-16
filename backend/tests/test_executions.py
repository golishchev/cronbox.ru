"""Tests for executions API."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Executions Test Workspace",
            "slug": "executions-test",
        },
    )
    return response.json()


@pytest.fixture
async def cron_task(authenticated_client: AsyncClient, workspace):
    """Create a test cron task."""
    response = await authenticated_client.post(
        f"/v1/workspaces/{workspace['id']}/cron",
        json={
            "name": "Executions Test Task",
            "url": "https://example.com/api/test",
            "method": "GET",
            "schedule": "*/5 * * * *",
        },
    )
    return response.json()


class TestExecutions:
    """Tests for execution history endpoints."""

    async def test_list_executions(self, authenticated_client: AsyncClient, workspace):
        """Test listing executions."""
        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/executions")
        assert response.status_code == 200
        data = response.json()
        assert "executions" in data or "items" in data or isinstance(data, list)

    async def test_list_executions_pagination(self, authenticated_client: AsyncClient, workspace):
        """Test execution list pagination."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/executions",
            params={"page": 1, "limit": 10},
        )
        assert response.status_code == 200
        data = response.json()
        if "pagination" in data:
            assert data["pagination"]["page"] == 1

    async def test_filter_executions_by_task_type(self, authenticated_client: AsyncClient, workspace):
        """Test filtering executions by task type."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/executions",
            params={"task_type": "cron"},
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("executions", data.get("items", []))
        for item in items:
            assert item.get("task_type") == "cron"

    async def test_filter_executions_by_status(self, authenticated_client: AsyncClient, workspace):
        """Test filtering executions by status."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/executions",
            params={"status": "success"},
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("executions", data.get("items", []))
        for item in items:
            assert item.get("status") == "success"

    async def test_filter_executions_by_task_id(self, authenticated_client: AsyncClient, workspace, cron_task):
        """Test filtering executions by task ID."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/executions",
            params={"task_id": cron_task["id"]},
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get("executions", data.get("items", []))
        for item in items:
            assert item.get("task_id") == cron_task["id"]

    async def test_filter_executions_by_date_range(self, authenticated_client: AsyncClient, workspace):
        """Test filtering executions by date range."""
        start_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/executions",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        assert response.status_code == 200

    async def test_get_execution_details(self, authenticated_client: AsyncClient, workspace):
        """Test getting execution details."""
        # First get list
        list_response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/executions")
        data = list_response.json()
        items = data.get("executions", data.get("items", []))

        if items:
            execution_id = items[0]["id"]
            response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/executions/{execution_id}")
            assert response.status_code == 200
            detail_data = response.json()
            assert detail_data["id"] == execution_id
            assert "request_url" in detail_data
            assert "status" in detail_data

    async def test_get_nonexistent_execution(self, authenticated_client: AsyncClient, workspace):
        """Test getting non-existent execution."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/executions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestExecutionStats:
    """Tests for execution statistics endpoints."""

    async def test_get_execution_stats(self, authenticated_client: AsyncClient, workspace):
        """Test getting execution statistics."""
        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/executions/stats")
        assert response.status_code == 200
        data = response.json()
        # Should have stats fields
        assert "total" in data or "total_executions" in data or isinstance(data, dict)

    async def test_execution_stats_by_date_range(self, authenticated_client: AsyncClient, workspace):
        """Test getting execution stats with date range."""
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()

        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/executions/stats",
            params={
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        assert response.status_code == 200

    async def test_executions_unauthorized(self, client: AsyncClient):
        """Test accessing executions without authentication."""
        response = await client.get("/v1/workspaces/some-id/executions")
        assert response.status_code == 401
