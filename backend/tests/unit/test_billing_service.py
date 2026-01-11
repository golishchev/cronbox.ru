"""Tests for BillingService."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest


class TestBillingServiceInit:
    """Tests for BillingService initialization."""

    def test_init_with_settings(self):
        """Test BillingService initializes with settings."""
        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            from app.services.billing import BillingService
            service = BillingService()

            assert service.shop_id == "shop-123"
            assert service.secret_key == "secret-key"
            assert service.base_url == "https://api.yookassa.ru/v3"

    def test_is_configured_true(self):
        """Test is_configured returns True when configured."""
        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            from app.services.billing import BillingService
            service = BillingService()

            assert service.is_configured is True

    def test_is_configured_false(self):
        """Test is_configured returns False when not configured."""
        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = None
            mock_settings.yookassa_secret_key = None

            from app.services.billing import BillingService
            service = BillingService()

            assert service.is_configured is False


class TestBillingServiceGetPlans:
    """Tests for BillingService.get_plans."""

    @pytest.mark.asyncio
    async def test_get_plans_public_only(self):
        """Test get_plans returns only public plans."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_plans = [MagicMock(), MagicMock()]
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = mock_plans
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute.return_value = mock_result

            result = await service.get_plans(mock_db, only_public=True)

            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_plans_all(self):
        """Test get_plans returns all plans."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_plans = [MagicMock(), MagicMock(), MagicMock()]
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = mock_plans
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute.return_value = mock_result

            result = await service.get_plans(mock_db, only_public=False)

            assert len(result) == 3


class TestBillingServiceGetPlanByName:
    """Tests for BillingService.get_plan_by_name."""

    @pytest.mark.asyncio
    async def test_get_plan_by_name_found(self):
        """Test get_plan_by_name returns plan."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_plan = MagicMock()
            mock_plan.name = "pro"
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_plan
            mock_db.execute.return_value = mock_result

            result = await service.get_plan_by_name(mock_db, "pro")

            assert result == mock_plan

    @pytest.mark.asyncio
    async def test_get_plan_by_name_not_found(self):
        """Test get_plan_by_name returns None when not found."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            result = await service.get_plan_by_name(mock_db, "nonexistent")

            assert result is None


class TestBillingServiceGetSubscription:
    """Tests for BillingService.get_subscription."""

    @pytest.mark.asyncio
    async def test_get_subscription_found(self):
        """Test get_subscription returns subscription."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            workspace_id = uuid4()
            mock_subscription = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_subscription
            mock_db.execute.return_value = mock_result

            result = await service.get_subscription(mock_db, workspace_id)

            assert result == mock_subscription


