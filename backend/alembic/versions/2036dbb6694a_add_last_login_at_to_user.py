"""add_last_login_at_to_user

Revision ID: 2036dbb6694a
Revises: 1687bba71720
Create Date: 2026-01-18 00:19:37.491002

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2036dbb6694a"
down_revision: Union[str, Sequence[str], None] = "1687bba71720"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "last_login_at")
