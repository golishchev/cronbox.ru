"""Notification settings API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_workspace
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.notification_settings import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    TestNotificationRequest,
)
from app.services.email import email_service
from app.services.i18n import get_i18n
from app.services.notifications import notification_service
from app.services.telegram import telegram_service

router = APIRouter(prefix="/workspaces/{workspace_id}/notifications", tags=["notifications"])


@router.get("", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get notification settings for a workspace."""
    settings = await notification_service.get_or_create_settings(db, workspace.id)
    return settings


@router.patch("", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    data: NotificationSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update notification settings for a workspace."""
    settings = await notification_service.get_or_create_settings(db, workspace.id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return settings


@router.post("/test")
async def send_test_notification(
    workspace: Annotated[Workspace, Depends(get_workspace)],
    data: TestNotificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Send a test notification."""
    i18n = get_i18n(current_user.preferred_language)
    settings = await notification_service.get_settings(db, workspace.id)
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notification settings not configured",
        )

    if data.channel == "telegram":
        if not settings.telegram_enabled or not settings.telegram_chat_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram notifications not configured",
            )

        success = False
        telegram_text = (
            f"<b>{i18n.t('notifications.test.telegram_title')}</b>\n\n"
            f"{i18n.t('notifications.test.telegram_body', workspace_name=workspace.name)}"
        )
        for chat_id in settings.telegram_chat_ids:
            result = await telegram_service.send_message(
                chat_id=chat_id,
                text=telegram_text,
            )
            if result:
                success = True

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send Telegram notification",
            )

    elif data.channel == "email":
        if not settings.email_enabled or not settings.email_addresses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email notifications not configured",
            )

        success = await email_service.send_email(
            to=settings.email_addresses,
            subject=i18n.t("notifications.test.email_subject", workspace_name=workspace.name),
            html=f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>{i18n.t("notifications.test.email_title")}</h2>
                <p>{i18n.t("notifications.test.email_body", workspace_name=workspace.name)}</p>
                <p>{i18n.t("notifications.test.email_success")}</p>
            </div>
            """,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email notification",
            )

    elif data.channel == "webhook":
        if not settings.webhook_enabled or not settings.webhook_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook notifications not configured",
            )

        success = await notification_service._send_webhook(
            url=settings.webhook_url,
            secret=settings.webhook_secret,
            event="test",
            data={
                "workspace_id": str(workspace.id),
                "workspace_name": workspace.name,
                "message": i18n.t("notifications.test.webhook_message"),
            },
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send webhook notification",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown channel: {data.channel}",
        )

    return {"success": True, "message": f"Test notification sent via {data.channel}"}
