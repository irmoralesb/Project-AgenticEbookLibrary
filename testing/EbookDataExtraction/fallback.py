from __future__ import annotations

import statistics
from typing import Iterator

import fitz

from EbookDataExtraction.normalize import filter_noise_paragraphs, lines_to_paragraphs


def _page_lines_with_sizes(page: fitz.Page) -> list[tuple[float, str, float]]:
    d = page.get_text("dict") or {}
    rows: list[tuple[float, str, float]] = []
    for block in d.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans)
            if not text.strip():
                continue
            y0 = float(line.get("bbox", (0.0, 0.0, 0.0, 0.0))[1])
            sizes = [float(s.get("size", 11.0)) for s in spans]
            mx = max(sizes) if sizes else 11.0
            rows.append((y0, text.replace("\u00ad", ""), mx))
    rows.sort(key=lambda r: r[0])
    return rows


def _median_size(rows: list[tuple[float, str, float]]) -> float:
    sizes = [s for _y, t, s in rows if len(t.strip()) > 2]
    if not sizes:
        return 11.0
    return float(statistics.median(sizes))


def iter_paragraphs_fallback(
    doc: fitz.Document,
    book_title: str,
) -> Iterator[tuple[str, str, str, int, int]]:
    """Yield (chapter, section, paragraph_text, page_start, page_end) without TOC.

    Uses font-size heuristics to propose section titles; chapter is always ``book_title``.
    """
    chapter = book_title
    current_section = ""
    for pno in range(len(doc)):
        page = doc.load_page(pno)
        page_num = pno + 1
        rows = _page_lines_with_sizes(page)
        if not rows:
            continue
        med = _median_size(rows)
        line_buf: list[str] = []

        def flush_buffer() -> Iterator[tuple[str, str, str, int, int]]:
            nonlocal line_buf
            if not line_buf:
                return
            raw = "\n".join(line_buf)
            line_buf = []
            paras = filter_noise_paragraphs(lines_to_paragraphs(raw.split("\n")))
            for para in paras:
                yield chapter, current_section, para, page_num, page_num

        for _y, text, sz in rows:
            stripped = text.strip()
            if not stripped:
                yield from flush_buffer()
                continue
            is_heading = (
                sz >= med * 1.12
                and len(stripped) < 180
                and len(stripped.split()) <= 18
            )
            if is_heading:
                yield from flush_buffer()
                current_section = stripped
            else:
                line_buf.append(stripped)
        yield from flush_buffer()
