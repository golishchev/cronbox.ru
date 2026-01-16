"""Unit tests for billing service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.payment import PaymentStatus
from app.models.subscription import SubscriptionStatus
from app.services.billing import BillingService


class TestBillingServiceInit:
    """Tests for BillingService initialization."""

    def test_is_configured_true(self):
        """Test is_configured when both credentials are set."""
        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop123"
            mock_settings.yookassa_secret_key = "secret123"

            service = BillingService()
            assert service.is_configured is True

    def test_is_configured_false_no_shop_id(self):
        """Test is_configured when shop_id is missing."""
        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = None
            mock_settings.yookassa_secret_key = "secret123"

            service = BillingService()
            assert service.is_configured is False

    def test_is_configured_false_no_secret(self):
        """Test is_configured when secret_key is missing."""
        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop123"
            mock_settings.yookassa_secret_key = None

            service = BillingService()
            assert service.is_configured is False


class TestBillingServiceGetPlans:
    """Tests for BillingService get_plans method."""

    @pytest.mark.asyncio
    async def test_get_plans_from_db(self):
        """Test getting plans from database when no cache."""
        mock_db = AsyncMock()
        mock_plans = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_plans
        mock_db.execute.return_value = mock_result

        with patch("app.services.billing.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock()

            service = BillingService()
            result = await service.get_plans(mock_db)

            assert len(result) == 2
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_plans_not_public(self):
        """Test getting all plans (not just public)."""
        mock_db = AsyncMock()
        mock_plans = [MagicMock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_plans
        mock_db.execute.return_value = mock_result

        service = BillingService()
        result = await service.get_plans(mock_db, only_public=False)

        assert len(result) == 1


class TestBillingServiceGetPlanMethods:
    """Tests for BillingService plan retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_plan_by_name(self):
        """Test getting plan by name."""
        mock_db = AsyncMock()
        mock_plan = MagicMock()
        mock_plan.name = "pro"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute.return_value = mock_result

        service = BillingService()
        result = await service.get_plan_by_name(mock_db, "pro")

        assert result == mock_plan

    @pytest.mark.asyncio
    async def test_get_plan_by_name_not_found(self):
        """Test getting non-existent plan by name."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = BillingService()
        result = await service.get_plan_by_name(mock_db, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_plan_by_id(self):
        """Test getting plan by ID."""
        mock_db = AsyncMock()
        plan_id = uuid4()
        mock_plan = MagicMock()
        mock_plan.id = plan_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute.return_value = mock_result

        service = BillingService()
        result = await service.get_plan_by_id(mock_db, plan_id)

        assert result == mock_plan


class TestBillingServiceSubscription:
    """Tests for BillingService subscription methods."""

    @pytest.mark.asyncio
    async def test_get_user_subscription(self):
        """Test getting user subscription."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_subscription = MagicMock()
        mock_subscription.user_id = user_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        mock_db.execute.return_value = mock_result

        service = BillingService()
        result = await service.get_user_subscription(mock_db, user_id)

        assert result == mock_subscription

    @pytest.mark.asyncio
    async def test_get_user_subscription_for_update(self):
        """Test getting user subscription with lock."""
        mock_db = AsyncMock()
        user_id = uuid4()
        mock_subscription = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        mock_db.execute.return_value = mock_result

        service = BillingService()
        result = await service.get_user_subscription_for_update(mock_db, user_id)

        assert result == mock_subscription

    @pytest.mark.asyncio
    async def test_get_user_plan_with_active_subscription(self):
        """Test getting user plan when they have an active subscription."""
        mock_db = AsyncMock()
        user_id = uuid4()
        plan_id = uuid4()

        mock_subscription = MagicMock()
        mock_subscription.status = SubscriptionStatus.ACTIVE
        mock_subscription.plan_id = plan_id

        mock_plan = MagicMock()
        mock_plan.id = plan_id
        mock_plan.name = "pro"

        service = BillingService()
        service.get_user_subscription = AsyncMock(return_value=mock_subscription)
        service.get_plan_by_id = AsyncMock(return_value=mock_plan)

        result = await service.get_user_plan(mock_db, user_id)

        assert result == mock_plan

    @pytest.mark.asyncio
    async def test_get_user_plan_fallback_to_free(self):
        """Test getting user plan fallback to free when no subscription."""
        mock_db = AsyncMock()
        user_id = uuid4()

        mock_free_plan = MagicMock()
        mock_free_plan.name = "free"

        service = BillingService()
        service.get_user_subscription = AsyncMock(return_value=None)
        service.get_plan_by_name = AsyncMock(return_value=mock_free_plan)

        result = await service.get_user_plan(mock_db, user_id)

        assert result == mock_free_plan
        service.get_plan_by_name.assert_called_with(mock_db, "free")

    @pytest.mark.asyncio
    async def test_get_user_plan_no_free_plan_raises(self):
        """Test getting user plan raises when free plan doesn't exist."""
        mock_db = AsyncMock()
        user_id = uuid4()

        service = BillingService()
        service.get_user_subscription = AsyncMock(return_value=None)
        service.get_plan_by_name = AsyncMock(return_value=None)

        with pytest.raises(RuntimeError) as exc_info:
            await service.get_user_plan(mock_db, user_id)

        assert "Free plan not found" in str(exc_info.value)


