import re


class IsbnExtractor:
    # Priority 1: explicit ISBN legend, then spaced/dashed/compacted body.
    ISBN_WITH_LEGEND_PATTERN = re.compile(
        r'(?<![\dXx])'
        r'ISBN(?:-1[03])?:?\s*'
        r'('
        r'(?:\d[\-\s]?){12}\d'  # ISBN-13
        r'|(?:\d[\-\s]?){9}[\dXx]'  # ISBN-10
        r')'
        r'(?![\dXx])',
        re.IGNORECASE,
    )

    # Priority 2: no legend — only hyphen-separated groups (must contain inner dashes).
    ISBN_HYPHEN_GROUPS_PATTERN = re.compile(
        r'(?<![\dXx-])((?:\d+-)+[\dXx]+)(?![\dXx])',
        re.IGNORECASE,
    )

    def _normalize_isbn(self, isbn: str) -> str:
        # Keep source dash formatting, but remove arbitrary whitespace noise.
        return re.sub(r"\s+", "", isbn).upper()

    @staticmethod
    def _is_valid_isbn_shape(canonical: str) -> bool:
        """True if digit count/checksum position matches ISBN-10 or ISBN-13."""
        stripped = ''.join(c for c in canonical if c not in '- ')
        if not stripped:
            return False
        if len(stripped) == 13 and stripped[:-1].isdigit() and stripped[-1].isdigit():
            return stripped[:3] in ('978', '979')
        if len(stripped) == 10:
            body, last = stripped[:-1], stripped[-1]
            if not body.isdigit():
                return False
            return last.isdigit() or last.upper() == 'X'
        return False

    def extract_isbn_from_text(self, texts: str | list[str]) -> str | None:
        ranges: list[str] = [texts] if isinstance(texts, str) else texts
        for text_range in ranges:
            for match in self.ISBN_WITH_LEGEND_PATTERN.finditer(text_range):
                captured = match.group(1)
                normalized = self._normalize_isbn(captured)
                if self._is_valid_isbn_shape(normalized):
                    return normalized
        # Only after scanning all ranges for legend matches...
        for text_range in ranges:
            for match in self.ISBN_HYPHEN_GROUPS_PATTERN.finditer(text_range):
                captured = match.group(1)
                normalized = self._normalize_isbn(captured)
                if self._is_valid_isbn_shape(normalized):
                    return normalized
        return None
