"""Squashed initial schema.

Revision ID: 20260403_0001
Revises:
Create Date: 2026-04-03 16:20:00
"""

from typing import Sequence, Union

from alembic import op

from app.database.db import Base
import app.models  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "20260403_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the full current application schema."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop the full application schema."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
