"""add_has_errors_to_ebooks

Revision ID: b7e3c1a9d042
Revises: a1c4e2f8b305
Create Date: 2026-04-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e3c1a9d042"
down_revision: Union[str, None] = "a1c4e2f8b305"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ebooks",
        sa.Column("has_errors", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("ebooks", "has_errors")
