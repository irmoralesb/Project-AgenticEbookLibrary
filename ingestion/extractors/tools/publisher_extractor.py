import re
from collections.abc import Callable

from llm_models.basic_models import BasicLocalModel


class PublisherExtractor:
    """Tier 1: regex against DB catalog names; tier 2: LLM structured extraction."""

    def __init__(
        self,
        llm: BasicLocalModel,
        catalog_name_loader: Callable[[], list[str]] | None = None,
    ) -> None:
        self.llm = llm
        self._catalog_name_loader = catalog_name_loader

    @staticmethod
    def _normalize_quotes(text: str) -> str:
        # PDF text often uses curly/smart apostrophes; normalize for pattern matching.
        return text.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'")

    @staticmethod
    def _pattern_from_names(names: list[str]) -> re.Pattern[str] | None:
        if not names:
            return None
        ordered = sorted(names, key=len, reverse=True)
        escaped = [re.escape(name) for name in ordered]
        return re.compile(
            r"(?<!\w)(" + "|".join(escaped) + r")(?!\w)",
            re.IGNORECASE,
        )

    def _match_catalog(self, text: str, names: list[str]) -> str | None:
        pattern = self._pattern_from_names(names)
        if pattern is None:
            return None
        ordered = sorted(names, key=len, reverse=True)
        match = pattern.search(self._normalize_quotes(text))
        if not match:
            return None
        matched_lower = match.group(1).lower()
        for canonical in ordered:
            if canonical.lower() == matched_lower:
                return canonical
        return match.group(1)

    def extract_publisher_from_text(self, texts: list[str]) -> str | None:
        names: list[str] = []
        if self._catalog_name_loader is not None:
            names = self._catalog_name_loader()

        if names:
            for text_range in texts:
                stripped = text_range.strip() if text_range else ""
                if not stripped:
                    continue
                hit = self._match_catalog(text_range, names)
                if hit:
                    return hit.strip()[:60]

        for text_range in texts:
            stripped = text_range.strip() if text_range else ""
            if not stripped:
                continue
            publisher = self.llm.extract_publisher(text_range).publisher
            if publisher is None:
                continue
            normalized = publisher.strip()
            if not normalized:
                continue
            return normalized[:60]
        return None
