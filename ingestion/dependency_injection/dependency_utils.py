import os
import sys
from collections.abc import Generator
from pathlib import Path

# Project root and ingestion root on path (flat imports: extractors, scanners, …;
# shared: domain, persistence from editable install or source tree).
_root = Path(__file__).resolve().parents[2]
_ing = Path(__file__).resolve().parents[1]
for _p in (_root, _ing):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from extractors.metadata_extractor.pdf_metadata_extractor import PdfDataExtractor
from extractors.tools.authors_extractor import AuthorsExtractor
from extractors.tools.category_extractor import CategoryExtractor
from extractors.tools.description_extractor import DescriptionExtractor
from extractors.tools.isbn_extractor import IsbnExtractor
from extractors.tools.language_extractor import LanguageExtractor
from extractors.tools.page_count_extractor import PageCounterExtractor
from extractors.tools.publisher_extractor import PublisherExtractor
from extractors.tools.title_extractor import TitleExtractor
from extractors.tools.year_extractor import YearExtractor
from llm_models.basic_models import BasicLocalModel
from persistence.repositories.ebook_repository import SqlAlchemyEbookRepository
from persistence.session import get_db_session as _get_db_session
from scanners.ebook_scanner import EbookScanner

load_dotenv()

BASIC_LLM_MODEL_URL = os.environ["BASIC_LLM_MODEL_URL"]
BASIC_MODEL_NAME = os.environ["BASIC_MODEL_NAME"]
BASIC_MODEL_TEMPERATURE = os.environ["BASIC_MODEL_TEMPERATURE"]
COVER_IMAGE_PATH=os.environ["COVER_IMAGE_PATH"]

def get_basic_llm_model() -> BasicLocalModel:
    """Provide the Basic LLM model, the goal is to use this one for easy tasks"""
    return BasicLocalModel(
        BASIC_LLM_MODEL_URL, BASIC_MODEL_NAME, BASIC_MODEL_TEMPERATURE
    )


def get_title_extractor() -> TitleExtractor:
    """Provide the Title Extractor instance."""
    return TitleExtractor(get_basic_llm_model())


def get_page_counter_extractor() -> PageCounterExtractor:
    """Provide the Page Counter Extractor instance."""
    return PageCounterExtractor()


def get_isbn_extractor() -> IsbnExtractor:
    """Provide the ISBN Extractor instance."""
    return IsbnExtractor()


def get_year_extractor() -> YearExtractor:
    """Provide the Year Extractor instance."""
    return YearExtractor()


def get_publisher_extractor() -> PublisherExtractor:
    """Provide the Publisher Extractor instance."""
    return PublisherExtractor()


def get_authors_extractor() -> AuthorsExtractor:
    """Provide the Authors Extractor instance."""
    return AuthorsExtractor(get_basic_llm_model())


def get_description_extractor() -> DescriptionExtractor:
    """Provide the Description Extractor instance."""
    return DescriptionExtractor(get_basic_llm_model())


def get_category_extractor() -> CategoryExtractor:
    """Provide the Category Extractor instance."""
    return CategoryExtractor(get_basic_llm_model())


def get_language_extractor() -> LanguageExtractor:
    """Provide the Language Extractor instance."""
    return LanguageExtractor(get_basic_llm_model())


def get_db_session() -> Generator[Session, None, None]:
    """Provide a database session for the current unit of work."""
    return _get_db_session()


def get_ebook_repository(session: Session) -> SqlAlchemyEbookRepository:
    """Provide a repository bound to the given SQLAlchemy session."""
    return SqlAlchemyEbookRepository(session)


def get_ebook_scanner() -> EbookScanner:
    """Provide the Ebook Scanner instance."""
    return EbookScanner()


def get_pdf_data_extractor() -> PdfDataExtractor:
    """Provide the PdfDataExtractor instance."""
    return PdfDataExtractor(
        title_extractor=get_title_extractor(),
        page_counter_extractor=get_page_counter_extractor(),
        isbn_extractor=get_isbn_extractor(),
        year_extractor=get_year_extractor(),
        publisher_extractor=get_publisher_extractor(),
        authors_extractor=get_authors_extractor(),
        description_extractor=get_description_extractor(),
        category_extractor=get_category_extractor(),
        language_extractor=get_language_extractor(),
    )
