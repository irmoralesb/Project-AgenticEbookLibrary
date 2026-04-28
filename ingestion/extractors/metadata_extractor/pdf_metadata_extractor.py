import re
import fitz
from pathlib import Path
from extractors.tools.title_extractor import TitleExtractor
from extractors.tools.page_count_extractor import PageCounterExtractor
from extractors.tools.isbn_extractor import IsbnExtractor
from extractors.tools.year_extractor import YearExtractor
from extractors.tools.publisher_extractor import PublisherExtractor
from extractors.tools.authors_extractor import AuthorsExtractor
from extractors.tools.description_extractor import DescriptionExtractor
from extractors.tools.category_extractor import CategoryExtractor
from extractors.tools.language_extractor import LanguageExtractor
from extractors.tools.cover_image_utils import find_existing_cover, guess_mime_type_from_suffix
from extractors.models.models import CoverExtractionResult, EbookMetadata, map_query_to_ebook_metadata
from extractors.models.errors import *

_FAILURE_SENTINELS: frozenset[str] = frozenset({"n/a", "not found"})


def _is_sentinel(value: str | None) -> bool:
    """Return True when value is None, blank, or a known failure placeholder."""
    return value is None or not value.strip() or value.strip().lower() in _FAILURE_SENTINELS


class PdfDataExtractor():
    _COVER_DPI: int = 160
    _COVER_FORMAT: str = "png"

    _EXTRACTOR_PAGE_WINDOWS: dict[str, int] = {
        "isbn": 5,
        "year": 5,
        "publisher": 5,
        "authors": 6,
        "language": 2,
        "description": 12,
        "category": 10,
    }

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

    def _normalize(self, text: str, max_chars: int = 12000) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:max_chars]

    def _get_pages_to_analize(self, pdf_file: fitz.Document, number_of_pages: int) -> str:
        n = min(number_of_pages, len(pdf_file))
        parts = []
        for page_index in range(n):
            page = pdf_file[page_index]
            parts.append(page.get_text())
        pages_to_analize = "\n\n".join(parts)
        return self._normalize(pages_to_analize)

    def _get_pages_range_to_analize(
        self,
        pdf_file: fitz.Document,
        start_page: int,
        end_page_exclusive: int,
        max_chars: int = 12000,
    ) -> str:
        total_pages = len(pdf_file)
        start = max(0, min(start_page, total_pages))
        end = max(start, min(end_page_exclusive, total_pages))
        parts: list[str] = []
        for page_index in range(start, end):
            parts.append(pdf_file[page_index].get_text())
        return self._normalize("\n\n".join(parts), max_chars=max_chars)

    def _build_extractor_windows(self, pdf_file: fitz.Document, number_of_pages: int) -> dict[str, str]:
        max_pages = min(number_of_pages, len(pdf_file))
        return {
            extractor_name: self._get_pages_range_to_analize(pdf_file, 0, min(pages, max_pages))
            for extractor_name, pages in self._EXTRACTOR_PAGE_WINDOWS.items()
        }

    def _extract_largest_image_from_page(self, pdf_file: fitz.Document, page: fitz.Page) -> CoverExtractionResult | None:
        images = page.get_images(full=True)
        if not images:
            return None

        best_data: bytes | None = None
        best_ext: str | None = None
        best_area = 0

        for image in images:
            xref = image[0]
            try:
                image_payload = pdf_file.extract_image(xref)
                data = image_payload.get("image")
                ext = image_payload.get("ext")
                width = int(image_payload.get("width", 0))
                height = int(image_payload.get("height", 0))
                area = width * height
            except Exception:
                continue

            if not data or not ext:
                continue

            if area > best_area:
                best_data = data
                best_ext = ext
                best_area = area

        if not best_data or not best_ext:
            return None

        return CoverExtractionResult(data=best_data, mime_type=f"image/{best_ext.lower()}")

    def extract_cover_image(
        self,
        pdf_path: Path,
        *,
        render_dpi: int = 160,
        render_format: str = "png",
        use_embedded_image_fallback: bool = False,
    ) -> CoverExtractionResult:
        pdf_path = pdf_path.resolve()
        try:
            with fitz.open(pdf_path) as pdf_file:
                if len(pdf_file) == 0:
                    raise PdfReadError(
                        "PDF has no pages",
                        file_name=pdf_path.name,
                        stage="cover_extraction",
                    )

                first_page = pdf_file[0]
                pix = first_page.get_pixmap(dpi=render_dpi)
                normalized_format = render_format.lower()
                if normalized_format == "jpg":
                    normalized_format = "jpeg"

                if normalized_format not in {"png", "jpeg"}:
                    normalized_format = "png"

                rendered = CoverExtractionResult(
                    data=pix.tobytes(normalized_format),
                    mime_type=f"image/{normalized_format}",
                )
                if not use_embedded_image_fallback:
                    return rendered

                embedded = self._extract_largest_image_from_page(pdf_file, first_page)
                return embedded if embedded is not None else rendered
        except PdfReadError:
            raise
        except Exception as exc:
            raise PdfReadError(
                "Failed to extract cover image",
                file_name=pdf_path.name,
                stage="cover_extraction",
                cause=exc,
            ) from exc

    def extract_and_save_cover_image(
        self,
        book_path: Path,
        cover_output_dir: Path,
        *,
        prior_cover_path: str | None = None,
    ) -> tuple[Path, str, bool]:
        """Return ``(saved_path, mime_type, was_reused)``.

        Checks for an existing cover image first; extracts and saves one only
        when none is found. ``was_reused`` is ``True`` when no extraction ran.
        """
        cover_output_dir.mkdir(parents=True, exist_ok=True)
        existing = find_existing_cover(book_path, cover_output_dir, prior_cover_path)
        if existing is not None:
            mime = guess_mime_type_from_suffix(existing) or "image/png"
            return existing, mime, True

        cover = self.extract_cover_image(
            book_path,
            render_dpi=self._COVER_DPI,
            render_format=self._COVER_FORMAT,
            use_embedded_image_fallback=False,
        )
        ext = cover.mime_type.split("/")[-1]
        dest = cover_output_dir / f"{book_path.stem}.{ext}"
        dest.write_bytes(cover.data)
        return dest.resolve(), cover.mime_type, False

    def extract_metadata(
        self,
        pdf_path: Path,
        number_of_pages_to_analize: int = 10,
        cover_output_dir: Path | None = None,
    ) -> EbookMetadata:
        pdf_path = pdf_path.resolve()
        has_errors = False

        try:
            with fitz.open(pdf_path) as pdf_file:
                pdf_total_pages = self.page_counter_extractor.get_total_page_number_for_pdf(
                    pdf_file)
                extractor_windows = self._build_extractor_windows(
                    pdf_file, number_of_pages_to_analize)
        except Exception as exc:
            has_errors = True
            raise PdfReadError("Failed to open/read pdf",
                               file_name=pdf_path.name, stage="pdf_read", cause=exc) from exc

        try:
            title_with_edition = self.title_extractor.get_title_and_edition(pdf_path.name)
        except Exception as exc:
            has_errors = True
            raise MetadataEnrichmentError(
                "Failed to extract the title",
                file_name=pdf_path.name, stage="title_extraction", cause=exc) from exc

        try:
            parsed_isbn = self.isbn_extractor.extract_isbn_from_text(extractor_windows["isbn"])
        except Exception:
            parsed_isbn = None
            has_errors = True

        try:
            parsed_year = self.year_extractor.extract_year_from_text(extractor_windows["year"])
        except Exception:
            parsed_year = None
            has_errors = True

        try:
            parsed_publisher = self.publisher_extractor.extract_publisher_from_text(extractor_windows["publisher"])
        except Exception:
            parsed_publisher = None
            has_errors = True

        try:
            parsed_authors = self.authors_extractor.get_authors(extractor_windows["authors"])
        except Exception:
            parsed_authors = []
            has_errors = True

        try:
            parsed_description = self.description_extractor.get_description(extractor_windows["description"])
        except Exception:
            parsed_description = None
            has_errors = True

        try:
            parsed_category = self.category_extractor.get_category(extractor_windows["category"])
        except Exception:
            parsed_category = None
            has_errors = True

        try:
            parsed_language = self.language_extractor.get_language(extractor_windows["language"])
        except Exception:
            parsed_language = None
            has_errors = True

        # --- Cover image ---
        cover_image_path: str | None = None
        cover_image_mime_type: str | None = None
        if cover_output_dir is not None:
            try:
                _cover_path, cover_image_mime_type, _ = self.extract_and_save_cover_image(
                    pdf_path, cover_output_dir
                )
                cover_image_path = str(_cover_path)
            except Exception:
                cover_image_path = None
                cover_image_mime_type = None
                has_errors = True

        has_errors = (
            has_errors
            or _is_sentinel(title_with_edition.title)
            or parsed_isbn is None
            or parsed_year is None
            or not parsed_authors
            or _is_sentinel(parsed_description)
            or parsed_category is None
            or parsed_publisher is None
            or _is_sentinel(parsed_language)
            or (cover_output_dir is not None and cover_image_path is None)
        )

        return map_query_to_ebook_metadata(
            title=title_with_edition.title,
            edition=title_with_edition.edition,
            file_name=pdf_path.name,
            page_count=pdf_total_pages,
            isbn=parsed_isbn,
            authors=parsed_authors,
            year=parsed_year,
            description=parsed_description,
            category=parsed_category.category if parsed_category else None,
            subcategory=parsed_category.subcategory if parsed_category else None,
            publisher=parsed_publisher,
            language=parsed_language,
            has_errors=has_errors,
            cover_image_path=cover_image_path,
            cover_image_mime_type=cover_image_mime_type,
        )
