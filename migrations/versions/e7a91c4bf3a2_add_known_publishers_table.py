"""add known_publishers table

Revision ID: e7a91c4bf3a2
Revises: d4e8f2a91c03
Create Date: 2026-05-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a91c4bf3a2"
down_revision: Union[str, None] = "d4e8f2a91c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Former in-code _KNOWN_PUBLISHERS (pre–DB catalog); seeded so regex tier matches legacy imprints.
_SEED_KNOWN_PUBLISHER_NAMES: tuple[str, ...] = (
    "No Starch Press",
    "Microsoft Press",
    "Addison-Wesley Professional",
    "Addison-Wesley",
    "Pearson Education",
    "Pearson",
    "O'Reilly Media",
    "O'Reilly",
    "Packt Publishing",
    "Packt",
    "Manning Publications",
    "Manning",
    "Apress",
    "Wrox Press",
    "Wrox",
    "Wiley",
    "Sybex",
    "Pragmatic Bookshelf",
    "The Pragmatic Programmers",
    "Springer",
    "CRC Press",
    "MIT Press",
    "Oxford University Press",
    "Cambridge University Press",
    "New Riders",
    "Que Publishing",
    "Sams Publishing",
    "Cengage Learning",
    "Jones & Bartlett",
    "IBM Press",
    "Oracle Press",
)


def upgrade() -> None:
    op.create_table(
        "known_publishers",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    conn = op.get_bind()
    insert_sql = sa.text(
        "INSERT INTO known_publishers (id, name) VALUES (gen_random_uuid(), :name)"
    )
    for name in _SEED_KNOWN_PUBLISHER_NAMES:
        conn.execute(insert_sql, {"name": name})


def downgrade() -> None:
    op.drop_table("known_publishers")
