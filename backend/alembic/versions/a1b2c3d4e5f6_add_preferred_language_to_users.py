"""add_preferred_language_to_users

Revision ID: a1b2c3d4e5f6
Revises: 05d50775a665
Create Date: 2026-01-08 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "05d50775a665"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add preferred_language column to users table."""
    op.add_column("users", sa.Column("preferred_language", sa.String(5), server_default="ru", nullable=False))


def downgrade() -> None:
    """Remove preferred_language column from users table."""
    op.drop_column("users", "preferred_language")
