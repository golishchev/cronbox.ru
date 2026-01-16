"""Template service for multilingual notification templates."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_template import NotificationChannel, NotificationTemplate
from app.models.workspace import Workspace

logger = structlog.get_logger()

# Default templates for seeding database
DEFAULT_TEMPLATES: list[dict] = [
    # ==================== TASK FAILURE ====================
    # English - Email
    {
        "code": "task_failure",
        "language": "en",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Task Failed: {task_name}",
        "body": """<h2>Task Failed</h2>
<p><strong>Workspace:</strong> {workspace_name}</p>
<p><strong>Task:</strong> {task_name}</p>
<p><strong>Type:</strong> {task_type}</p>
<p><strong>Error:</strong> {error_message}</p>
<p>Please check your task configuration and try again.</p>""",
        "description": "Email notification when a task execution fails",
        "variables": ["workspace_name", "task_name", "task_type", "error_message"],
    },
    # English - Telegram
    {
        "code": "task_failure",
        "language": "en",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Task Failed</b>

<b>Workspace:</b> {workspace_name}
<b>Task:</b> {task_name}
<b>Type:</b> {task_type}
<b>Error:</b> {error_message}""",
        "description": "Telegram notification when a task execution fails",
        "variables": ["workspace_name", "task_name", "task_type", "error_message"],
    },
    # Russian - Email
    {
        "code": "task_failure",
        "language": "ru",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Ошибка задачи: {task_name}",
        "body": """<h2>Ошибка выполнения задачи</h2>
<p><strong>Рабочее пространство:</strong> {workspace_name}</p>
<p><strong>Задача:</strong> {task_name}</p>
<p><strong>Тип:</strong> {task_type}</p>
<p><strong>Ошибка:</strong> {error_message}</p>
<p>Пожалуйста, проверьте настройки задачи и попробуйте снова.</p>""",
        "description": "Email уведомление об ошибке выполнения задачи",
        "variables": ["workspace_name", "task_name", "task_type", "error_message"],
    },
    # Russian - Telegram
    {
        "code": "task_failure",
        "language": "ru",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Ошибка задачи</b>

<b>Пространство:</b> {workspace_name}
<b>Задача:</b> {task_name}
<b>Тип:</b> {task_type}
<b>Ошибка:</b> {error_message}""",
        "description": "Telegram уведомление об ошибке выполнения задачи",
        "variables": ["workspace_name", "task_name", "task_type", "error_message"],
    },
    # ==================== TASK RECOVERY ====================
    # English - Email
    {
        "code": "task_recovery",
        "language": "en",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Task Recovered: {task_name}",
        "body": """<h2>Task Recovered</h2>
<p><strong>Workspace:</strong> {workspace_name}</p>
<p><strong>Task:</strong> {task_name}</p>
<p><strong>Type:</strong> {task_type}</p>
<p><strong>Status:</strong> Back to normal</p>
<p>Your task is now executing successfully again.</p>""",
        "description": "Email notification when a task recovers from failure",
        "variables": ["workspace_name", "task_name", "task_type"],
    },
    # English - Telegram
    {
        "code": "task_recovery",
        "language": "en",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Task Recovered</b>

<b>Workspace:</b> {workspace_name}
<b>Task:</b> {task_name}
<b>Type:</b> {task_type}
<b>Status:</b> Back to normal""",
        "description": "Telegram notification when a task recovers from failure",
        "variables": ["workspace_name", "task_name", "task_type"],
    },
    # Russian - Email
    {
        "code": "task_recovery",
        "language": "ru",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Задача восстановлена: {task_name}",
        "body": """<h2>Задача восстановлена</h2>
<p><strong>Рабочее пространство:</strong> {workspace_name}</p>
<p><strong>Задача:</strong> {task_name}</p>
<p><strong>Тип:</strong> {task_type}</p>
<p><strong>Статус:</strong> Работает нормально</p>
<p>Ваша задача снова выполняется успешно.</p>""",
        "description": "Email уведомление о восстановлении задачи",
        "variables": ["workspace_name", "task_name", "task_type"],
    },
    # Russian - Telegram
    {
        "code": "task_recovery",
        "language": "ru",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Задача восстановлена</b>

<b>Пространство:</b> {workspace_name}
<b>Задача:</b> {task_name}
<b>Тип:</b> {task_type}
<b>Статус:</b> Работает нормально""",
        "description": "Telegram уведомление о восстановлении задачи",
        "variables": ["workspace_name", "task_name", "task_type"],
    },
    # ==================== TASK SUCCESS ====================
    # English - Email
    {
        "code": "task_success",
        "language": "en",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Task Succeeded: {task_name}",
        "body": """<h2>Task Succeeded</h2>
<p><strong>Workspace:</strong> {workspace_name}</p>
<p><strong>Task:</strong> {task_name}</p>
<p><strong>Type:</strong> {task_type}</p>
<p><strong>Duration:</strong> {duration_ms}ms</p>""",
        "description": "Email notification when a task executes successfully",
        "variables": ["workspace_name", "task_name", "task_type", "duration_ms"],
    },
    # English - Telegram
    {
        "code": "task_success",
        "language": "en",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Task Succeeded</b>

<b>Workspace:</b> {workspace_name}
<b>Task:</b> {task_name}
<b>Type:</b> {task_type}
<b>Duration:</b> {duration_ms}ms""",
        "description": "Telegram notification when a task executes successfully",
        "variables": ["workspace_name", "task_name", "task_type", "duration_ms"],
    },
    # Russian - Email
    {
        "code": "task_success",
        "language": "ru",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Задача выполнена: {task_name}",
        "body": """<h2>Задача выполнена успешно</h2>
<p><strong>Рабочее пространство:</strong> {workspace_name}</p>
<p><strong>Задача:</strong> {task_name}</p>
<p><strong>Тип:</strong> {task_type}</p>
<p><strong>Время выполнения:</strong> {duration_ms}мс</p>""",
        "description": "Email уведомление об успешном выполнении задачи",
        "variables": ["workspace_name", "task_name", "task_type", "duration_ms"],
    },
    # Russian - Telegram
    {
        "code": "task_success",
        "language": "ru",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Задача выполнена</b>

<b>Пространство:</b> {workspace_name}
<b>Задача:</b> {task_name}
<b>Тип:</b> {task_type}
<b>Время:</b> {duration_ms}мс""",
        "description": "Telegram уведомление об успешном выполнении задачи",
        "variables": ["workspace_name", "task_name", "task_type", "duration_ms"],
    },
    # ==================== SUBSCRIPTION EXPIRING ====================
    # English - Email
    {
        "code": "subscription_expiring",
        "language": "en",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Subscription expiring in {days_remaining} day(s)",
        "body": """<h2>Subscription Expiring Soon</h2>
<p><strong>Workspace:</strong> {workspace_name}</p>
<p><strong>Expires in:</strong> {days_remaining} day(s)</p>
<p><strong>Expiration date:</strong> {expiration_date}</p>
<p>Renew your subscription to avoid service interruption.</p>""",
        "description": "Email notification when subscription is about to expire",
        "variables": ["workspace_name", "days_remaining", "expiration_date"],
    },
    # English - Telegram
    {
        "code": "subscription_expiring",
        "language": "en",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Subscription Expiring Soon</b>

<b>Workspace:</b> {workspace_name}
<b>Expires in:</b> {days_remaining} day(s)
<b>Expiration date:</b> {expiration_date}

Renew your subscription to avoid service interruption.""",
        "description": "Telegram notification when subscription is about to expire",
        "variables": ["workspace_name", "days_remaining", "expiration_date"],
    },
    # Russian - Email
    {
        "code": "subscription_expiring",
        "language": "ru",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Подписка истекает через {days_remaining} дн.",
        "body": """<h2>Подписка скоро истекает</h2>
<p><strong>Рабочее пространство:</strong> {workspace_name}</p>
<p><strong>Истекает через:</strong> {days_remaining} дн.</p>
<p><strong>Дата истечения:</strong> {expiration_date}</p>
<p>Продлите подписку, чтобы избежать прерывания сервиса.</p>""",
        "description": "Email уведомление о скором истечении подписки",
        "variables": ["workspace_name", "days_remaining", "expiration_date"],
    },
    # Russian - Telegram
    {
        "code": "subscription_expiring",
        "language": "ru",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Подписка скоро истекает</b>

<b>Пространство:</b> {workspace_name}
<b>Истекает через:</b> {days_remaining} дн.
<b>Дата истечения:</b> {expiration_date}

Продлите подписку, чтобы избежать прерывания сервиса.""",
        "description": "Telegram уведомление о скором истечении подписки",
        "variables": ["workspace_name", "days_remaining", "expiration_date"],
    },
    # ==================== SUBSCRIPTION EXPIRED ====================
    # English - Email
    {
        "code": "subscription_expired",
        "language": "en",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Subscription expired",
        "body": """<h2>Subscription Expired</h2>
<p><strong>Workspace:</strong> {workspace_name}</p>
<p>Your subscription has expired and workspace has been downgraded to the free plan.</p>
<p><strong>Tasks paused:</strong> {tasks_paused} (exceeded free plan limit)</p>
<p>Renew your subscription to restore full access.</p>""",
        "description": "Email notification when subscription has expired",
        "variables": ["workspace_name", "tasks_paused"],
    },
    # English - Telegram
    {
        "code": "subscription_expired",
        "language": "en",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Subscription Expired</b>

<b>Workspace:</b> {workspace_name}
Your subscription has expired and workspace has been downgraded to the free plan.
<b>Tasks paused:</b> {tasks_paused} (exceeded free plan limit)

Renew your subscription to restore full access.""",
        "description": "Telegram notification when subscription has expired",
        "variables": ["workspace_name", "tasks_paused"],
    },
    # Russian - Email
    {
        "code": "subscription_expired",
        "language": "ru",
        "channel": NotificationChannel.EMAIL,
        "subject": "[CronBox] Подписка истекла",
        "body": """<h2>Подписка истекла</h2>
<p><strong>Рабочее пространство:</strong> {workspace_name}</p>
<p>Ваша подписка истекла, и рабочее пространство переведено на бесплатный план.</p>
<p><strong>Задач приостановлено:</strong> {tasks_paused} (превышен лимит бесплатного плана)</p>
<p>Продлите подписку, чтобы восстановить полный доступ.</p>""",
        "description": "Email уведомление об истечении подписки",
        "variables": ["workspace_name", "tasks_paused"],
    },
    # Russian - Telegram
    {
        "code": "subscription_expired",
        "language": "ru",
        "channel": NotificationChannel.TELEGRAM,
        "subject": None,
        "body": """<b>Подписка истекла</b>

<b>Пространство:</b> {workspace_name}
Ваша подписка истекла, пространство переведено на бесплатный план.
<b>Задач приостановлено:</b> {tasks_paused} (превышен лимит)

Продлите подписку для восстановления доступа.""",
        "description": "Telegram уведомление об истечении подписки",
        "variables": ["workspace_name", "tasks_paused"],
    },
]


