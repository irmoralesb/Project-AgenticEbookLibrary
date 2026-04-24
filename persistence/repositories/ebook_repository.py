import uuid
from typing import Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.ebook_metadata import EbookMetadata
from persistence.mappers import ebook_metadata_to_orm
from persistence.orm.ebook_orm import EbookORM


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