class TestBillingServiceCreatePayment:
    """Tests for BillingService.create_payment."""

    @pytest.mark.asyncio
    async def test_create_payment_not_configured(self):
        """Test create_payment returns None when not configured."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = None
            mock_settings.yookassa_secret_key = None

            service = BillingService()
            mock_db = AsyncMock()

            result = await service.create_payment(
                mock_db, uuid4(), uuid4(), "monthly"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_create_payment_plan_not_found(self):
        """Test create_payment returns None when plan not found."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            with patch.object(service, "get_plan_by_id", return_value=None):
                result = await service.create_payment(
                    mock_db, uuid4(), uuid4(), "monthly"
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_create_payment_free_plan(self):
        """Test create_payment returns None for free plan."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_plan = MagicMock()
            mock_plan.price_monthly = 0

            with patch.object(service, "get_plan_by_id", return_value=mock_plan):
                result = await service.create_payment(
                    mock_db, uuid4(), uuid4(), "monthly"
                )

                assert result is None

    @pytest.mark.asyncio
    @patch("app.services.billing.httpx.AsyncClient")
    async def test_create_payment_success(self, mock_client_class):
        """Test create_payment success."""
        from app.services.billing import BillingService

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "id": "yookassa-payment-123",
            "confirmation": {"confirmation_url": "https://yookassa.ru/checkout"}
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"
            mock_settings.cors_origins = ["https://cronbox.ru"]

            service = BillingService()
            mock_db = AsyncMock()
            mock_db.add = MagicMock()

            mock_plan = MagicMock()
            mock_plan.price_monthly = 29900  # kopeks
            mock_plan.price_yearly = 299000
            mock_plan.display_name = "Pro Plan"

            with patch.object(service, "get_plan_by_id", return_value=mock_plan):
                result = await service.create_payment(
                    mock_db, uuid4(), uuid4(), "monthly"
                )

                assert result is not None
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called()


class TestBillingServiceHandleWebhook:
    """Tests for BillingService.handle_webhook."""

    @pytest.mark.asyncio
    async def test_handle_webhook_no_payment_id(self):
        """Test handle_webhook returns False with no payment ID."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            result = await service.handle_webhook(mock_db, "payment.succeeded", {})

            assert result is False

    @pytest.mark.asyncio
    async def test_handle_webhook_payment_not_found(self):
        """Test handle_webhook returns False when payment not found."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            result = await service.handle_webhook(
                mock_db, "payment.succeeded", {"id": "yookassa-123"}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_handle_webhook_payment_succeeded(self):
        """Test handle_webhook processes successful payment."""
        from app.models.payment import PaymentStatus
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payment = MagicMock()
            mock_payment.status = PaymentStatus.PENDING
            mock_payment.amount = 29900
            mock_payment.currency = "RUB"
            mock_payment.workspace_id = uuid4()
            mock_payment.extra_data = {"plan_id": str(uuid4()), "billing_period": "monthly"}
            mock_payment.id = uuid4()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_payment
            mock_db.execute.return_value = mock_result

            with patch.object(service, "_handle_payment_succeeded", new_callable=AsyncMock) as mock_handler:
                mock_handler.return_value = True

                result = await service.handle_webhook(
                    mock_db,
                    "payment.succeeded",
                    {"id": "yookassa-123", "amount": {"value": "299.00", "currency": "RUB"}}
                )

                assert result is True
                mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_payment_cancelled(self):
        """Test handle_webhook processes cancelled payment."""
        from app.services.billing import BillingService, PaymentStatus

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payment = MagicMock()
            mock_payment.status = PaymentStatus.PENDING

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_payment
            mock_db.execute.return_value = mock_result

            result = await service.handle_webhook(
                mock_db, "payment.canceled", {"id": "yookassa-123"}
            )

            assert result is True
            assert mock_payment.status == PaymentStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_handle_webhook_refund_succeeded(self):
        """Test handle_webhook processes refund."""
        from app.services.billing import BillingService, PaymentStatus

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payment = MagicMock()
            mock_payment.status = PaymentStatus.SUCCEEDED

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_payment
            mock_db.execute.return_value = mock_result

            result = await service.handle_webhook(
                mock_db, "refund.succeeded", {"id": "yookassa-123"}
            )

            assert result is True
            assert mock_payment.status == PaymentStatus.REFUNDED


class TestBillingServicePaymentSucceeded:
    """Tests for _handle_payment_succeeded."""

    @pytest.mark.asyncio
    async def test_payment_already_processed(self):
        """Test idempotency - payment already processed."""
        from app.services.billing import BillingService, PaymentStatus

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payment = MagicMock()
            mock_payment.status = PaymentStatus.SUCCEEDED
            mock_payment.id = uuid4()

            result = await service._handle_payment_succeeded(
                mock_db, mock_payment, {"amount": {"value": "299.00", "currency": "RUB"}}
            )

            assert result is True  # Idempotent success

    @pytest.mark.asyncio
    async def test_payment_invalid_status(self):
        """Test payment with invalid status."""
        from app.services.billing import BillingService, PaymentStatus

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payment = MagicMock()
            mock_payment.status = PaymentStatus.CANCELLED
            mock_payment.id = uuid4()

            result = await service._handle_payment_succeeded(
                mock_db, mock_payment, {"amount": {"value": "299.00", "currency": "RUB"}}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_payment_amount_mismatch(self):
        """Test payment with amount mismatch."""
        from app.services.billing import BillingService, PaymentStatus

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payment = MagicMock()
            mock_payment.status = PaymentStatus.PENDING
            mock_payment.amount = 29900
            mock_payment.currency = "RUB"
            mock_payment.id = uuid4()

            result = await service._handle_payment_succeeded(
                mock_db, mock_payment, {"amount": {"value": "199.00", "currency": "RUB"}}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_payment_currency_mismatch(self):
        """Test payment with currency mismatch."""
        from app.services.billing import BillingService, PaymentStatus

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payment = MagicMock()
            mock_payment.status = PaymentStatus.PENDING
            mock_payment.amount = 29900
            mock_payment.currency = "RUB"
            mock_payment.id = uuid4()

            result = await service._handle_payment_succeeded(
                mock_db, mock_payment, {"amount": {"value": "299.00", "currency": "USD"}}
            )

            assert result is False


class TestBillingServiceCancelSubscription:
    """Tests for cancel_subscription."""

    @pytest.mark.asyncio
    async def test_cancel_subscription_not_found(self):
        """Test cancel_subscription returns False when not found."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            with patch.object(service, "get_subscription", return_value=None):
                result = await service.cancel_subscription(mock_db, uuid4())

                assert result is False

    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(self):
        """Test cancel_subscription at period end."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_subscription = MagicMock()
            mock_subscription.cancel_at_period_end = False

            with patch.object(service, "get_subscription", return_value=mock_subscription):
                result = await service.cancel_subscription(mock_db, uuid4(), immediately=False)

                assert result is True
                assert mock_subscription.cancel_at_period_end is True
                mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately(self):
        """Test cancel_subscription immediately."""
        from app.services.billing import BillingService, SubscriptionStatus

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            workspace_id = uuid4()
            mock_subscription = MagicMock()

            mock_free_plan = MagicMock()
            mock_free_plan.id = uuid4()

            mock_workspace = MagicMock()

            mock_workspace_result = MagicMock()
            mock_workspace_result.scalar_one_or_none.return_value = mock_workspace
            mock_db.execute.return_value = mock_workspace_result

            with patch.object(service, "get_subscription", return_value=mock_subscription):
                with patch.object(service, "get_plan_by_name", return_value=mock_free_plan):
                    result = await service.cancel_subscription(mock_db, workspace_id, immediately=True)

                    assert result is True
                    assert mock_subscription.status == SubscriptionStatus.CANCELLED


class TestBillingServicePaymentHistory:
    """Tests for get_payment_history."""

    @pytest.mark.asyncio
    async def test_get_payment_history(self):
        """Test get_payment_history returns payments."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_payments = [MagicMock(), MagicMock()]
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = mock_payments
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute.return_value = mock_result

            result = await service.get_payment_history(mock_db, uuid4(), limit=20, offset=0)

            assert len(result) == 2


class TestBillingServiceExpiringSubscriptions:
    """Tests for get_expiring_subscriptions."""

    @pytest.mark.asyncio
    async def test_get_expiring_subscriptions(self):
        """Test get_expiring_subscriptions."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_subscriptions = [MagicMock()]
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = mock_subscriptions
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute.return_value = mock_result

            result = await service.get_expiring_subscriptions(mock_db, days_before=7)

            assert len(result) == 1


class TestBillingServiceCheckExpiredSubscriptions:
    """Tests for check_expired_subscriptions."""

    @pytest.mark.asyncio
    async def test_check_expired_subscriptions_none(self):
        """Test check_expired_subscriptions with no expired."""
        from app.services.billing import BillingService

        with patch("app.services.billing.settings") as mock_settings:
            mock_settings.yookassa_shop_id = "shop-123"
            mock_settings.yookassa_secret_key = "secret-key"

            service = BillingService()
            mock_db = AsyncMock()

            mock_scalars = MagicMock()
            mock_scalars.all.return_value = []
            mock_result = MagicMock()
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute.return_value = mock_result

            result = await service.check_expired_subscriptions(mock_db)

            assert result == []


class TestBillingServiceGlobalInstance:
    """Tests for global billing_service instance."""

    def test_global_instance_exists(self):
        """Test global billing_service instance exists."""
        from app.services.billing import billing_service

        assert billing_service is not None
