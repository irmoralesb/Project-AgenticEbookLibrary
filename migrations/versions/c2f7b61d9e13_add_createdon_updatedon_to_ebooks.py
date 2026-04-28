"""add_createdon_updatedon_to_ebooks

Revision ID: c2f7b61d9e13
Revises: b7e3c1a9d042
Create Date: 2026-04-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2f7b61d9e13"
down_revision: Union[str, None] = "b7e3c1a9d042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ebooks",
        sa.Column(
            "CreatedOn",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )
    op.add_column(
        "ebooks",
        sa.Column(
            "UpdatedOn",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ebooks", "UpdatedOn")
    op.drop_column("ebooks", "CreatedOn")
