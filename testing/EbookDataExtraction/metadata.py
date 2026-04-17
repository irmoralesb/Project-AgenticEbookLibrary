from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

def _isbn10_check_digit(body9: str) -> str:
    total = sum((10 - i) * int(body9[i]) for i in range(9))
    r = total % 11
    return "X" if r == 1 else str((11 - r) % 11)


def _isbn10_valid(s: str) -> bool:
    if len(s) != 10 or not s[:9].isdigit():
        return False
    last = s[9].upper()
    if last not in "0123456789X":
        return False
    return _isbn10_check_digit(s[:9]) == last


def _isbn13_valid(s: str) -> bool:
    if len(s) != 13 or not s.isdigit():
        return False
    total = sum(int(s[i]) * (1 if i % 2 == 0 else 3) for i in range(12))
    check = (10 - (total % 10)) % 10
    return check == int(s[12])


def _isbn10_to_isbn13(s: str) -> str:
    """978 + 9-digit body + new EAN check digit."""
    body = "978" + s[:9]
    total = sum(int(body[i]) * (1 if i % 2 == 0 else 3) for i in range(12))
    check = (10 - (total % 10)) % 10
    return body + str(check)


def _normalize_isbn_candidate(raw: str) -> str | None:
    compact = re.sub(r"[\s\-]", "", raw.strip())
    if not compact:
        return None
    compact = compact.upper()
    m13 = re.fullmatch(r"97[89]\d{10}", compact)
    if m13 and _isbn13_valid(compact):
        return compact
    m10 = re.fullmatch(r"\d{9}[\dX]", compact)
    if m10 and _isbn10_valid(compact):
        return _isbn10_to_isbn13(compact)
    return None


def infer_isbn(doc: fitz.Document, meta: dict[str, Any]) -> str:
    """Best-effort ISBN from PDF metadata and the first few pages (copyright/imprint)."""
    blobs: list[str] = []
    for k, v in meta.items():
        if not v or not isinstance(v, str):
            continue
        lk = str(k).lower()
        if "isbn" in lk or lk in ("identifier", "dc:identifier"):
            blobs.append(v)
    for key in ("subject", "keywords", "title"):
        blobs.append((meta.get(key) or "").strip())
    head: list[str] = []
    for i in range(min(4, len(doc))):
        head.append(doc.load_page(i).get_text("text") or "")
    blobs.append("\n".join(head))

    for blob in blobs:
        if not blob:
            continue
        compact_line = re.sub(r"[\s\-]", "", blob)
        for m in re.finditer(r"97[89]\d{10}|\d{9}[\dX]", compact_line, re.I):
            cand = _normalize_isbn_candidate(m.group(0))
            if cand:
                return cand
    return ""


def _pdf_date_to_year(raw: str | None) -> int | None:
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("D:") and len(s) >= 6:
        # D:YYYYMMDDHHmmSS...
        digits = s[2:6]
        if digits.isdigit():
            y = int(digits)
            if 1900 <= y <= 2100:
                return y
    m = YEAR_RE.search(s)
    if m:
        return int(m.group(0))
    return None


def infer_year(
    meta: dict[str, Any],
    title: str,
    source_path: Path,
) -> int | None:
    for key in ("creationDate", "modDate", "CreationDate", "ModDate"):
        y = _pdf_date_to_year(meta.get(key))
        if y is not None:
            return y
    for blob in (title, source_path.stem):
        m = YEAR_RE.search(blob)
        if m:
            return int(m.group(0))
    return None


def _sample_text_for_language(doc: fitz.Document, max_pages: int = 4, max_chars: int = 12000) -> str:
    parts: list[str] = []
    n = min(len(doc), max_pages)
    for i in range(n):
        parts.append(doc.load_page(i).get_text("text") or "")
    return "\n".join(parts)[:max_chars]


def infer_language(doc: fitz.Document, meta: dict[str, Any]) -> str:
    raw = (meta.get("language") or meta.get("lang") or "").strip()
    if raw:
        return raw.split("-")[0].strip() if "-" in raw else raw
    try:
        from langdetect import detect

        sample = _sample_text_for_language(doc)
        if len(sample.strip()) < 80:
            return ""
        return detect(sample) or ""
    except Exception:
        return ""


def build_book_metadata(
    doc: fitz.Document,
    source_path: Path,
    project_root: Path,
    chapters: list[str],
    chapter_start_pages: list[int | None] | None = None,
) -> dict[str, Any]:
    meta = doc.metadata or {}
    title_raw = (meta.get("title") or "").strip()
    title = title_raw if title_raw else source_path.stem
    author = (meta.get("author") or "").strip()
    language = infer_language(doc, meta)
    year = infer_year(meta, title, source_path)
    isbn = infer_isbn(doc, meta)
    rel = source_path
    try:
        rel = source_path.resolve().relative_to(project_root.resolve())
    except ValueError:
        rel = source_path
    source_file = str(rel).replace("\\", "/")
    if chapter_start_pages is None:
        chapter_start_pages = [None] * len(chapters)
    elif len(chapter_start_pages) != len(chapters):
        raise ValueError("chapter_start_pages must match chapters length")
    return {
        "title": title,
        "author": author,
        "language": language,
        "year": year,
        "isbn": isbn,
        "chapters": chapters,
        "chapter_start_pages": chapter_start_pages,
        "source_file": source_file,
        "page_count": len(doc),
    }
