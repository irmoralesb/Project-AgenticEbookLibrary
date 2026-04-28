import re

class IsbnExtractor:
    ISBN_PATTERN = re.compile(
        r'(?<![\dXx])'                 # no ISBN chars before the match
        r'(?:ISBN(?:-1[03])?:?\s*)?'   # optional ISBN label
        r'('
        r'(?:\d[\-\s]?){12}\d'         # ISBN-13
        r'|(?:\d[\-\s]?){9}[\dXx]'     # ISBN-10
        r')'
        r'(?![\dXx])',                 # no ISBN chars after the match
        re.IGNORECASE
    )

    def _normalize_isbn(self, isbn: str) -> str:
        # Keep source dash formatting, but remove arbitrary whitespace noise.
        return re.sub(r"\s+", "", isbn).upper()


    def extract_isbn_from_text(self, text: str) -> str | None:
        for match in self.ISBN_PATTERN.finditer(text):
            return self._normalize_isbn(match.group(1))
        return None