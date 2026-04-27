"""FastAPI dependency providers for DB session and repository."""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from persistence.repositories.ebook_repository import (
    EbookRepository,
    SqlAlchemyEbookRepository,
)
from persistence.session import get_db_session as _get_db_session


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure commit / rollback / close."""
    yield from _get_db_session()


def get_repository(session: Session = Depends(get_db)) -> EbookRepository:
    """Provide a repository bound to the current request's session."""
    return SqlAlchemyEbookRepository(session)
