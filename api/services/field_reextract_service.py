"""Targeted single-field metadata re-extraction helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz
from ebooklib import epub
from fastapi import HTTPException, status

from api.schemas import ReextractDirection, ReextractFieldName
from ingestion.dependency_injection.dependency_utils import (
    get_authors_extractor,
    get_epub_data_extractor,
    get_isbn_extractor,
    get_pdf_data_extractor,
    get_publisher_extractor,
    get_year_extractor,
)
from persistence.orm.ebook_orm import EbookORM

_PAGE_RANGE_PATTERN = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")


@dataclass(frozen=True)
class ReextractResult:
    field: ReextractFieldName
    value: str | list[str] | None
    used_start_page: int
    used_end_page: int
    direction: ReextractDirection
    message: str


def _parse_page_range(page_range: str) -> tuple[int, int]:
    match = _PAGE_RANGE_PATTERN.match(page_range)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid page_range format. Expected 'start-end' (example: '5-10').",
        )

    start_page = int(match.group(1))
    end_page = int(match.group(2))
    if start_page < 1 or end_page < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page range must use positive 1-based page numbers.",
        )
    if start_page > end_page:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Page range start must be less than or equal to end.",
        )
    return start_page, end_page


def _to_internal_bounds(
    start_page: int,
    end_page: int,
    total_pages: int,
    direction: ReextractDirection,
) -> tuple[int, int]:
    if total_pages < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ebook has no pages to analyze.",
        )
    if end_page > total_pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Page range out of bounds. Maximum page is {total_pages}.",
        )

    if direction == "front_to_back":
        return start_page, end_page

    mapped_start = total_pages - end_page + 1
    mapped_end = total_pages - start_page + 1
    return mapped_start, mapped_end


def _extract_pdf_range_text(file_path: Path, start_page: int, end_page: int) -> str:
    extractor = get_pdf_data_extractor()
    with fitz.open(file_path) as pdf_file:
        return extractor._get_pages_range_to_analize(
            pdf_file=pdf_file,
            start_page=start_page - 1,
            end_page_exclusive=end_page,
        )


def _extract_epub_range_text(file_path: Path, start_page: int, end_page: int) -> str:
    extractor = get_epub_data_extractor()
    book = epub.read_epub(str(file_path), options={"ignore_ncx": True})
    return extractor._get_text_range_from_spine(
        book=book,
        start_item=start_page - 1,
        end_item_exclusive=end_page,
    )


def _resolve_field_value(
    field: ReextractFieldName, text: str
) -> str | list[str] | int | None:
    if field == "authors":
        value = get_authors_extractor().get_authors([text])
        return value if value else None
    if field == "isbn":
        return get_isbn_extractor().extract_isbn_from_text([text])
    if field == "year":
        return get_year_extractor().extract_year_from_text([text])
    return get_publisher_extractor().extract_publisher_from_text([text])


def reextract_field_for_ebook(
    ebook: EbookORM,
    field: ReextractFieldName,
    page_range: str,
    direction: ReextractDirection,
) -> ReextractResult:
    if not ebook.file_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ebook has no source file path.",
        )

    source_path = Path(ebook.file_path).expanduser().resolve()
    if not source_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ebook source file not found: {source_path}",
        )

    start_page, end_page = _parse_page_range(page_range)
    extension = source_path.suffix.lower()

    if extension == ".pdf":
        with fitz.open(source_path) as pdf_file:
            total_pages = len(pdf_file)
        used_start, used_end = _to_internal_bounds(start_page, end_page, total_pages, direction)
        text = _extract_pdf_range_text(source_path, used_start, used_end)
    elif extension == ".epub":
        book = epub.read_epub(str(source_path), options={"ignore_ncx": True})
        total_pages = len(book.spine)
        used_start, used_end = _to_internal_bounds(start_page, end_page, total_pages, direction)
        text = _extract_epub_range_text(source_path, used_start, used_end)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported ebook type '{extension}'. Only .pdf and .epub are supported.",
        )

    value = _resolve_field_value(field, text)
    message = "Field extracted successfully." if value else "No value found in selected range."

    return ReextractResult(
        field=field,
        value=value,
        used_start_page=used_start,
        used_end_page=used_end,
        direction=direction,
        message=message,
    )
