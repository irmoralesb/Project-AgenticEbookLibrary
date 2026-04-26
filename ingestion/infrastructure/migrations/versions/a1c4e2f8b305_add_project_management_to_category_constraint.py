"""add_project_management_to_category_constraint

Revision ID: a1c4e2f8b305
Revises: 3f9d0d4d3dc2
Create Date: 2026-04-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c4e2f8b305"
down_revision: Union[str, None] = "3f9d0d4d3dc2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_CATEGORIES = (
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

_NEW_CATEGORIES = (
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
    "Project Management",
    "Other",
)


def _check_expr(categories: tuple[str, ...]) -> str:
    values = ", ".join(f"'{v}'" for v in categories)
    return f"category IN ({values})"


def upgrade() -> None:
    op.drop_constraint("ck_ebooks_category", "ebooks", type_="check")
    op.create_check_constraint(
        "ck_ebooks_category",
        "ebooks",
        _check_expr(_NEW_CATEGORIES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_ebooks_category", "ebooks", type_="check")
    op.create_check_constraint(
        "ck_ebooks_category",
        "ebooks",
        _check_expr(_OLD_CATEGORIES),
    )
