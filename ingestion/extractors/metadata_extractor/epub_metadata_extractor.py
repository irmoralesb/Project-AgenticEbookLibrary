import re
from html.parser import HTMLParser
from pathlib import Path

import ebooklib
from ebooklib import epub

from extractors.models.errors import EpubReadError, MetadataEnrichmentError
from extractors.models.models import CoverExtractionResult, EbookMetadata, map_query_to_ebook_metadata
from extractors.tools.authors_extractor import AuthorsExtractor
from extractors.tools.category_extractor import CategoryExtractor
from extractors.tools.description_extractor import DescriptionExtractor
from extractors.tools.isbn_extractor import IsbnExtractor
from extractors.tools.language_extractor import LanguageExtractor
from extractors.tools.page_count_extractor import PageCounterExtractor
from extractors.tools.publisher_extractor import PublisherExtractor
from extractors.tools.title_extractor import TitleExtractor
from extractors.tools.year_extractor import YearExtractor

_FAILURE_SENTINELS: frozenset[str] = frozenset({"n/a", "not found"})


def _is_sentinel(value: str | None) -> bool:
    """Return True when value is None, blank, or a known failure placeholder."""
    return value is None or not value.strip() or value.strip().lower() in _FAILURE_SENTINELS


class _HtmlTextExtractor(HTMLParser):
    """Minimal HTML-tag stripper backed by the stdlib html.parser."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(raw: bytes | str) -> str:
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    parser = _HtmlTextExtractor()
    parser.feed(text)
    return parser.get_text()


class EpubDataExtractor:
    def __init__(
        self,
        title_extractor: TitleExtractor,
        page_counter_extractor: PageCounterExtractor,
        isbn_extractor: IsbnExtractor,
        year_extractor: YearExtractor,
        publisher_extractor: PublisherExtractor,
        authors_extractor: AuthorsExtractor,
        description_extractor: DescriptionExtractor,
        category_extractor: CategoryExtractor,
        language_extractor: LanguageExtractor,
    ) -> None:
        self.title_extractor = title_extractor
        self.page_counter_extractor = page_counter_extractor
        self.isbn_extractor = isbn_extractor
        self.year_extractor = year_extractor
        self.publisher_extractor = publisher_extractor
        self.authors_extractor = authors_extractor
        self.description_extractor = description_extractor
        self.category_extractor = category_extractor
        self.language_extractor = language_extractor

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize(self, text: str, max_chars: int = 12000) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:max_chars]

    def _get_dc(self, book: epub.EpubBook, field: str) -> list[str]:
        """Return all non-empty Dublin Core values for the given field name."""
        entries = book.get_metadata("DC", field)
        return [v for v, _ in entries if v and v.strip()] if entries else []

    def _get_text_from_spine(self, book: epub.EpubBook, max_items: int) -> str:
        parts: list[str] = []
        count = 0
        for item_id, _ in book.spine:
            if count >= max_items:
                break
            item = book.get_item_with_id(item_id)
            if item is None:
                continue
            content = item.get_content()
            if content:
                parts.append(_strip_html(content))
            count += 1
        return self._normalize("\n\n".join(parts))

    def _parse_year_from_dc_date(self, date_str: str) -> int | None:
        """Extract a 4-digit year from common EPUB date formats (YYYY, YYYY-MM-DD)."""
        match = re.search(r"\b((?:19|20)\d{2})\b", date_str)
        if match:
            year = int(match.group(1))
            if year in range(1950, 2051):
                return year
        return None

    def _find_cover_item(self, book: epub.EpubBook) -> epub.EpubItem | None:
        # Priority 1 — OPF <meta name="cover" content="<id>"/> (EPUB2 + many EPUB3 files).
        # ebooklib surfaces this as entries in get_metadata('OPF', 'meta').
        for _value, attrs in (book.get_metadata("OPF", "meta") or []):
            if attrs.get("name", "").lower() == "cover":
                cover_id = attrs.get("content", "")
                if cover_id:
                    item = book.get_item_with_id(cover_id)
                    if item is not None and item.media_type.startswith("image/"):
                        return item

        # Priority 2 — EPUB3: manifest item with properties containing "cover-image".
        for item in book.get_items():
            props = getattr(item, "properties", None) or []
            if "cover-image" in props:
                return item

        # Priority 3 — common id conventions.
        for candidate_id in ("cover-image", "cover"):
            item = book.get_item_with_id(candidate_id)
            if item is not None and item.media_type.startswith("image/"):
                return item

        # Last resort — largest image in the manifest (skips tiny CSS/UI icons).
        best_item: epub.EpubItem | None = None
        best_size: int = 0
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            size = len(item.get_content() or b"")
            if size > best_size:
                best_size = size
                best_item = item

        return best_item

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract_cover_image(self, epub_path: Path) -> CoverExtractionResult:
        epub_path = epub_path.resolve()
        try:
            book = epub.read_epub(str(epub_path), options={"ignore_ncx": True})
        except Exception as exc:
            raise EpubReadError(
                "Failed to open EPUB file",
                file_name=epub_path.name,
                stage="cover_extraction",
                cause=exc,
            ) from exc

        cover_item = self._find_cover_item(book)
        if cover_item is None:
            raise EpubReadError(
                "No cover image found in EPUB manifest",
                file_name=epub_path.name,
                stage="cover_extraction",
            )

        data = cover_item.get_content()
        media_type: str = getattr(cover_item, "media_type", "") or "image/jpeg"
        return CoverExtractionResult(data=data, mime_type=media_type)

    def extract_metadata(self, epub_path: Path, number_of_spine_items_to_analyse: int = 10) -> EbookMetadata:
        epub_path = epub_path.resolve()
        has_errors = False

        try:
            book = epub.read_epub(str(epub_path), options={"ignore_ncx": True})
        except Exception as exc:
            raise EpubReadError(
                "Failed to open/read EPUB",
                file_name=epub_path.name,
                stage="epub_read",
                cause=exc,
            ) from exc

        spine_item_count = self.page_counter_extractor.get_total_spine_items_for_epub(book)
        text_sample = self._get_text_from_spine(book, number_of_spine_items_to_analyse)

        # --- Title ---
        dc_titles = self._get_dc(book, "title")
        if dc_titles:
            parsed_title = dc_titles[0].strip()
            parsed_edition = "Not Specified"
        else:
            try:
                title_with_edition = self.title_extractor.get_title_and_edition(epub_path.name)
                parsed_title = title_with_edition.title
                parsed_edition = title_with_edition.edition
            except Exception as exc:
                raise MetadataEnrichmentError(
                    "Failed to extract the title",
                    file_name=epub_path.name,
                    stage="title_extraction",
                    cause=exc,
                ) from exc

        # --- Authors ---
        dc_creators = self._get_dc(book, "creator")
        if dc_creators:
            parsed_authors = dc_creators
        else:
            try:
                parsed_authors = self.authors_extractor.get_authors(text_sample)
            except Exception:
                parsed_authors = []
                has_errors = True

        # --- Language ---
        dc_languages = self._get_dc(book, "language")
        if dc_languages:
            parsed_language: str | None = dc_languages[0].strip()
        else:
            try:
                parsed_language = self.language_extractor.get_language(text_sample)
            except Exception:
                parsed_language = None
                has_errors = True

        # --- Publisher ---
        dc_publishers = self._get_dc(book, "publisher")
        if dc_publishers:
            parsed_publisher: str | None = dc_publishers[0].strip()
        else:
            try:
                parsed_publisher = self.publisher_extractor.extract_publisher_from_text(text_sample)
            except Exception:
                parsed_publisher = None
                has_errors = True

        # --- ISBN ---
        dc_identifiers = self._get_dc(book, "identifier")
        parsed_isbn: str | None = None
        for identifier in dc_identifiers:
            candidate = self.isbn_extractor.extract_isbn_from_text(identifier)
            if candidate:
                parsed_isbn = candidate
                break
        if parsed_isbn is None:
            try:
                parsed_isbn = self.isbn_extractor.extract_isbn_from_text(text_sample)
            except Exception:
                parsed_isbn = None
                has_errors = True

        # --- Year ---
        dc_dates = self._get_dc(book, "date")
        parsed_year: int | None = None
        for date_str in dc_dates:
            parsed_year = self._parse_year_from_dc_date(date_str)
            if parsed_year is not None:
                break
        if parsed_year is None:
            try:
                parsed_year = self.year_extractor.extract_year_from_text(text_sample)
            except Exception:
                parsed_year = None
                has_errors = True

        # --- Description ---
        dc_descriptions = self._get_dc(book, "description")
        if dc_descriptions:
            parsed_description: str | None = dc_descriptions[0].strip()
        else:
            try:
                parsed_description = self.description_extractor.get_description(text_sample)
            except Exception:
                parsed_description = None
                has_errors = True

        # --- Category (always via LLM — not in OPF standard) ---
        try:
            parsed_category = self.category_extractor.get_category(text_sample)
        except Exception:
            parsed_category = None
            has_errors = True

        has_errors = (
            has_errors
            or _is_sentinel(parsed_title)
            or parsed_isbn is None
            or parsed_year is None
            or not parsed_authors
            or _is_sentinel(parsed_description)
            or parsed_category is None
            or parsed_publisher is None
            or _is_sentinel(parsed_language)
        )

        return map_query_to_ebook_metadata(
            title=parsed_title,
            edition=parsed_edition if dc_titles else parsed_edition,
            file_name=epub_path.name,
            page_count=spine_item_count,
            isbn=parsed_isbn,
            authors=parsed_authors,
            year=parsed_year,
            description=parsed_description,
            category=parsed_category.category if parsed_category else None,
            subcategory=parsed_category.subcategory if parsed_category else None,
            publisher=parsed_publisher,
            language=parsed_language,
            has_errors=has_errors,
        )
