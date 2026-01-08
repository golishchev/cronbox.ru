"""Main notification orchestrator service."""
import httpx
import structlog
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.notification_settings import NotificationSettings
from app.models.workspace import Workspace
from app.services.telegram import telegram_service
from app.services.postal import postal_service
from app.services.email import email_service  # SMTP fallback

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

    async def _send_email_notification(
        self,
        db: AsyncSession,
        notification_type: str,
        to: list[str],
        task_name: str,
        task_type: str,
        workspace_name: str,
        workspace_id: UUID,
        error_message: str | None = None,
        task_url: str | None = None,
        duration_ms: int | None = None,
    ) -> bool:
        """Send email notification via Postal or SMTP fallback."""
        # Try Postal first
        if app_settings.use_postal and postal_service.is_configured:
            if notification_type == "failure":
                result = await postal_service.send_task_failure_notification(
                    db=db,
                    to=to,
                    task_name=task_name,
                    task_type=task_type,
                    error_message=error_message,
                    workspace_name=workspace_name,
                    workspace_id=workspace_id,
                    task_url=task_url,
                )
            elif notification_type == "recovery":
                result = await postal_service.send_task_recovery_notification(
                    db=db,
                    to=to,
                    task_name=task_name,
                    task_type=task_type,
                    workspace_name=workspace_name,
                    workspace_id=workspace_id,
                )
            elif notification_type == "success":
                result = await postal_service.send_task_success_notification(
                    db=db,
                    to=to,
                    task_name=task_name,
                    task_type=task_type,
                    workspace_name=workspace_name,
                    workspace_id=workspace_id,
                    duration_ms=duration_ms,
                )
            else:
                return False

            return result is not None

        # Fallback to SMTP
        if email_service.is_configured:
            if notification_type == "failure":
                return await email_service.send_task_failure_notification(
                    to=to,
                    task_name=task_name,
                    task_type=task_type,
                    error_message=error_message,
                    workspace_name=workspace_name,
                    task_url=task_url,
                )
            elif notification_type == "recovery":
                return await email_service.send_task_recovery_notification(
                    to=to,
                    task_name=task_name,
                    task_type=task_type,
                    workspace_name=workspace_name,
                )
            elif notification_type == "success":
                return await email_service.send_task_success_notification(
                    to=to,
                    task_name=task_name,
                    task_type=task_type,
                    workspace_name=workspace_name,
                    duration_ms=duration_ms,
                )

        logger.warning("No email service configured")
        return False

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

        # Get workspace name
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        workspace_name = workspace.name if workspace else "Unknown"

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            for chat_id in settings.telegram_chat_ids:
                await telegram_service.send_task_failure_notification(
                    chat_id=chat_id,
                    task_name=task_name,
                    task_type=task_type,
                    error_message=error_message,
                    workspace_name=workspace_name,
                )

        # Send Email notifications (Postal or SMTP)
        if settings.email_enabled and settings.email_addresses:
            await self._send_email_notification(
                db=db,
                notification_type="failure",
                to=settings.email_addresses,
                task_name=task_name,
                task_type=task_type,
                workspace_name=workspace_name,
                workspace_id=workspace_id,
                error_message=error_message,
                task_url=task_url,
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

        # Get workspace name
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        workspace_name = workspace.name if workspace else "Unknown"

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            for chat_id in settings.telegram_chat_ids:
                await telegram_service.send_task_recovery_notification(
                    chat_id=chat_id,
                    task_name=task_name,
                    task_type=task_type,
                    workspace_name=workspace_name,
                )

        # Send Email notifications (Postal or SMTP)
        if settings.email_enabled and settings.email_addresses:
            await self._send_email_notification(
                db=db,
                notification_type="recovery",
                to=settings.email_addresses,
                task_name=task_name,
                task_type=task_type,
                workspace_name=workspace_name,
                workspace_id=workspace_id,
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

        # Get workspace name
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        workspace_name = workspace.name if workspace else "Unknown"

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            for chat_id in settings.telegram_chat_ids:
                await telegram_service.send_task_success_notification(
                    chat_id=chat_id,
                    task_name=task_name,
                    task_type=task_type,
                    workspace_name=workspace_name,
                    duration_ms=duration_ms,
                )

        # Send Email notifications (Postal or SMTP)
        if settings.email_enabled and settings.email_addresses:
            await self._send_email_notification(
                db=db,
                notification_type="success",
                to=settings.email_addresses,
                task_name=task_name,
                task_type=task_type,
                workspace_name=workspace_name,
                workspace_id=workspace_id,
                duration_ms=duration_ms,
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
