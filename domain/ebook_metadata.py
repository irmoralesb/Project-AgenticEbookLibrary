from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
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
]


class EbookMetadata(BaseModel):
    """Document-level metadata for a technical ebook PDF (pre-RAG ingestion)."""

    title: str | None = Field(
        default="Not Found",
        max_length=100,
        description="Book title in display form, e.g. 'Prompt Engineering for Generative AI'",
    )
    isbn: str | None = Field(
        default="Not Found",
        max_length=20,
        description="ISBN-10 or ISBN-13 as printed (hyphens allowed)",
    )
    authors: list[str] = Field(
        default_factory=list, description="Author names in display order"
    )
    year: int | None = Field(
        default=None,
        ge=1950,
        le=2050,
        description="Publication or copyright year",
    )
    description: str | None = Field(
        default="Not Found",
        max_length=2000,
        description="Many books have a summary about the book in the first pages.",
    )
    category: Category | None = Field(
        default="Other",
        description="High-level shelf, e.g. Programming, Networking, Architecture",
    )
    subcategory: str | None = Field(
        default="Other",
        max_length=40,
        description="Narrower topic, e.g. C#, Python, Domain Driven Design",
    )
    publisher: str | None = Field(
        default="Unknown", max_length=60, description="Publisher name"
    )
    edition: str | None = Field(
        default="Not Specified",
        max_length=20,
        description="Edition label, e.g. '3rd' or '2024'",
    )
    language: str | None = Field(
        default="en",
        max_length=10,
        description="BCP 47 or ISO 639-1 code if known, e.g. 'en'",
    )
    page_count: int | None = Field(
        default=None, ge=0, description="Total pages in the PDF"
    )
    file_name: str | None = Field(
        default="Not Found", max_length=512, description="The Pdf file name"
    )
    cover_image_path: str | None = Field(
        default=None, max_length=1024, description="Stored path for extracted cover image"
    )
    cover_image_mime_type: str | None = Field(
        default=None, max_length=50, description="Cover image MIME type, e.g. image/png"
    )
    has_errors: bool = Field(
        default=False,
        description="Flag to identify if the metadata extraction failed.",
    )