class TemplateService:
    """Service for managing notification templates."""

    async def get_template(
        self,
        db: AsyncSession,
        code: str,
        language: str,
        channel: NotificationChannel | str,
    ) -> NotificationTemplate | None:
        """
        Get template by code, language and channel.
        Falls back to 'en' if template for requested language not found.
        """
        if isinstance(channel, str):
            channel = NotificationChannel(channel)

        # Try to get template for requested language
        result = await db.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.code == code,
                NotificationTemplate.language == language,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()

        # Fallback to English if not found
        if template is None and language != "en":
            result = await db.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.code == code,
                    NotificationTemplate.language == "en",
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.is_active.is_(True),
                )
            )
            template = result.scalar_one_or_none()

        return template

    def render(self, template: NotificationTemplate | None, variables: dict) -> tuple[str | None, str]:
        """
        Render template with variables using str.format().
        Returns (subject, body). Subject is None for Telegram.
        """
        if template is None:
            return None, ""

        # Render body
        try:
            body = template.body.format(**variables)
        except KeyError as e:
            logger.warning(
                "Missing variable in template",
                template_code=template.code,
                missing_var=str(e),
            )
            body = template.body

        # Render subject (only for email)
        subject = None
        if template.subject:
            try:
                subject = template.subject.format(**variables)
            except KeyError as e:
                logger.warning(
                    "Missing variable in template subject",
                    template_code=template.code,
                    missing_var=str(e),
                )
                subject = template.subject

        return subject, body

    async def get_user_language(self, db: AsyncSession, workspace_id: UUID) -> str:
        """Get preferred language from workspace owner."""
        result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        workspace = result.scalar_one_or_none()

        if workspace and workspace.owner:
            return workspace.owner.preferred_language or "en"

        return "en"

    async def seed_default_templates(self, db: AsyncSession) -> int:
        """
        Seed default templates into database.
        Only creates templates that don't exist (by code/language/channel).
        Returns count of created templates.
        """
        created = 0

        for template_data in DEFAULT_TEMPLATES:
            # Check if template exists
            result = await db.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.code == template_data["code"],
                    NotificationTemplate.language == template_data["language"],
                    NotificationTemplate.channel == template_data["channel"],
                )
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                template = NotificationTemplate(**template_data)
                db.add(template)
                created += 1

        if created > 0:
            await db.commit()
            logger.info("Seeded notification templates", count=created)

        return created

    async def get_all_templates(self, db: AsyncSession) -> list[NotificationTemplate]:
        """Get all templates for admin UI."""
        result = await db.execute(
            select(NotificationTemplate).order_by(
                NotificationTemplate.code,
                NotificationTemplate.language,
                NotificationTemplate.channel,
            )
        )
        return list(result.scalars().all())

    async def get_template_by_id(self, db: AsyncSession, template_id: UUID) -> NotificationTemplate | None:
        """Get template by ID."""
        return await db.get(NotificationTemplate, template_id)

    async def update_template(
        self,
        db: AsyncSession,
        template: NotificationTemplate,
        subject: str | None = None,
        body: str | None = None,
        is_active: bool | None = None,
    ) -> NotificationTemplate:
        """Update template content."""
        if subject is not None:
            template.subject = subject
        if body is not None:
            template.body = body
        if is_active is not None:
            template.is_active = is_active

        await db.commit()
        await db.refresh(template)
        return template

    def get_default_template(self, code: str, language: str, channel: NotificationChannel | str) -> dict | None:
        """Get default template data for reset functionality."""
        if isinstance(channel, str):
            channel = NotificationChannel(channel)

        for template in DEFAULT_TEMPLATES:
            if template["code"] == code and template["language"] == language and template["channel"] == channel:
                return template
        return None


# Global instance
template_service = TemplateService()
