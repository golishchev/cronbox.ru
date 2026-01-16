"""Tests for EmailService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEmailServiceInit:
    """Tests for EmailService initialization."""

    def test_init_with_settings(self):
        """Test EmailService initializes with settings."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            assert service.host == "smtp.example.com"
            assert service.port == 587
            assert service.user == "user@example.com"
            assert service.use_tls is True

    def test_is_configured_true(self):
        """Test is_configured returns True when configured."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            assert service.is_configured is True

    def test_is_configured_false_no_host(self):
        """Test is_configured returns False when no host."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = None
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            assert service.is_configured is False

    def test_is_configured_false_no_user(self):
        """Test is_configured returns False when no user."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = None
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            assert service.is_configured is False


class TestEmailServiceSendEmail:
    """Tests for EmailService.send_email."""

    @pytest.mark.asyncio
    async def test_send_email_not_configured(self):
        """Test send_email returns False when not configured."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = None
            mock_settings.smtp_port = None
            mock_settings.smtp_user = None
            mock_settings.smtp_password = None
            mock_settings.smtp_use_tls = False
            mock_settings.email_from = None

            from app.services.email import EmailService

            service = EmailService()

            result = await service.send_email(
                to="test@example.com",
                subject="Test",
                html="<p>Test</p>",
            )

            assert result is False

    @pytest.mark.asyncio
    @patch("app.services.email.aiosmtplib.send")
    async def test_send_email_success(self, mock_send):
        """Test send_email success."""
        mock_send.return_value = None

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            result = await service.send_email(
                to="test@example.com",
                subject="Test Subject",
                html="<p>Test body</p>",
                text="Test body",
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email.aiosmtplib.send")
    async def test_send_email_list_recipients(self, mock_send):
        """Test send_email with list of recipients."""
        mock_send.return_value = None

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            result = await service.send_email(
                to=["test1@example.com", "test2@example.com"],
                subject="Test Subject",
                html="<p>Test body</p>",
            )

            assert result is True

    @pytest.mark.asyncio
    @patch("app.services.email.aiosmtplib.send")
    async def test_send_email_failure(self, mock_send):
        """Test send_email handles exception."""
        mock_send.side_effect = Exception("SMTP connection failed")

        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            result = await service.send_email(
                to="test@example.com",
                subject="Test",
                html="<p>Test</p>",
            )

            assert result is False


class TestEmailServiceTaskNotifications:
    """Tests for task notification methods."""

    @pytest.mark.asyncio
    async def test_send_task_failure_notification(self):
        """Test send_task_failure_notification."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                result = await service.send_task_failure_notification(
                    to="test@example.com",
                    task_name="My Task",
                    task_type="cron",
                    error_message="Connection timeout",
                    workspace_name="Test Workspace",
                    task_url="https://api.example.com/webhook",
                )

                assert result is True
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert "Task Failed" in call_args[0][1]  # subject
                assert "My Task" in call_args[0][2]  # html
                assert "Connection timeout" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_send_task_failure_notification_no_url(self):
        """Test send_task_failure_notification without URL."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                result = await service.send_task_failure_notification(
                    to="test@example.com",
                    task_name="My Task",
                    task_type="delayed",
                    error_message=None,
                    workspace_name="Test Workspace",
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_send_task_recovery_notification(self):
        """Test send_task_recovery_notification."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                result = await service.send_task_recovery_notification(
                    to="test@example.com",
                    task_name="My Task",
                    task_type="cron",
                    workspace_name="Test Workspace",
                )

                assert result is True
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert "Recovered" in call_args[0][1]  # subject
                assert "Back to normal" in call_args[0][2]  # html

    @pytest.mark.asyncio
    async def test_send_task_success_notification(self):
        """Test send_task_success_notification."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                result = await service.send_task_success_notification(
                    to="test@example.com",
                    task_name="My Task",
                    task_type="cron",
                    workspace_name="Test Workspace",
                    duration_ms=150,
                )

                assert result is True
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert "Succeeded" in call_args[0][1]  # subject
                assert "150ms" in call_args[0][2]  # html

    @pytest.mark.asyncio
    async def test_send_task_success_notification_no_duration(self):
        """Test send_task_success_notification without duration."""
        with patch("app.services.email.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@example.com"
            mock_settings.smtp_password = "password"
            mock_settings.smtp_use_tls = True
            mock_settings.email_from = "noreply@example.com"

            from app.services.email import EmailService

            service = EmailService()

            with patch.object(service, "send_email", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                result = await service.send_task_success_notification(
                    to="test@example.com",
                    task_name="My Task",
                    task_type="cron",
                    workspace_name="Test Workspace",
                )

                assert result is True


class TestEmailServiceGlobalInstance:
    """Tests for global email_service instance."""

    def test_global_instance_exists(self):
        """Test global email_service instance exists."""
        from app.services.email import email_service

        assert email_service is not None
