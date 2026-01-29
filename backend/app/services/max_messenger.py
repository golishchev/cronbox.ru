"""MAX notification service."""

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class MaxMessengerService:
    """Service for sending MAX notifications."""

    def __init__(self):
        self.bot_token = settings.max_bot_token
        self.base_url = "https://platform-api.max.ru"

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        format: str = "html",
    ) -> bool:
        """Send a message to a MAX chat."""
        if not self.is_configured:
            logger.warning("MAX bot not configured")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={"Authorization": self.bot_token},
                    params={"chat_id": chat_id},
                    json={
                        "text": text,
                        "format": format,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to send MAX message", error=str(e), chat_id=chat_id)
            return False


# Global instance
max_messenger_service = MaxMessengerService()
