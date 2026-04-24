"""initial_ebooks_table

Revision ID: eaad33598bc1
Revises:
Create Date: 2026-04-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "eaad33598bc1"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VALID_CATEGORIES = (
    "Programming",
    "Software Engineering & Design Patterns",
    "Data Structures & Algorithms",
    "Web Development",
    "Mobile App Development",
    "Cybersecurity & Ethical Hacking",
    "DevOps",
    "Operating Systems",
    "Cloud Services",
    "Architecture",
    "Networking",
    "Databases",
    "AI/ML",
    "Other",
)

_CATEGORY_CHECK = "category IN ({})".format(
    ", ".join(f"'{v}'" for v in _VALID_CATEGORIES)
)


def upgrade() -> None:
    op.create_table(
        "ebooks",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "is_metadata_stored", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "is_embeded_data_stored",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("isbn", sa.String(20), nullable=True),
        sa.Column(
            "authors",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("subcategory", sa.String(40), nullable=False),
        sa.Column(
            "publisher", sa.String(60), nullable=False, server_default="Unknown"
        ),
        sa.Column(
            "edition",
            sa.String(20),
            nullable=False,
            server_default="Not Specified",
        ),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.CheckConstraint(_CATEGORY_CHECK, name="ck_ebooks_category"),
        sa.CheckConstraint(
            "year IS NULL OR (year >= 1950 AND year <= 2050)",
            name="ck_ebooks_year",
        ),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count >= 0",
            name="ck_ebooks_page_count",
        ),
    )

    # Required for gen_random_uuid() used as server_default on the id column.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    op.drop_table("ebooks")
