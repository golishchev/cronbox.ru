"""workspace_slug_unique_per_owner

Make workspace slug unique per owner instead of globally unique.

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-01-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change slug uniqueness from global to per-owner."""
    # Drop the global unique index on slug
    # Note: This was created as a UNIQUE INDEX, not a CONSTRAINT
    op.drop_index('ix_workspaces_slug', table_name='workspaces')

    # Create a new unique constraint on (slug, owner_id)
    op.create_unique_constraint(
        'uq_workspaces_slug_owner',
        'workspaces',
        ['slug', 'owner_id']
    )

    # Keep the index on slug for performance (non-unique)
    op.create_index('ix_workspaces_slug', 'workspaces', ['slug'])


def downgrade() -> None:
    """Revert to global slug uniqueness."""
    # Drop the per-owner unique constraint
    op.drop_constraint('uq_workspaces_slug_owner', 'workspaces', type_='unique')

    # Drop the non-unique index
    op.drop_index('ix_workspaces_slug', table_name='workspaces')

    # Recreate the global unique constraint
    op.create_index('ix_workspaces_slug', 'workspaces', ['slug'], unique=True)
