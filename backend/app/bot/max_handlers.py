"""MAX bot handler using long polling."""

import asyncio

import httpx
import structlog

from app.config import settings
from app.services.i18n import t

logger = structlog.get_logger()

DEFAULT_LANG = "ru"
BASE_URL = "https://platform-api.max.ru"


async def handle_message(text: str, chat_id: int, token: str) -> None:
    """Handle an incoming message and reply."""
    command = (text or "").strip().split()[0].lower() if text else ""

    if command in ("/start", "/help"):
        reply = t(
            "max_bot.start.greeting",
            DEFAULT_LANG,
            chat_id=chat_id,
        )
    else:
        reply = t(
            "max_bot.start.greeting",
            DEFAULT_LANG,
            chat_id=chat_id,
        )

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BASE_URL}/messages",
                headers={"Authorization": token},
                params={"chat_id": chat_id},
                json={"text": reply, "format": "html"},
                timeout=10.0,
            )
    except Exception as e:
        logger.error("Failed to send Max bot reply", error=str(e), chat_id=chat_id)


async def handle_bot_started(chat_id: int, user_name: str | None, token: str) -> None:
    """Handle bot_started event — user pressed Start."""
    reply = t(
        "max_bot.start.greeting",
        DEFAULT_LANG,
        chat_id=chat_id,
    )
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BASE_URL}/messages",
                headers={"Authorization": token},
                params={"chat_id": chat_id},
                json={"text": reply, "format": "html"},
                timeout=10.0,
            )
    except Exception as e:
        logger.error("Failed to send Max bot_started reply", error=str(e), chat_id=chat_id)


async def poll_updates(token: str) -> None:
    """Long-poll for updates from Max API."""
    marker: int | None = None
    headers = {"Authorization": token}

    logger.info("Starting Max bot long polling")

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        while True:
            params: dict = {"timeout": 30, "types": "message_created,bot_started"}
            if marker is not None:
                params["marker"] = marker

            try:
                resp = await client.get(
                    f"{BASE_URL}/updates",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.TimeoutException:
                continue
            except Exception as e:
                logger.error("Max bot polling error", error=str(e))
                await asyncio.sleep(5)
                continue

            if "marker" in data and data["marker"] is not None:
                marker = data["marker"]

            for update in data.get("updates", []):
                update_type = update.get("update_type")

                try:
                    if update_type == "message_created":
                        msg = update.get("message", {})
                        body = msg.get("body", {})
                        text = body.get("text", "")
                        recipient = msg.get("recipient", {})
                        chat_id = recipient.get("chat_id")
                        if chat_id:
                            await handle_message(text, chat_id, token)

                    elif update_type == "bot_started":
                        chat_id = update.get("chat_id")
                        user = update.get("user", {})
                        user_name = user.get("name")
                        if chat_id:
                            await handle_bot_started(chat_id, user_name, token)
                except Exception as e:
                    logger.error(
                        "Error handling Max update",
                        error=str(e),
                        update_type=update_type,
                    )


async def run_max_bot() -> None:
    """Start the MAX bot."""
    token = settings.max_bot_token
    if not token:
        logger.warning("MAX_BOT_TOKEN not configured, skipping Max bot startup")
        return

    logger.info("Starting MAX bot")
    try:
        await poll_updates(token)
    except asyncio.CancelledError:
        logger.info("Max bot stopped")
    except Exception as e:
        logger.error("Max bot fatal error", error=str(e))
