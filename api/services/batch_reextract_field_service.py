"""Batch re-extract + persist: runs in a worker thread with per-book DB sessions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from api.schemas import BatchReextractFieldJobRequest, ReextractFieldName
from api.services.field_reextract_service import reextract_field_for_ebook
from persistence.repositories.ebook_repository import SqlAlchemyEbookRepository
from persistence.session import SessionLocal


def reextract_value_to_repo_update(
    field: ReextractFieldName,
    value: str | list[str] | int | None,
) -> dict[str, Any] | None:
    """Map extracted value to ``EbookRepository.update`` payload, or None to skip persist."""
    if value is None:
        return None
    if field == "authors":
        if not isinstance(value, list) or len(value) == 0:
            return None
        return {"authors": [str(x) for x in value]}
    if field == "tags":
        if not isinstance(value, list) or len(value) == 0:
            return None
        return {"tags": [str(x) for x in value]}
    if field == "isbn":
        if not isinstance(value, str) or not value.strip():
            return None
        return {"isbn": value.strip()}
    if field == "publisher":
        if not isinstance(value, str) or not value.strip():
            return None
        return {"publisher": value.strip()}
    if field == "year":
        if isinstance(value, int) and 1950 <= value <= 2050:
            return {"year": value}
        if isinstance(value, str) and value.strip():
            try:
                y = int(value.strip())
            except ValueError:
                return None
            if 1950 <= y <= 2050:
                return {"year": y}
        return None
    return None


def run_batch_reextract_field_job(
    job: BatchReextractFieldJobRequest,
    on_progress: Callable[[str], None],
) -> None:
    total = len(job.ebook_ids)
    for i, ebook_id in enumerate(job.ebook_ids, start=1):
        session = SessionLocal()
        try:
            repo = SqlAlchemyEbookRepository(session)
            row = repo.get_by_id(ebook_id)
            if row is None:
                on_progress(f"[{i}/{total}] {ebook_id}: not found in database.")
                continue

            title = row.title or row.file_name or str(ebook_id)

            try:
                result = reextract_field_for_ebook(
                    ebook=row,
                    field=job.field,
                    page_range=job.page_range,
                    direction=job.direction,
                )
            except HTTPException as e:
                detail = e.detail if isinstance(e.detail, str) else str(e.detail)
                on_progress(f"[{i}/{total}] {title}: {detail}")
                continue
            except Exception as e:  # noqa: BLE001
                on_progress(f"[{i}/{total}] {title}: error — {e}")
                continue

            payload = reextract_value_to_repo_update(result.field, result.value)
            if payload is None:
                on_progress(f"[{i}/{total}] {title}: {result.message} (not saved)")
                continue

            updated = repo.update(ebook_id, payload)
            if updated is None:
                on_progress(f"[{i}/{total}] {title}: update skipped (row missing).")
                continue

            session.commit()
            on_progress(f"[{i}/{total}] {title}: saved {result.field}.")
        except Exception as e:  # noqa: BLE001
            session.rollback()
            on_progress(f"[{i}/{total}] {ebook_id}: database error — {e}")
        finally:
            session.close()
