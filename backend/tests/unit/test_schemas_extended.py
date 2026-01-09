"""Extended tests for Pydantic schemas."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.auth import (
    TokenResponse,
    TokenPayload,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    LoginResponse,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerificationRequest,
    TelegramConnectRequest,
    TelegramConnectResponse,
    TelegramLinkRequest,
)
from app.schemas.delayed_task import (
    DelayedTaskBase,
    DelayedTaskCreate,
    DelayedTaskResponse,
    DelayedTaskUpdate,
    DelayedTaskListResponse,
)
from app.schemas.workspace import (
    WorkspaceBase,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceWithStats,
)
from app.schemas.billing import (
    PlanResponse,
    SubscriptionResponse,
    PaymentResponse,
    CreatePaymentRequest,
)
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.execution import ExecutionResponse, ExecutionListResponse
from app.schemas.notification_settings import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from app.schemas.worker import (
    WorkerCreate,
    WorkerResponse,
    WorkerTaskInfo,
    WorkerTaskResult,
)


class TestAuthSchemas:
    """Tests for authentication schemas."""

    def test_token_response(self):
        """Test TokenResponse schema."""
        token = TokenResponse(
            access_token="access123",
            refresh_token="refresh456",
        )
        assert token.access_token == "access123"
        assert token.refresh_token == "refresh456"
        assert token.token_type == "bearer"

    def test_token_payload(self):
        """Test TokenPayload schema."""
        payload = TokenPayload(
            sub="user-id-123",
            email="test@example.com",
            exp=1234567890,
            type="access",
        )
        assert payload.sub == "user-id-123"
        assert payload.email == "test@example.com"
        assert payload.type == "access"

    def test_refresh_token_request(self):
        """Test RefreshTokenRequest schema."""
        request = RefreshTokenRequest(refresh_token="token123")
        assert request.refresh_token == "token123"

    def test_register_request_valid(self):
        """Test valid RegisterRequest."""
        request = RegisterRequest(
            email="test@example.com",
            password="securepassword123",
            name="Test User",
        )
        assert request.email == "test@example.com"
        assert request.name == "Test User"

    def test_register_request_password_too_short(self):
        """Test RegisterRequest with password too short."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                password="short",
                name="Test User",
            )

    def test_register_request_invalid_email(self):
        """Test RegisterRequest with invalid email."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                password="securepassword123",
                name="Test User",
            )

    def test_password_change_request(self):
        """Test PasswordChangeRequest schema."""
        request = PasswordChangeRequest(
            current_password="oldpassword123",
            new_password="newpassword456",
        )
        assert request.current_password == "oldpassword123"
        assert request.new_password == "newpassword456"

    def test_password_reset_request(self):
        """Test PasswordResetRequest schema."""
        request = PasswordResetRequest(email="test@example.com")
        assert request.email == "test@example.com"

    def test_password_reset_confirm(self):
        """Test PasswordResetConfirm schema."""
        request = PasswordResetConfirm(
            token="reset-token",
            new_password="newpassword123",
        )
        assert request.token == "reset-token"

    def test_email_verification_request(self):
        """Test EmailVerificationRequest schema."""
        request = EmailVerificationRequest(token="verify-token")
        assert request.token == "verify-token"

    def test_telegram_connect_request(self):
        """Test TelegramConnectRequest schema (empty)."""
        request = TelegramConnectRequest()
        assert request is not None

    def test_telegram_connect_response(self):
        """Test TelegramConnectResponse schema."""
        response = TelegramConnectResponse(
            code="123456",
            expires_in=600,
            bot_username="cronbox_bot",
        )
        assert response.code == "123456"
        assert response.expires_in == 600

    def test_telegram_link_request(self):
        """Test TelegramLinkRequest schema."""
        request = TelegramLinkRequest(
            code="123456",
            telegram_id=12345678,
            telegram_username="testuser",
        )
        assert request.telegram_id == 12345678


class TestDelayedTaskSchemas:
    """Tests for delayed task schemas."""

    def test_delayed_task_base(self):
        """Test DelayedTaskBase schema."""
        task = DelayedTaskBase(
            url="https://api.example.com/webhook",
            execute_at=datetime.now() + timedelta(hours=1),
        )
        assert str(task.url) == "https://api.example.com/webhook"
        assert task.method.value == "POST"  # default

    def test_delayed_task_create(self):
        """Test DelayedTaskCreate schema."""
        task = DelayedTaskCreate(
            url="https://api.example.com/webhook",
            execute_at=datetime.now() + timedelta(hours=1),
            idempotency_key="unique-key-123",
            name="Test Delayed Task",
            tags=["test", "webhook"],
        )
        assert task.idempotency_key == "unique-key-123"
        assert task.name == "Test Delayed Task"
        assert len(task.tags) == 2

    def test_delayed_task_update(self):
        """Test DelayedTaskUpdate schema with partial data."""
        update = DelayedTaskUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.url is None
        assert update.tags is None


class TestWorkspaceSchemas:
    """Tests for workspace schemas."""

    def test_workspace_base(self):
        """Test WorkspaceBase schema."""
        workspace = WorkspaceBase(name="My Workspace")
        assert workspace.name == "My Workspace"
        assert workspace.default_timezone == "Europe/Moscow"

    def test_workspace_create(self):
        """Test WorkspaceCreate schema."""
        workspace = WorkspaceCreate(
            name="My Workspace",
            slug="my-workspace",
        )
        assert workspace.slug == "my-workspace"

    def test_workspace_create_invalid_slug(self):
        """Test WorkspaceCreate with invalid slug."""
        with pytest.raises(ValidationError):
            WorkspaceCreate(
                name="My Workspace",
                slug="Invalid Slug!",  # Contains uppercase and special chars
            )

    def test_workspace_update(self):
        """Test WorkspaceUpdate schema."""
        update = WorkspaceUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.default_timezone is None


class TestBillingSchemas:
    """Tests for billing schemas."""

    def test_create_payment_request(self):
        """Test CreatePaymentRequest schema."""
        request = CreatePaymentRequest(
            plan_id=uuid4(),
            billing_period="monthly",
        )
        assert request.billing_period == "monthly"

    def test_create_payment_request_yearly(self):
        """Test CreatePaymentRequest with yearly billing."""
        request = CreatePaymentRequest(
            plan_id=uuid4(),
            billing_period="yearly",
        )
        assert request.billing_period == "yearly"


class TestUserSchemas:
    """Tests for user schemas."""

    def test_user_update_partial(self):
        """Test UserUpdate schema with partial data."""
        update = UserUpdate(name="New Name")
        assert update.name == "New Name"

    def test_user_update_language(self):
        """Test UserUpdate schema with language."""
        update = UserUpdate(preferred_language="en")
        assert update.preferred_language == "en"


class TestWorkerSchemas:
    """Tests for worker schemas."""

    def test_worker_create(self):
        """Test WorkerCreate schema."""
        worker = WorkerCreate(
            name="My Worker",
            description="Test worker",
        )
        assert worker.name == "My Worker"

    def test_worker_task_info(self):
        """Test WorkerTaskInfo schema."""
        task = WorkerTaskInfo(
            task_id=uuid4(),
            task_type="cron",
            url="https://api.example.com",
            method="POST",
            headers={"Authorization": "Bearer token"},
            body='{"key": "value"}',
            timeout_seconds=30,
            retry_count=3,
            retry_delay_seconds=60,
            workspace_id=uuid4(),
            task_name="Test Task",
        )
        assert task.task_type == "cron"
        assert task.timeout_seconds == 30

    def test_worker_task_result(self):
        """Test WorkerTaskResult schema."""
        now = datetime.now()
        result = WorkerTaskResult(
            task_id=uuid4(),
            task_type="cron",
            status_code=200,
            response_headers={"content-type": "application/json"},
            response_body='{"status": "ok"}',
            started_at=now,
            finished_at=now,
            duration_ms=150,
        )
        assert result.status_code == 200

    def test_worker_task_result_failed(self):
        """Test WorkerTaskResult schema for failed request."""
        now = datetime.now()
        result = WorkerTaskResult(
            task_id=uuid4(),
            task_type="cron",
            error="Connection refused",
            error_type="connection_error",
            started_at=now,
            finished_at=now,
            duration_ms=5000,
        )
        assert result.error == "Connection refused"


class TestNotificationSettingsSchemas:
    """Tests for notification settings schemas."""

    def test_notification_settings_update(self):
        """Test NotificationSettingsUpdate schema."""
        update = NotificationSettingsUpdate(
            email_enabled=True,
            telegram_enabled=False,
            webhook_url="https://webhook.example.com/notify",
        )
        assert update.email_enabled is True
        assert update.telegram_enabled is False

    def test_notification_settings_update_partial(self):
        """Test partial NotificationSettingsUpdate."""
        update = NotificationSettingsUpdate(notify_on_failure=False)
        assert update.notify_on_failure is False
        assert update.telegram_enabled is None


class TestPaginationInListResponses:
    """Tests for pagination in list response schemas."""

    def test_delayed_task_list_response(self):
        """Test DelayedTaskListResponse schema."""
        from app.schemas.cron_task import PaginationMeta

        response = DelayedTaskListResponse(
            tasks=[],
            pagination=PaginationMeta(
                page=1,
                limit=10,
                total=0,
                total_pages=0,
            ),
        )
        assert len(response.tasks) == 0
        assert response.pagination.page == 1
