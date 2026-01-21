"""Tests for notifications API."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def workspace(authenticated_client: AsyncClient):
    """Create a test workspace."""
    response = await authenticated_client.post(
        "/v1/workspaces",
        json={
            "name": "Notifications Test Workspace",
            "slug": "notifications-test",
        },
    )
    return response.json()


class TestNotificationSettings:
    """Tests for notification settings endpoints."""

    async def test_get_notification_settings(self, authenticated_client: AsyncClient, workspace):
        """Test getting notification settings."""
        response = await authenticated_client.get(f"/v1/workspaces/{workspace['id']}/notifications")
        assert response.status_code == 200
        data = response.json()
        # Should have default settings
        assert "telegram_enabled" in data
        assert "email_enabled" in data
        assert "webhook_enabled" in data

    async def test_update_email_notifications(self, authenticated_client: AsyncClient, workspace):
        """Test that email notifications are blocked on Free plan."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "email_enabled": True,
                "email_addresses": ["notify@example.com"],
            },
        )
        # Free plan doesn't allow email notifications
        assert response.status_code == 403

    async def test_update_telegram_notifications(self, authenticated_client: AsyncClient, workspace):
        """Test that Telegram notifications are blocked on Free plan."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "telegram_enabled": True,
                "telegram_chat_ids": ["123456789"],
            },
        )
        # Free plan doesn't allow Telegram notifications
        assert response.status_code == 403

    async def test_update_webhook_notifications(self, authenticated_client: AsyncClient, workspace):
        """Test that webhook notifications are blocked on Free plan."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "webhook_enabled": True,
                "webhook_url": "https://example.com/webhooks/cronbox",
                "webhook_secret": "secret123",
            },
        )
        # Free plan doesn't allow webhook notifications
        assert response.status_code == 403

    async def test_update_email_addresses_without_enabling(self, authenticated_client: AsyncClient, workspace):
        """Test updating email addresses without enabling email notifications (should work)."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "email_addresses": ["notify@example.com"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "notify@example.com" in data["email_addresses"]

    async def test_update_notification_events(self, authenticated_client: AsyncClient, workspace):
        """Test updating which events trigger notifications."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "notify_on_failure": True,
                "notify_on_recovery": True,
                "notify_on_success": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["notify_on_failure"] is True
        assert data["notify_on_recovery"] is True
        assert data["notify_on_success"] is False

    async def test_disable_all_notifications(self, authenticated_client: AsyncClient, workspace):
        """Test disabling all notification channels."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "telegram_enabled": False,
                "email_enabled": False,
                "webhook_enabled": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_enabled"] is False
        assert data["email_enabled"] is False
        assert data["webhook_enabled"] is False


class TestTestNotifications:
    """Tests for sending test notifications."""

    async def test_send_test_email_disabled(self, authenticated_client: AsyncClient, workspace):
        """Test sending a test email notification when disabled fails."""
        # Email is not enabled on Free plan
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/notifications/test",
            json={"channel": "email"},
        )
        # Should fail because email is not enabled
        assert response.status_code == 400

    async def test_send_test_telegram_disabled(self, authenticated_client: AsyncClient, workspace):
        """Test sending a test Telegram notification when disabled fails."""
        # Telegram is not enabled on Free plan
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/notifications/test",
            json={"channel": "telegram"},
        )
        # Should fail because Telegram is not enabled
        assert response.status_code == 400

    async def test_send_test_webhook_disabled(self, authenticated_client: AsyncClient, workspace):
        """Test sending a test webhook notification when disabled fails."""
        # Webhook is not enabled on Free plan
        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/notifications/test",
            json={"channel": "webhook"},
        )
        # Should fail because webhook is not enabled
        assert response.status_code == 400

    async def test_notifications_unauthorized(self, client: AsyncClient):
        """Test accessing notifications without authentication."""
        response = await client.get("/v1/workspaces/some-id/notifications")
        assert response.status_code == 401
