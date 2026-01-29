"""Telegram bot command handlers."""

import structlog
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.services.i18n import t

logger = structlog.get_logger()

# Default language for bot (can be extended to support per-user language)
DEFAULT_BOT_LANG = "ru"

# Initialize bot and dispatcher
bot = Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None
dp = Dispatcher()


async def get_user_language(telegram_id: int) -> str:
    """Get user language from database or return default."""
    from app.db.repositories.users import UserRepository

    try:
        async with AsyncSessionLocal() as db:
            user_repo = UserRepository(db)
            user = await user_repo.get_by_telegram_id(telegram_id)
            if user and user.language:
                return user.language
    except Exception:
        pass
    return DEFAULT_BOT_LANG


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    if not message.from_user:
        return

    chat_id = message.from_user.id
    lang = await get_user_language(message.from_user.id)
    await message.answer(
        t("bot.start.greeting", lang, chat_id=chat_id),
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    if not message.from_user:
        return

    lang = await get_user_language(message.from_user.id)
    await message.answer(
        t("bot.help.title", lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def run_bot():
    """Start the Telegram bot polling."""
    if not bot:
        logger.warning("Telegram bot token not configured, skipping bot startup")
        return

    # Initialize Redis
    from app.core.redis import redis_client

    await redis_client.initialize()
    logger.info("Redis initialized for bot")

    # Delete webhook if exists (to avoid conflicts with polling)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted, ready for polling")
    except Exception as e:
        logger.warning(f"Failed to delete webhook: {e}")

    logger.info("Starting Telegram bot polling")
    try:
        await dp.start_polling(bot)
    finally:
        await redis_client.close()


async def stop_bot():
    """Stop the Telegram bot."""
    if bot:
        await bot.session.close()
        logger.info("Telegram bot stopped")
