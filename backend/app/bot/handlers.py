"""Telegram bot command handlers."""
import re

import structlog
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.services.auth import AuthService
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
    if not message.text or not message.from_user:
        return

    # Check if deep link with code
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        code = args[1].strip()
        # Try to link account with this code
        await process_link_code(message, code)
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


@dp.message(Command("link"))
async def cmd_link(message: Message):
    """Handle /link command."""
    if not message.text or not message.from_user:
        return

    lang = await get_user_language(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            t("bot.link.missing_code", lang),
            parse_mode="HTML",
        )
        return

    code = args[1].strip()
    await process_link_code(message, code)


async def process_link_code(message: Message, code: str):
    """Process account linking with code."""
    if not message.from_user:
        return

    lang = await get_user_language(message.from_user.id)

    # Validate code format (6 digits)
    if not re.match(r"^\d{6}$", code):
        await message.answer(
            t("bot.link.invalid_format", lang),
            parse_mode="HTML",
        )
        return

    try:
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(db)
            user = await auth_service.link_telegram_by_code(
                code=code,
                telegram_id=message.from_user.id,
                telegram_username=message.from_user.username,
            )

            if user:
                await db.commit()
                # Use user's language after linking
                user_lang = user.language or lang
                await message.answer(
                    t("bot.link.success", user_lang, email=user.email, name=user.name),
                    parse_mode="HTML",
                )
                logger.info(
                    "Telegram account linked via bot",
                    user_id=str(user.id),
                    telegram_id=message.from_user.id,
                )
            else:
                await message.answer(
                    t("bot.link.failed", lang),
                    parse_mode="HTML",
                )
    except Exception as e:
        logger.error("Error linking Telegram account", error=str(e), code=code)
        await message.answer(
            t("bot.link.error", lang),
            parse_mode="HTML",
        )


@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Handle /status command."""
    if not message.from_user:
        return

    from app.db.repositories.users import UserRepository

    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_telegram_id(message.from_user.id)

        if user:
            lang = user.language or DEFAULT_BOT_LANG
            status_text = t("bot.status.active", lang) if user.is_active else t("bot.status.inactive", lang)
            verified_text = t("bot.status.yes", lang) if user.email_verified else t("bot.status.no", lang)
            await message.answer(
                t("bot.status.linked", lang, email=user.email, name=user.name, status=status_text, email_verified=verified_text),
                parse_mode="HTML",
            )
        else:
            lang = DEFAULT_BOT_LANG
            await message.answer(
                t("bot.status.not_linked", lang),
                parse_mode="HTML",
            )


@dp.message(Command("unlink"))
async def cmd_unlink(message: Message):
    """Handle /unlink command."""
    if not message.from_user:
        return

    from app.db.repositories.users import UserRepository

    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_telegram_id(message.from_user.id)

        if not user:
            await message.answer(
                t("bot.unlink.not_linked", DEFAULT_BOT_LANG),
                parse_mode="HTML",
            )
            return

        lang = user.language or DEFAULT_BOT_LANG

        # Unlink account
        await user_repo.update(user, telegram_id=None, telegram_username=None)
        await db.commit()

        await message.answer(
            t("bot.unlink.success", lang),
            parse_mode="HTML",
        )
        logger.info(
            "Telegram account unlinked via bot",
            user_id=str(user.id),
            telegram_id=message.from_user.id,
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

    logger.info("Starting Telegram bot")
    try:
        await dp.start_polling(bot)
    finally:
        await redis_client.close()


async def stop_bot():
    """Stop the Telegram bot."""
    if bot:
        await bot.session.close()
        logger.info("Telegram bot stopped")
