"""Tests for service layer with mocks."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.payment import Payment, PaymentStatus
from app.services.billing import BillingService


class TestBillingService:
    """Tests for BillingService."""

    def test_is_configured_false_when_no_credentials(self):
        """Test is_configured returns False when no credentials."""
        service = BillingService()

        # With default empty credentials
        with patch.object(service, "shop_id", ""):
            with patch.object(service, "secret_key", ""):
                assert service.is_configured is False

    def test_is_configured_true_when_credentials_set(self):
        """Test is_configured returns True with credentials."""
        service = BillingService()

        with patch.object(service, "shop_id", "12345"):
            with patch.object(service, "secret_key", "secret"):
                assert service.is_configured is True

    def test_get_auth(self):
        """Test _get_auth returns tuple of credentials."""
        service = BillingService()

        with patch.object(service, "shop_id", "shop123"):
            with patch.object(service, "secret_key", "key456"):
                auth = service._get_auth()

                assert auth == ("shop123", "key456")

    @pytest.mark.asyncio
    async def test_get_plans(self):
        """Test getting plans from database."""
        service = BillingService()

        # Create mock db session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(id=uuid4(), name="free"),
            MagicMock(id=uuid4(), name="pro"),
        ]
        mock_db.execute.return_value = mock_result

        plans = await service.get_plans(mock_db)

        assert len(plans) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_plan_by_name(self):
        """Test getting plan by name."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.name = "pro"  # Set name explicitly
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_plan
        mock_db.execute.return_value = mock_result

        plan = await service.get_plan_by_name(mock_db, "pro")

        assert plan is not None
        assert plan.name == "pro"

    @pytest.mark.asyncio
    async def test_get_plan_by_name_not_found(self):
        """Test getting non-existent plan returns None."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        plan = await service.get_plan_by_name(mock_db, "nonexistent")

        assert plan is None

    @pytest.mark.asyncio
    async def test_get_subscription(self):
        """Test getting workspace subscription."""
        service = BillingService()
        workspace_id = uuid4()

        mock_db = AsyncMock()
        mock_subscription = MagicMock(
            id=uuid4(),
            workspace_id=workspace_id,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        mock_db.execute.return_value = mock_result

        subscription = await service.get_subscription(mock_db, workspace_id)

        assert subscription is not None
        assert subscription.workspace_id == workspace_id

    @pytest.mark.asyncio
    async def test_create_payment_not_configured(self):
        """Test create_payment returns None when not configured."""
        service = BillingService()
        # Service is not configured when shop_id or secret_key are empty
        service.shop_id = ""
        service.secret_key = ""

        result = await service.create_payment(
            AsyncMock(),
            uuid4(),
            uuid4(),
        )

        assert result is None


class TestPaymentWebhookHandling:
    """Tests for payment webhook handling."""

    @pytest.mark.asyncio
    async def test_handle_webhook_no_payment_id(self):
        """Test webhook handling with no payment ID."""
        service = BillingService()
        mock_db = AsyncMock()

        result = await service.handle_webhook(mock_db, "payment.succeeded", {})

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_webhook_payment_not_found(self):
        """Test webhook handling when payment not found."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.handle_webhook(
            mock_db,
            "payment.succeeded",
            {"id": "yookassa-payment-id"},
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_payment_succeeded_already_processed(self):
        """Test idempotency - payment already processed."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_payment = MagicMock()
        mock_payment.status = PaymentStatus.SUCCEEDED
        mock_payment.id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_db.execute.return_value = mock_result

        result = await service.handle_webhook(
            mock_db,
            "payment.succeeded",
            {"id": "payment-id"},
        )

        # Should return True (idempotent - already processed)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_payment_succeeded_amount_mismatch(self):
        """Test webhook rejected on amount mismatch."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_payment = MagicMock()
        mock_payment.status = PaymentStatus.PENDING
        mock_payment.id = uuid4()
        mock_payment.amount = 29900  # Expected amount in kopeks
        mock_payment.currency = "RUB"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_db.execute.return_value = mock_result

        result = await service.handle_webhook(
            mock_db,
            "payment.succeeded",
            {
                "id": "payment-id",
                "amount": {
                    "value": "199.00",  # Different amount
                    "currency": "RUB",
                },
            },
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_payment_succeeded_currency_mismatch(self):
        """Test webhook rejected on currency mismatch."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_payment = MagicMock()
        mock_payment.status = PaymentStatus.PENDING
        mock_payment.id = uuid4()
        mock_payment.amount = 29900
        mock_payment.currency = "RUB"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_db.execute.return_value = mock_result

        result = await service.handle_webhook(
            mock_db,
            "payment.succeeded",
            {
                "id": "payment-id",
                "amount": {
                    "value": "299.00",
                    "currency": "USD",  # Wrong currency
                },
            },
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_payment_cancelled(self):
        """Test handling cancelled payment."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_payment = MagicMock()
        mock_payment.status = PaymentStatus.PENDING
        mock_payment.id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_db.execute.return_value = mock_result

        result = await service.handle_webhook(
            mock_db,
            "payment.canceled",
            {"id": "payment-id"},
        )

        assert result is True
        assert mock_payment.status == PaymentStatus.CANCELLED
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_refund_succeeded(self):
        """Test handling successful refund."""
        service = BillingService()

        mock_db = AsyncMock()
        mock_payment = MagicMock()
        mock_payment.status = PaymentStatus.SUCCEEDED
        mock_payment.id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_payment
        mock_db.execute.return_value = mock_result

        result = await service.handle_webhook(
            mock_db,
            "refund.succeeded",
            {"id": "payment-id"},
        )

        assert result is True
        assert mock_payment.status == PaymentStatus.REFUNDED


class TestSubscriptionManagement:
    """Tests for subscription management."""

    @pytest.mark.asyncio
    async def test_cancel_subscription_not_found(self):
        """Test cancelling non-existent subscription."""
        service = BillingService()

        mock_db = AsyncMock()

        with patch.object(service, "get_subscription", return_value=None):
            result = await service.cancel_subscription(mock_db, uuid4())

            assert result is False

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately(self):
        """Test immediate subscription cancellation."""
        service = BillingService()
        workspace_id = uuid4()

        mock_db = AsyncMock()
        mock_subscription = MagicMock()
        mock_subscription.workspace_id = workspace_id

        mock_free_plan = MagicMock(id=uuid4())
        mock_workspace_result = MagicMock()
        mock_workspace = MagicMock()
        mock_workspace_result.scalar_one_or_none.return_value = mock_workspace
        mock_db.execute.return_value = mock_workspace_result

        with patch.object(service, "get_subscription", return_value=mock_subscription):
            with patch.object(service, "get_plan_by_name", return_value=mock_free_plan):
                result = await service.cancel_subscription(
                    mock_db,
                    workspace_id,
                    immediately=True,
                )

                assert result is True
                # Subscription should be cancelled
                from app.models.subscription import SubscriptionStatus
                assert mock_subscription.status == SubscriptionStatus.CANCELLED
                assert mock_subscription.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(self):
        """Test subscription cancellation at period end."""
        service = BillingService()
        workspace_id = uuid4()

        mock_db = AsyncMock()
        mock_subscription = MagicMock()
        mock_subscription.workspace_id = workspace_id

        with patch.object(service, "get_subscription", return_value=mock_subscription):
            result = await service.cancel_subscription(
                mock_db,
                workspace_id,
                immediately=False,
            )

            assert result is True
            assert mock_subscription.cancel_at_period_end is True
            assert mock_subscription.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_get_payment_history(self):
        """Test getting payment history."""
        service = BillingService()
        workspace_id = uuid4()

        mock_db = AsyncMock()
        mock_payments = [
            MagicMock(id=uuid4(), amount=29900),
            MagicMock(id=uuid4(), amount=29900),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_payments
        mock_db.execute.return_value = mock_result

        payments = await service.get_payment_history(mock_db, workspace_id)

        assert len(payments) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_payment_history_pagination(self):
        """Test payment history with pagination."""
        service = BillingService()
        workspace_id = uuid4()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.get_payment_history(
            mock_db,
            workspace_id,
            limit=5,
            offset=10,
        )

        mock_db.execute.assert_called_once()
