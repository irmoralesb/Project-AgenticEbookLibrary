import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


class Base(DeclarativeBase):
    pass


class EbookORM(Base):
    __tablename__ = "ebooks"
    __table_args__ = (
        CheckConstraint(_CATEGORY_CHECK, name="ck_ebooks_category"),
        CheckConstraint(
            "year IS NULL OR (year >= 1950 AND year <= 2050)",
            name="ck_ebooks_year",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count >= 0",
            name="ck_ebooks_page_count",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    is_metadata_stored: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_embeded_data_stored: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    authors: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(40), nullable=False)
    publisher: Mapped[str] = mapped_column(
        String(60), nullable=False, default="Unknown"
    )
    edition: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Not Specified"
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    cover_image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cover_image_mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_errors: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_on: Mapped[datetime] = mapped_column(
        "CreatedOn",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.timezone("utc", func.now()),
    )
    updated_on: Mapped[datetime] = mapped_column(
        "UpdatedOn",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.timezone("utc", func.now()),
        onupdate=func.timezone("utc", func.now()),
    )
