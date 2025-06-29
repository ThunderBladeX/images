"""Add grey to color_tag_enum

Revision ID: d9c8b7a6e5f4
Revises: f8e7d6c5b4a3
Create Date: 2024-02-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd9c8b7a6e5f4'
down_revision: Union[str, None] = 'f8e7d6c5b4a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'gray'")
    op.execute("ALTER TYPE color_tag_enum ADD VALUE 'darkgray'")


def downgrade() -> None:
    pass
