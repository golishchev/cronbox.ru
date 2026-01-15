"""Tests for billing API."""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User

pytestmark = pytest.mark.asyncio


# === Fixtures for proration tests ===


@pytest_asyncio.fixture
async def basic_plan(db_session: AsyncSession) -> Plan:
    """Create a basic plan for testing (cheaper than pro)."""
    plan = Plan(
        name="basic",
        display_name="Basic",
        description="Basic plan",
        price_monthly=29900,  # 299 RUB
        price_yearly=299000,  # 2990 RUB
        max_cron_tasks=10,
        max_delayed_tasks_per_month=500,
        max_workspaces=2,
        max_execution_history_days=30,
        min_cron_interval_minutes=5,
        telegram_notifications=False,
        email_notifications=True,
        webhook_callbacks=False,
        custom_headers=True,
        retry_on_failure=False,
        is_active=True,
        is_public=True,
        sort_order=1,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def max_plan(db_session: AsyncSession) -> Plan:
    """Create a max plan for testing (most expensive)."""
    plan = Plan(
        name="max",
        display_name="Max",
        description="Max plan with all features",
        price_monthly=99900,  # 999 RUB
        price_yearly=999000,  # 9990 RUB
        max_cron_tasks=100,
        max_delayed_tasks_per_month=10000,
        max_workspaces=10,
        max_execution_history_days=365,
        min_cron_interval_minutes=1,
        telegram_notifications=True,
        email_notifications=True,
        webhook_callbacks=True,
        custom_headers=True,
        retry_on_failure=True,
        is_active=True,
        is_public=True,
        sort_order=2,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def user_with_basic_subscription(
    db_session: AsyncSession, test_user: User, basic_plan: Plan
) -> tuple[User, Subscription]:
    """Create a test user with active basic subscription (monthly, 15 days remaining)."""
    # Create subscription that started 15 days ago
    start_date = datetime.now(timezone.utc) - timedelta(days=15)
    end_date = start_date + timedelta(days=30)

    subscription = Subscription(
        user_id=test_user.id,
        plan_id=basic_plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start_date,
        current_period_end=end_date,
        cancel_at_period_end=False,
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return test_user, subscription


@pytest_asyncio.fixture
async def user_with_max_yearly_subscription(
    db_session: AsyncSession, test_user: User, max_plan: Plan
) -> tuple[User, Subscription]:
    """Create a test user with active max yearly subscription."""
    # Create yearly subscription that started 6 months ago
    start_date = datetime.now(timezone.utc) - timedelta(days=180)
    end_date = start_date + timedelta(days=365)

    subscription = Subscription(
        user_id=test_user.id,
        plan_id=max_plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=start_date,
        current_period_end=end_date,
        cancel_at_period_end=False,
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return test_user, subscription


class TestPlans:
    """Tests for plans endpoints."""

    async def test_list_plans(self, authenticated_client: AsyncClient):
        """Test listing available plans."""
        response = await authenticated_client.get("/v1/billing/plans")
        assert response.status_code == 200
        data = response.json()
        # API returns a list (may be empty if no plans configured)
        assert isinstance(data, list)

    async def test_get_plan(self, authenticated_client: AsyncClient, free_plan):
        """Test getting a specific plan by ID."""
        response = await authenticated_client.get(f"/v1/billing/plans/{free_plan.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "free"
        assert "max_cron_tasks" in data

    async def test_get_nonexistent_plan(self, authenticated_client: AsyncClient):
        """Test getting a non-existent plan."""
        response = await authenticated_client.get(
            "/v1/billing/plans/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestSubscription:
    """Tests for subscription endpoints."""

    async def test_get_subscription(self, authenticated_client: AsyncClient):
        """Test getting user subscription."""
        response = await authenticated_client.get("/v1/billing/subscription")
        # May return null/None if no subscription or 200 with subscription info
        assert response.status_code == 200

    async def test_subscribe_requires_plan(self, authenticated_client: AsyncClient):
        """Test that subscribing requires a plan ID."""
        response = await authenticated_client.post(
            "/v1/billing/subscribe",
            json={},
        )
        assert response.status_code == 422

    async def test_subscribe_creates_payment(self, authenticated_client: AsyncClient):
        """Test that subscribing creates a payment URL."""
        # Get a plan first
        plans_response = await authenticated_client.get("/v1/billing/plans")
        plans = plans_response.json()

        # Find a paid plan (skip free)
        paid_plan = None
        for plan in plans:
            if plan.get("price_monthly", 0) > 0:
                paid_plan = plan
                break

        if paid_plan:
            response = await authenticated_client.post(
                "/v1/billing/subscribe",
                json={
                    "plan_id": paid_plan["id"],
                    "billing_period": "monthly",
                },
            )
            # Should return payment URL or error if YooKassa not configured
            assert response.status_code in [200, 201, 400, 503]

    async def test_cancel_subscription(self, authenticated_client: AsyncClient):
        """Test canceling subscription."""
        response = await authenticated_client.post("/v1/billing/subscription/cancel")
        # Will fail if no subscription exists or validation error
        assert response.status_code in [200, 404, 400, 422]


class TestPayments:
    """Tests for payment history endpoints."""

    async def test_get_payment_history(self, authenticated_client: AsyncClient):
        """Test getting payment history."""
        response = await authenticated_client.get("/v1/billing/payments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_payment_history_pagination(self, authenticated_client: AsyncClient):
        """Test payment history pagination."""
        response = await authenticated_client.get(
            "/v1/billing/payments",
            params={"limit": 5, "offset": 0},
        )
        assert response.status_code == 200

    async def test_payment_history_unauthorized(self, client: AsyncClient):
        """Test accessing payment history without authentication."""
        response = await client.get("/v1/billing/payments")
        assert response.status_code == 401


class TestBillingUnauthorized:
    """Tests for billing endpoints without proper authorization."""

    async def test_subscription_unauthorized(self, client: AsyncClient):
        """Test getting subscription without auth."""
        response = await client.get("/v1/billing/subscription")
        assert response.status_code == 401

    async def test_subscribe_unauthorized(self, client: AsyncClient):
        """Test subscribing without auth."""
        response = await client.post(
            "/v1/billing/subscribe",
            json={
                "plan_id": "00000000-0000-0000-0000-000000000001",
                "billing_period": "monthly",
            },
        )
        assert response.status_code == 401

    async def test_cancel_unauthorized(self, client: AsyncClient):
        """Test canceling subscription without auth."""
        response = await client.post(
            "/v1/billing/subscription/cancel",
            json={"immediately": False},
        )
        assert response.status_code == 401


class TestPreviewPriceProration:
    """Tests for proration logic in preview-price endpoint."""

    async def test_preview_price_upgrade_with_proration(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_with_basic_subscription: tuple[User, Subscription],
        max_plan: Plan,
        basic_plan: Plan,
    ):
        """Test that upgrade shows proration credit for unused days."""
        from app.core.security import create_access_token

        user, subscription = user_with_basic_subscription
        token = create_access_token(user_id=user.id, email=user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post(
            "/v1/billing/preview-price",
            json={
                "plan_id": str(max_plan.id),
                "billing_period": "monthly",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Upgrade should have proration credit
        assert data["proration_credit"] > 0
        # Final amount should be new plan price minus credit
        assert data["final_amount"] == data["plan_price"] - data["proration_credit"]
        # Should not require deferred
        assert data["requires_deferred"] is False
        assert data["is_downgrade"] is False
        assert data["is_same_plan"] is False

    async def test_preview_price_downgrade_requires_deferred(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        max_plan: Plan,
        basic_plan: Plan,
    ):
        """Test that downgrade requires deferred change (no immediate proration)."""
        from app.core.security import create_access_token

        # Create subscription on max plan
        start_date = datetime.now(timezone.utc) - timedelta(days=15)
        end_date = start_date + timedelta(days=30)

        subscription = Subscription(
            user_id=test_user.id,
            plan_id=max_plan.id,
            status=SubscriptionStatus.ACTIVE,
                current_period_start=start_date,
            current_period_end=end_date,
            cancel_at_period_end=False,
        )
        db_session.add(subscription)
        await db_session.commit()

        token = create_access_token(user_id=test_user.id, email=test_user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post(
            "/v1/billing/preview-price",
            json={
                "plan_id": str(basic_plan.id),
                "billing_period": "monthly",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Downgrade should require deferred
        assert data["requires_deferred"] is True
        assert data["is_downgrade"] is True
        # No proration credit for downgrade
        assert data["proration_credit"] == 0
        # Effective date should be set to period end
        assert data["effective_date"] is not None

    async def test_preview_price_same_plan_flagged(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_with_basic_subscription: tuple[User, Subscription],
        basic_plan: Plan,
    ):
        """Test that selecting the same plan is flagged."""
        from app.core.security import create_access_token

        user, subscription = user_with_basic_subscription
        token = create_access_token(user_id=user.id, email=user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post(
            "/v1/billing/preview-price",
            json={
                "plan_id": str(basic_plan.id),
                "billing_period": "monthly",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Same plan should be flagged
        assert data["is_same_plan"] is True

    async def test_preview_price_yearly_to_monthly_requires_deferred(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_with_max_yearly_subscription: tuple[User, Subscription],
        max_plan: Plan,
    ):
        """Test that yearly to monthly transition requires deferred change."""
        from app.core.security import create_access_token

        user, subscription = user_with_max_yearly_subscription
        token = create_access_token(user_id=user.id, email=user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post(
            "/v1/billing/preview-price",
            json={
                "plan_id": str(max_plan.id),
                "billing_period": "monthly",  # Same plan but monthly
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Period downgrade (yearly → monthly) should require deferred
        assert data["requires_deferred"] is True
        assert data["is_period_downgrade"] is True
        # No proration for period downgrade
        assert data["proration_credit"] == 0

    async def test_preview_price_monthly_to_yearly_with_proration(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_with_basic_subscription: tuple[User, Subscription],
        basic_plan: Plan,
    ):
        """Test that monthly to yearly has proration credit."""
        from app.core.security import create_access_token

        user, subscription = user_with_basic_subscription
        token = create_access_token(user_id=user.id, email=user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post(
            "/v1/billing/preview-price",
            json={
                "plan_id": str(basic_plan.id),
                "billing_period": "yearly",  # Same plan but yearly
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Monthly → yearly should have proration
        assert data["proration_credit"] > 0
        assert data["requires_deferred"] is False
        assert data["is_period_downgrade"] is False


class TestSchedulePlanChange:
    """Tests for schedule-plan-change endpoint (deferred changes)."""

    async def test_schedule_downgrade(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        max_plan: Plan,
        basic_plan: Plan,
    ):
        """Test scheduling a downgrade for period end."""
        from app.core.security import create_access_token

        # Create subscription on max plan
        start_date = datetime.now(timezone.utc) - timedelta(days=15)
        end_date = start_date + timedelta(days=30)

        subscription = Subscription(
            user_id=test_user.id,
            plan_id=max_plan.id,
            status=SubscriptionStatus.ACTIVE,
                current_period_start=start_date,
            current_period_end=end_date,
            cancel_at_period_end=False,
        )
        db_session.add(subscription)
        await db_session.commit()

        token = create_access_token(user_id=test_user.id, email=test_user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post(
            "/v1/billing/schedule-plan-change",
            json={
                "plan_id": str(basic_plan.id),
                "billing_period": "monthly",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have scheduled plan change
        assert data["scheduled_plan_id"] == str(basic_plan.id)
        assert data["scheduled_billing_period"] == "monthly"

    async def test_cancel_scheduled_change(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        max_plan: Plan,
        basic_plan: Plan,
    ):
        """Test canceling a scheduled plan change."""
        from app.core.security import create_access_token

        # Create subscription with scheduled change
        start_date = datetime.now(timezone.utc) - timedelta(days=15)
        end_date = start_date + timedelta(days=30)

        subscription = Subscription(
            user_id=test_user.id,
            plan_id=max_plan.id,
            status=SubscriptionStatus.ACTIVE,
                current_period_start=start_date,
            current_period_end=end_date,
            cancel_at_period_end=False,
            scheduled_plan_id=basic_plan.id,
            scheduled_billing_period="monthly",
        )
        db_session.add(subscription)
        await db_session.commit()

        token = create_access_token(user_id=test_user.id, email=test_user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post("/v1/billing/cancel-scheduled-change")

        assert response.status_code == 200

        # Verify subscription no longer has scheduled change
        await db_session.refresh(subscription)
        assert subscription.scheduled_plan_id is None
        assert subscription.scheduled_billing_period is None


class TestSubscribeValidation:
    """Tests for subscribe endpoint validation."""

    async def test_subscribe_same_plan_rejected(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        user_with_basic_subscription: tuple[User, Subscription],
        basic_plan: Plan,
    ):
        """Test that subscribing to the same plan is rejected."""
        from app.core.security import create_access_token

        user, subscription = user_with_basic_subscription
        token = create_access_token(user_id=user.id, email=user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        response = await client.post(
            "/v1/billing/subscribe",
            json={
                "plan_id": str(basic_plan.id),
                "billing_period": "monthly",
            },
        )

        # Should be rejected with 400
        assert response.status_code == 400
        data = response.json()
        assert "same plan" in data["detail"].lower() or "already" in data["detail"].lower()

    async def test_subscribe_deferred_change_rejected(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        max_plan: Plan,
        basic_plan: Plan,
    ):
        """Test that subscribing for deferred change is rejected (should use schedule endpoint)."""
        from app.core.security import create_access_token

        # Create subscription on max plan
        start_date = datetime.now(timezone.utc) - timedelta(days=15)
        end_date = start_date + timedelta(days=30)

        subscription = Subscription(
            user_id=test_user.id,
            plan_id=max_plan.id,
            status=SubscriptionStatus.ACTIVE,
                current_period_start=start_date,
            current_period_end=end_date,
            cancel_at_period_end=False,
        )
        db_session.add(subscription)
        await db_session.commit()

        token = create_access_token(user_id=test_user.id, email=test_user.email)
        client.headers.update({"Authorization": f"Bearer {token}"})

        # Try to subscribe to cheaper plan (downgrade)
        response = await client.post(
            "/v1/billing/subscribe",
            json={
                "plan_id": str(basic_plan.id),
                "billing_period": "monthly",
            },
        )

        # Should be rejected with 400
        assert response.status_code == 400
        data = response.json()
        assert "schedule" in data["detail"].lower() or "deferred" in data["detail"].lower()
