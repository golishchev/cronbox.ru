"""remove_region_from_workers

Revision ID: c7d8e9f0a1b2
Revises: 4daf8661bd73
Create Date: 2026-01-14 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "4daf8661bd73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove region column from workers table."""
    op.drop_column("workers", "region")


def downgrade() -> None:
    """Add region column back to workers table."""
    op.add_column("workers", sa.Column("region", sa.String(length=50), nullable=True))
