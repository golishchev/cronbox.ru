"""Billing schemas."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    """Plan response schema."""

    id: UUID
    name: str
    display_name: str
    description: str | None

    # Pricing (in kopeks)
    price_monthly: int
    price_yearly: int

    # Limits
    max_cron_tasks: int
    max_delayed_tasks_per_month: int
    max_workspaces: int
    max_execution_history_days: int
    min_cron_interval_minutes: int

    # Features
    telegram_notifications: bool
    email_notifications: bool
    webhook_callbacks: bool
    custom_headers: bool
    retry_on_failure: bool

    # Visibility
    is_active: bool
    is_public: bool
    sort_order: int

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Subscription response schema."""

    id: UUID
    user_id: UUID
    plan_id: UUID
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    cancelled_at: datetime | None

    # Include plan details
    plan: PlanResponse | None = None

    class Config:
        from_attributes = True


class CreatePaymentRequest(BaseModel):
    """Request to create a payment."""

    plan_id: UUID
    billing_period: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    return_url: str | None = None


class PaymentResponse(BaseModel):
    """Payment response schema."""

    id: UUID
    user_id: UUID
    amount: int
    currency: str
    status: str
    description: str | None
    yookassa_confirmation_url: str | None
    paid_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class CancelSubscriptionRequest(BaseModel):
    """Request to cancel subscription."""

    immediately: bool = False


class WebhookPayload(BaseModel):
    """YooKassa webhook payload."""

    type: str
    event: str
    object: dict