class TestBillingServiceCreatePayment:
    """Tests for BillingService create_payment method."""

    @pytest.mark.asyncio
    async def test_create_payment_not_configured(self):
        """Test create_payment when YooKassa not configured."""
        mock_db = AsyncMock()

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = None
            mock_settings.yookassa_secret_key = None

            service = BillingService()
            result = await service.create_payment(mock_db, uuid4(), uuid4(), "monthly")

            assert result is None

    @pytest.mark.asyncio
    async def test_create_payment_plan_not_found(self):
        """Test create_payment when plan not found."""
        mock_db = AsyncMock()

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop123"
            mock_settings.yookassa_secret_key = "secret123"

            service = BillingService()
            service.get_plan_by_id = AsyncMock(return_value=None)

            result = await service.create_payment(mock_db, uuid4(), uuid4(), "monthly")

            assert result is None

    @pytest.mark.asyncio
    async def test_create_payment_free_plan(self):
        """Test create_payment rejects free plan."""
        mock_db = AsyncMock()

        mock_plan = MagicMock()
        mock_plan.price_monthly = 0
        mock_plan.price_yearly = 0

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop123"
            mock_settings.yookassa_secret_key = "secret123"

            service = BillingService()
            service.get_plan_by_id = AsyncMock(return_value=mock_plan)

            result = await service.create_payment(mock_db, uuid4(), uuid4(), "monthly")

            assert result is None


class TestBillingServiceInvalidateCache:
    """Tests for BillingService cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_plans_cache_success(self):
        """Test invalidating plans cache."""
        with patch("app.services.billing.redis_client") as mock_redis:
            mock_redis.delete = AsyncMock()

            service = BillingService()
            await service.invalidate_plans_cache()

            mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_plans_cache_error(self):
        """Test invalidating cache handles errors."""
        with patch("app.services.billing.redis_client") as mock_redis:
            mock_redis.delete = AsyncMock(side_effect=Exception("Redis error"))

            service = BillingService()
            # Should not raise
            await service.invalidate_plans_cache()


class TestBillingHelperFunctions:
    """Tests for billing helper functions."""

    def test_get_billing_description(self):
        """Test billing description generation."""
        from app.services.billing import _get_billing_description

        description = _get_billing_description("Pro", "monthly", "en")
        assert "Pro" in description

    def test_get_receipt_description(self):
        """Test receipt description generation."""
        from app.services.billing import _get_receipt_description

        description = _get_receipt_description("Pro", "yearly", "en")
        assert "Pro" in description
