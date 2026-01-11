"""Add account lockout fields to users table

Revision ID: b2c3d4e5f6a7
Revises: 1b4363cc1e2c
Create Date: 2026-01-09 14:00:00.000000

Security: Adds fields for brute force protection via account lockout.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = '1b4363cc1e2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add account lockout fields to users table."""
    # Track failed login attempts
    op.add_column(
        'users',
        sa.Column(
            'failed_login_attempts',
            sa.Integer(),
            server_default='0',
            nullable=False
        )
    )

    # Account lock expiration time
    op.add_column(
        'users',
        sa.Column(
            'locked_until',
            sa.DateTime(timezone=True),
            nullable=True
        )
    )


def downgrade() -> None:
    """Remove account lockout fields from users table."""
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
