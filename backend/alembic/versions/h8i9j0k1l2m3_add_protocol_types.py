"""add_protocol_types

Add protocol_type field (http, icmp, tcp) to cron_tasks, delayed_tasks and executions.
Add ICMP/TCP specific fields for monitoring results.

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-01-21 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add protocol type support for ICMP and TCP monitoring."""
    # Create protocol type enum
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'protocoltype') THEN
                CREATE TYPE protocoltype AS ENUM ('http', 'icmp', 'tcp');
            END IF;
        END$$;
    """)

    # Add columns to cron_tasks
    op.add_column(
        "cron_tasks",
        sa.Column(
            "protocol_type",
            sa.Enum("http", "icmp", "tcp", name="protocoltype", create_type=False),
            nullable=False,
            server_default="http",
        ),
    )
    op.add_column(
        "cron_tasks",
        sa.Column("host", sa.String(255), nullable=True),
    )
    op.add_column(
        "cron_tasks",
        sa.Column("port", sa.Integer(), nullable=True),
    )
    op.add_column(
        "cron_tasks",
        sa.Column("icmp_count", sa.Integer(), nullable=False, server_default="3"),
    )

    # Make url nullable for cron_tasks (not needed for ICMP/TCP)
    op.alter_column("cron_tasks", "url", existing_type=sa.String(2048), nullable=True)

    # Add columns to delayed_tasks
    op.add_column(
        "delayed_tasks",
        sa.Column(
            "protocol_type",
            sa.Enum("http", "icmp", "tcp", name="protocoltype", create_type=False),
            nullable=False,
            server_default="http",
        ),
    )
    op.add_column(
        "delayed_tasks",
        sa.Column("host", sa.String(255), nullable=True),
    )
    op.add_column(
        "delayed_tasks",
        sa.Column("port", sa.Integer(), nullable=True),
    )
    op.add_column(
        "delayed_tasks",
        sa.Column("icmp_count", sa.Integer(), nullable=False, server_default="3"),
    )

    # Make url nullable for delayed_tasks
    op.alter_column("delayed_tasks", "url", existing_type=sa.String(2048), nullable=True)

    # Add columns to executions
    op.add_column(
        "executions",
        sa.Column(
            "protocol_type",
            sa.Enum("http", "icmp", "tcp", name="protocoltype", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "executions",
        sa.Column("target_host", sa.String(255), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("target_port", sa.Integer(), nullable=True),
    )

    # ICMP results
    op.add_column(
        "executions",
        sa.Column("icmp_packets_sent", sa.Integer(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("icmp_packets_received", sa.Integer(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("icmp_packet_loss", sa.Float(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("icmp_min_rtt", sa.Float(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("icmp_avg_rtt", sa.Float(), nullable=True),
    )
    op.add_column(
        "executions",
        sa.Column("icmp_max_rtt", sa.Float(), nullable=True),
    )

    # TCP results
    op.add_column(
        "executions",
        sa.Column("tcp_connection_time", sa.Float(), nullable=True),
    )

    # Make request_url and request_method nullable for ICMP/TCP executions
    op.alter_column("executions", "request_url", existing_type=sa.String(2048), nullable=True)
    op.alter_column(
        "executions",
        "request_method",
        existing_type=sa.Enum("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", name="httpmethod"),
        nullable=True,
    )


def downgrade() -> None:
    """Remove protocol type support."""
    # Remove columns from executions
    op.drop_column("executions", "tcp_connection_time")
    op.drop_column("executions", "icmp_max_rtt")
    op.drop_column("executions", "icmp_avg_rtt")
    op.drop_column("executions", "icmp_min_rtt")
    op.drop_column("executions", "icmp_packet_loss")
    op.drop_column("executions", "icmp_packets_received")
    op.drop_column("executions", "icmp_packets_sent")
    op.drop_column("executions", "target_port")
    op.drop_column("executions", "target_host")
    op.drop_column("executions", "protocol_type")

    # Restore request_url and request_method as not nullable
    op.alter_column("executions", "request_url", existing_type=sa.String(2048), nullable=False)
    op.alter_column(
        "executions",
        "request_method",
        existing_type=sa.Enum("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", name="httpmethod"),
        nullable=False,
    )

    # Remove columns from delayed_tasks
    op.drop_column("delayed_tasks", "icmp_count")
    op.drop_column("delayed_tasks", "port")
    op.drop_column("delayed_tasks", "host")
    op.drop_column("delayed_tasks", "protocol_type")

    # Restore url as not nullable
    op.alter_column("delayed_tasks", "url", existing_type=sa.String(2048), nullable=False)

    # Remove columns from cron_tasks
    op.drop_column("cron_tasks", "icmp_count")
    op.drop_column("cron_tasks", "port")
    op.drop_column("cron_tasks", "host")
    op.drop_column("cron_tasks", "protocol_type")

    # Restore url as not nullable
    op.alter_column("cron_tasks", "url", existing_type=sa.String(2048), nullable=False)

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS protocoltype;")
