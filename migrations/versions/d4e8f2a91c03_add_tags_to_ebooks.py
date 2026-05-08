"""add_tags_to_ebooks

Revision ID: d4e8f2a91c03
Revises: e9b4c1d72f80
Create Date: 2026-05-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4e8f2a91c03"
down_revision: Union[str, None] = "e9b4c1d72f80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ebooks",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("ebooks", "tags")
