"""Unit tests for EpubDataExtractor.

All tests use mocks — no real EPUB files are required.
The ebooklib.epub.EpubBook object is mocked to return controlled metadata,
mirroring the style used in test_extractor_tools.py.
"""
from unittest.mock import MagicMock, Mock, patch
from pathlib import Path

import pytest

from extractors.metadata_extractor.epub_metadata_extractor import EpubDataExtractor
from extractors.models.errors import EpubReadError
from extractors.models.models import CoverExtractionResult, QueryCategoryMetadata, QueryTitleWithEdition
from extractors.tools.page_count_extractor import PageCounterExtractor


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_extractor(**overrides) -> EpubDataExtractor:
    """Return an EpubDataExtractor whose tool dependencies are all Mocks.

    Defaults are configured with safe return values so tests that only care
    about a single field do not fail on unrelated Pydantic validation.
    """
    page_counter = Mock()
    page_counter.get_total_spine_items_for_epub.return_value = 0

    isbn = Mock()
    isbn.extract_isbn_from_text.return_value = None

    year = Mock()
    year.extract_year_from_text.return_value = None

    publisher = Mock()
    publisher.extract_publisher_from_text.return_value = None

    authors = Mock()
    authors.get_authors.return_value = []

    description = Mock()
    description.get_description.return_value = None

    category = Mock()
    category.get_category.return_value = QueryCategoryMetadata()

    language = Mock()
    language.get_language.return_value = None

    defaults = {
        "title_extractor": Mock(),
        "page_counter_extractor": page_counter,
        "isbn_extractor": isbn,
        "year_extractor": year,
        "publisher_extractor": publisher,
        "authors_extractor": authors,
        "description_extractor": description,
        "category_extractor": category,
        "language_extractor": language,
    }
    defaults.update(overrides)
    return EpubDataExtractor(**defaults)


def _make_book(
    *,
    dc_title: list[str] | None = None,
    dc_creator: list[str] | None = None,
    dc_language: list[str] | None = None,
    dc_publisher: list[str] | None = None,
    dc_identifier: list[str] | None = None,
    dc_date: list[str] | None = None,
    dc_description: list[str] | None = None,
    spine: list | None = None,
    items: list | None = None,
) -> MagicMock:
    """Build a minimal EpubBook mock with controlled DC metadata."""
    book = MagicMock()

    dc_map: dict[str, list[str]] = {
        "title": dc_title or [],
        "creator": dc_creator or [],
        "language": dc_language or [],
        "publisher": dc_publisher or [],
        "identifier": dc_identifier or [],
        "date": dc_date or [],
        "description": dc_description or [],
    }

    def _get_metadata(ns: str, field: str):
        if ns != "DC":
            return []
        values = dc_map.get(field, [])
        return [(v, {}) for v in values]

    book.get_metadata.side_effect = _get_metadata
    book.spine = spine or []
    book.get_item_with_id.return_value = None

    # get_items_of_type returns an empty iterator by default
    book.get_items_of_type.return_value = iter([])
    book.get_items.return_value = iter(items or [])

    return book


def _spine_item(item_id: str, content: bytes = b"<p>Sample text</p>") -> MagicMock:
    item = MagicMock()
    item.id = item_id
    item.get_content.return_value = content
    return item


# ---------------------------------------------------------------------------
# extract_metadata — OPF DC metadata paths
# ---------------------------------------------------------------------------

def test_extract_metadata_uses_dc_title_and_skips_llm(tmp_path: Path) -> None:
    epub_file = tmp_path / "mybook.epub"
    epub_file.write_bytes(b"fake")

    book = _make_book(
        dc_title=["Clean Code"],
        dc_creator=["Robert C. Martin"],
        dc_language=["en"],
        dc_publisher=["Prentice Hall"],
        dc_identifier=["ISBN 9780132350884"],
        dc_date=["2008-08-01"],
        dc_description=["A handbook of agile software craftsmanship."],
        spine=[("chap1", True)],
    )
    spine_item = _spine_item("chap1")
    book.get_item_with_id.return_value = spine_item

    title_mock = Mock()
    isbn_mock = Mock()
    isbn_mock.extract_isbn_from_text.return_value = "9780132350884"

    extractor = _make_extractor(title_extractor=title_mock, isbn_extractor=isbn_mock)

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    assert metadata.title == "Clean Code"
    # LLM title extractor must NOT have been called
    title_mock.get_title_and_edition.assert_not_called()
    assert metadata.authors == ["Robert C. Martin"]
    assert metadata.language == "en"
    assert metadata.publisher == "Prentice Hall"
    assert metadata.isbn == "9780132350884"
    assert metadata.year == 2008
    assert "agile" in metadata.description.lower()


def test_extract_metadata_falls_back_to_llm_title_when_dc_title_absent(tmp_path: Path) -> None:
    epub_file = tmp_path / "clean_code.epub"
    epub_file.write_bytes(b"fake")

    book = _make_book(
        dc_creator=["Robert C. Martin"],
        dc_language=["en"],
        dc_publisher=["Prentice Hall"],
        dc_identifier=["ISBN 9780132350884"],
        dc_date=["2008"],
        dc_description=["A handbook."],
        spine=[("chap1", True)],
    )
    book.get_item_with_id.return_value = _spine_item("chap1")

    title_mock = Mock()
    title_mock.get_title_and_edition.return_value = QueryTitleWithEdition(
        title="Clean Code", edition="1st Edition"
    )

    extractor = _make_extractor(title_extractor=title_mock)

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    title_mock.get_title_and_edition.assert_called_once_with("clean_code.epub")
    assert metadata.title == "Clean Code"
    assert metadata.edition == "1st Edition"


