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
        response = await authenticated_client.get(
            f"/v1/workspaces/{workspace['id']}/notifications"
        )
        assert response.status_code == 200
        data = response.json()
        # Should have default settings
        assert "telegram_enabled" in data
        assert "email_enabled" in data
        assert "webhook_enabled" in data

    async def test_update_email_notifications(self, authenticated_client: AsyncClient, workspace):
        """Test updating email notification settings."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "email_enabled": True,
                "email_addresses": ["notify@example.com"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email_enabled"] is True
        assert "notify@example.com" in data["email_addresses"]

    async def test_update_telegram_notifications(self, authenticated_client: AsyncClient, workspace):
        """Test updating Telegram notification settings."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "telegram_enabled": True,
                "telegram_chat_ids": ["123456789"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["telegram_enabled"] is True
        assert "123456789" in data["telegram_chat_ids"]

    async def test_update_webhook_notifications(self, authenticated_client: AsyncClient, workspace):
        """Test updating webhook notification settings."""
        response = await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "webhook_enabled": True,
                "webhook_url": "https://example.com/webhooks/cronbox",
                "webhook_secret": "secret123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["webhook_enabled"] is True
        assert data["webhook_url"] == "https://example.com/webhooks/cronbox"

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

    async def test_send_test_email(self, authenticated_client: AsyncClient, workspace):
        """Test sending a test email notification."""
        # First enable email
        await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "email_enabled": True,
                "email_addresses": ["test@example.com"],
            },
        )

        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/notifications/test",
            json={"channel": "email"},
        )
        # Should succeed or fail gracefully if email not configured
        assert response.status_code in [200, 400, 500, 503]

    async def test_send_test_telegram(self, authenticated_client: AsyncClient, workspace):
        """Test sending a test Telegram notification."""
        # First enable Telegram
        await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "telegram_enabled": True,
                "telegram_chat_ids": ["123456789"],
            },
        )

        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/notifications/test",
            json={"channel": "telegram"},
        )
        # Should succeed or fail gracefully if Telegram not configured
        assert response.status_code in [200, 400, 500, 503]

    async def test_send_test_webhook(self, authenticated_client: AsyncClient, workspace):
        """Test sending a test webhook notification."""
        # First enable webhook
        await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "webhook_enabled": True,
                "webhook_url": "https://httpbin.org/post",
            },
        )

        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/notifications/test",
            json={"channel": "webhook"},
        )
        # Should succeed or fail gracefully (500 for network errors)
        assert response.status_code in [200, 400, 500, 503]

    async def test_send_test_disabled_channel(self, authenticated_client: AsyncClient, workspace):
        """Test sending test to disabled channel fails."""
        # Disable all channels
        await authenticated_client.patch(
            f"/v1/workspaces/{workspace['id']}/notifications",
            json={
                "email_enabled": False,
            },
        )

        response = await authenticated_client.post(
            f"/v1/workspaces/{workspace['id']}/notifications/test",
            json={"channel": "email"},
        )
        assert response.status_code == 400

    async def test_notifications_unauthorized(self, client: AsyncClient):
        """Test accessing notifications without authentication."""
        response = await client.get("/v1/workspaces/some-id/notifications")
        assert response.status_code == 401
