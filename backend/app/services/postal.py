"""Postal email service with full API integration."""
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email_log import EmailLog, EmailStatus, EmailType

logger = structlog.get_logger()


class PostalService:
    """Service for sending emails via Postal HTTP API with full tracking."""

    def __init__(self):
        self.api_url = settings.postal_api_url.rstrip("/") if settings.postal_api_url else ""
        self.api_key = settings.postal_api_key
        self.server_key = settings.postal_server_key
        self.webhook_secret = settings.postal_webhook_secret
        self.from_email = settings.email_from

    @property
    def is_configured(self) -> bool:
        """Check if Postal is properly configured."""
        return bool(self.api_url and self.server_key)

    def _get_headers(self) -> dict:
        """Get headers for Postal API requests."""
        return {
            "Content-Type": "application/json",
            "X-Server-API-Key": self.server_key,
        }

    async def send_email(
        self,
        db: AsyncSession,
        to: str | list[str],
        subject: str,
        html: str,
        text: str | None = None,
        email_type: EmailType = EmailType.OTHER,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        metadata: dict | None = None,
        tag: str | None = None,
        track_opens: bool = True,
        track_clicks: bool = True,
    ) -> EmailLog | None:
        """
        Send an email via Postal API.

        Args:
            db: Database session
            to: Recipient email(s)
            subject: Email subject
            html: HTML body
            text: Plain text body (optional)
            email_type: Type of email for categorization
            workspace_id: Associated workspace ID
            user_id: Associated user ID
            metadata: Additional metadata to store
            tag: Postal tag for categorization
            track_opens: Enable open tracking
            track_clicks: Enable click tracking

        Returns:
            EmailLog record or None if failed
        """
        if not self.is_configured:
            logger.warning("Postal not configured, skipping email")
            return None

        to_list = [to] if isinstance(to, str) else to

        # Create email log record
        email_log = EmailLog(
            workspace_id=workspace_id,
            user_id=user_id,
            to_email=to_list[0],  # Primary recipient
            from_email=self.from_email,
            subject=subject,
            email_type=email_type,
            html_body=html,
            text_body=text,
            status=EmailStatus.QUEUED,
            extra_data=metadata or {},
        )
        db.add(email_log)
        await db.flush()

        try:
            # Build Postal API request
            payload = {
                "to": to_list,
                "from": self.from_email,
                "subject": subject,
                "html_body": html,
            }

            if text:
                payload["plain_body"] = text

            if tag:
                payload["tag"] = tag

            # Tracking settings
            if not track_opens:
                payload["track_opens"] = False
            if not track_clicks:
                payload["track_clicks"] = False

            # Send via Postal API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/send/message",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()

            # Check response
            if result.get("status") == "success":
                data = result.get("data", {})
                messages = data.get("messages", {})

                # Get the first message ID (for single recipient)
                if messages and to_list[0] in messages:
                    msg_info = messages[to_list[0]]
                    email_log.mark_sent(
                        postal_message_id=str(msg_info.get("id")),
                        postal_server=data.get("server"),
                    )
                else:
                    # Fallback - mark as sent without specific ID
                    email_log.status = EmailStatus.SENT
                    email_log.sent_at = datetime.now(timezone.utc)

                await db.commit()
                logger.info(
                    "Email sent via Postal",
                    email_id=str(email_log.id),
                    postal_message_id=email_log.postal_message_id,
                    to=to_list,
                )
                return email_log
            else:
                # API returned error
                error_msg = result.get("data", {}).get("message", "Unknown error")
                email_log.mark_failed(error_msg)
                await db.commit()
                logger.error("Postal API error", error=error_msg)
                return email_log

        except httpx.HTTPError as e:
            email_log.mark_failed(str(e))
            await db.commit()
            logger.error("Failed to send email via Postal", error=str(e))
            return email_log

        except Exception as e:
            email_log.mark_failed(str(e))
            await db.commit()
            logger.error("Unexpected error sending email", error=str(e))
            return email_log

    async def send_raw(
        self,
        db: AsyncSession,
        mail_from: str,
        rcpt_to: list[str],
        data: str,
        workspace_id: UUID | None = None,
    ) -> dict | None:
        """Send raw MIME email via Postal."""
        if not self.is_configured:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/send/raw",
                    headers=self._get_headers(),
                    json={
                        "mail_from": mail_from,
                        "rcpt_to": rcpt_to,
                        "data": data,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error("Failed to send raw email", error=str(e))
            return None

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify Postal webhook signature.

        Postal signs webhooks using HMAC-SHA1.
        """
        if not self.webhook_secret:
            logger.warning("Postal webhook secret not configured")
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha1,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def process_webhook(
        self,
        db: AsyncSession,
        event_type: str,
        payload: dict,
    ) -> bool:
        """
        Process Postal webhook event.

        Event types:
        - MessageSent: Message was sent
        - MessageDelivered: Message was delivered
        - MessageDelayed: Delivery is delayed
        - MessageBounced: Message bounced
        - MessageHeld: Message held (spam, etc.)
        - MessageLinkClicked: Link in message clicked
        - MessageLoaded: Message was opened/loaded
        """
        message_id = payload.get("message", {}).get("id")
        if not message_id:
            message_id = payload.get("original_message", {}).get("id")

        if not message_id:
            logger.warning("No message ID in webhook payload")
            return False

        # Find email log by postal message ID
        result = await db.execute(
            select(EmailLog).where(EmailLog.postal_message_id == str(message_id))
        )
        email_log = result.scalar_one_or_none()

        if not email_log:
            logger.warning("Email log not found for message", message_id=message_id)
            return False

        # Process based on event type
        if event_type == "MessageSent":
            if email_log.status == EmailStatus.QUEUED:
                email_log.status = EmailStatus.SENT
                email_log.sent_at = datetime.now(timezone.utc)

        elif event_type == "MessageDelivered":
            email_log.mark_delivered()

        elif event_type == "MessageBounced":
            bounce_info = payload.get("bounce", {})
            email_log.mark_bounced(
                bounce_type="hard" if bounce_info.get("type") == "hard" else "soft",
                code=bounce_info.get("code"),
                message=bounce_info.get("message"),
            )

        elif event_type == "MessageLoaded":
            email_log.mark_opened()

        elif event_type == "MessageLinkClicked":
            url = payload.get("url")
            email_log.mark_clicked(url)

        elif event_type == "MessageHeld":
            email_log.status = EmailStatus.HELD
            email_log.status_details = payload.get("message", {}).get("hold_reason")

        elif event_type == "MessageDelayed":
            email_log.status_details = f"Delivery delayed: {payload.get('details', '')}"

        await db.commit()
        logger.info(
            "Processed Postal webhook",
            event_type=event_type,
            email_id=str(email_log.id),
            status=email_log.status.value,
        )
        return True

    async def get_message_info(self, message_id: str) -> dict | None:
        """Get message info from Postal API."""
        if not self.is_configured:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/messages/message",
                    headers=self._get_headers(),
                    json={"id": int(message_id)},
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error("Failed to get message info", error=str(e), message_id=message_id)
            return None

    async def get_message_deliveries(self, message_id: str) -> list[dict] | None:
        """Get delivery attempts for a message."""
        if not self.is_configured:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/messages/deliveries",
                    headers=self._get_headers(),
                    json={"id": int(message_id)},
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()
                return result.get("data", [])

        except Exception as e:
            logger.error("Failed to get deliveries", error=str(e), message_id=message_id)
            return None

    # Convenience methods for specific email types

    async def send_task_failure_notification(
        self,
        db: AsyncSession,
        to: str | list[str],
        task_name: str,
        task_type: str,
        error_message: str | None,
        workspace_name: str,
        workspace_id: UUID,
        task_url: str | None = None,
    ) -> EmailLog | None:
        """Send a task failure notification email."""
        subject = f"[CronBox] Task Failed: {task_name}"

        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc2626;">Task Failed</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Workspace</td>
                    <td style="padding: 8px 0;"><strong>{workspace_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Task</td>
                    <td style="padding: 8px 0;"><strong>{task_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Type</td>
                    <td style="padding: 8px 0;">{task_type}</td>
                </tr>
                {f'<tr><td style="padding: 8px 0; color: #666;">URL</td><td style="padding: 8px 0;">{task_url}</td></tr>' if task_url else ''}
            </table>
            {f'<div style="margin-top: 16px; padding: 12px; background: #fef2f2; border-radius: 4px; color: #991b1b;"><strong>Error:</strong> {error_message[:500] if error_message else "Unknown error"}</div>' if error_message else ''}
            <p style="margin-top: 24px; color: #666; font-size: 12px;">
                This is an automated notification from CronBox.
            </p>
        </div>
        """

        text = f"""Task Failed

Workspace: {workspace_name}
Task: {task_name}
Type: {task_type}
{f'URL: {task_url}' if task_url else ''}
{f'Error: {error_message[:500]}' if error_message else ''}

This is an automated notification from CronBox.
"""

        return await self.send_email(
            db=db,
            to=to,
            subject=subject,
            html=html,
            text=text,
            email_type=EmailType.TASK_FAILURE,
            workspace_id=workspace_id,
            tag="task-failure",
            metadata={
                "task_name": task_name,
                "task_type": task_type,
                "workspace_name": workspace_name,
            },
        )

    async def send_task_recovery_notification(
        self,
        db: AsyncSession,
        to: str | list[str],
        task_name: str,
        task_type: str,
        workspace_name: str,
        workspace_id: UUID,
    ) -> EmailLog | None:
        """Send a task recovery notification email."""
        subject = f"[CronBox] Task Recovered: {task_name}"

        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #16a34a;">Task Recovered</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Workspace</td>
                    <td style="padding: 8px 0;"><strong>{workspace_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Task</td>
                    <td style="padding: 8px 0;"><strong>{task_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Type</td>
                    <td style="padding: 8px 0;">{task_type}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Status</td>
                    <td style="padding: 8px 0; color: #16a34a;"><strong>Back to normal</strong></td>
                </tr>
            </table>
            <p style="margin-top: 24px; color: #666; font-size: 12px;">
                This is an automated notification from CronBox.
            </p>
        </div>
        """

        text = f"""Task Recovered

Workspace: {workspace_name}
Task: {task_name}
Type: {task_type}
Status: Back to normal

This is an automated notification from CronBox.
"""

        return await self.send_email(
            db=db,
            to=to,
            subject=subject,
            html=html,
            text=text,
            email_type=EmailType.TASK_RECOVERY,
            workspace_id=workspace_id,
            tag="task-recovery",
            metadata={
                "task_name": task_name,
                "task_type": task_type,
                "workspace_name": workspace_name,
            },
        )

    async def send_task_success_notification(
        self,
        db: AsyncSession,
        to: str | list[str],
        task_name: str,
        task_type: str,
        workspace_name: str,
        workspace_id: UUID,
        duration_ms: int | None = None,
    ) -> EmailLog | None:
        """Send a task success notification email."""
        subject = f"[CronBox] Task Succeeded: {task_name}"

        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #16a34a;">Task Succeeded</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Workspace</td>
                    <td style="padding: 8px 0;"><strong>{workspace_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Task</td>
                    <td style="padding: 8px 0;"><strong>{task_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Type</td>
                    <td style="padding: 8px 0;">{task_type}</td>
                </tr>
                {f'<tr><td style="padding: 8px 0; color: #666;">Duration</td><td style="padding: 8px 0;">{duration_ms}ms</td></tr>' if duration_ms else ''}
            </table>
            <p style="margin-top: 24px; color: #666; font-size: 12px;">
                This is an automated notification from CronBox.
            </p>
        </div>
        """

        text = f"""Task Succeeded

Workspace: {workspace_name}
Task: {task_name}
Type: {task_type}
{f'Duration: {duration_ms}ms' if duration_ms else ''}

This is an automated notification from CronBox.
"""

        return await self.send_email(
            db=db,
            to=to,
            subject=subject,
            html=html,
            text=text,
            email_type=EmailType.TASK_SUCCESS,
            workspace_id=workspace_id,
            tag="task-success",
            metadata={
                "task_name": task_name,
                "task_type": task_type,
                "workspace_name": workspace_name,
                "duration_ms": duration_ms,
            },
        )


# Global instance
postal_service = PostalService()
