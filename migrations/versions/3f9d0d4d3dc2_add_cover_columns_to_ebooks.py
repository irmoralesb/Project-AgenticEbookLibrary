"""add_cover_columns_to_ebooks

Revision ID: 3f9d0d4d3dc2
Revises: eaad33598bc1
Create Date: 2026-04-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3f9d0d4d3dc2"
down_revision: Union[str, None] = "eaad33598bc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ebooks", sa.Column("cover_image_path", sa.String(length=1024), nullable=True))
    op.add_column("ebooks", sa.Column("cover_image_mime_type", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("ebooks", "cover_image_mime_type")
    op.drop_column("ebooks", "cover_image_path")
