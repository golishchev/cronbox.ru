import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class PaymentStatus(str, enum.Enum):
    """Payment status."""

    PENDING = "pending"
    WAITING_FOR_CAPTURE = "waiting_for_capture"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Payment(Base, UUIDMixin, TimestampMixin):
    """Payment model - stores payment history."""

    __tablename__ = "payments"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )

    # Amount (in kopeks for RUB)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")

    # Status
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.PENDING,
    )

    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # YooKassa data
    yookassa_payment_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    yookassa_confirmation_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True
    )
    yookassa_payment_method: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Extra data
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    workspace: Mapped["Workspace"] = relationship()
