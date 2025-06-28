"""Add more colors to color_tag_enum

Revision ID: f8e7d6c5b4a3
Revises: 1b2c3d4e5f6a
Create Date: 2024-02-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f8e7d6c5b4a3'
down_revision: Union[str, None] = '1b2c3d4e5f6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'blushred'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'softorange'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'lightyellow'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'sagegreen'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'skyblue'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'magenta'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'pink'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'honeybrown'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'brown'")

def downgrade() -> None:
    pass
