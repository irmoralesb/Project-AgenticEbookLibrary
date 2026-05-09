"""Load publisher imprint names from the catalog table for regex extraction."""

from __future__ import annotations

from sqlalchemy import select

from persistence.orm.known_publisher_orm import KnownPublisherORM
from persistence.session import SessionLocal


def list_known_publisher_names_ordered_for_matching() -> list[str]:
    """Return distinct non-empty catalog names, longest first (regex alternation order)."""
    session = SessionLocal()
    try:
        stmt = select(KnownPublisherORM.name)
        rows = session.scalars(stmt).all()
    finally:
        session.close()

    names = [n.strip() for n in rows if n and n.strip()]
    names.sort(key=len, reverse=True)
    return names


def load_known_publisher_names_from_db() -> list[str]:
    """Names for tier-1 regex; returns empty list if the database cannot be read."""
    try:
        return list_known_publisher_names_ordered_for_matching()
    except Exception:
        return []
