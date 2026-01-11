"""Main notification orchestrator service."""
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.notification_settings import NotificationSettings
from app.models.notification_template import NotificationChannel
from app.models.workspace import Workspace
from app.services.email import email_service  # SMTP fallback
from app.services.postal import postal_service
from app.services.telegram import telegram_service
from app.services.template_service import template_service

logger = structlog.get_logger()


class NotificationService:
    """Orchestrates sending notifications through various channels."""

    async def get_settings(
        self,
        db: AsyncSession,
        workspace_id: UUID,
    ) -> NotificationSettings | None:
        """Get notification settings for a workspace."""
        result = await db.execute(
            select(NotificationSettings).where(
                NotificationSettings.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_settings(
        self,
        db: AsyncSession,
        workspace_id: UUID,
    ) -> NotificationSettings:
        """Get or create notification settings for a workspace."""
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            settings = NotificationSettings(workspace_id=workspace_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)
        return settings

    async def _get_workspace_info(
        self, db: AsyncSession, workspace_id: UUID
    ) -> tuple[str, str]:
        """Get workspace name and owner's preferred language."""
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()

        workspace_name = workspace.name if workspace else "Unknown"
        language = "en"
        if workspace and workspace.owner:
            language = workspace.owner.preferred_language or "en"

        return workspace_name, language

    async def _send_templated_telegram(
        self,
        db: AsyncSession,
        chat_ids: list[int],
        template_code: str,
        language: str,
        variables: dict,
    ) -> None:
        """Send Telegram notification using template."""
        template = await template_service.get_template(
            db, template_code, language, NotificationChannel.TELEGRAM
        )
        _, body = template_service.render(template, variables)

        if body:
            for chat_id in chat_ids:
                await telegram_service.send_message(chat_id, body)

    async def _send_templated_email(
        self,
        db: AsyncSession,
        to: list[str],
        template_code: str,
        language: str,
        variables: dict,
        workspace_id: UUID,
        tag: str | None = None,
    ) -> None:
        """Send email notification using template."""
        template = await template_service.get_template(
            db, template_code, language, NotificationChannel.EMAIL
        )
        subject, body = template_service.render(template, variables)

        if not body:
            return

        if app_settings.use_postal and postal_service.is_configured:
            await postal_service.send_email(
                db=db,
                to=to,
                subject=subject or "[CronBox] Notification",
                html=body,
                text=body.replace("<br>", "\n").replace("</p>", "\n"),
                workspace_id=workspace_id,
                tag=tag,
            )
        elif email_service.is_configured:
            await email_service.send_email(
                to=to,
                subject=subject or "[CronBox] Notification",
                html=body,
                text=body.replace("<br>", "\n").replace("</p>", "\n"),
            )

    async def send_task_failure(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        task_name: str,
        task_type: str,
        error_message: str | None = None,
        task_url: str | None = None,
    ) -> None:
        """Send failure notifications through all enabled channels."""
        settings = await self.get_settings(db, workspace_id)
        if not settings or not settings.notify_on_failure:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "task_name": task_name,
            "task_type": task_type,
            "error_message": error_message or "Unknown error",
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            await self._send_templated_telegram(
                db, settings.telegram_chat_ids, "task_failure", language, variables
            )

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            await self._send_templated_email(
                db,
                settings.email_addresses,
                "task_failure",
                language,
                variables,
                workspace_id,
                tag="task-failure",
            )

        # Send Webhook notifications
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="task.failed",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "task_name": task_name,
                    "task_type": task_type,
                    "error_message": error_message,
                    "task_url": task_url,
                },
            )

    async def send_task_recovery(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        task_name: str,
        task_type: str,
    ) -> None:
        """Send recovery notifications through all enabled channels."""
        settings = await self.get_settings(db, workspace_id)
        if not settings or not settings.notify_on_recovery:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "task_name": task_name,
            "task_type": task_type,
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            await self._send_templated_telegram(
                db, settings.telegram_chat_ids, "task_recovery", language, variables
            )

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            await self._send_templated_email(
                db,
                settings.email_addresses,
                "task_recovery",
                language,
                variables,
                workspace_id,
                tag="task-recovery",
            )

        # Send Webhook notifications
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="task.recovered",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "task_name": task_name,
                    "task_type": task_type,
                },
            )

    async def send_task_success(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        task_name: str,
        task_type: str,
        duration_ms: int | None = None,
    ) -> None:
        """Send success notifications through all enabled channels."""
        settings = await self.get_settings(db, workspace_id)
        if not settings or not settings.notify_on_success:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "task_name": task_name,
            "task_type": task_type,
            "duration_ms": str(duration_ms or 0),
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            await self._send_templated_telegram(
                db, settings.telegram_chat_ids, "task_success", language, variables
            )

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            await self._send_templated_email(
                db,
                settings.email_addresses,
                "task_success",
                language,
                variables,
                workspace_id,
                tag="task-success",
            )

        # Send Webhook notifications
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="task.succeeded",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "task_name": task_name,
                    "task_type": task_type,
                    "duration_ms": duration_ms,
                },
            )

    async def send_subscription_expiring(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        days_remaining: int,
        expiration_date: str,
    ) -> None:
        """Send subscription expiring notifications through all enabled channels."""
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "days_remaining": str(days_remaining),
            "expiration_date": expiration_date,
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            await self._send_templated_telegram(
                db,
                settings.telegram_chat_ids,
                "subscription_expiring",
                language,
                variables,
            )

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            await self._send_templated_email(
                db,
                settings.email_addresses,
                "subscription_expiring",
                language,
                variables,
                workspace_id,
                tag="subscription-expiring",
            )

        # Send Webhook notification
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="subscription.expiring",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "days_remaining": days_remaining,
                    "expiration_date": expiration_date,
                },
            )

        logger.info(
            "Subscription expiring notification sent",
            workspace_id=str(workspace_id),
            days_remaining=days_remaining,
        )

    async def send_subscription_expired(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        tasks_paused: int,
    ) -> None:
        """Send subscription expired notifications through all enabled channels."""
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "tasks_paused": str(tasks_paused),
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            await self._send_templated_telegram(
                db,
                settings.telegram_chat_ids,
                "subscription_expired",
                language,
                variables,
            )

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            await self._send_templated_email(
                db,
                settings.email_addresses,
                "subscription_expired",
                language,
                variables,
                workspace_id,
                tag="subscription-expired",
            )

        # Send Webhook notification
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="subscription.expired",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "tasks_paused": tasks_paused,
                },
            )

        logger.info(
            "Subscription expired notification sent",
            workspace_id=str(workspace_id),
            tasks_paused=tasks_paused,
        )

    async def _send_webhook(
        self,
        url: str,
        secret: str | None,
        event: str,
        data: dict,
    ) -> bool:
        """Send a webhook notification."""
        try:
            headers = {"Content-Type": "application/json"}
            if secret:
                headers["X-Webhook-Secret"] = secret

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"event": event, "data": data},
                    timeout=10.0,
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error("Failed to send webhook", error=str(e), url=url)
            return False


# Global instance
notification_service = NotificationService()
