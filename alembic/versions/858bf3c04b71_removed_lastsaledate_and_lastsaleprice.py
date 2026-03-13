"""removed lastsaledate and lastsaleprice

Revision ID: 858bf3c04b71
Revises: 6de94e144773
Create Date: 2026-03-13 10:20:17.902230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '858bf3c04b71'
down_revision: Union[str, Sequence[str], None] = '6de94e144773'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
