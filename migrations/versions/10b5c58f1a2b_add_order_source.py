"""add order source column

Revision ID: 10b5c58f1a2b
Revises: f43f935df183
Create Date: 2026-03-03 11:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10b5c58f1a2b'
down_revision = 'f43f935df183'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'orders',
        sa.Column('source', sa.String(length=32), nullable=False, server_default=sa.text("'manual'"))
    )


def downgrade():
    op.drop_column('orders', 'source')
