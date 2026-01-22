"""Add process monitors tables.

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2025-01-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, None] = "c77d06c7d679"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create process_monitors table
    op.create_table(
        "process_monitors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_token", sa.String(length=32), nullable=False),
        sa.Column("end_token", sa.String(length=32), nullable=False),
        sa.Column(
            "schedule_type",
            sa.Enum("cron", "interval", "exact_time", name="scheduletype"),
            nullable=False,
        ),
        sa.Column("schedule_cron", sa.String(length=100), nullable=True),
        sa.Column("schedule_interval", sa.Integer(), nullable=True),
        sa.Column("schedule_exact_time", sa.String(length=10), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="Europe/Moscow"),
        sa.Column("start_grace_period", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("end_timeout", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column(
            "status",
            sa.Enum(
                "waiting_start",
                "running",
                "completed",
                "missed_start",
                "missed_end",
                "paused",
                name="processmonitorstatus",
            ),
            nullable=False,
        ),
        sa.Column("is_paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_duration_ms", sa.Integer(), nullable=True),
        sa.Column("next_expected_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_run_id", sa.String(length=36), nullable=True),
        sa.Column("consecutive_successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notify_on_missed_start", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_missed_end", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_recovery", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_success", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_process_monitors_workspace_id"), "process_monitors", ["workspace_id"])
    op.create_index(op.f("ix_process_monitors_start_token"), "process_monitors", ["start_token"], unique=True)
    op.create_index(op.f("ix_process_monitors_end_token"), "process_monitors", ["end_token"], unique=True)
    op.create_index(op.f("ix_process_monitors_next_expected_start"), "process_monitors", ["next_expected_start"])
    op.create_index(op.f("ix_process_monitors_end_deadline"), "process_monitors", ["end_deadline"])

    # Create process_monitor_events table
    op.create_table(
        "process_monitor_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("monitor_id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum("start", "end", "timeout", "missed", name="processmonitoreventtype"),
            nullable=False,
        ),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status_message", sa.String(length=255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(
            ["monitor_id"],
            ["process_monitors.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_process_monitor_events_monitor_id"), "process_monitor_events", ["monitor_id"])
    op.create_index(op.f("ix_process_monitor_events_run_id"), "process_monitor_events", ["run_id"])

    # Add process_monitors_count to workspaces
    op.add_column("workspaces", sa.Column("process_monitors_count", sa.Integer(), server_default="0", nullable=False))

    # Add process monitor limits to plans
    op.add_column("plans", sa.Column("max_process_monitors", sa.Integer(), server_default="0", nullable=False))
    op.add_column(
        "plans", sa.Column("min_process_monitor_interval_minutes", sa.Integer(), server_default="5", nullable=False)
    )


def downgrade() -> None:
    # Remove plan limits
    op.drop_column("plans", "min_process_monitor_interval_minutes")
    op.drop_column("plans", "max_process_monitors")

    # Remove workspace counter
    op.drop_column("workspaces", "process_monitors_count")

    # Drop process_monitor_events table
    op.drop_index(op.f("ix_process_monitor_events_run_id"), table_name="process_monitor_events")
    op.drop_index(op.f("ix_process_monitor_events_monitor_id"), table_name="process_monitor_events")
    op.drop_table("process_monitor_events")

    # Drop process_monitors table
    op.drop_index(op.f("ix_process_monitors_end_deadline"), table_name="process_monitors")
    op.drop_index(op.f("ix_process_monitors_next_expected_start"), table_name="process_monitors")
    op.drop_index(op.f("ix_process_monitors_end_token"), table_name="process_monitors")
    op.drop_index(op.f("ix_process_monitors_start_token"), table_name="process_monitors")
    op.drop_index(op.f("ix_process_monitors_workspace_id"), table_name="process_monitors")
    op.drop_table("process_monitors")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS processmonitoreventtype")
    op.execute("DROP TYPE IF EXISTS processmonitorstatus")
    op.execute("DROP TYPE IF EXISTS scheduletype")
