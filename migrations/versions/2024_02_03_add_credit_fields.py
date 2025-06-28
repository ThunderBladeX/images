"""Add credit fields

Revision ID: 1b2c3d4e5f6a
Revises: e3d1f0a9b8c7
Create Date: 2024-02-03 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '1b2c3d4e5f6a'
down_revision: Union[str, None] = 'e3d1f0a9b8c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('images', sa.Column('credit_text', sa.String(), nullable=True))
    op.add_column('images', sa.Column('credit_url', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('images', 'credit_url')
    op.drop_column('images', 'credit_text')
