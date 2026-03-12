"""empty message

Revision ID: 685d1e0a8109
Revises: 3b07a4ab6943
Create Date: 2026-03-11 12:14:50.931005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision: str = '685d1e0a8109'
down_revision: Union[str, Sequence[str], None] = '3b07a4ab6943'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'inquiries',
        sa.Column(
            'type',
            postgresql.ENUM('CONTACT', 'SERVICE', name='inquiry_type', create_type=False),
            nullable=False
        ),
        sa.Column('first_name', sa.VARCHAR(), nullable=False),
        sa.Column('last_name', sa.VARCHAR(), nullable=True),
        sa.Column('email', sa.VARCHAR(), nullable=False),
        sa.Column('phone_number', sa.VARCHAR(), nullable=True),
        sa.Column('message', sa.TEXT(), nullable=False),
        sa.Column('services', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='inquiries_pkey')
    )

    op.create_index('ix_inquiries_id', 'inquiries', ['id'], unique=False)

    op.create_table(
        'subscription_settings',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('subscription_duration_days', sa.INTEGER(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='subscription_settings_pkey')
    )

    op.create_table(
        'system_config',
        sa.Column('config_key', sa.VARCHAR(length=150), nullable=False),
        sa.Column('config_value', sa.TEXT(), nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('is_secret', sa.BOOLEAN(), server_default=sa.text('false')),
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='system_config_pkey'),
        sa.UniqueConstraint('config_key', name='system_config_config_key_key')
    )


def downgrade() -> None:
    op.drop_table('system_config')
    op.drop_table('subscription_settings')
    op.drop_index('ix_inquiries_id', table_name='inquiries')
    op.drop_table('inquiries')