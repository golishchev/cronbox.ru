"""Email notification service using SMTP."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import aiosmtplib
import structlog

from app.config import settings
from app.services.i18n import t

logger = structlog.get_logger()

# OTP email expiration in minutes (for display purposes)
OTP_EXPIRE_MINUTES = settings.otp_expire_minutes


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
        # Escape user-controlled inputs to prevent HTML injection
        safe_task_name = escape(task_name)
        safe_task_type = escape(task_type)
        safe_workspace_name = escape(workspace_name)
        safe_task_url = escape(task_url) if task_url else None
        safe_error_message = escape(error_message[:500]) if error_message else None

        subject = f"[CronBox] Task Failed: {safe_task_name}"

        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc2626;">Task Failed</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Workspace</td>
                    <td style="padding: 8px 0;"><strong>{safe_workspace_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Task</td>
                    <td style="padding: 8px 0;"><strong>{safe_task_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Type</td>
                    <td style="padding: 8px 0;">{safe_task_type}</td>
                </tr>
                {f'<tr><td style="padding: 8px 0; color: #666;">URL</td><td style="padding: 8px 0;">{safe_task_url}</td></tr>' if safe_task_url else ""}
            </table>
            {f'<div style="margin-top: 16px; padding: 12px; background: #fef2f2; border-radius: 4px; color: #991b1b;"><strong>Error:</strong> {safe_error_message}</div>' if safe_error_message else ""}
            <p style="margin-top: 24px; color: #666; font-size: 12px;">
                This is an automated notification from CronBox.
            </p>
        </div>
        """

        text = f"""Task Failed

Workspace: {workspace_name}
Task: {task_name}
Type: {task_type}
{f"URL: {task_url}" if task_url else ""}
{f"Error: {error_message[:500]}" if error_message else ""}

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
        # Escape user-controlled inputs to prevent HTML injection
        safe_task_name = escape(task_name)
        safe_task_type = escape(task_type)
        safe_workspace_name = escape(workspace_name)

        subject = f"[CronBox] Task Recovered: {safe_task_name}"

        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #16a34a;">Task Recovered</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Workspace</td>
                    <td style="padding: 8px 0;"><strong>{safe_workspace_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Task</td>
                    <td style="padding: 8px 0;"><strong>{safe_task_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Type</td>
                    <td style="padding: 8px 0;">{safe_task_type}</td>
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
        # Escape user-controlled inputs to prevent HTML injection
        safe_task_name = escape(task_name)
        safe_task_type = escape(task_type)
        safe_workspace_name = escape(workspace_name)

        subject = f"[CronBox] Task Succeeded: {safe_task_name}"

        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #16a34a;">Task Succeeded</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #666;">Workspace</td>
                    <td style="padding: 8px 0;"><strong>{safe_workspace_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Task</td>
                    <td style="padding: 8px 0;"><strong>{safe_task_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #666;">Type</td>
                    <td style="padding: 8px 0;">{safe_task_type}</td>
                </tr>
                {f'<tr><td style="padding: 8px 0; color: #666;">Duration</td><td style="padding: 8px 0;">{duration_ms}ms</td></tr>' if duration_ms else ""}
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
{f"Duration: {duration_ms}ms" if duration_ms else ""}

This is an automated notification from CronBox.
"""

        return await self.send_email(to, subject, html, text)

    async def send_otp_email(
        self,
        to: str,
        code: str,
        expire_minutes: int | None = None,
        lang: str = "ru",
    ) -> bool:
        """Send OTP code email for passwordless login."""
        if expire_minutes is None:
            expire_minutes = OTP_EXPIRE_MINUTES

        subject = t("email.otp.subject", lang) + f": {code}"

        html = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>{t("email.otp.title", lang)}</h2>
            <p>{t("email.otp.code_label", lang)}</p>
            <div style="margin: 24px 0; padding: 20px; background: #f3f4f6; border-radius: 8px; text-align: center;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1f2937;">{code}</span>
            </div>
            <p style="color: #666;">
                {t("email.otp.validity", lang, minutes=expire_minutes)}
            </p>
            <p style="margin-top: 24px; color: #666; font-size: 12px;">
                {t("email.otp.ignore_notice", lang)}
            </p>
        </div>
        """

        text = f"""{t("email.otp.title", lang)}

{t("email.otp.code_label", lang)} {code}

{t("email.otp.validity", lang, minutes=expire_minutes)}

{t("email.otp.ignore_notice", lang)}
"""

        return await self.send_email(to, subject, html, text)


# Global instance
email_service = EmailService()
