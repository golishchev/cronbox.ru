"""add_heartbeat_tables

Add heartbeat monitor (Dead Man's Switch) feature.

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-01-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add heartbeat tables and related columns."""
    # Create heartbeatstatus enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'heartbeatstatus') THEN
                CREATE TYPE heartbeatstatus AS ENUM ('waiting', 'healthy', 'late', 'dead', 'paused');
            END IF;
        END
        $$;
    """)

    # Create heartbeats table
    op.create_table(
        "heartbeats",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ping_token", sa.String(length=32), nullable=False),
        sa.Column("expected_interval", sa.Integer(), nullable=False),
        sa.Column("grace_period", sa.Integer(), nullable=False, server_default="600"),
        sa.Column(
            "status",
            postgresql.ENUM("waiting", "healthy", "late", "dead", "paused", name="heartbeatstatus", create_type=False),
            nullable=False,
            server_default="waiting",
        ),
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_ping_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_expected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_misses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_alert_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alert_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notify_on_late", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_recovery", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ping_token"),
    )
    op.create_index("ix_heartbeats_workspace_id", "heartbeats", ["workspace_id"], unique=False)
    op.create_index("ix_heartbeats_ping_token", "heartbeats", ["ping_token"], unique=True)
    op.create_index("ix_heartbeats_next_expected_at", "heartbeats", ["next_expected_at"], unique=False)

    # Create heartbeat_pings table
    op.create_table(
        "heartbeat_pings",
        sa.Column("heartbeat_id", sa.UUID(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status_message", sa.String(length=255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["heartbeat_id"], ["heartbeats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_heartbeat_pings_heartbeat_id", "heartbeat_pings", ["heartbeat_id"], unique=False)

    # Add heartbeats_count to workspaces
    op.add_column("workspaces", sa.Column("heartbeats_count", sa.Integer(), nullable=False, server_default="0"))

    # Add heartbeat limits to plans
    op.add_column("plans", sa.Column("max_heartbeats", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "plans", sa.Column("min_heartbeat_interval_minutes", sa.Integer(), nullable=False, server_default="5")
    )


def downgrade() -> None:
    """Remove heartbeat tables and related columns."""
    # Remove columns from plans
    op.drop_column("plans", "min_heartbeat_interval_minutes")
    op.drop_column("plans", "max_heartbeats")

    # Remove column from workspaces
    op.drop_column("workspaces", "heartbeats_count")

    # Drop heartbeat_pings table
    op.drop_index("ix_heartbeat_pings_heartbeat_id", table_name="heartbeat_pings")
    op.drop_table("heartbeat_pings")

    # Drop heartbeats table
    op.drop_index("ix_heartbeats_next_expected_at", table_name="heartbeats")
    op.drop_index("ix_heartbeats_ping_token", table_name="heartbeats")
    op.drop_index("ix_heartbeats_workspace_id", table_name="heartbeats")
    op.drop_table("heartbeats")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS heartbeatstatus")
