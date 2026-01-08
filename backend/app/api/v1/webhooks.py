"""Webhook endpoints for external services."""
import hashlib
import hmac
import structlog

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.services.billing import billing_service
from app.services.postal import postal_service

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/yookassa")
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle YooKassa payment notifications."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    event_type = body.get("event")
    payment_object = body.get("object")

    if not event_type or not payment_object:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event type or object",
        )

    # Process the webhook
    success = await billing_service.handle_webhook(db, event_type, payment_object)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )

    return {"status": "ok"}


@router.post("/postal")
async def postal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_postal_signature: str | None = Header(None, alias="X-Postal-Signature"),
):
    """
    Handle Postal email delivery webhooks.

    Postal sends webhooks for various email events:
    - MessageSent: Email was sent to mail server
    - MessageDelivered: Email was delivered
    - MessageBounced: Email bounced (hard or soft)
    - MessageHeld: Email held by Postal
    - MessageDelayed: Delivery delayed
    - MessageLoaded: Email was opened
    - MessageLinkClicked: Link in email was clicked
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if webhook secret is configured
    if settings.postal_webhook_secret:
        if not x_postal_signature:
            logger.warning("Postal webhook missing signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature",
            )

        if not postal_service.verify_webhook_signature(body, x_postal_signature):
            logger.warning("Postal webhook invalid signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    event_type = payload.get("event")
    if not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event type",
        )

    logger.info("Received Postal webhook", event_type=event_type)

    # Process the webhook
    success = await postal_service.process_webhook(db, event_type, payload)

    if not success:
        # Log but don't fail - Postal may retry
        logger.warning("Failed to process Postal webhook", event_type=event_type)

    return {"status": "ok"}
