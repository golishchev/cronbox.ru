"""add process_monitor_id to executions

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2025-01-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k1l2m3n4o5p6"
down_revision: Union[str, None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add process_monitor_id to executions table."""
    # Add process_monitor_id to executions table
    op.add_column("executions", sa.Column("process_monitor_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_executions_process_monitor_id",
        "executions",
        "process_monitors",
        ["process_monitor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove process_monitor_id from executions table."""
    # Remove foreign key and column
    op.drop_constraint("fk_executions_process_monitor_id", "executions", type_="foreignkey")
    op.drop_column("executions", "process_monitor_id")
