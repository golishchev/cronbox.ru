"""Telegram notification service."""

from html import escape

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class TelegramService:
    """Service for sending Telegram notifications."""

    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token)

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a message to a Telegram chat."""
        if not self.is_configured:
            logger.warning("Telegram bot not configured")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to send Telegram message", error=str(e), chat_id=chat_id)
            return False

    async def send_task_failure_notification(
        self,
        chat_id: int | str,
        task_name: str,
        task_type: str,
        error_message: str | None,
        workspace_name: str,
    ) -> bool:
        """Send a task failure notification."""
        # Escape user-controlled inputs to prevent HTML injection
        safe_workspace_name = escape(workspace_name)
        safe_task_name = escape(task_name)
        safe_task_type = escape(task_type)

        text = (
            f"<b>Task Failed</b>\n\n"
            f"<b>Workspace:</b> {safe_workspace_name}\n"
            f"<b>Task:</b> {safe_task_name}\n"
            f"<b>Type:</b> {safe_task_type}\n"
        )
        if error_message:
            safe_error_message = escape(error_message[:500])
            text += f"<b>Error:</b> {safe_error_message}\n"

        return await self.send_message(chat_id, text)

    async def send_task_recovery_notification(
        self,
        chat_id: int | str,
        task_name: str,
        task_type: str,
        workspace_name: str,
    ) -> bool:
        """Send a task recovery notification."""
        # Escape user-controlled inputs to prevent HTML injection
        safe_workspace_name = escape(workspace_name)
        safe_task_name = escape(task_name)
        safe_task_type = escape(task_type)

        text = (
            f"<b>Task Recovered</b>\n\n"
            f"<b>Workspace:</b> {safe_workspace_name}\n"
            f"<b>Task:</b> {safe_task_name}\n"
            f"<b>Type:</b> {safe_task_type}\n"
            f"<b>Status:</b> Back to normal"
        )
        return await self.send_message(chat_id, text)

    async def send_task_success_notification(
        self,
        chat_id: int | str,
        task_name: str,
        task_type: str,
        workspace_name: str,
        duration_ms: int | None,
    ) -> bool:
        """Send a task success notification."""
        # Escape user-controlled inputs to prevent HTML injection
        safe_workspace_name = escape(workspace_name)
        safe_task_name = escape(task_name)
        safe_task_type = escape(task_type)

        text = (
            f"<b>Task Succeeded</b>\n\n"
            f"<b>Workspace:</b> {safe_workspace_name}\n"
            f"<b>Task:</b> {safe_task_name}\n"
            f"<b>Type:</b> {safe_task_type}\n"
        )
        if duration_ms:
            text += f"<b>Duration:</b> {duration_ms}ms\n"

        return await self.send_message(chat_id, text)

    async def send_subscription_expiring_notification(
        self,
        chat_id: int | str,
        workspace_name: str,
        days_remaining: int,
        expiration_date: str,
    ) -> bool:
        """Send a subscription expiring notification."""
        # Escape user-controlled inputs to prevent HTML injection
        safe_workspace_name = escape(workspace_name)
        safe_expiration_date = escape(expiration_date)

        text = (
            f"<b>Subscription Expiring Soon</b>\n\n"
            f"<b>Workspace:</b> {safe_workspace_name}\n"
            f"<b>Expires in:</b> {days_remaining} day(s)\n"
            f"<b>Expiration date:</b> {safe_expiration_date}\n\n"
            f"Renew your subscription to avoid service interruption."
        )
        return await self.send_message(chat_id, text)

    async def send_subscription_expired_notification(
        self,
        chat_id: int | str,
        workspace_name: str,
        tasks_paused: int,
    ) -> bool:
        """Send a subscription expired notification."""
        # Escape user-controlled inputs to prevent HTML injection
        safe_workspace_name = escape(workspace_name)

        text = (
            f"<b>Subscription Expired</b>\n\n"
            f"<b>Workspace:</b> {safe_workspace_name}\n"
            f"Your subscription has expired and workspace has been downgraded to the free plan.\n"
        )
        if tasks_paused > 0:
            text += f"<b>Tasks paused:</b> {tasks_paused} (exceeded free plan limit)\n"
        text += "\nRenew your subscription to restore full access."

        return await self.send_message(chat_id, text)

    async def send_new_user_notification(
        self,
        user_email: str,
        user_name: str,
        registration_method: str = "email",
    ) -> bool:
        """Send notification to admin about new user registration."""
        admin_chat_id = settings.admin_telegram_id
        if not admin_chat_id:
            logger.debug("Admin Telegram ID not configured, skipping notification")
            return False

        # Escape user-controlled inputs to prevent HTML injection
        safe_user_email = escape(user_email)
        safe_user_name = escape(user_name)
        safe_registration_method = escape(registration_method)

        text = (
            f"<b>New User Registered</b>\n\n"
            f"<b>Email:</b> {safe_user_email}\n"
            f"<b>Name:</b> {safe_user_name}\n"
            f"<b>Method:</b> {safe_registration_method}"
        )
        return await self.send_message(admin_chat_id, text)


# Global instance
telegram_service = TelegramService()
