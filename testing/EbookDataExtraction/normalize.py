from __future__ import annotations

import re

MIN_PARA_CHARS = 20

HEADING_LINE_RE = re.compile(
    r"^(chapter|appendix|part)\s+[\dIVXLC]+",
    re.IGNORECASE,
)
SECTION_NUM_RE = re.compile(r"^\d+(\.\d+)*\s+\S")


def _looks_like_heading(line: str) -> bool:
    s = line.strip()
    if len(s) < 4 or len(s) > 200:
        return False
    if HEADING_LINE_RE.match(s):
        return True
    if SECTION_NUM_RE.match(s) and s[0].isdigit():
        return True
    if s.isupper() and len(s.split()) <= 12:
        return True
    return False


def lines_to_paragraphs(lines: list[str]) -> list[str]:
    paras: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paras.append(" ".join(current))
                current = []
            continue
        current.append(stripped)
    if current:
        paras.append(" ".join(current))
    return paras


def page_text_to_paragraphs(raw: str) -> list[str]:
    if not raw:
        return []
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    return lines_to_paragraphs(lines)


def filter_noise_paragraphs(paras: list[str]) -> list[str]:
    out: list[str] = []
    for p in paras:
        t = p.strip()
        if len(t) < MIN_PARA_CHARS and not _looks_like_heading(t):
            continue
        out.append(t)
    return out
