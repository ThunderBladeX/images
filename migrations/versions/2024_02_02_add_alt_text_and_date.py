"""Add alt text and date fields

Revision ID: e3d1f0a9b8c7
Revises: 8a9b1c2d3e4f
Create Date: 2024-02-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e3d1f0a9b8c7'
down_revision: Union[str, None] = '8a9b1c2d3e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('images', sa.Column('alt_text', sa.Text(), nullable=True))
    op.add_column('images', sa.Column('month_made', sa.Integer(), nullable=True))
    op.add_column('images', sa.Column('day_made', sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column('images', 'day_made')
    op.drop_column('images', 'month_made')
    op.drop_column('images', 'alt_text')
