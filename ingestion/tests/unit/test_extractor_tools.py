from unittest.mock import Mock

import pytest

from extractors.models.models import QueryAuthors, QueryCategoryMetadata, QueryTitleWithEdition
from extractors.tools.authors_extractor import AuthorsExtractor
from extractors.tools.category_extractor import CategoryExtractor
from extractors.tools.description_extractor import DescriptionExtractor
from extractors.tools.isbn_extractor import IsbnExtractor
from extractors.tools.language_extractor import LanguageExtractor
from extractors.tools.page_count_extractor import PageCounterExtractor
from extractors.tools.publisher_extractor import PublisherExtractor
from extractors.tools.title_extractor import TitleExtractor
from extractors.tools.year_extractor import YearExtractor


# ---------------------------------------------------------------------------
# IsbnExtractor
# ---------------------------------------------------------------------------

def test_extract_isbn_from_text_returns_isbn_13_and_removes_spaces() -> None:
    text = "Some front matter... ISBN 978 1 492 06796 1 ..."
    extractor = IsbnExtractor()

    isbn = extractor.extract_isbn_from_text(text)

    assert isbn == "9781492067961"


def test_extract_isbn_from_text_returns_none_when_missing() -> None:
    text = "No ISBN appears in this text."
    extractor = IsbnExtractor()

    isbn = extractor.extract_isbn_from_text(text)

    assert isbn is None


def test_extract_isbn_from_text_preserves_hyphens_and_uppercases_x() -> None:
    text = "Appendix. ISBN-10: 1-4028-9462-x"
    extractor = IsbnExtractor()

    isbn = extractor.extract_isbn_from_text(text)

    assert isbn == "1-4028-9462-X"


def test_extract_isbn_from_text_finds_isolated_isbn_without_prefix() -> None:
    text = "Copyright page\n978-1-492-06796-1\nAll rights reserved."
    extractor = IsbnExtractor()

    isbn = extractor.extract_isbn_from_text(text)

    assert isbn == "978-1-492-06796-1"


# ---------------------------------------------------------------------------
# YearExtractor
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("© 2021 Some Author", 2021),
    ("Copyright © 2019 Publisher", 2019),
    ("Copyright 2018 by the author", 2018),
    ("Published in 2020 by Apress", 2020),
    ("First published 2015", 2015),
    ("Printed in the USA 2023", 2023),
    ("Some text with no year at all", None),
    ("Ancient text from 1200", None),
])
def test_year_extractor_extracts_year(text: str, expected: int | None) -> None:
    extractor = YearExtractor()
    assert extractor.extract_year_from_text(text) == expected


def test_year_extractor_prefers_copyright_over_bare_year() -> None:
    # The copyright pattern should win over a bare year that appears earlier.
    text = "Edition 1999 reprint. © 2022 Acme Corp."
    extractor = YearExtractor()
    assert extractor.extract_year_from_text(text) == 2022


# ---------------------------------------------------------------------------
# PublisherExtractor
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Published by O'Reilly Media, Inc.", "O'Reilly Media"),
    ("A Packt Publishing book", "Packt Publishing"),
    ("Manning Publications Co.", "Manning Publications"),
    ("Apress, a Springer company", "Apress"),
    ("No known publisher here", None),
    ("microsoft press edition", "Microsoft Press"),
])
def test_publisher_extractor_extracts_canonical_publisher(text: str, expected: str | None) -> None:
    extractor = PublisherExtractor()
    assert extractor.extract_publisher_from_text(text) == expected


def test_publisher_extractor_returns_canonical_casing() -> None:
    extractor = PublisherExtractor()
    result = extractor.extract_publisher_from_text("published by o'reilly media")
    assert result == "O'Reilly Media"


def test_publisher_extractor_matches_curly_apostrophe_from_pdf() -> None:
    # PDF text frequently uses the right single quotation mark (U+2019) instead of ASCII apostrophe.
    extractor = PublisherExtractor()
    result = extractor.extract_publisher_from_text("Published by O\u2019Reilly Media, Inc.")
    assert result == "O'Reilly Media"


