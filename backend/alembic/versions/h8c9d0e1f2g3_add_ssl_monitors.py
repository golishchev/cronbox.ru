"""add_ssl_monitors

Add SSL Certificate Monitoring feature.

Revision ID: h8c9d0e1f2g3
Revises: 4a095f5a9ba6
Create Date: 2026-01-19 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2g3"
down_revision: Union[str, Sequence[str], None] = "4a095f5a9ba6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add SSL monitors table and related columns."""
    # Create sslmonitorstatus enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sslmonitorstatus') THEN
                CREATE TYPE sslmonitorstatus AS ENUM (
                    'pending', 'valid', 'expiring', 'expired', 'invalid', 'error', 'paused'
                );
            END IF;
        END
        $$;
    """)

    # Create ssl_monitors table
    op.create_table(
        "ssl_monitors",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="443"),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "valid",
                "expiring",
                "expired",
                "invalid",
                "error",
                "paused",
                name="sslmonitorstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default="false"),
        # Certificate info
        sa.Column("issuer", sa.String(length=512), nullable=True),
        sa.Column("subject", sa.String(length=512), nullable=True),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("days_until_expiry", sa.Integer(), nullable=True),
        # TLS info
        sa.Column("tls_version", sa.String(length=32), nullable=True),
        sa.Column("cipher_suite", sa.String(length=128), nullable=True),
        # Chain info
        sa.Column("chain_valid", sa.Boolean(), nullable=True),
        sa.Column("hostname_match", sa.Boolean(), nullable=True),
        # Check tracking
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        # Retry logic
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        # Notification tracking
        sa.Column("last_notification_days", sa.Integer(), nullable=True),
        sa.Column("notify_on_expiring", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_error", sa.Boolean(), nullable=False, server_default="true"),
        # Standard fields
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ssl_monitors_workspace_id", "ssl_monitors", ["workspace_id"], unique=False)
    op.create_index("ix_ssl_monitors_domain", "ssl_monitors", ["domain"], unique=False)
    op.create_index("ix_ssl_monitors_next_check_at", "ssl_monitors", ["next_check_at"], unique=False)
    op.create_index("ix_ssl_monitors_next_retry_at", "ssl_monitors", ["next_retry_at"], unique=False)

    # Add ssl_monitors_count to workspaces
    op.add_column("workspaces", sa.Column("ssl_monitors_count", sa.Integer(), nullable=False, server_default="0"))

    # Add max_ssl_monitors to plans
    op.add_column("plans", sa.Column("max_ssl_monitors", sa.Integer(), nullable=False, server_default="0"))

    # Set SSL monitors limits for paid plans
    op.execute("UPDATE plans SET max_ssl_monitors = 3 WHERE name = 'starter'")
    op.execute("UPDATE plans SET max_ssl_monitors = 10 WHERE name = 'pro'")

    # Add ssl_monitor_id to executions table
    op.add_column("executions", sa.Column("ssl_monitor_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_executions_ssl_monitor_id",
        "executions",
        "ssl_monitors",
        ["ssl_monitor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove SSL monitors table and related columns."""
    # Remove ssl_monitor_id from executions (if exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_executions_ssl_monitor_id'
                AND table_name = 'executions'
            ) THEN
                ALTER TABLE executions DROP CONSTRAINT fk_executions_ssl_monitor_id;
            END IF;
        END
        $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'executions' AND column_name = 'ssl_monitor_id'
            ) THEN
                ALTER TABLE executions DROP COLUMN ssl_monitor_id;
            END IF;
        END
        $$;
    """)

    # Remove column from plans
    op.drop_column("plans", "max_ssl_monitors")

    # Remove column from workspaces
    op.drop_column("workspaces", "ssl_monitors_count")

    # Drop ssl_monitors table
    op.drop_index("ix_ssl_monitors_next_retry_at", table_name="ssl_monitors")
    op.drop_index("ix_ssl_monitors_next_check_at", table_name="ssl_monitors")
    op.drop_index("ix_ssl_monitors_domain", table_name="ssl_monitors")
    op.drop_index("ix_ssl_monitors_workspace_id", table_name="ssl_monitors")
    op.drop_table("ssl_monitors")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS sslmonitorstatus")
