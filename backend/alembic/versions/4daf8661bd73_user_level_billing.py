"""user_level_billing

Move subscription from workspace-level to user-level.
- Add user_id to subscriptions (replace workspace_id)
- Add is_blocked/blocked_at to workspaces
- Remove plan_id from workspaces (plan comes from user subscription)
- Add user_id to payments for history

Revision ID: 4daf8661bd73
Revises: be84994e62e5
Create Date: 2026-01-09 19:18:00.144330

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4daf8661bd73'
down_revision: Union[str, Sequence[str], None] = 'be84994e62e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate to user-level billing."""

    # 1. Add user_id to subscriptions (nullable first for migration)
    op.add_column(
        'subscriptions',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # 2. Migrate data: copy user_id from workspace.owner_id
    op.execute("""
        UPDATE subscriptions s
        SET user_id = w.owner_id
        FROM workspaces w
        WHERE s.workspace_id = w.id
    """)

    # 3. Make user_id NOT NULL
    op.alter_column('subscriptions', 'user_id', nullable=False)

    # 4. Add foreign key and unique constraint for user_id
    op.create_foreign_key(
        'subscriptions_user_id_fkey',
        'subscriptions', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_unique_constraint(
        'subscriptions_user_id_key',
        'subscriptions',
        ['user_id']
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])

    # 5. Drop old workspace_id constraint and column
    # Note: The unique constraint is a unique index, not a named constraint
    op.drop_index('ix_subscriptions_workspace_id', 'subscriptions')
    op.drop_constraint('subscriptions_workspace_id_fkey', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'workspace_id')

    # 6. Add is_blocked and blocked_at to workspaces
    op.add_column(
        'workspaces',
        sa.Column('is_blocked', sa.Boolean(), server_default='false', nullable=False)
    )
    op.add_column(
        'workspaces',
        sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 7. Remove plan_id from workspaces (plan comes from user subscription now)
    op.drop_constraint('workspaces_plan_id_fkey', 'workspaces', type_='foreignkey')
    op.drop_index('ix_workspaces_plan_id', 'workspaces')
    op.drop_column('workspaces', 'plan_id')

    # 8. Add user_id to payments for history
    op.add_column(
        'payments',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Migrate payment data
    op.execute("""
        UPDATE payments p
        SET user_id = w.owner_id
        FROM workspaces w
        WHERE p.workspace_id = w.id
    """)

    # Add foreign key for payments.user_id
    op.create_foreign_key(
        'payments_user_id_fkey',
        'payments', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])


def downgrade() -> None:
    """Revert to workspace-level billing."""

    # 1. Re-add plan_id to workspaces
    op.add_column(
        'workspaces',
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Get free plan id and set it as default for all workspaces
    op.execute("""
        UPDATE workspaces w
        SET plan_id = (SELECT id FROM plans WHERE name = 'free' LIMIT 1)
    """)

    op.alter_column('workspaces', 'plan_id', nullable=False)
    op.create_foreign_key(
        'workspaces_plan_id_fkey',
        'workspaces', 'plans',
        ['plan_id'], ['id']
    )
    op.create_index('ix_workspaces_plan_id', 'workspaces', ['plan_id'])

    # 2. Remove is_blocked and blocked_at from workspaces
    op.drop_column('workspaces', 'blocked_at')
    op.drop_column('workspaces', 'is_blocked')

    # 3. Re-add workspace_id to subscriptions
    op.add_column(
        'subscriptions',
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Migrate back: get first workspace for each user
    op.execute("""
        UPDATE subscriptions s
        SET workspace_id = (
            SELECT w.id FROM workspaces w
            WHERE w.owner_id = s.user_id
            ORDER BY w.created_at ASC
            LIMIT 1
        )
    """)

    op.alter_column('subscriptions', 'workspace_id', nullable=False)
    op.create_foreign_key(
        'subscriptions_workspace_id_fkey',
        'subscriptions', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )
    # Create unique index (not named constraint) as per original schema
    op.create_index('ix_subscriptions_workspace_id', 'subscriptions', ['workspace_id'], unique=True)

    # 4. Remove user_id from subscriptions
    op.drop_index('ix_subscriptions_user_id', 'subscriptions')
    op.drop_constraint('subscriptions_user_id_key', 'subscriptions', type_='unique')
    op.drop_constraint('subscriptions_user_id_fkey', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'user_id')

    # 5. Remove user_id from payments
    op.drop_index('ix_payments_user_id', 'payments')
    op.drop_constraint('payments_user_id_fkey', 'payments', type_='foreignkey')
    op.drop_column('payments', 'user_id')
