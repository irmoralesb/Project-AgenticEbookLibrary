"""Pydantic request / response models for the API layer.

These are intentionally separate from the domain models so the HTTP contract
can evolve independently of the internal EbookMetadata / EbookORM types.
"""

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field

TagKeyword = Annotated[str, Field(max_length=80)]


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
    tags: list[str]
    publisher: str | None
    edition: str | None
    language: str | None
    page_count: int | None
    file_name: str | None
    file_path: str | None
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
    category: str | None = Field(default=None, max_length=60)
    subcategory: str | None = Field(default=None, max_length=40)
    tags: list[TagKeyword] | None = Field(default=None, max_length=50)
    publisher: str | None = Field(default=None, max_length=60)
    edition: str | None = Field(default=None, max_length=20)
    language: str | None = Field(default=None, max_length=10)
    page_count: int | None = Field(default=None, ge=0)
    file_path: str | None = Field(default=None, max_length=2048)
    has_errors: bool | None = None


class IngestRequest(BaseModel):
    """Body for POST /api/ingest/start."""

    path: str = Field(description="Absolute directory path to scan for ebooks.")
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


ReextractFieldName = Literal["authors", "isbn", "publisher", "year"]
ReextractDirection = Literal["front_to_back", "back_to_front"]


class ReextractFieldRequest(BaseModel):
    field: ReextractFieldName
    page_range: str = Field(
        description="1-based inclusive page range in the format 'start-end', e.g. '5-10'."
    )
    direction: ReextractDirection


class ReextractFieldResponse(BaseModel):
    field: ReextractFieldName
    value: str | list[str] | int | None
    used_start_page: int
    used_end_page: int
    direction: ReextractDirection
    message: str
