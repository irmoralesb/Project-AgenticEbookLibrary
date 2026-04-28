"""Tests for the cover_output_dir parameter wired into extract_metadata.

These tests verify that both PdfDataExtractor and EpubDataExtractor
populate cover_image_path / cover_image_mime_type on the returned metadata
when cover_output_dir is supplied, and gracefully set has_errors when
cover extraction fails.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from extractors.metadata_extractor.epub_metadata_extractor import EpubDataExtractor
from extractors.metadata_extractor.pdf_metadata_extractor import PdfDataExtractor
from extractors.models.models import QueryCategoryMetadata, QueryTitleWithEdition


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_pdf_extractor(**overrides) -> PdfDataExtractor:
    page_counter = Mock()
    page_counter.get_total_page_number_for_pdf.return_value = 10

    title = Mock()
    title.get_title_and_edition.return_value = QueryTitleWithEdition(
        title="Test Book", edition="1st"
    )

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

    defaults = dict(
        title_extractor=title,
        page_counter_extractor=page_counter,
        isbn_extractor=isbn,
        year_extractor=year,
        publisher_extractor=publisher,
        authors_extractor=authors,
        description_extractor=description,
        category_extractor=category,
        language_extractor=language,
    )
    defaults.update(overrides)
    return PdfDataExtractor(**defaults)


def _make_epub_extractor(**overrides) -> EpubDataExtractor:
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

    defaults = dict(
        title_extractor=Mock(),
        page_counter_extractor=page_counter,
        isbn_extractor=isbn,
        year_extractor=year,
        publisher_extractor=publisher,
        authors_extractor=authors,
        description_extractor=description,
        category_extractor=category,
        language_extractor=language,
    )
    defaults.update(overrides)
    return EpubDataExtractor(**defaults)


# ---------------------------------------------------------------------------
# PdfDataExtractor.extract_metadata — cover_output_dir
# ---------------------------------------------------------------------------

_PDF_OPEN = "extractors.metadata_extractor.pdf_metadata_extractor.fitz.open"


def _make_fitz_doc(page_count: int = 1) -> MagicMock:
    doc = MagicMock()
    doc.__len__ = Mock(return_value=page_count)
    doc.__enter__ = Mock(return_value=doc)
    doc.__exit__ = Mock(return_value=False)
    page = MagicMock()
    page.get_text.return_value = ""
    pix = MagicMock()
    pix.tobytes.return_value = b"fake-image"
    page.get_pixmap.return_value = pix
    doc.__getitem__ = Mock(return_value=page)
    return doc


def test_pdf_extract_metadata_populates_cover_when_dir_provided(tmp_path: Path) -> None:
    pdf_file = tmp_path / "mybook.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")
    cover_dir = tmp_path / "covers"

    extractor = _make_pdf_extractor()
    fitz_doc = _make_fitz_doc()

    with patch(_PDF_OPEN, return_value=fitz_doc):
        metadata = extractor.extract_metadata(pdf_file, cover_output_dir=cover_dir)

    assert metadata.cover_image_path is not None
    assert Path(metadata.cover_image_path).exists()
    assert metadata.cover_image_mime_type == "image/png"


def test_pdf_extract_metadata_no_cover_when_dir_not_provided(tmp_path: Path) -> None:
    pdf_file = tmp_path / "mybook.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")

    extractor = _make_pdf_extractor()
    fitz_doc = _make_fitz_doc()

    with patch(_PDF_OPEN, return_value=fitz_doc):
        metadata = extractor.extract_metadata(pdf_file)

    assert metadata.cover_image_path is None
    assert metadata.cover_image_mime_type is None


def test_pdf_extract_metadata_sets_has_errors_on_cover_failure(tmp_path: Path) -> None:
    pdf_file = tmp_path / "mybook.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")
    cover_dir = tmp_path / "covers"

    extractor = _make_pdf_extractor()
    fitz_doc = _make_fitz_doc()

    with patch(_PDF_OPEN, return_value=fitz_doc):
        with patch.object(extractor, "extract_and_save_cover_image", side_effect=RuntimeError("no cover")):
            metadata = extractor.extract_metadata(pdf_file, cover_output_dir=cover_dir)

    assert metadata.has_errors is True
    assert metadata.cover_image_path is None


# ---------------------------------------------------------------------------
# EpubDataExtractor.extract_metadata — cover_output_dir
# ---------------------------------------------------------------------------

_EPUB_READ = "extractors.metadata_extractor.epub_metadata_extractor.epub.read_epub"


def _make_epub_book(*, dc_title: str = "Test Book") -> MagicMock:
    book = MagicMock()
    dc_map = {
        "title": [(dc_title, {})],
        "creator": [("Author One", {})],
        "language": [("en", {})],
        "publisher": [("Publisher", {})],
        "identifier": [],
        "date": [("2020", {})],
        "description": [("A description.", {})],
    }

    def _get_metadata(ns: str, field: str):
        if ns == "DC":
            return dc_map.get(field, [])
        return []

    book.get_metadata.side_effect = _get_metadata
    book.spine = []
    book.get_item_with_id.return_value = None
    book.get_items_of_type.return_value = iter([])
    book.get_items.return_value = iter([])
    return book


def test_epub_extract_metadata_populates_cover_when_dir_provided(tmp_path: Path) -> None:
    epub_file = tmp_path / "mybook.epub"
    epub_file.write_bytes(b"PK")
    cover_dir = tmp_path / "covers"
    expected_cover = cover_dir / "mybook.jpeg"

    extractor = _make_epub_extractor()
    book = _make_epub_book()

    with patch(_EPUB_READ, return_value=book):
        with patch.object(
            extractor,
            "extract_and_save_cover_image",
            return_value=(expected_cover, "image/jpeg", False),
        ):
            metadata = extractor.extract_metadata(epub_file, cover_output_dir=cover_dir)

    assert metadata.cover_image_path == str(expected_cover)
    assert metadata.cover_image_mime_type == "image/jpeg"


def test_epub_extract_metadata_no_cover_when_dir_not_provided(tmp_path: Path) -> None:
    epub_file = tmp_path / "mybook.epub"
    epub_file.write_bytes(b"PK")

    extractor = _make_epub_extractor()
    book = _make_epub_book()

    with patch(_EPUB_READ, return_value=book):
        metadata = extractor.extract_metadata(epub_file)

    assert metadata.cover_image_path is None
    assert metadata.cover_image_mime_type is None


def test_epub_extract_metadata_sets_has_errors_on_cover_failure(tmp_path: Path) -> None:
    epub_file = tmp_path / "mybook.epub"
    epub_file.write_bytes(b"PK")
    cover_dir = tmp_path / "covers"

    extractor = _make_epub_extractor()
    book = _make_epub_book()

    with patch(_EPUB_READ, return_value=book):
        with patch.object(
            extractor, "extract_and_save_cover_image", side_effect=RuntimeError("no cover")
        ):
            metadata = extractor.extract_metadata(epub_file, cover_output_dir=cover_dir)

    assert metadata.has_errors is True
    assert metadata.cover_image_path is None
