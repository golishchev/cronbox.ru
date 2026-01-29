"""merge_heartbeats_and_overlap_prevention

Revision ID: 1687bba71720
Revises: g7b8c9d0e1f2, g7h8i9j0k1l2
Create Date: 2026-01-17 23:15:27.514635

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "1687bba71720"
down_revision: Union[str, Sequence[str], None] = ("g7b8c9d0e1f2", "g7h8i9j0k1l2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
