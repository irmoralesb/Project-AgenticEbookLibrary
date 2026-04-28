from dataclasses import dataclass

from pydantic import BaseModel, Field

from domain.ebook_metadata import Category, EbookMetadata


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


class QueryCategoryMetadata(BaseModel):
    """Category and subcategory extracted by the LLM from the first pages of an ebook."""

    category: Category | None = Field(
        default="Other",
        description=(
            "General topic of the book. Must be exactly one of: "
            "Programming, Software Engineering & Design Patterns, Data Structures & Algorithms, "
            "Web Development, Mobile App Development, Cybersecurity & Ethical Hacking, DevOps, "
            "Operating Systems, Cloud Services, Architecture, Networking, Databases, AI/ML, "
            "Project Management, Other."
        ),
    )
    subcategory: str | None = Field(
        default="Other",
        max_length=40,
        description=(
            "Specific topic within the chosen category, e.g. "
            "Programming -> C#/Python/JavaScript, "
            "Software Engineering & Design Patterns -> Domain Driven Design/Clean Architecture/SOLID, "
            "Data Structures & Algorithms -> Arrays/Graphs/Dynamic Programming, "
            "Web Development -> HTML/CSS/React/ASP.NET, "
            "Mobile App Development -> Android/iOS/Flutter, "
            "Cybersecurity & Ethical Hacking -> Penetration Testing/Threat Modeling, "
            "DevOps -> CI/CD/Docker/Kubernetes, "
            "Operating Systems -> Linux/Windows Internals/Process Scheduling, "
            "Cloud Services -> Azure/AWS/GCP, "
            "Architecture -> Microservices/Event-Driven Architecture/System Design, "
            "Networking -> Firewall/Routing/TCP-IP, "
            "Databases -> MS SQL/PostgreSQL/MongoDB, "
            "AI/ML -> Machine Learning/LLMs/Neural Networks, "
            "Project Management -> Agile Development/Scrum/Kanban/Extreme Programming. "
            "Return 'Other' when none applies."
        ),
    )


def map_query_to_ebook_metadata(
    *,
    title: str,
    file_name: str,
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
        page_count=page_count,
        edition=_fallback_text(edition, "Not Specified"),
        isbn=_fallback_text(isbn, "Not Found"),
        authors=authors or [],
        year=year,
        description=_fallback_text(description, "Not Found"),
        category=_fallback_text(category, "Other"),
        subcategory=_fallback_text(subcategory, "Other"),
        publisher=_fallback_text(publisher, "Unknown"),
        language=_fallback_text(language, "en"),
        has_errors=has_errors,
        cover_image_path=cover_image_path,
        cover_image_mime_type=cover_image_mime_type,
    )
