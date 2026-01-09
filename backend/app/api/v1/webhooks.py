"""Webhook endpoints for external services."""
import ipaddress
import structlog

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.services.billing import billing_service
from app.services.postal import postal_service

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# YooKassa webhook IP ranges (official documentation)
# https://yookassa.ru/developers/using-api/webhooks
YOOKASSA_IP_RANGES = [
    ipaddress.ip_network("185.71.76.0/27"),
    ipaddress.ip_network("185.71.77.0/27"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.156.11/32"),
    ipaddress.ip_network("77.75.156.35/32"),
    ipaddress.ip_network("77.75.154.128/25"),
    ipaddress.ip_network("2a02:5180::/32"),
]


def _get_client_ip(request: Request) -> str:
    """Extract real client IP from request."""
    # Check X-Forwarded-For header (set by reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection
    return request.client.host if request.client else "unknown"


def _is_yookassa_ip(ip_str: str) -> bool:
    """Check if IP belongs to YooKassa."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in YOOKASSA_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


async def _verify_payment_with_yookassa(payment_id: str) -> dict | None:
    """
    Verify payment by fetching it from YooKassa API.

    This is an additional security measure - we verify that the payment
    actually exists in YooKassa with the claimed status.
    """
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.yookassa.ru/v3/payments/{payment_id}",
                auth=(settings.yookassa_shop_id, settings.yookassa_secret_key),
                timeout=10.0,
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        logger.error("Failed to verify payment with YooKassa", error=str(e))
        return None


@router.post("/yookassa")
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle YooKassa payment notifications.

    Security measures:
    1. Verify source IP belongs to YooKassa (in production)
    2. Verify payment status via YooKassa API
    3. Validate payment amount and currency match our records
    """
    # Get client IP
    client_ip = _get_client_ip(request)

    # In production, verify the request comes from YooKassa IPs
    if settings.environment == "production":
        if not _is_yookassa_ip(client_ip):
            logger.warning(
                "YooKassa webhook from unauthorized IP",
                client_ip=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized source IP",
            )

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

    payment_id = payment_object.get("id")
    if not payment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payment ID",
        )

    # Verify payment with YooKassa API (additional security)
    if settings.environment == "production" and event_type == "payment.succeeded":
        verified_payment = await _verify_payment_with_yookassa(payment_id)
        if not verified_payment:
            logger.warning(
                "Failed to verify payment with YooKassa",
                payment_id=payment_id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment verification failed",
            )

        # Check that status matches what webhook claims
        if verified_payment.get("status") != "succeeded":
            logger.warning(
                "Payment status mismatch",
                webhook_event=event_type,
                actual_status=verified_payment.get("status"),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment status mismatch",
            )

    logger.info(
        "Processing YooKassa webhook",
        event_type=event_type,
        payment_id=payment_id,
        client_ip=client_ip,
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
