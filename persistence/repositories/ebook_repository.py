import uuid
from typing import Protocol, runtime_checkable

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.ebook_metadata import EbookMetadata
from persistence.mappers import ebook_metadata_to_orm
from persistence.orm.ebook_orm import EbookORM

_UPDATABLE_FIELDS = frozenset(
    {
        "title",
        "isbn",
        "authors",
        "year",
        "description",
        "category",
        "subcategory",
        "publisher",
        "edition",
        "language",
        "page_count",
        "cover_image_path",
        "cover_image_mime_type",
        "has_errors",
    }
)


@runtime_checkable
class EbookRepository(Protocol):
    """Persistence port for ebook aggregate (shared across pipeline stages)."""

    def add_from_metadata(self, metadata: EbookMetadata) -> EbookORM:
        """Insert a row from extracted metadata; marks metadata as stored."""
        ...

    def get_by_id(self, ebook_id: uuid.UUID) -> EbookORM | None:
        """Load by primary key (for later stages: RAG, admin, etc.)."""
        ...

    def exists_by_file_name(self, file_name: str) -> bool:
        """True if a row with this file name (including extension) is already stored."""
        ...

    def list_all(self, skip: int = 0, limit: int = 100) -> list[EbookORM]:
        """Return a paginated slice of all ebook rows ordered by title."""
        ...

    def update(self, ebook_id: uuid.UUID, data: dict) -> EbookORM | None:
        """Partially update allowed fields; returns updated row or None if not found."""
        ...

    def delete(self, ebook_id: uuid.UUID) -> bool:
        """Delete by PK; returns True if a row was removed, False if not found."""
        ...


class SqlAlchemyEbookRepository:  # implements EbookRepository
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_from_metadata(self, metadata: EbookMetadata) -> EbookORM:
        row = ebook_metadata_to_orm(metadata)
        row.is_metadata_stored = True
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_id(self, ebook_id: uuid.UUID) -> EbookORM | None:
        return self._session.get(EbookORM, ebook_id)

    def exists_by_file_name(self, file_name: str) -> bool:
        stmt = select(EbookORM.id).where(EbookORM.file_name == file_name).limit(1)
        return self._session.execute(stmt).first() is not None

    def list_all(self, skip: int = 0, limit: int = 100) -> list[EbookORM]:
        stmt = select(EbookORM).order_by(EbookORM.title).offset(skip).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def update(self, ebook_id: uuid.UUID, data: dict) -> EbookORM | None:
        row = self._session.get(EbookORM, ebook_id)
        if row is None:
            return None
        for field, value in data.items():
            if field in _UPDATABLE_FIELDS:
                setattr(row, field, value)
        self._session.flush()
        return row

    def delete(self, ebook_id: uuid.UUID) -> bool:
        stmt = sa_delete(EbookORM).where(EbookORM.id == ebook_id)
        result = self._session.execute(stmt)
        return result.rowcount > 0
