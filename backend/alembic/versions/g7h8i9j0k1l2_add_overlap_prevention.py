"""add_overlap_prevention

Add Overlap Prevention feature with overlap policies, task queue, and metrics.

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-01-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add overlap prevention columns and task_queue table."""
    # Create overlap policy enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'overlappolicy') THEN
                CREATE TYPE overlappolicy AS ENUM ('allow', 'skip', 'queue');
            END IF;
        END
        $$;
    """)

    # Add overlap prevention columns to cron_tasks
    op.add_column(
        "cron_tasks",
        sa.Column(
            "overlap_policy",
            postgresql.ENUM("allow", "skip", "queue", name="overlappolicy", create_type=False),
            nullable=False,
            server_default="allow",
        ),
    )
    op.add_column(
        "cron_tasks",
        sa.Column("max_instances", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "cron_tasks",
        sa.Column("max_queue_size", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "cron_tasks",
        sa.Column("execution_timeout", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cron_tasks",
        sa.Column("running_instances", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add overlap prevention columns to task_chains
    op.add_column(
        "task_chains",
        sa.Column(
            "overlap_policy",
            postgresql.ENUM("allow", "skip", "queue", name="overlappolicy", create_type=False),
            nullable=False,
            server_default="allow",
        ),
    )
    op.add_column(
        "task_chains",
        sa.Column("max_instances", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "task_chains",
        sa.Column("max_queue_size", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "task_chains",
        sa.Column("execution_timeout", sa.Integer(), nullable=True),
    )
    op.add_column(
        "task_chains",
        sa.Column("running_instances", sa.Integer(), nullable=False, server_default="0"),
    )

    # Create task_queue table for queue strategy
    op.create_table(
        "task_queue",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("task_type", sa.String(length=20), nullable=False),  # 'cron' or 'chain'
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("initial_variables", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_queue_workspace_id", "task_queue", ["workspace_id"], unique=False)
    op.create_index("ix_task_queue_task_id", "task_queue", ["task_id"], unique=False)
    op.create_index("ix_task_queue_task_type", "task_queue", ["task_type"], unique=False)
    op.create_index("ix_task_queue_queued_at", "task_queue", ["queued_at"], unique=False)
    op.create_index("ix_task_queue_priority_queued_at", "task_queue", ["priority", "queued_at"], unique=False)

    # Add skipped_reason to executions
    op.add_column(
        "executions",
        sa.Column("skipped_reason", sa.String(length=100), nullable=True),
    )

    # Add skipped_reason to chain_executions
    op.add_column(
        "chain_executions",
        sa.Column("skipped_reason", sa.String(length=100), nullable=True),
    )

    # Add overlap metrics to workspaces
    op.add_column(
        "workspaces",
        sa.Column("executions_skipped", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "workspaces",
        sa.Column("executions_queued", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add overlap prevention settings to plans
    op.add_column(
        "plans",
        sa.Column("overlap_prevention_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "plans",
        sa.Column("max_queue_size", sa.Integer(), nullable=False, server_default="10"),
    )


def downgrade() -> None:
    """Remove overlap prevention columns and task_queue table."""
    # Remove columns from plans
    op.drop_column("plans", "max_queue_size")
    op.drop_column("plans", "overlap_prevention_enabled")

    # Remove columns from workspaces
    op.drop_column("workspaces", "executions_queued")
    op.drop_column("workspaces", "executions_skipped")

    # Remove skipped_reason from chain_executions
    op.drop_column("chain_executions", "skipped_reason")

    # Remove skipped_reason from executions
    op.drop_column("executions", "skipped_reason")

    # Drop task_queue table
    op.drop_index("ix_task_queue_priority_queued_at", table_name="task_queue")
    op.drop_index("ix_task_queue_queued_at", table_name="task_queue")
    op.drop_index("ix_task_queue_task_type", table_name="task_queue")
    op.drop_index("ix_task_queue_task_id", table_name="task_queue")
    op.drop_index("ix_task_queue_workspace_id", table_name="task_queue")
    op.drop_table("task_queue")

    # Remove overlap prevention columns from task_chains
    op.drop_column("task_chains", "running_instances")
    op.drop_column("task_chains", "execution_timeout")
    op.drop_column("task_chains", "max_queue_size")
    op.drop_column("task_chains", "max_instances")
    op.drop_column("task_chains", "overlap_policy")

    # Remove overlap prevention columns from cron_tasks
    op.drop_column("cron_tasks", "running_instances")
    op.drop_column("cron_tasks", "execution_timeout")
    op.drop_column("cron_tasks", "max_queue_size")
    op.drop_column("cron_tasks", "max_instances")
    op.drop_column("cron_tasks", "overlap_policy")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS overlappolicy")
