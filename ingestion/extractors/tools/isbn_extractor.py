import re

class IsbnExtractor:
    ISBN_PATTERN = re.compile(
        r'(?:ISBN(?:-1[03])?:?\s*)'   # ISBN label
        r'('
        r'(?:\d[\-\s]?){12}\d'        # ISBN-13 first (avoid partial ISBN-10 match)
        r'|(?:\d[\-\s]?){9}[\dXx]'    # ISBN-10
        r')'
        r'(?![\dXx])',                # no extra ISBN chars after the match
        re.IGNORECASE
    )

    def _normalize_isbn(self, isbn: str) -> str:
        # Canonical form for internal processing: digits (and trailing X for ISBN-10).
        return re.sub(r"[\s\-]+", "", isbn).upper()


    def extract_isbn_from_text(self, text: str) -> str | None:
        match = self.ISBN_PATTERN.search(text)
        return self._normalize_isbn(match.group(1)) if match else None