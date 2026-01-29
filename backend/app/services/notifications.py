"""Main notification orchestrator service."""

from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings as app_settings
from app.models.notification_settings import NotificationSettings
from app.models.notification_template import NotificationChannel
from app.models.payment import Payment
from app.models.workspace import Workspace
from app.services.email import email_service  # SMTP fallback
from app.services.max_messenger import max_messenger_service
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
        result = await db.execute(select(NotificationSettings).where(NotificationSettings.workspace_id == workspace_id))
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

    async def _get_workspace_info(self, db: AsyncSession, workspace_id: UUID) -> tuple[str, str]:
        """Get workspace name and owner's preferred language."""
        result = await db.execute(
            select(Workspace).options(selectinload(Workspace.owner)).where(Workspace.id == workspace_id)
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
        template = await template_service.get_template(db, template_code, language, NotificationChannel.TELEGRAM)
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
        template = await template_service.get_template(db, template_code, language, NotificationChannel.EMAIL)
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

    async def _send_templated_max(
        self,
        db: AsyncSession,
        chat_ids: list[str],
        template_code: str,
        language: str,
        variables: dict,
    ) -> None:
        """Send MAX notification using template."""
        template = await template_service.get_template(db, template_code, language, NotificationChannel.MAX)
        _, body = template_service.render(template, variables)

        if body:
            for chat_id in chat_ids:
                await max_messenger_service.send_message(chat_id, body)

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
            await self._send_templated_telegram(db, settings.telegram_chat_ids, "task_failure", language, variables)

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            await self._send_templated_max(db, settings.max_chat_ids, "task_failure", language, variables)

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
            await self._send_templated_telegram(db, settings.telegram_chat_ids, "task_recovery", language, variables)

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            await self._send_templated_max(db, settings.max_chat_ids, "task_recovery", language, variables)

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
        task_level_override: bool = False,
    ) -> None:
        """Send success notifications through all enabled channels.

        Args:
            task_level_override: If True, skip workspace-level notify_on_success check.
                Used when the task itself has notify_on_success enabled.
        """
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return
        if not task_level_override and not settings.notify_on_success:
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
            await self._send_templated_telegram(db, settings.telegram_chat_ids, "task_success", language, variables)

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            await self._send_templated_max(db, settings.max_chat_ids, "task_success", language, variables)

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

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            await self._send_templated_max(
                db, settings.max_chat_ids, "subscription_expiring", language, variables
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
        user_id: UUID,
        tasks_paused: int,
        workspaces_blocked: int = 0,
    ) -> None:
        """Send subscription expired notifications through all enabled channels."""
        # Get user's first workspace for notification settings
        workspace_result = await db.execute(
            select(Workspace).where(Workspace.owner_id == user_id).order_by(Workspace.created_at.asc()).limit(1)
        )
        workspace = workspace_result.scalar_one_or_none()
        if not workspace:
            return

        workspace_id = workspace.id
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "tasks_paused": str(tasks_paused),
            "workspaces_blocked": str(workspaces_blocked),
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

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            await self._send_templated_max(
                db, settings.max_chat_ids, "subscription_expired", language, variables
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
                    "workspaces_blocked": workspaces_blocked,
                },
            )

        logger.info(
            "Subscription expired notification sent",
            user_id=str(user_id),
            tasks_paused=tasks_paused,
            workspaces_blocked=workspaces_blocked,
        )

    async def send_subscription_renewed(
        self,
        db: AsyncSession,
        user_id: UUID,
        payment: Payment,
    ) -> None:
        """Send subscription auto-renewed notification."""
        # Get user's first workspace for notification settings
        workspace_result = await db.execute(
            select(Workspace).where(Workspace.owner_id == user_id).order_by(Workspace.created_at.asc()).limit(1)
        )
        workspace = workspace_result.scalar_one_or_none()
        if not workspace:
            return

        workspace_id = workspace.id
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        # Format amount (from kopeks to rubles)
        amount_rub = f"{payment.amount / 100:.2f}"

        variables = {
            "workspace_name": workspace_name,
            "amount": amount_rub,
            "currency": payment.currency,
            "description": payment.description or "Подписка",
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            await self._send_templated_telegram(
                db,
                settings.telegram_chat_ids,
                "subscription_renewed",
                language,
                variables,
            )

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            await self._send_templated_max(
                db, settings.max_chat_ids, "subscription_renewed", language, variables
            )

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            await self._send_templated_email(
                db,
                settings.email_addresses,
                "subscription_renewed",
                language,
                variables,
                workspace_id,
                tag="subscription-renewed",
            )

        # Send Webhook notification
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="subscription.renewed",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "payment_id": str(payment.id),
                },
            )

        logger.info(
            "Subscription renewed notification sent",
            user_id=str(user_id),
            payment_id=str(payment.id),
        )

    async def send_chain_notification(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        chain_name: str,
        event: str,  # "success", "failure", "partial"
        duration_ms: int | None = None,
        error_message: str | None = None,
        completed_steps: int | None = None,
        failed_steps: int | None = None,
        total_steps: int | None = None,
        task_level_override: bool = False,
    ) -> None:
        """Send task chain notifications through all enabled channels."""
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        # Check notification settings based on event
        if event == "success" and not task_level_override and not settings.notify_on_success:
            return
        if event == "failure" and not settings.notify_on_failure:
            return
        # For partial, we use failure notification setting
        if event == "partial" and not settings.notify_on_failure:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "chain_name": chain_name,
            "completed_steps": str(completed_steps or 0),
            "failed_steps": str(failed_steps or 0),
            "total_steps": str(total_steps or 0),
            "duration_ms": str(duration_ms or 0),
            "error_message": error_message or "",
        }

        # Determine template code based on event
        template_code = f"chain_{event}"

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            try:
                await self._send_templated_telegram(db, settings.telegram_chat_ids, template_code, language, variables)
            except Exception as e:
                # Template might not exist, send a generic message
                logger.warning(
                    "Chain notification template not found, using fallback",
                    template=template_code,
                    error=str(e),
                )
                message = self._format_chain_notification_fallback(
                    chain_name, event, completed_steps, failed_steps, total_steps, error_message
                )
                for chat_id in settings.telegram_chat_ids:
                    await telegram_service.send_message(chat_id, message)

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            try:
                await self._send_templated_max(db, settings.max_chat_ids, template_code, language, variables)
            except Exception as e:
                logger.warning(
                    "Chain Max notification template not found, using fallback",
                    template=template_code,
                    error=str(e),
                )
                message = self._format_chain_notification_fallback(
                    chain_name, event, completed_steps, failed_steps, total_steps, error_message
                )
                for chat_id in settings.max_chat_ids:
                    await max_messenger_service.send_message(chat_id, message)

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            try:
                await self._send_templated_email(
                    db,
                    settings.email_addresses,
                    template_code,
                    language,
                    variables,
                    workspace_id,
                    tag=f"chain-{event}",
                )
            except Exception:
                # Template might not exist, skip email
                pass

        # Send Webhook notifications
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event=f"chain.{event}",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "chain_name": chain_name,
                    "completed_steps": completed_steps,
                    "failed_steps": failed_steps,
                    "total_steps": total_steps,
                    "duration_ms": duration_ms,
                    "error_message": error_message,
                },
            )

    def _format_chain_notification_fallback(
        self,
        chain_name: str,
        event: str,
        completed_steps: int | None,
        failed_steps: int | None,
        total_steps: int | None,
        error_message: str | None,
    ) -> str:
        """Format chain notification as plain text fallback."""
        if event == "success":
            return f"Chain '{chain_name}' completed successfully ({completed_steps}/{total_steps} steps)"
        elif event == "failure":
            msg = f"Chain '{chain_name}' failed ({completed_steps}/{total_steps} steps)"
            if error_message:
                msg += f"\nError: {error_message}"
            return msg
        elif event == "partial":
            return (
                f"Chain '{chain_name}' partially completed\n"
                f"Completed: {completed_steps}, Failed: {failed_steps}, Total: {total_steps}"
            )
        return f"Chain '{chain_name}': {event}"

    async def send_ssl_expiring(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        monitor_name: str,
        domain: str,
        days_until_expiry: int,
        valid_until: "datetime | None" = None,
    ) -> None:
        """Send SSL certificate expiring notification."""

        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        expiry_date = valid_until.strftime("%Y-%m-%d") if valid_until else "Unknown"

        variables = {
            "workspace_name": workspace_name,
            "monitor_name": monitor_name,
            "domain": domain,
            "days_until_expiry": str(days_until_expiry),
            "expiry_date": expiry_date,
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            try:
                await self._send_templated_telegram(db, settings.telegram_chat_ids, "ssl_expiring", language, variables)
            except Exception:
                # Template might not exist, send fallback
                if days_until_expiry <= 0:
                    message = f"SSL certificate for {domain} ({monitor_name}) has expired!"
                else:
                    message = f"SSL certificate for {domain} ({monitor_name}) expires in {days_until_expiry} days (on {expiry_date})"
                for chat_id in settings.telegram_chat_ids:
                    await telegram_service.send_message(chat_id, message)

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            try:
                await self._send_templated_max(db, settings.max_chat_ids, "ssl_expiring", language, variables)
            except Exception:
                if days_until_expiry <= 0:
                    message = f"SSL certificate for {domain} ({monitor_name}) has expired!"
                else:
                    message = f"SSL certificate for {domain} ({monitor_name}) expires in {days_until_expiry} days (on {expiry_date})"
                for chat_id in settings.max_chat_ids:
                    await max_messenger_service.send_message(chat_id, message)

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            try:
                await self._send_templated_email(
                    db,
                    settings.email_addresses,
                    "ssl_expiring",
                    language,
                    variables,
                    workspace_id,
                    tag="ssl-expiring",
                )
            except Exception:
                pass

        # Send Webhook notifications
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="ssl.expiring",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "monitor_name": monitor_name,
                    "domain": domain,
                    "days_until_expiry": days_until_expiry,
                    "expiry_date": expiry_date,
                },
            )

        logger.info(
            "SSL expiring notification sent",
            workspace_id=str(workspace_id),
            domain=domain,
            days_until_expiry=days_until_expiry,
        )

    async def send_ssl_error(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        monitor_name: str,
        domain: str,
        error: str,
    ) -> None:
        """Send SSL check error notification."""
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "monitor_name": monitor_name,
            "domain": domain,
            "error": error,
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            try:
                await self._send_templated_telegram(db, settings.telegram_chat_ids, "ssl_error", language, variables)
            except Exception:
                # Template might not exist, send fallback
                message = f"SSL check failed for {domain} ({monitor_name})\nError: {error}"
                for chat_id in settings.telegram_chat_ids:
                    await telegram_service.send_message(chat_id, message)

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            try:
                await self._send_templated_max(db, settings.max_chat_ids, "ssl_error", language, variables)
            except Exception:
                message = f"SSL check failed for {domain} ({monitor_name})\nError: {error}"
                for chat_id in settings.max_chat_ids:
                    await max_messenger_service.send_message(chat_id, message)

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            try:
                await self._send_templated_email(
                    db,
                    settings.email_addresses,
                    "ssl_error",
                    language,
                    variables,
                    workspace_id,
                    tag="ssl-error",
                )
            except Exception:
                pass

        # Send Webhook notifications
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="ssl.error",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "monitor_name": monitor_name,
                    "domain": domain,
                    "error": error,
                },
            )

        logger.info(
            "SSL error notification sent",
            workspace_id=str(workspace_id),
            domain=domain,
            error=error,
        )

    async def send_ssl_invalid(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        monitor_name: str,
        domain: str,
        error: str,
    ) -> None:
        """Send SSL certificate invalid notification."""
        settings = await self.get_settings(db, workspace_id)
        if not settings:
            return

        workspace_name, language = await self._get_workspace_info(db, workspace_id)

        variables = {
            "workspace_name": workspace_name,
            "monitor_name": monitor_name,
            "domain": domain,
            "error": error,
        }

        # Send Telegram notifications
        if settings.telegram_enabled and settings.telegram_chat_ids:
            try:
                await self._send_templated_telegram(db, settings.telegram_chat_ids, "ssl_invalid", language, variables)
            except Exception:
                # Template might not exist, send fallback
                message = f"SSL certificate invalid for {domain} ({monitor_name})\n{error}"
                for chat_id in settings.telegram_chat_ids:
                    await telegram_service.send_message(chat_id, message)

        # Send MAX notifications
        if settings.max_enabled and settings.max_chat_ids:
            try:
                await self._send_templated_max(db, settings.max_chat_ids, "ssl_invalid", language, variables)
            except Exception:
                message = f"SSL certificate invalid for {domain} ({monitor_name})\n{error}"
                for chat_id in settings.max_chat_ids:
                    await max_messenger_service.send_message(chat_id, message)

        # Send Email notifications
        if settings.email_enabled and settings.email_addresses:
            try:
                await self._send_templated_email(
                    db,
                    settings.email_addresses,
                    "ssl_invalid",
                    language,
                    variables,
                    workspace_id,
                    tag="ssl-invalid",
                )
            except Exception:
                pass

        # Send Webhook notifications
        if settings.webhook_enabled and settings.webhook_url:
            await self._send_webhook(
                url=settings.webhook_url,
                secret=settings.webhook_secret,
                event="ssl.invalid",
                data={
                    "workspace_id": str(workspace_id),
                    "workspace_name": workspace_name,
                    "monitor_name": monitor_name,
                    "domain": domain,
                    "error": error,
                },
            )

        logger.info(
            "SSL invalid notification sent",
            workspace_id=str(workspace_id),
            domain=domain,
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
