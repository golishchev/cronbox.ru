"""Tests for SQLAlchemy models."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.cron_task import CronTask, HttpMethod, TaskStatus
from app.models.delayed_task import DelayedTask
from app.models.email_log import EmailLog, EmailStatus, EmailType
from app.models.execution import Execution
from app.models.notification_settings import NotificationSettings
from app.models.notification_template import NotificationTemplate
from app.models.payment import Payment, PaymentStatus
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.models.worker import Worker, WorkerStatus
from app.models.workspace import Workspace


class TestHttpMethod:
    """Tests for HttpMethod enum."""

    def test_all_methods_defined(self):
        """Test all HTTP methods are defined."""
        methods = list(HttpMethod)
        assert HttpMethod.GET in methods
        assert HttpMethod.POST in methods
        assert HttpMethod.PUT in methods
        assert HttpMethod.PATCH in methods
        assert HttpMethod.DELETE in methods

    def test_method_values(self):
        """Test HTTP method values."""
        assert HttpMethod.GET.value == "GET"
        assert HttpMethod.POST.value == "POST"
        assert HttpMethod.PUT.value == "PUT"
        assert HttpMethod.PATCH.value == "PATCH"
        assert HttpMethod.DELETE.value == "DELETE"


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses_defined(self):
        """Test all task statuses are defined."""
        statuses = list(TaskStatus)
        assert TaskStatus.PENDING in statuses
        assert TaskStatus.RUNNING in statuses
        assert TaskStatus.SUCCESS in statuses
        assert TaskStatus.FAILED in statuses

    def test_status_values(self):
        """Test task status values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.SUCCESS.value == "success"
        assert TaskStatus.FAILED.value == "failed"


class TestSubscriptionStatus:
    """Tests for SubscriptionStatus enum."""

    def test_all_statuses_defined(self):
        """Test all subscription statuses are defined."""
        statuses = list(SubscriptionStatus)
        assert SubscriptionStatus.ACTIVE in statuses
        assert SubscriptionStatus.CANCELLED in statuses
        assert SubscriptionStatus.EXPIRED in statuses

    def test_status_values(self):
        """Test subscription status values."""
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.CANCELLED.value == "cancelled"
        assert SubscriptionStatus.EXPIRED.value == "expired"


class TestPaymentStatus:
    """Tests for PaymentStatus enum."""

    def test_all_statuses_defined(self):
        """Test all payment statuses are defined."""
        statuses = list(PaymentStatus)
        assert PaymentStatus.PENDING in statuses
        assert PaymentStatus.SUCCEEDED in statuses
        assert PaymentStatus.CANCELLED in statuses
        assert PaymentStatus.REFUNDED in statuses

    def test_status_values(self):
        """Test payment status values."""
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.SUCCEEDED.value == "succeeded"
        assert PaymentStatus.CANCELLED.value == "cancelled"
        assert PaymentStatus.REFUNDED.value == "refunded"


class TestEmailStatus:
    """Tests for EmailStatus enum."""

    def test_all_statuses_defined(self):
        """Test all email statuses are defined."""
        statuses = list(EmailStatus)
        assert EmailStatus.QUEUED in statuses
        assert EmailStatus.SENT in statuses
        assert EmailStatus.FAILED in statuses
        assert EmailStatus.DELIVERED in statuses
        assert EmailStatus.BOUNCED in statuses

    def test_email_type_enum(self):
        """Test EmailType enum."""
        types = list(EmailType)
        assert EmailType.TASK_FAILURE in types
        assert EmailType.TASK_RECOVERY in types
        assert EmailType.WELCOME in types


class TestWorkerStatus:
    """Tests for WorkerStatus enum."""

    def test_all_statuses_defined(self):
        """Test all worker statuses are defined."""
        statuses = list(WorkerStatus)
        assert WorkerStatus.ONLINE in statuses
        assert WorkerStatus.OFFLINE in statuses
        assert WorkerStatus.BUSY in statuses


class TestUserModel:
    """Tests for User model."""

    def test_user_is_locked_false_when_no_locked_until(self):
        """Test is_locked returns False when locked_until is None."""
        user = User()
        user.locked_until = None
        assert user.is_locked() is False

    def test_user_is_locked_false_when_expired(self):
        """Test is_locked returns False when lockout expired."""
        user = User()
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert user.is_locked() is False

    def test_user_is_locked_true_when_active(self):
        """Test is_locked returns True when still locked."""
        user = User()
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        assert user.is_locked() is True


class TestWorkerModel:
    """Tests for Worker model."""

    def test_generate_api_key(self):
        """Test API key generation."""
        key = Worker.generate_api_key()
        assert key.startswith("wk_")
        assert len(key) > 10

    def test_get_key_prefix(self):
        """Test getting key prefix."""
        key = "wk_abcdefghij1234567890"
        prefix = Worker.get_key_prefix(key)
        assert len(prefix) == 11
        assert prefix == "wk_abcdefgh"

    def test_get_key_prefix_short_key(self):
        """Test getting prefix for short key."""
        key = "short"
        prefix = Worker.get_key_prefix(key)
        assert prefix == "short"


class TestEmailLogModel:
    """Tests for EmailLog model methods."""

    def test_mark_sent(self):
        """Test marking email as sent."""
        log = EmailLog()
        log.mark_sent("message-123", "postal-server")

        assert log.status == EmailStatus.SENT
        assert log.postal_message_id == "message-123"
        assert log.postal_server == "postal-server"
        assert log.sent_at is not None

    def test_mark_delivered(self):
        """Test marking email as delivered."""
        log = EmailLog()
        log.mark_delivered()

        assert log.status == EmailStatus.DELIVERED
        assert log.delivered_at is not None

    def test_mark_opened(self):
        """Test marking email as opened."""
        log = EmailLog()
        log.status = EmailStatus.SENT
        log.open_count = 0

        log.mark_opened()

        assert log.status == EmailStatus.OPENED
        assert log.opened_at is not None
        assert log.open_count == 1

    def test_mark_opened_increments_count(self):
        """Test that multiple opens increment count."""
        log = EmailLog()
        log.status = EmailStatus.SENT
        log.open_count = 5

        log.mark_opened()

        assert log.open_count == 6

    def test_mark_clicked(self):
        """Test marking email link as clicked."""
        log = EmailLog()
        log.status = EmailStatus.SENT
        log.click_count = 0

        log.mark_clicked()

        assert log.status == EmailStatus.CLICKED
        assert log.clicked_at is not None
        assert log.click_count == 1

    def test_mark_bounced(self):
        """Test marking email as bounced."""
        log = EmailLog()
        log.mark_bounced("hard", "550", "User not found")

        assert log.status == EmailStatus.BOUNCED
        assert log.bounced_at is not None
        assert log.bounce_type == "hard"
        assert log.bounce_code == "550"
        assert log.bounce_message == "User not found"

    def test_mark_failed(self):
        """Test marking email as failed."""
        log = EmailLog()
        log.mark_failed("Connection timeout")

        assert log.status == EmailStatus.FAILED
        assert log.failed_at is not None
        assert log.status_details == "Connection timeout"
