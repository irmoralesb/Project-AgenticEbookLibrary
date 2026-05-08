"""drop_category_check_constraint

Revision ID: e9b4c1d72f80
Revises: f4c2b8a91d70
Create Date: 2026-05-05

"""
from typing import Sequence, Union

from alembic import op

revision: str = "e9b4c1d72f80"
down_revision: Union[str, Sequence[str], None] = "f4c2b8a91d70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match pre-drop ck_ebooks_category (used only on downgrade).
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
    "Project Management",
    "Video Game Development",
    "Drawing",
    "Other",
)

_CATEGORY_CHECK = "category IN ({})".format(
    ", ".join(f"'{v}'" for v in _VALID_CATEGORIES)
)


def upgrade() -> None:
    op.drop_constraint("ck_ebooks_category", "ebooks", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_ebooks_category",
        "ebooks",
        _CATEGORY_CHECK,
    )
