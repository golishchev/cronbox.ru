"""merge_ssl_monitors_and_protocol_types

Revision ID: c77d06c7d679
Revises: h8c9d0e1f2g3, h8i9j0k1l2m3
Create Date: 2026-01-21 14:53:25.405404

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c77d06c7d679"
down_revision: Union[str, Sequence[str], None] = ("h8c9d0e1f2g3", "h8i9j0k1l2m3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
