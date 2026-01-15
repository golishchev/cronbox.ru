import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SubscriptionStatus(str, enum.Enum):
    """Subscription status."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Subscription(Base, UUIDMixin, TimestampMixin):
    """Subscription model - links user to a plan."""

    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id"),
        index=True,
    )

    # Status
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
    )

    # Billing period
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Cancellation
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # YooKassa payment method for auto-renewal
    yookassa_payment_method_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Scheduled plan change (for downgrade or yearly→monthly)
    scheduled_plan_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("plans.id"), nullable=True
    )
    scheduled_billing_period: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscription")
    plan: Mapped["Plan"] = relationship()
