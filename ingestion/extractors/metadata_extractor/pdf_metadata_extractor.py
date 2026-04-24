import re
import fitz
from pathlib import Path
from dataclasses import dataclass
from extractors.tools.title_extractor import TitleExtractor
from extractors.tools.metadata_extractor import PdfMetadataExtractor
from extractors.tools.page_count_extractor import PageCounterExtractor
from extractors.models.models import EbookMetadata, QueryEbookMetadata, map_query_to_ebook_metadata
from extractors.models.errors import *


class PdfDataExtractor():
    def __init__(self, title_extractor: TitleExtractor, page_counter_extractor: PageCounterExtractor, metadata_extractor: PdfMetadataExtractor) -> None:
        self.title_extractor = title_extractor
        self.page_counter_extractor = page_counter_extractor
        self.metadata_extractor = metadata_extractor

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

    @dataclass(frozen=True)
    class CoverExtractionResult:
        data: bytes
        mime_type: str

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

        return self.CoverExtractionResult(data=best_data, mime_type=f"image/{best_ext.lower()}")

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

                rendered = self.CoverExtractionResult(
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

    def extract_metadata(self, pdf_path: Path, number_of_pages_to_analize: int = 10) -> EbookMetadata:
        pdf_path = pdf_path.resolve()
        has_errors = False
        try:
            with fitz.open(pdf_path) as pdf_file:
                pdf_total_pages = self.page_counter_extractor.get_total_page_number(
                    pdf_file)
                pages_to_analize = self._get_pages_to_analize(
                    pdf_file, number_of_pages_to_analize)

        except Exception as exc:
            has_errors = True
            raise PdfReadError("Failed to open/read pdf",
                               file_name=pdf_path.name, stage="pdf_read", cause=exc) from exc
            

        try:
            title_with_edition = self.title_extractor.get_title_and_edition(
                pdf_path.name)
            print(f"Title: {title_with_edition}")
        except Exception as exc:
            has_errors = True
            raise MetadataEnrichmentError(
                "Failed to extract the title", file_name=pdf_path.name, stage="title_extraction", cause=exc) from exc

        try:
            metadata = self.metadata_extractor.get_metadata(pages_to_analize, pdf_path.name)
        except Exception:
            metadata = QueryEbookMetadata()
            has_errors = True
            
        return map_query_to_ebook_metadata(
            metadata,
            title=title_with_edition.title,
            edition=title_with_edition.edition,
            file_name=pdf_path.name,
            page_count=pdf_total_pages,
            has_errors=has_errors
        )
