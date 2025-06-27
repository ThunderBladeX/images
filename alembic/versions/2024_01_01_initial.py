"""Initial migration

Revision ID: 8a9b1c2d3e4f
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '8a9b1c2d3e4f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('uuid_filename', sa.String(), nullable=False),
    sa.Column('original_filename', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('supabase_url', sa.String(), nullable=False),
    sa.Column('markdown_url', sa.Text(), nullable=False),
    sa.Column('color_tag', sa.Enum('red', 'orange', 'yellow', 'green', 'blue', 'indigo', 'violet', 'black', 'white', name='color_tag_enum'), nullable=False),
    sa.Column('year_made', sa.Integer(), nullable=False),
    sa.Column('is_sensitive', sa.Boolean(), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_images_id'), 'images', ['id'], unique=False)
    op.create_index(op.f('ix_images_uuid_filename'), 'images', ['uuid_filename'], unique=True)
    op.create_index(op.f('ix_images_year_made'), 'images', ['year_made'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_images_year_made'), table_name='images')
    op.drop_index(op.f('ix_images_uuid_filename'), table_name='images')
    op.drop_index(op.f('ix_images_id'), table_name='images')
    op.drop_table('images')
