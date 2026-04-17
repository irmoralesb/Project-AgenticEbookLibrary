from __future__ import annotations

import re

import fitz

MAX_TOC_SCAN_PAGES = 50
MIN_LINKS_TO_START = 10
MIN_LINKS_TO_CONTINUE = 5
CONTENTS_RE = re.compile(r"\bcontents\b", re.IGNORECASE)
DOT_LEADER_RE = re.compile(r"\.{2,}.*$")


def _count_goto_links(page: fitz.Page) -> int:
    n = 0
    for L in page.get_links():
        if L.get("kind") == 1 and L.get("page") is not None:
            n += 1
    return n


def clean_toc_title(raw: str) -> str:
    s = re.sub(r"\s+", " ", (raw or "").strip())
    s = DOT_LEADER_RE.sub("", s).strip()
    s = re.sub(r"[\s.]+$", "", s)
    return s.strip()


def find_link_toc_page_indices(doc: fitz.Document) -> list[int]:
    """Find 0-based page indices that form a linked Table of Contents (no PDF outline)."""
    start: int | None = None
    limit = min(len(doc), MAX_TOC_SCAN_PAGES)
    for i in range(limit):
        page = doc.load_page(i)
        n = _count_goto_links(page)
        text = (page.get_text("text") or "")[:6000]
        if n >= MIN_LINKS_TO_START and CONTENTS_RE.search(text):
            start = i
            break
    if start is None:
        return []
    out: list[int] = [start]
    j = start + 1
    while j < len(doc) and j < start + 25:
        page = doc.load_page(j)
        n = _count_goto_links(page)
        if n >= MIN_LINKS_TO_CONTINUE:
            out.append(j)
            j += 1
        else:
            break
    return out


def _x_to_level(x0: float, ordered_bins: list[float]) -> int:
    rx = round(float(x0), 0)
    if rx in ordered_bins:
        return ordered_bins.index(rx) + 1
    nearest = min(ordered_bins, key=lambda b: abs(b - rx))
    return ordered_bins.index(nearest) + 1


def synthetic_toc_from_links(doc: fitz.Document) -> list[list]:
    """Build ``[level, title, page_1based]`` entries like :meth:`fitz.Document.get_toc` when outline is empty.

    Uses internal (``kind == 1``) links on detected Contents pages; indentation (``x0``) maps to depth.
    """
    toc_pages = find_link_toc_page_indices(doc)
    if not toc_pages:
        return []

    rows: list[tuple[int, float, float, int, str]] = []
    for pi in toc_pages:
        page = doc.load_page(pi)
        for L in page.get_links():
            if L.get("kind") != 1 or L.get("page") is None:
                continue
            r = L.get("from")
            if r is None:
                continue
            dest0 = int(L["page"])
            title = clean_toc_title(page.get_textbox(r))
            if len(title) < 2:
                continue
            rows.append((pi, float(r.y0), float(r.x0), dest0, title))

    if not rows:
        return []

    rows.sort(key=lambda t: (t[0], t[1]))
    x_bins = sorted({round(t[2], 0) for t in rows})
    if not x_bins:
        return []

    out: list[list] = []
    for _pi, _y0, x0, dest0, title in rows:
        level = _x_to_level(x0, x_bins)
        page_1based = dest0 + 1
        out.append([level, title, page_1based])
    return out