def test_publisher_extractor_prefers_longer_match() -> None:
    # "Addison-Wesley Professional" must beat "Addison-Wesley".
    extractor = PublisherExtractor()
    result = extractor.extract_publisher_from_text("Addison-Wesley Professional, a Pearson imprint")
    assert result == "Addison-Wesley Professional"


# ---------------------------------------------------------------------------
# TitleExtractor
# ---------------------------------------------------------------------------

def test_title_extractor_delegates_to_llm_and_returns_query_model() -> None:
    expected = QueryTitleWithEdition(title="Python Tricks", edition="2nd Edition")
    llm = Mock()
    llm.extract_title_and_edition.return_value = expected
    extractor = TitleExtractor(llm)

    result = extractor.get_title_and_edition("python_tricks_2nd_ed.pdf")

    llm.extract_title_and_edition.assert_called_once_with("python_tricks_2nd_ed.pdf")
    assert result == expected


# ---------------------------------------------------------------------------
# AuthorsExtractor
# ---------------------------------------------------------------------------

def test_authors_extractor_delegates_to_llm_and_returns_list() -> None:
    llm = Mock()
    llm.extract_authors.return_value = QueryAuthors(authors=["Alice Smith", "Bob Jones"])
    extractor = AuthorsExtractor(llm)

    result = extractor.get_authors("some book text")

    llm.extract_authors.assert_called_once_with("some book text")
    assert result == ["Alice Smith", "Bob Jones"]


# ---------------------------------------------------------------------------
# DescriptionExtractor
# ---------------------------------------------------------------------------

def test_description_extractor_delegates_to_llm() -> None:
    llm = Mock()
    llm.extract_description.return_value = "A practical guide to Python."
    extractor = DescriptionExtractor(llm)

    result = extractor.get_description("raw pdf text")

    llm.extract_description.assert_called_once_with("raw pdf text")
    assert result == "A practical guide to Python."


def test_description_extractor_returns_none_when_llm_returns_none() -> None:
    llm = Mock()
    llm.extract_description.return_value = None
    extractor = DescriptionExtractor(llm)

    assert extractor.get_description("text") is None


# ---------------------------------------------------------------------------
# CategoryExtractor
# ---------------------------------------------------------------------------

def test_category_extractor_delegates_to_llm_and_returns_model() -> None:
    expected = QueryCategoryMetadata(category="Programming", subcategory="Python")
    llm = Mock()
    llm.extract_category.return_value = expected
    extractor = CategoryExtractor(llm)

    result = extractor.get_category("raw pdf text")

    llm.extract_category.assert_called_once_with("raw pdf text")
    assert result.category == "Programming"
    assert result.subcategory == "Python"


def test_category_extractor_defaults_to_other_when_llm_returns_defaults() -> None:
    llm = Mock()
    llm.extract_category.return_value = QueryCategoryMetadata()
    extractor = CategoryExtractor(llm)

    result = extractor.get_category("text")

    assert result.category == "Other"
    assert result.subcategory == "Other"


# ---------------------------------------------------------------------------
# LanguageExtractor
# ---------------------------------------------------------------------------

def test_language_extractor_delegates_to_llm() -> None:
    llm = Mock()
    llm.extract_language.return_value = "es"
    extractor = LanguageExtractor(llm)

    result = extractor.get_language("texto en español")

    llm.extract_language.assert_called_once_with("texto en español")
    assert result == "es"


def test_language_extractor_returns_llm_value_unchanged() -> None:
    llm = Mock()
    llm.extract_language.return_value = "de"
    extractor = LanguageExtractor(llm)

    assert extractor.get_language("text") == "de"


# ---------------------------------------------------------------------------
# PageCounterExtractor
# ---------------------------------------------------------------------------

def test_page_counter_extractor_returns_document_length() -> None:
    mock_pdf = Mock()
    mock_pdf.__len__ = Mock(return_value=348)
    extractor = PageCounterExtractor()

    total_pages = extractor.get_total_page_number_for_pdf(mock_pdf)
    assert total_pages == 348
