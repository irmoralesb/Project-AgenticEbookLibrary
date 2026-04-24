from domain.ebook_metadata import EbookMetadata
from persistence.orm.ebook_orm import EbookORM


def ebook_metadata_to_orm(metadata: EbookMetadata) -> EbookORM:
    """Convert a Pydantic EbookMetadata instance into a new (unsaved) EbookORM row."""
    return EbookORM(
        title=metadata.title or "Not Found",
        isbn=metadata.isbn,
        authors=metadata.authors,
        year=metadata.year,
        description=metadata.description,
        category=metadata.category or "Other",
        subcategory=metadata.subcategory or "Other",
        publisher=metadata.publisher or "Unknown",
        edition=metadata.edition or "Not Specified",
        language=metadata.language or "en",
        page_count=metadata.page_count,
        file_name=metadata.file_name or "Not Found",
        cover_image_path=metadata.cover_image_path,
        cover_image_mime_type=metadata.cover_image_mime_type,
    )
