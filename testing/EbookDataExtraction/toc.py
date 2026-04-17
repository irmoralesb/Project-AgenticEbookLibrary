from __future__ import annotations

from collections import defaultdict


def chapter_titles_from_toc(toc: list[list]) -> list[str]:
    return [t for t, _ in chapter_outline_level1(toc)]


def chapter_outline_level1(toc: list[list]) -> list[tuple[str, int | None]]:
    """First-seen order of level-1 TOC entries with optional PDF start page."""
    ordered: list[tuple[str, int | None]] = []
    seen: set[str] = set()
    for item in toc:
        if len(item) < 3:
            continue
        level, title, page = item[0], item[1], item[2]
        if level != 1:
            continue
        t = (title or "").strip() or "Untitled"
        if t not in seen:
            seen.add(t)
            try:
                p = int(page)
                p = p if p >= 1 else None
            except (TypeError, ValueError):
                p = None
            ordered.append((t, p))
    return ordered


def group_toc_events_by_page(toc: list[list]) -> dict[int, list[tuple[int, str]]]:
    by_page: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for item in toc:
        if len(item) < 3:
            continue
        level, title, page = int(item[0]), item[1], int(item[2])
        if page < 1:
            continue
        t = (title or "").strip() or "Untitled"
        by_page[page].append((level, t))
    return dict(by_page)


def apply_toc_to_stack(stack: list[tuple[int, str]], level: int, title: str) -> None:
    while stack and stack[-1][0] >= level:
        stack.pop()
    stack.append((level, title))


def stack_to_labels(stack: list[tuple[int, str]]) -> tuple[str, str]:
    if not stack:
        return "Document", ""
    chapter = stack[0][1]
    section = stack[1][1] if len(stack) > 1 else ""
    return chapter, section


def build_initial_stack_for_page_one(
    events_by_page: dict[int, list[tuple[int, str]]],
    page_count: int,
) -> list[tuple[int, str]]:
    """Apply any TOC entries on page 1 before processing."""
    stack: list[tuple[int, str]] = []
    for level, title in events_by_page.get(1, []):
        apply_toc_to_stack(stack, level, title)
    return stack


def usable_outline(toc: list[list]) -> bool:
    return bool(toc)
