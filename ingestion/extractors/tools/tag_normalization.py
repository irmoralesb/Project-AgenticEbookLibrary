import re
import unicodedata

_GENERIC_DENYLIST: frozenset[str] = frozenset({
    "book", "ebook", "chapter", "introduction", "overview",
    "guide", "handbook", "tutorial", "summary", "preface",
    "table-of-contents", "index", "glossary", "appendix",
    "the", "and", "or", "for", "with", "without",
    "n-a", "not-found", "unknown",
})

_KEEP_AS_IS: frozenset[str] = frozenset({
    "rag", "llm", "ai", "ml", "nlp", "api", "sql", "ci-cd",
})

_NON_ALNUM_RUN = re.compile(r"[^a-z0-9]+")
_EDGE_DASHES = re.compile(r"^-+|-+$")


def canonicalize_tag(raw: str) -> str | None:
    """Return canonical tag or None when raw is unusable.
    Rules: lowercase, ascii-fold, kebab-case, 1-80 chars,
    not in generic denylist.
    """
    if not raw:
        return None

    folded = unicodedata.normalize("NFKD", raw)
    folded = folded.encode("ascii", "ignore").decode("ascii").lower().strip()

    if not folded:
        return None

    kebab = _NON_ALNUM_RUN.sub("-", folded)
    kebab = _EDGE_DASHES.sub("", kebab)

    if not kebab or len(kebab) > 80:
        return None

    if kebab in _GENERIC_DENYLIST:
        return None

    if kebab in _KEEP_AS_IS:
        return kebab

    if len(kebab) <= 2:
        return None

    return kebab


def canonicalize_tags(raw_tags: list[str], *, drop_equal_to: list[str | None] | None = None, max_count: int = 15) -> list[str]:
    """Apply canonicalize_tag, dedupe (case-insensitive), drop fields equal to
    category/subcategory, cap to max_count preserving first-seen order."""
    forbidden = {
        canonicalize_tag(value) for value in (drop_equal_to or []) if value
    }

    forbidden.discard(None)

    seen: set[str] = set()
    result: list[str] = []

    for raw in raw_tags:
        canonical = canonicalize_tag(raw)
        if canonical is None or canonical in seen or canonical in forbidden:
            continue

        seen.add(canonical)
        result.append(canonical)
        if len(result) >= max_count:
            break
    return result
