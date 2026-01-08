"""Telegram notification service."""
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
        text = (
            f"<b>Task Failed</b>\n\n"
            f"<b>Workspace:</b> {workspace_name}\n"
            f"<b>Task:</b> {task_name}\n"
            f"<b>Type:</b> {task_type}\n"
        )
        if error_message:
            text += f"<b>Error:</b> {error_message[:500]}\n"

        return await self.send_message(chat_id, text)

    async def send_task_recovery_notification(
        self,
        chat_id: int | str,
        task_name: str,
        task_type: str,
        workspace_name: str,
    ) -> bool:
        """Send a task recovery notification."""
        text = (
            f"<b>Task Recovered</b>\n\n"
            f"<b>Workspace:</b> {workspace_name}\n"
            f"<b>Task:</b> {task_name}\n"
            f"<b>Type:</b> {task_type}\n"
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
        text = (
            f"<b>Task Succeeded</b>\n\n"
            f"<b>Workspace:</b> {workspace_name}\n"
            f"<b>Task:</b> {task_name}\n"
            f"<b>Type:</b> {task_type}\n"
        )
        if duration_ms:
            text += f"<b>Duration:</b> {duration_ms}ms\n"

        return await self.send_message(chat_id, text)


# Global instance
telegram_service = TelegramService()
