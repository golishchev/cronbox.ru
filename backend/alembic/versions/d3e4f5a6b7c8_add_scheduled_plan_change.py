"""add_scheduled_plan_change

Add scheduled_plan_id and scheduled_billing_period to subscriptions
for deferred plan changes (downgrade or yearly→monthly).

Revision ID: d3e4f5a6b7c8
Revises: c7d8e9f0a1b2
Create Date: 2026-01-15 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scheduled plan change fields to subscriptions."""
    op.add_column(
        'subscriptions',
        sa.Column('scheduled_plan_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'subscriptions',
        sa.Column('scheduled_billing_period', sa.String(10), nullable=True)
    )

    # Add foreign key for scheduled_plan_id
    op.create_foreign_key(
        'subscriptions_scheduled_plan_id_fkey',
        'subscriptions', 'plans',
        ['scheduled_plan_id'], ['id']
    )


def downgrade() -> None:
    """Remove scheduled plan change fields from subscriptions."""
    op.drop_constraint('subscriptions_scheduled_plan_id_fkey', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'scheduled_billing_period')
    op.drop_column('subscriptions', 'scheduled_plan_id')
