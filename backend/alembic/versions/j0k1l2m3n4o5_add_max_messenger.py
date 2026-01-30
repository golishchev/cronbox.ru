"""add MAX notifications

Revision ID: j0k1l2m3n4o5
Revises: 469467ee9ee6
Create Date: 2025-01-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, None] = "469467ee9ee6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # notification_settings: add MAX fields
    op.add_column(
        "notification_settings",
        sa.Column("max_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "notification_settings",
        sa.Column("max_chat_ids", sa.ARRAY(sa.String()), nullable=True),
    )

    # plans: add max_notifications feature flag
    op.add_column(
        "plans",
        sa.Column("max_notifications", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Update existing plans to have max_notifications=false
    op.execute("UPDATE plans SET max_notifications = false WHERE max_notifications IS NULL")

    # Add MAX to NotificationChannel enum
    op.execute("ALTER TYPE notificationchannel ADD VALUE IF NOT EXISTS 'MAX'")


def downgrade() -> None:
    op.drop_column("plans", "max_notifications")
    op.drop_column("notification_settings", "max_chat_ids")
    op.drop_column("notification_settings", "max_enabled")
    # Note: PostgreSQL doesn't support removing enum values directly
