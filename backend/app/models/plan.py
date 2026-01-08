from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Plan(Base, UUIDMixin, TimestampMixin):
    """Subscription plan model."""

    __tablename__ = "plans"

    # Identification
    name: Mapped[str] = mapped_column(String(50), unique=True)  # free, starter, pro
    display_name: Mapped[str] = mapped_column(String(100))  # "Free", "Starter", "Pro"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pricing (in kopeks for RUB, or cents)
    price_monthly: Mapped[int] = mapped_column(Integer, default=0)  # 0 for free
    price_yearly: Mapped[int] = mapped_column(Integer, default=0)

    # Limits
    max_cron_tasks: Mapped[int] = mapped_column(Integer, default=5)
    max_delayed_tasks_per_month: Mapped[int] = mapped_column(Integer, default=100)
    max_workspaces: Mapped[int] = mapped_column(Integer, default=1)
    max_execution_history_days: Mapped[int] = mapped_column(Integer, default=7)
    min_cron_interval_minutes: Mapped[int] = mapped_column(Integer, default=5)

    # Features
    telegram_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_callbacks: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_headers: Mapped[bool] = mapped_column(Boolean, default=True)
    retry_on_failure: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
