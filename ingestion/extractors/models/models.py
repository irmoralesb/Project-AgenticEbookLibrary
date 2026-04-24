from pydantic import BaseModel, Field

from domain.ebook_metadata import Category, EbookMetadata


class QueryTitleWithEdition(BaseModel):
    """It stores the title and the edition number of the book"""

    title: str = Field(description="The title of the ebook")
    edition: str = Field(description="The edition corresponding to the ebook")


class QueryEbookMetadata(BaseModel):
    """Metadata the LLM must extract from the first pages of an ebook PDF."""

    isbn: str | None = Field(
        default="Not Found",
        max_length=20,
        description="ISBN-10 or ISBN-13 as printed in the book (keep hyphens). Return null when not present.",
    )
    authors: list[str] = Field(
        default_factory=list,
        description="Author names in printed order. Return an empty list when no authors are found.",
    )
    year: int | None = Field(
        default=None,
        ge=1950,
        le=2050,
        description="Publication or copyright year as an integer. Return null when not found.",
    )
    description: str | None = Field(
        default="Not Found",
        max_length=2000,
        description=(
            "The self summary in the book located in the first pages."
            "If not found otherwise synthesize a concise description from the available text. "
            "Never return the string 'N/A' here."
        ),
    )
    category: Category | None = Field(
        default="Other",
        description=(
            "General topic of the book. Must be exactly one of: "
            "Programming, Software Engineering & Design Patterns, Data Structures & Algorithms, "
            "Web Development, Mobile App Development, Cybersecurity & Ethical Hacking, DevOps, "
            "Operating Systems, Cloud Services, Architecture, Networking, Databases, AI/ML, Other."
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
            "AI/ML -> Machine Learning/LLMs/Neural Networks. "
            "Project Management -> Agile Development/Scrum/Kanban/Extreme Programming"
            "Return 'Other' when none applies."
        ),
    )
    publisher: str | None = Field(
        default="Unknown",
        max_length=60,
        description="Publisher name, e.g. O'Reilly, Apress, Microsoft Press. Return 'Unknown' when not found.",
    )
    language: str | None = Field(
        default="en",
        max_length=10,
        description="ISO-639-1 code for the book's language, e.g. 'en', 'es'. Default to 'en' when unclear.",
    )
    has_errors: bool = Field(
        default=False,
        description="Flag to identify if the metadata extraction failed.",
    )


def map_query_to_ebook_metadata(
    query_metadata: QueryEbookMetadata,
    *,
    title: str,
    file_name: str,
    page_count: int | None = None,
    edition: str = "Not Specified",
    has_errors: bool,
) -> EbookMetadata:
    """Map LLM-extracted query metadata into the final document metadata model."""

    query_values = query_metadata.model_dump()

    def _fallback_text(value: str | None, fallback: str) -> str:
        if value is None:
            return fallback
        normalized_value = value.strip()
        return normalized_value if normalized_value else fallback

    return EbookMetadata(
        title=_fallback_text(title, "Not Found"),
        file_name=_fallback_text(file_name, "Not Found"),
        page_count=page_count,
        edition=_fallback_text(edition, "Not Specified"),
        isbn=_fallback_text(query_values.get("isbn"), "Not Found"),
        authors=query_values.get("authors") or [],
        year=query_values.get("year"),
        description=_fallback_text(query_values.get("description"), "Not Found"),
        category=_fallback_text(query_values.get("category"), "Other"),
        subcategory=_fallback_text(query_values.get("subcategory"), "Other"),
        publisher=_fallback_text(query_values.get("publisher"), "Unknown"),
        language=_fallback_text(query_values.get("language"), "en"),
        has_errors=has_errors,
    )
