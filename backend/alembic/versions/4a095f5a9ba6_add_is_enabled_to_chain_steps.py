"""add is_enabled to chain_steps

Revision ID: 4a095f5a9ba6
Revises: 2036dbb6694a
Create Date: 2026-01-18 18:18:42.158104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a095f5a9ba6'
down_revision: Union[str, Sequence[str], None] = '2036dbb6694a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'chain_steps',
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true'))
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chain_steps', 'is_enabled')
