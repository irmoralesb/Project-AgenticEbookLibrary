"""Pydantic request / response models for the API layer.

These are intentionally separate from the domain models so the HTTP contract
can evolve independently of the internal EbookMetadata / EbookORM types.
"""

import uuid
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


class EbookResponse(BaseModel):
    """Serialised representation of a stored ebook row."""

    id: uuid.UUID
    title: str | None
    isbn: str | None
    authors: list[str]
    year: int | None
    description: str | None
    category: str | None
    subcategory: str | None
    publisher: str | None
    edition: str | None
    language: str | None
    page_count: int | None
    file_name: str | None
    cover_image_path: str | None
    cover_image_mime_type: str | None
    has_errors: bool
    is_metadata_stored: bool
    is_embeded_data_stored: bool

    model_config = {"from_attributes": True}


class EbookUpdateRequest(BaseModel):
    """All fields are optional — only provided keys will be updated."""

    title: str | None = Field(default=None, max_length=100)
    isbn: str | None = Field(default=None, max_length=20)
    authors: list[str] | None = None
    year: int | None = Field(default=None, ge=1950, le=2050)
    description: str | None = Field(default=None, max_length=2000)
    category: Category | None = None
    subcategory: str | None = Field(default=None, max_length=40)
    publisher: str | None = Field(default=None, max_length=60)
    edition: str | None = Field(default=None, max_length=20)
    language: str | None = Field(default=None, max_length=10)
    page_count: int | None = Field(default=None, ge=0)
    has_errors: bool | None = None


class IngestRequest(BaseModel):
    """Body for POST /api/ingest/start."""

    path: str = Field(description="Absolute directory path to scan for ebooks.")
    extension: str = Field(
        default="pdf",
        description="File extension to filter (pdf or epub).",
        pattern=r"^(pdf|epub)$",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of new books to process.",
    )


class IngestStartResponse(BaseModel):
    """Returned by POST /api/ingest/start when the job is enqueued."""

    job_id: str
    message: str


class FolderPickerResponse(BaseModel):
    path: str | None
