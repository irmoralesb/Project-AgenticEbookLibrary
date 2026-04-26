import re


class PublisherExtractor:
    # Ordered from most specific to most generic to avoid false positives.
    _KNOWN_PUBLISHERS: list[str] = [
        "No Starch Press",
        "Microsoft Press",
        "Addison-Wesley Professional",
        "Addison-Wesley",
        "Pearson Education",
        "Pearson",
        "O'Reilly Media",
        "O'Reilly",
        "Packt Publishing",
        "Packt",
        "Manning Publications",
        "Manning",
        "Apress",
        "Wrox Press",
        "Wrox",
        "Wiley",
        "Sybex",
        "Pragmatic Bookshelf",
        "The Pragmatic Programmers",
        "Springer",
        "CRC Press",
        "MIT Press",
        "Oxford University Press",
        "Cambridge University Press",
        "New Riders",
        "Que Publishing",
        "Sams Publishing",
        "Cengage Learning",
        "Jones & Bartlett",
        "IBM Press",
        "Oracle Press",
    ]

    def __init__(self) -> None:
        # Build a single alternation pattern; longer names must come first (already ordered above).
        escaped = [re.escape(name) for name in self._KNOWN_PUBLISHERS]
        self._pattern = re.compile(
            r"(?<!\w)(" + "|".join(escaped) + r")(?!\w)",
            re.IGNORECASE,
        )

    @staticmethod
    def _normalize_quotes(text: str) -> str:
        # PDF text often uses curly/smart apostrophes; normalize to straight so patterns match.
        return text.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'")

    def extract_publisher_from_text(self, text: str) -> str | None:
        match = self._pattern.search(self._normalize_quotes(text))
        if not match:
            return None
        # Return the canonical casing from our list, not whatever the PDF used.
        matched_lower = match.group(1).lower()
        for canonical in self._KNOWN_PUBLISHERS:
            if canonical.lower() == matched_lower:
                return canonical
        return match.group(1)
