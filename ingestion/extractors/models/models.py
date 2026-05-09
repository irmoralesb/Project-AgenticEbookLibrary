from dataclasses import dataclass

from pydantic import BaseModel, Field

from domain.ebook_metadata import EbookMetadata


@dataclass(frozen=True)
class CoverExtractionResult:
    data: bytes
    mime_type: str


class QueryTitleWithEdition(BaseModel):
    """It stores the title and the edition number of the book"""

    title: str = Field(description="The title of the ebook")
    edition: str = Field(description="The edition corresponding to the ebook")


class QueryAuthors(BaseModel):
    """It stores a list of authors of the book"""

    authors: list[str] = Field(
        description="Author names, no special sort. if they are not found return empty list"
    )


class QueryPublisher(BaseModel):
    """Publisher imprint extracted by the LLM from colophon-style early pages."""

    publisher: str | None = Field(
        default=None,
        max_length=60,
        description=(
            "The publishing imprint or publishing house exactly as evidenced in the text "
            '(e.g. after "Published by", on the copyright page, or in the colophon). '
            "At most 60 characters. Use null when no publisher is clearly stated or you are unsure."
        ),
    )


class QueryCategoryMetadata(BaseModel):
    """Category and subcategory extracted by the LLM from the first pages of an ebook."""

    category: str | None = Field(
        default="Other",
        max_length=60,
        description=(
            "Concise shelf-style label for the book’s subject (≤60 characters). "
            "Examples for orientation only (not an exhaustive list): Programming, History, Cooking. "
            "Use 'Other' when the topic is unclear."
        ),
    )
    subcategory: str | None = Field(
        default="Other",
        max_length=40,
        description=(
            "More specific facet under the category (≤40 characters), e.g. Python under Programming "
            "or Medieval Europe under History. Use 'Other' when unsure."
        ),
    )


def map_query_to_ebook_metadata(
    *,
    title: str,
    file_name: str,
    file_path: str | None = None,
    page_count: int | None = None,
    edition: str = "Not Specified",
    isbn: str | None,
    authors: list[str],
    year: int | None,
    description: str | None,
    category: str | None,
    subcategory: str | None,
    publisher: str | None,
    language: str | None,
    has_errors: bool,
    cover_image_path: str | None = None,
    cover_image_mime_type: str | None = None,
    tags: list[str] | None = None,
) -> EbookMetadata:
    """Assemble the final EbookMetadata from individually extracted fields."""

    def _fallback_text(value: str | None, fallback: str) -> str:
        if value is None:
            return fallback
        normalized = value.strip()
        return normalized if normalized else fallback

    return EbookMetadata(
        title=_fallback_text(title, "Not Found"),
        file_name=_fallback_text(file_name, "Not Found"),
        file_path=file_path.strip() if file_path and file_path.strip() else None,
        page_count=page_count,
        edition=_fallback_text(edition, "Not Specified"),
        isbn=_fallback_text(isbn, "Not Found"),
        authors=authors or [],
        year=year,
        description=_fallback_text(description, "Not Found"),
        category=_fallback_text(category, "Other"),
        subcategory=_fallback_text(subcategory, "Other"),
        tags=list(tags) if tags else [],
        publisher=_fallback_text(publisher, "Unknown"),
        language=_fallback_text(language, "en"),
        has_errors=has_errors,
        cover_image_path=cover_image_path,
        cover_image_mime_type=cover_image_mime_type,
    )
