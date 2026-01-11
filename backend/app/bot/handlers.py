"""Telegram bot command handlers."""
import re

import structlog
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.services.auth import AuthService

logger = structlog.get_logger()

# Initialize bot and dispatcher
bot = Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None
dp = Dispatcher()


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
    await message.answer(
        "👋 <b>Привет!</b> Я бот CronBox.\n\n"
        f"🆔 <b>Ваш Chat ID:</b> <code>{chat_id}</code>\n\n"
        "Я буду отправлять вам уведомления о выполнении задач.\n\n"
        "<b>Доступные команды:</b>\n"
        "/link <code>код</code> — привязать аккаунт CronBox\n"
        "/status — проверить статус привязки\n"
        "/help — показать справку\n\n"
        "💡 <b>Чтобы привязать аккаунт:</b>\n"
        "1. Зайдите в настройки CronBox\n"
        "2. Нажмите «Привязать Telegram»\n"
        "3. Скопируйте код и отправьте мне командой /link",
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    await message.answer(
        "📖 <b>Справка по CronBox Bot</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — начать работу с ботом\n"
        "/link <code>код</code> — привязать аккаунт CronBox\n"
        "/status — проверить статус привязки\n"
        "/unlink — отвязать аккаунт\n"
        "/help — показать эту справку\n\n"
        "<b>Уведомления:</b>\n"
        "После привязки аккаунта вы будете получать уведомления о:\n"
        "• Неудачных выполнениях задач\n"
        "• Восстановлении задач после ошибок\n"
        "• Успешных выполнениях (если включено)\n\n"
        "🌐 <a href=\"https://cronbox.ru\">cronbox.ru</a>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@dp.message(Command("link"))
async def cmd_link(message: Message):
    """Handle /link command."""
    if not message.text or not message.from_user:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "❌ Укажите код привязки.\n\n"
            "<b>Пример:</b> /link 123456\n\n"
            "Код можно получить в настройках CronBox → Telegram.",
            parse_mode="HTML",
        )
        return

    code = args[1].strip()
    await process_link_code(message, code)


async def process_link_code(message: Message, code: str):
    """Process account linking with code."""
    if not message.from_user:
        return

    # Validate code format (6 digits)
    if not re.match(r"^\d{6}$", code):
        await message.answer(
            "❌ Неверный формат кода.\n"
            "Код должен состоять из 6 цифр.",
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
                await message.answer(
                    f"✅ <b>Аккаунт успешно привязан!</b>\n\n"
                    f"Email: {user.email}\n"
                    f"Имя: {user.name}\n\n"
                    "Теперь вы будете получать уведомления о задачах в этот чат.",
                    parse_mode="HTML",
                )
                logger.info(
                    "Telegram account linked via bot",
                    user_id=str(user.id),
                    telegram_id=message.from_user.id,
                )
            else:
                await message.answer(
                    "❌ <b>Не удалось привязать аккаунт.</b>\n\n"
                    "Возможные причины:\n"
                    "• Код неверный или истёк\n"
                    "• Этот Telegram уже привязан к другому аккаунту\n\n"
                    "Получите новый код в настройках CronBox.",
                    parse_mode="HTML",
                )
    except Exception as e:
        logger.error("Error linking Telegram account", error=str(e), code=code)
        await message.answer(
            "❌ <b>Произошла ошибка.</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
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
            await message.answer(
                f"✅ <b>Аккаунт привязан</b>\n\n"
                f"Email: {user.email}\n"
                f"Имя: {user.name}\n"
                f"Статус: {'Активен' if user.is_active else 'Неактивен'}\n"
                f"Email подтверждён: {'Да' if user.email_verified else 'Нет'}",
                parse_mode="HTML",
            )
        else:
            await message.answer(
                "❌ <b>Аккаунт не привязан</b>\n\n"
                "Используйте команду /link для привязки аккаунта CronBox.",
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
                "❌ Ваш Telegram не привязан к аккаунту CronBox.",
                parse_mode="HTML",
            )
            return

        # Unlink account
        await user_repo.update(user, telegram_id=None, telegram_username=None)
        await db.commit()

        await message.answer(
            "✅ <b>Аккаунт отвязан</b>\n\n"
            "Вы больше не будете получать уведомления в Telegram.\n"
            "Для повторной привязки используйте /link.",
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
