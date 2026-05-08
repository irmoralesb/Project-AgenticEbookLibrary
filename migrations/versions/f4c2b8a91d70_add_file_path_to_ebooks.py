"""add_file_path_to_ebooks

Revision ID: f4c2b8a91d70
Revises: 63be6fc0db78
Create Date: 2026-05-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c2b8a91d70"
down_revision: Union[str, Sequence[str], None] = "63be6fc0db78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ebooks",
        sa.Column("file_path", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ebooks", "file_path")