def test_extract_metadata_uses_dc_creator_list_for_authors(tmp_path: Path) -> None:
    epub_file = tmp_path / "coauthored.epub"
    epub_file.write_bytes(b"fake")

    book = _make_book(
        dc_title=["Co-Authored Book"],
        dc_creator=["Alice Smith", "Bob Jones"],
        dc_language=["en"],
        dc_date=["2023"],
        spine=[],
    )
    authors_mock = Mock()

    extractor = _make_extractor(authors_extractor=authors_mock)

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    assert metadata.authors == ["Alice Smith", "Bob Jones"]
    authors_mock.get_authors.assert_not_called()


def test_extract_metadata_falls_back_to_llm_authors_when_dc_creator_absent(tmp_path: Path) -> None:
    epub_file = tmp_path / "noauthor.epub"
    epub_file.write_bytes(b"fake")

    book = _make_book(
        dc_title=["Some Book"],
        dc_language=["en"],
        dc_date=["2020"],
        spine=[("c1", True)],
    )
    book.get_item_with_id.return_value = _spine_item("c1")

    authors_mock = Mock()
    authors_mock.get_authors.return_value = ["Jane Doe"]

    extractor = _make_extractor(authors_extractor=authors_mock)

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    authors_mock.get_authors.assert_called_once()
    assert metadata.authors == ["Jane Doe"]


def test_extract_metadata_extracts_isbn_from_dc_identifier(tmp_path: Path) -> None:
    epub_file = tmp_path / "book.epub"
    epub_file.write_bytes(b"fake")

    book = _make_book(
        dc_title=["ISBN Book"],
        dc_creator=["Author"],
        dc_language=["en"],
        dc_identifier=["urn:isbn:978-0-13-235088-4"],
        dc_date=["2010"],
        spine=[],
    )
    isbn_mock = Mock()
    isbn_mock.extract_isbn_from_text.return_value = "9780132350884"

    extractor = _make_extractor(isbn_extractor=isbn_mock)

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    # ISBN extractor should have been called with the identifier string
    isbn_mock.extract_isbn_from_text.assert_any_call("urn:isbn:978-0-13-235088-4")
    assert metadata.isbn == "9780132350884"


def test_extract_metadata_extracts_year_from_dc_date(tmp_path: Path) -> None:
    epub_file = tmp_path / "dated.epub"
    epub_file.write_bytes(b"fake")

    book = _make_book(
        dc_title=["Dated Book"],
        dc_creator=["Author"],
        dc_language=["en"],
        dc_date=["2019-06-15"],
        spine=[],
    )
    extractor = _make_extractor()

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    assert metadata.year == 2019


def test_extract_metadata_sets_has_errors_when_required_fields_missing(tmp_path: Path) -> None:
    epub_file = tmp_path / "incomplete.epub"
    epub_file.write_bytes(b"fake")

    book = _make_book(
        dc_title=["Incomplete Book"],
        spine=[],
    )
    extractor = _make_extractor()

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    assert metadata.has_errors is True


# ---------------------------------------------------------------------------
# extract_cover_image
# ---------------------------------------------------------------------------

def test_extract_cover_image_returns_cover_bytes_from_manifest(tmp_path: Path) -> None:
    epub_file = tmp_path / "withcover.epub"
    epub_file.write_bytes(b"fake")

    cover_item = MagicMock()
    cover_item.get_content.return_value = b"\x89PNG\r\n\x1a\n"
    cover_item.media_type = "image/png"
    cover_item.properties = ["cover-image"]

    book = MagicMock()
    book.get_items.return_value = iter([cover_item])

    extractor = _make_extractor()

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        result = extractor.extract_cover_image(epub_file)

    assert isinstance(result, CoverExtractionResult)
    assert result.data == b"\x89PNG\r\n\x1a\n"
    assert result.mime_type == "image/png"


def test_extract_cover_image_raises_epub_read_error_on_open_failure(tmp_path: Path) -> None:
    epub_file = tmp_path / "corrupt.epub"
    epub_file.write_bytes(b"not an epub")

    extractor = _make_extractor()

    with patch(
        "extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub",
        side_effect=Exception("corrupt file"),
    ):
        with pytest.raises(EpubReadError) as exc_info:
            extractor.extract_cover_image(epub_file)

    assert exc_info.value.stage == "cover_extraction"
    assert exc_info.value.file_name == "corrupt.epub"


def test_extract_cover_image_raises_epub_read_error_when_no_cover_found(tmp_path: Path) -> None:
    epub_file = tmp_path / "nocover.epub"
    epub_file.write_bytes(b"fake")

    book = MagicMock()
    book.get_items.return_value = iter([])
    book.get_item_with_id.return_value = None
    book.get_items_of_type.return_value = iter([])

    extractor = _make_extractor()

    with patch("extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub", return_value=book):
        with pytest.raises(EpubReadError) as exc_info:
            extractor.extract_cover_image(epub_file)

    assert exc_info.value.stage == "cover_extraction"


# ---------------------------------------------------------------------------
# PageCounterExtractor — get_total_spine_items_for_epub
# ---------------------------------------------------------------------------

def test_page_counter_extractor_returns_spine_length() -> None:
    book = MagicMock()
    book.spine = [("chap1", True), ("chap2", True), ("chap3", True)]
    extractor = PageCounterExtractor()

    count = extractor.get_total_spine_items_for_epub(book)

    assert count == 3


def test_page_counter_extractor_returns_zero_for_empty_spine() -> None:
    book = MagicMock()
    book.spine = []
    extractor = PageCounterExtractor()

    assert extractor.get_total_spine_items_for_epub(book) == 0
