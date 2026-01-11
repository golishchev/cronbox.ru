"""Unit tests for billing API endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestListPlans:
    """Tests for list_plans endpoint."""

    @pytest.mark.asyncio
    async def test_list_plans_returns_plans(self):
        """Test listing plans."""
        from app.api.v1.billing import list_plans

        mock_db = AsyncMock()
        mock_plans = [MagicMock(), MagicMock()]

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_plans = AsyncMock(return_value=mock_plans)

            result = await list_plans(db=mock_db)

            assert result == mock_plans
            mock_service.get_plans.assert_called_once_with(mock_db)


class TestGetPlan:
    """Tests for get_plan endpoint."""

    @pytest.mark.asyncio
    async def test_get_plan_found(self):
        """Test getting a plan by ID."""
        from app.api.v1.billing import get_plan

        mock_db = AsyncMock()
        plan_id = uuid4()
        mock_plan = MagicMock()

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_plan_by_id = AsyncMock(return_value=mock_plan)

            result = await get_plan(plan_id=plan_id, db=mock_db)

            assert result == mock_plan

    @pytest.mark.asyncio
    async def test_get_plan_not_found(self):
        """Test getting a non-existent plan raises 404."""
        from fastapi import HTTPException

        from app.api.v1.billing import get_plan

        mock_db = AsyncMock()
        plan_id = uuid4()

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_plan_by_id = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_plan(plan_id=plan_id, db=mock_db)

            assert exc_info.value.status_code == 404
            assert "Plan not found" in exc_info.value.detail


class TestGetSubscription:
    """Tests for get_subscription endpoint."""

    @pytest.mark.asyncio
    async def test_get_subscription_workspace_not_found(self):
        """Test getting subscription for non-existent workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import get_subscription

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(None, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_subscription(
                    workspace_id=workspace_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Workspace not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_subscription_forbidden(self):
        """Test getting subscription for another user's workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import get_subscription

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = uuid4()  # Different from current user

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_subscription(
                    workspace_id=workspace_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
            assert "Not authorized" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_subscription_no_subscription(self):
        """Test getting subscription when none exists."""
        from app.api.v1.billing import get_subscription

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id  # Same as current user

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )

            result = await get_subscription(
                workspace_id=workspace_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_subscription_with_plan(self):
        """Test getting subscription with plan."""
        from app.api.v1.billing import get_subscription
        from app.schemas.billing import PlanResponse, SubscriptionResponse

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        mock_plan = MagicMock()
        mock_plan.id = uuid4()
        mock_plan.name = "pro"
        mock_plan.display_name = "Pro Plan"
        mock_plan.max_cron_tasks = 100
        mock_plan.max_delayed_tasks = 1000
        mock_plan.max_executions_per_day = 10000
        mock_plan.max_request_size_kb = 1024
        mock_plan.max_response_size_kb = 4096
        mock_plan.log_retention_days = 30
        mock_plan.price_monthly = 29900
        mock_plan.price_yearly = 299000
        mock_plan.is_public = True
        mock_plan.features = {"support": "email"}

        mock_subscription = MagicMock()
        mock_subscription.id = uuid4()
        mock_subscription.workspace_id = workspace_id
        mock_subscription.plan_id = mock_plan.id
        mock_subscription.status = "active"
        mock_subscription.billing_period = "monthly"
        mock_subscription.current_period_start = None
        mock_subscription.current_period_end = None
        mock_subscription.cancel_at_period_end = False
        mock_subscription.cancelled_at = None
        mock_subscription.created_at = None
        mock_subscription.updated_at = None

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, mock_plan, mock_subscription)
            )

            with patch.object(SubscriptionResponse, "model_validate") as mock_validate:
                mock_response = MagicMock(spec=SubscriptionResponse)
                mock_validate.return_value = mock_response

                with patch.object(PlanResponse, "model_validate") as mock_plan_validate:
                    mock_plan_response = MagicMock(spec=PlanResponse)
                    mock_plan_validate.return_value = mock_plan_response

                    result = await get_subscription(
                        workspace_id=workspace_id,
                        current_user=mock_user,
                        db=mock_db,
                    )

                    assert result is not None


class TestCreateSubscriptionPayment:
    """Tests for create_subscription_payment endpoint."""

    @pytest.mark.asyncio
    async def test_create_payment_workspace_not_found(self):
        """Test creating payment for non-existent workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import create_subscription_payment
        from app.schemas.billing import CreatePaymentRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()
        request = CreatePaymentRequest(
            plan_id=uuid4(),
            billing_period="monthly",
        )

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(None, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_payment(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_payment_forbidden(self):
        """Test creating payment for another user's workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import create_subscription_payment
        from app.schemas.billing import CreatePaymentRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = uuid4()  # Different from current user

        request = CreatePaymentRequest(
            plan_id=uuid4(),
            billing_period="monthly",
        )

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_payment(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_payment_not_configured(self):
        """Test creating payment when YooKassa not configured."""
        from fastapi import HTTPException

        from app.api.v1.billing import create_subscription_payment
        from app.schemas.billing import CreatePaymentRequest

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        request = CreatePaymentRequest(
            plan_id=uuid4(),
            billing_period="monthly",
        )

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )
            mock_service.is_configured = False

            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_payment(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 503
            assert "Payment system is not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_payment_failed(self):
        """Test creating payment when creation fails."""
        from fastapi import HTTPException

        from app.api.v1.billing import create_subscription_payment
        from app.schemas.billing import CreatePaymentRequest

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        request = CreatePaymentRequest(
            plan_id=uuid4(),
            billing_period="monthly",
        )

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )
            mock_service.is_configured = True
            mock_service.create_payment = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await create_subscription_payment(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 500
            assert "Failed to create payment" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_payment_success(self):
        """Test successful payment creation."""
        from app.api.v1.billing import create_subscription_payment
        from app.schemas.billing import CreatePaymentRequest

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        request = CreatePaymentRequest(
            plan_id=uuid4(),
            billing_period="monthly",
        )

        mock_payment = MagicMock()
        mock_payment.id = uuid4()
        mock_payment.confirmation_url = "https://yookassa.ru/checkout"

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )
            mock_service.is_configured = True
            mock_service.create_payment = AsyncMock(return_value=mock_payment)

            result = await create_subscription_payment(
                workspace_id=workspace_id,
                request=request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == mock_payment


class TestCancelSubscription:
    """Tests for cancel_subscription endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_workspace_not_found(self):
        """Test canceling subscription for non-existent workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import cancel_subscription
        from app.schemas.billing import CancelSubscriptionRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()
        request = CancelSubscriptionRequest(immediately=False)

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(None, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await cancel_subscription(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_forbidden(self):
        """Test canceling subscription for another user's workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import cancel_subscription
        from app.schemas.billing import CancelSubscriptionRequest

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = uuid4()

        request = CancelSubscriptionRequest(immediately=False)

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await cancel_subscription(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cancel_no_subscription(self):
        """Test canceling when no subscription exists."""
        from fastapi import HTTPException

        from app.api.v1.billing import cancel_subscription
        from app.schemas.billing import CancelSubscriptionRequest

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        request = CancelSubscriptionRequest(immediately=False)

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await cancel_subscription(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "No active subscription" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_cancel_failed(self):
        """Test canceling when cancel fails."""
        from fastapi import HTTPException

        from app.api.v1.billing import cancel_subscription
        from app.schemas.billing import CancelSubscriptionRequest

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        mock_subscription = MagicMock()

        request = CancelSubscriptionRequest(immediately=False)

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, mock_subscription)
            )
            mock_service.cancel_subscription = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await cancel_subscription(
                    workspace_id=workspace_id,
                    request=request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 500
            assert "Failed to cancel" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_cancel_success(self):
        """Test successful subscription cancellation."""
        from app.api.v1.billing import cancel_subscription
        from app.schemas.billing import CancelSubscriptionRequest

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        mock_subscription = MagicMock()

        request = CancelSubscriptionRequest(immediately=False)

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, mock_subscription)
            )
            mock_service.cancel_subscription = AsyncMock(return_value=True)

            result = await cancel_subscription(
                workspace_id=workspace_id,
                request=request,
                current_user=mock_user,
                db=mock_db,
            )

            assert "message" in result
            assert "cancelled" in result["message"].lower()


class TestGetPaymentHistory:
    """Tests for get_payment_history endpoint."""

    @pytest.mark.asyncio
    async def test_payment_history_workspace_not_found(self):
        """Test getting payment history for non-existent workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import get_payment_history

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(None, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_payment_history(
                    workspace_id=workspace_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_payment_history_forbidden(self):
        """Test getting payment history for another user's workspace."""
        from fastapi import HTTPException

        from app.api.v1.billing import get_payment_history

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = uuid4()

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_payment_history(
                    workspace_id=workspace_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_payment_history_success(self):
        """Test successful payment history retrieval."""
        from app.api.v1.billing import get_payment_history

        mock_db = AsyncMock()
        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.id = user_id
        workspace_id = uuid4()

        mock_workspace = MagicMock()
        mock_workspace.owner_id = user_id

        mock_payments = [MagicMock(), MagicMock()]

        with patch("app.api.v1.billing.billing_service") as mock_service:
            mock_service.get_workspace_with_plan = AsyncMock(
                return_value=(mock_workspace, None, None)
            )
            mock_service.get_payment_history = AsyncMock(return_value=mock_payments)

            result = await get_payment_history(
                workspace_id=workspace_id,
                current_user=mock_user,
                limit=20,
                offset=0,
                db=mock_db,
            )

            assert result == mock_payments
            mock_service.get_payment_history.assert_called_once_with(
                mock_db, workspace_id, limit=20, offset=0
            )
