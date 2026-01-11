"""Email notification service using SMTP."""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import structlog

from app.config import settings

logger = structlog.get_logger()


class EmailService:
    """Service for sending email notifications via SMTP."""

    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.use_tls = settings.smtp_use_tls
        self.from_email = settings.email_from

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        text: str | None = None,
    ) -> bool:
        """Send an email via SMTP."""
        if not self.is_configured:
            logger.warning("Email service not configured")
            return False

        to_list = [to] if isinstance(to, str) else to

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to_list)

            # Add text part (fallback)
            if text:
                part_text = MIMEText(text, "plain", "utf-8")
                msg.attach(part_text)

            # Add HTML part
            part_html = MIMEText(html, "html", "utf-8")
            msg.attach(part_html)

            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=self.use_tls,
            )
            logger.info("Email sent successfully", to=to_list, subject=subject)
            return True

        except Exception as e:
            logger.error("Failed to send email", error=str(e), to=to_list)
            return False

    async def send_task_failure_notification(
        self,
        to: str | list[str],
        task_name: str,
        task_type: str,
        error_message: str | None,
        workspace_name: str,
        task_url: str | None = None,
    ) -> bool:
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

        return await self.send_email(to, subject, html, text)

    async def send_task_recovery_notification(
        self,
        to: str | list[str],
        task_name: str,
        task_type: str,
        workspace_name: str,
    ) -> bool:
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

        return await self.send_email(to, subject, html, text)

    async def send_task_success_notification(
        self,
        to: str | list[str],
        task_name: str,
        task_type: str,
        workspace_name: str,
        duration_ms: int | None = None,
    ) -> bool:
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

        return await self.send_email(to, subject, html, text)


# Global instance
email_service = EmailService()
