from unittest.mock import Mock

import pytest

from extractors.models.models import (
    QueryAuthors,
    QueryCategoryMetadata,
    QueryPublisher,
    QueryTitleWithEdition,
)
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


def test_extract_isbn_from_text_ignores_bare_digits_without_prefix_or_dashes() -> None:
    text = "Catalog number 0785342694521 and edition 076790818X."
    extractor = IsbnExtractor()

    assert extractor.extract_isbn_from_text(text) is None


def test_extract_isbn_from_text_prefers_isbn_legend_over_earlier_hyphenated_number() -> None:
    text = (
        "978-0-596-52718-8\n"
        "ISBN 9780596527210"
    )
    extractor = IsbnExtractor()

    assert extractor.extract_isbn_from_text(text) == "9780596527210"


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
    assert extractor.extract_year_from_text([text]) == expected


def test_year_extractor_prefers_copyright_over_bare_year() -> None:
    # The copyright pattern should win over a bare year that appears earlier.
    text = "Edition 1999 reprint. © 2022 Acme Corp."
    extractor = YearExtractor()
    assert extractor.extract_year_from_text([text]) == 2022


# ---------------------------------------------------------------------------
# PublisherExtractor
# ---------------------------------------------------------------------------

def test_publisher_extractor_catalog_hit_skips_llm() -> None:
    llm = Mock()
    extractor = PublisherExtractor(
        llm,
        catalog_name_loader=lambda: ["No Starch Press", "Packt"],
    )

    result = extractor.extract_publisher_from_text(
        ["Copyright © 2024 No Starch Press, Inc."]
    )

    llm.extract_publisher.assert_not_called()
    assert result == "No Starch Press"


def test_publisher_extractor_catalog_prefers_longer_name() -> None:
    llm = Mock()
    extractor = PublisherExtractor(
        llm,
        catalog_name_loader=lambda: ["Addison-Wesley", "Addison-Wesley Professional"],
    )

    result = extractor.extract_publisher_from_text(
        ["Addison-Wesley Professional, a Pearson imprint"]
    )

    llm.extract_publisher.assert_not_called()
    assert result == "Addison-Wesley Professional"


def test_publisher_extractor_delegates_to_llm_when_catalog_empty() -> None:
    llm = Mock()
    llm.extract_publisher.return_value = QueryPublisher(publisher="No Starch Press")
    extractor = PublisherExtractor(llm, catalog_name_loader=lambda: [])

    result = extractor.extract_publisher_from_text(["Copyright © 2024 No Starch Press"])

    llm.extract_publisher.assert_called_once_with("Copyright © 2024 No Starch Press")
    assert result == "No Starch Press"


def test_publisher_extractor_delegates_to_llm_when_no_catalog_loader() -> None:
    llm = Mock()
    llm.extract_publisher.return_value = QueryPublisher(publisher="No Starch Press")
    extractor = PublisherExtractor(llm)

    result = extractor.extract_publisher_from_text(["Copyright © 2024 No Starch Press"])

    llm.extract_publisher.assert_called_once_with("Copyright © 2024 No Starch Press")
    assert result == "No Starch Press"


def test_publisher_extractor_returns_none_when_llm_returns_null() -> None:
    llm = Mock()
    llm.extract_publisher.return_value = QueryPublisher(publisher=None)
    extractor = PublisherExtractor(llm, catalog_name_loader=lambda: [])

    assert extractor.extract_publisher_from_text(["no imprint here"]) is None


def test_publisher_extractor_strips_whitespace_and_truncates_to_60_chars() -> None:
    llm = Mock()
    # Bypass Pydantic max_length — model may still return overlong strings from the LLM runtime.
    long_val = Mock()
    long_val.publisher = f" {'x' * 70} "
    llm.extract_publisher.return_value = long_val
    extractor = PublisherExtractor(llm, catalog_name_loader=lambda: [])

    result = extractor.extract_publisher_from_text(["text"])
    assert result == "x" * 60


def test_publisher_extractor_tries_later_ranges_after_null_from_llm() -> None:
    llm = Mock()
    llm.extract_publisher.side_effect = [
        QueryPublisher(publisher=None),
        QueryPublisher(publisher="  Tiny Owl Books  "),
    ]
    extractor = PublisherExtractor(llm, catalog_name_loader=lambda: [])

    assert (
        extractor.extract_publisher_from_text(["first excerpt", "second excerpt"])
        == "Tiny Owl Books"
    )
    assert llm.extract_publisher.call_count == 2


def test_publisher_extractor_skips_whitespace_only_ranges_without_calling_llm() -> None:
    llm = Mock()
    llm.extract_publisher.return_value = QueryPublisher(publisher="Acme Publishing")
    extractor = PublisherExtractor(llm, catalog_name_loader=lambda: [])

    assert extractor.extract_publisher_from_text(["  \n  ", "\t", "copyright page"]) == "Acme Publishing"
    llm.extract_publisher.assert_called_once_with("copyright page")


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

    result = extractor.get_authors(["some book text"])

    llm.extract_authors.assert_called_once_with("some book text")
    assert result == ["Alice Smith", "Bob Jones"]


# ---------------------------------------------------------------------------
# DescriptionExtractor
# ---------------------------------------------------------------------------

def test_description_extractor_delegates_to_llm() -> None:
    llm = Mock()
    llm.extract_description.return_value = "A practical guide to Python."
    extractor = DescriptionExtractor(llm)

    result = extractor.get_description(["raw pdf text"])

    llm.extract_description.assert_called_once_with("raw pdf text")
    assert result == "A practical guide to Python."


def test_description_extractor_returns_none_when_llm_returns_none() -> None:
    llm = Mock()
    llm.extract_description.return_value = None
    extractor = DescriptionExtractor(llm)

    assert extractor.get_description(["text"]) is None


# ---------------------------------------------------------------------------
# CategoryExtractor
# ---------------------------------------------------------------------------

def test_category_extractor_delegates_to_llm_and_returns_model() -> None:
    expected = QueryCategoryMetadata(category="Programming", subcategory="Python")
    llm = Mock()
    llm.extract_category.return_value = expected
    extractor = CategoryExtractor(llm)

    result = extractor.get_category(["raw pdf text"])

    llm.extract_category.assert_called_once_with("raw pdf text")
    assert result.category == "Programming"
    assert result.subcategory == "Python"


def test_category_extractor_defaults_to_other_when_llm_returns_defaults() -> None:
    llm = Mock()
    llm.extract_category.return_value = QueryCategoryMetadata()
    extractor = CategoryExtractor(llm)

    result = extractor.get_category(["text"])

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
