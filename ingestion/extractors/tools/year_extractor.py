import re


class YearExtractor:
    # Matches common copyright/publication year patterns found in book front matter.
    # Tries the most explicit patterns first, then a bare 4-digit year as a fallback.
    _PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"(?:©|Copyright\s*©?)\s*(\d{4})", re.IGNORECASE),
        re.compile(r"(?:First\s+)?[Pp]ublished\s+(?:in\s+)?(\d{4})"),
        re.compile(r"[Pp]rint(?:ed)?\s+in\s+\w+\s+(\d{4})"),
        re.compile(r"\b((?:19|20)\d{2})\b"),
    ]
    _VALID_RANGE = range(1950, 2051)

    def extract_year_from_text(self, text: str) -> int | None:
        for pattern in self._PATTERNS:
            for match in pattern.finditer(text):
                year = int(match.group(1))
                if year in self._VALID_RANGE:
                    return year
        return None
