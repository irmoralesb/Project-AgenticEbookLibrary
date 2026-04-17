from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator

import fitz

from EbookDataExtraction.db import save_book_to_postgres
from EbookDataExtraction.fallback import iter_paragraphs_fallback
from EbookDataExtraction.link_toc import synthetic_toc_from_links
from EbookDataExtraction.io import book_slug, write_book
from EbookDataExtraction.metadata import build_book_metadata
from EbookDataExtraction.normalize import filter_noise_paragraphs, page_text_to_paragraphs
from EbookDataExtraction.toc import (
    apply_toc_to_stack,
    chapter_outline_level1,
    group_toc_events_by_page,
    stack_to_labels,
    usable_outline,
)


def _iter_paragraphs_with_toc(
    doc: fitz.Document,
    toc: list[list],
) -> Iterator[tuple[str, str, str, int, int]]:
    events = group_toc_events_by_page(toc)
    stack: list[tuple[int, str]] = []
    for page_1based in range(1, len(doc) + 1):
        for level, title in events.get(page_1based, []):
            apply_toc_to_stack(stack, level, title)
        chapter, section = stack_to_labels(stack)
        page = doc.load_page(page_1based - 1)
        raw = page.get_text("text") or ""
        for para in filter_noise_paragraphs(page_text_to_paragraphs(raw)):
            yield chapter, section, para, page_1based, page_1based


def process_pdf(
    pdf_path: Path,
    project_root: Path,
    storage_root: Path,
    database_url: str | None = None,
) -> tuple[dict[str, Any], int]:
    pdf_path = pdf_path.resolve()
    project_root = project_root.resolve()
    storage_root = storage_root.resolve()

    doc = fitz.open(pdf_path)
    try:
        toc = doc.get_toc() or []
        if not toc:
            toc = synthetic_toc_from_links(doc)
        title_base = ((doc.metadata or {}).get("title") or "").strip() or pdf_path.stem

        if usable_outline(toc):
            outline = chapter_outline_level1(toc)
            if outline:
                chapters = [t for t, _ in outline]
                chapter_start_pages = [p for _, p in outline]
            else:
                chapters = [title_base]
                chapter_start_pages = [None]
            paragraph_source = _iter_paragraphs_with_toc(doc, toc)
        else:
            chapters = [title_base]
            chapter_start_pages = [None]
            paragraph_source = iter_paragraphs_fallback(doc, title_base)

        metadata = build_book_metadata(
            doc, pdf_path, project_root, chapters, chapter_start_pages
        )
        source_file = metadata["source_file"]
        book_title = metadata["title"]
        isbn = metadata.get("isbn") or ""

        counts: defaultdict[tuple[str, str], int] = defaultdict(int)
        chunks: list[dict[str, Any]] = []

        for chapter, section, text, p_start, p_end in paragraph_source:
            key = (chapter, section)
            counts[key] += 1
            chunks.append(
                {
                    "chapter": chapter,
                    "section": section,
                    "paragraph_index": counts[key],
                    "text": text,
                    "page_start": p_start,
                    "page_end": p_end,
                    "source_file": source_file,
                    "book_title": book_title,
                    "isbn": isbn,
                }
            )

        slug = book_slug(pdf_path)
        write_book(storage_root, slug, metadata, chunks)
        if database_url:
            save_book_to_postgres(database_url, slug, metadata, chunks)
        return metadata, len(chunks)
    finally:
        doc.close()
