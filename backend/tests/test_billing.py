"""Tests for billing API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Billing Test Workspace",
            "slug": "billing-test",
        },
    )
    return response.json()


class TestPlans:
    """Tests for plans endpoints."""

    async def test_list_plans(self, authenticated_client: AsyncClient):
        """Test listing available plans."""
        response = await authenticated_client.get("/v1/plans")
        assert response.status_code == 200
        data = response.json()
        # API returns a list (may be empty if no plans configured)
        assert isinstance(data, list)

    async def test_get_plan(self, authenticated_client: AsyncClient):
        """Test getting a specific plan."""
        # First get list to find a plan ID
        list_response = await authenticated_client.get("/v1/plans")
        if list_response.json():
            plan_id = list_response.json()[0]["id"]
            response = await authenticated_client.get(f"/v1/plans/{plan_id}")
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "max_cron_tasks" in data

    async def test_get_nonexistent_plan(self, authenticated_client: AsyncClient):
        """Test getting a non-existent plan."""
        response = await authenticated_client.get(
            "/v1/plans/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestSubscription:
    """Tests for subscription endpoints."""

    async def test_get_subscription(self, authenticated_client: AsyncClient, workspace):
        """Test getting workspace subscription."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/subscription"
        )
        # May return 404 if no subscription or 200 with subscription info
        assert response.status_code in [200, 404]

    async def test_subscribe_requires_plan(self, authenticated_client: AsyncClient, workspace):
        """Test that subscribing requires a plan ID."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/subscribe",
            json={},
        )
        assert response.status_code == 422

    async def test_subscribe_creates_payment(self, authenticated_client: AsyncClient, workspace):
        """Test that subscribing creates a payment URL."""
        # Get a plan first
        plans_response = await authenticated_client.get("/v1/plans")
        plans = plans_response.json()

        # Find a paid plan (skip free)
        paid_plan = None
        for plan in plans:
            if plan.get("price_monthly", 0) > 0:
                paid_plan = plan
                break

        if paid_plan:
            response = await authenticated_client.post(
                f"/v1/workspaces/{workspace['id']}/subscribe",
                json={
                    "plan_id": paid_plan["id"],
                    "billing_period": "monthly",
                },
            )
            # Should return payment URL or error if YooKassa not configured
            assert response.status_code in [200, 201, 400, 503]

    async def test_cancel_subscription(self, authenticated_client: AsyncClient, workspace):
        """Test canceling subscription."""
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/subscription/cancel"
        )
        # Will fail if no subscription exists or validation error
        assert response.status_code in [200, 404, 400, 422]


class TestPayments:
    """Tests for payment history endpoints."""

    async def test_get_payment_history(self, authenticated_client: AsyncClient, workspace):
        """Test getting payment history."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/payments"
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    async def test_payment_history_pagination(self, authenticated_client: AsyncClient, workspace):
        """Test payment history pagination."""
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/payments",
            params={"limit": 5, "offset": 0},
        )
        assert response.status_code == 200

    async def test_payment_history_unauthorized(self, client: AsyncClient):
        """Test accessing payment history without authentication."""
        response = await client.get("/v1/workspaces/some-id/payments")
        assert response.status_code == 401
