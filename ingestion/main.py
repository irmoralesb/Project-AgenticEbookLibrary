import argparse
import os
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv

from dependency_injection.dependency_utils import (
    get_db_session,
    get_ebook_repository,
    get_ebook_scanner,
    get_epub_data_extractor,
    get_pdf_data_extractor,
)

load_dotenv()

PAGES_TO_ANALIZE = 5
COVER_IMAGE_DPI = 160
COVER_IMAGE_FORMAT = "png"
COVER_IMAGE_FOLDER = "cover_images"


def _get_extractor(extension: str):
    ext = extension.lstrip(".").lower()
    if ext == "pdf":
        return get_pdf_data_extractor()
    if ext == "epub":
        return get_epub_data_extractor()
    raise ValueError(f"Unsupported extension: {extension!r}. Supported: pdf, epub.")


def run_ingestion(
    path: str,
    extension: str,
    limit: int | None = None,
    cover_image_path: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Scan *path* for ebooks of *extension* type and persist their metadata.

    Args:
        path: Directory to scan recursively.
        extension: File extension to filter (e.g. ``"pdf"`` or ``"epub"``).
        limit: Maximum number of new books to process; ``None`` means all.
        on_progress: Optional callback called with a human-readable progress
            message for each significant event (found, skip, stored, error).

    Returns:
        Mapping with ``succeeded`` and ``failed`` counts.
    """

    def _emit(msg: str) -> None:
        if on_progress is not None:
            on_progress(msg)

    extractor = _get_extractor(extension)
    is_pdf = extension.lstrip(".").lower() == "pdf"

    scanner = get_ebook_scanner()
    ebook_path_list = scanner.get_ebooks_from_path(path=path, extension=extension)

    total_books_found = len(ebook_path_list)
    _emit(f"Books found: {total_books_found}")

    configured_cover_dir = cover_image_path or os.getenv("COVER_IMAGE_PATH") or COVER_IMAGE_FOLDER
    cover_output_dir = Path(configured_cover_dir).expanduser().resolve()
    cover_output_dir.mkdir(parents=True, exist_ok=True)

    paths_to_extract: list[str] = []
    for session in get_db_session():
        repo = get_ebook_repository(session)
        for ebook_path in ebook_path_list:
            if limit is not None and len(paths_to_extract) >= limit:
                break
            file_name = Path(ebook_path).name
            if repo.exists_by_file_name(file_name):
                _emit(f"Skip (already in DB): {file_name}")
                continue
            paths_to_extract.append(ebook_path)

    succeeded: int = 0
    failed: int = 0

    for ebook_path in paths_to_extract:
        book_path = Path(ebook_path)
        _emit(f"Processing: {book_path.name}")
        try:
            metadata = extractor.extract_metadata(book_path, PAGES_TO_ANALIZE)

            try:
                if is_pdf:
                    cover = extractor.extract_cover_image(
                        book_path,
                        render_dpi=COVER_IMAGE_DPI,
                        render_format=COVER_IMAGE_FORMAT,
                        use_embedded_image_fallback=False,
                    )
                else:
                    cover = extractor.extract_cover_image(book_path)
                ext = cover.mime_type.split("/")[-1]
                cover_file_path = cover_output_dir / f"{book_path.stem}.{ext}"
                cover_file_path.write_bytes(cover.data)
                metadata.cover_image_path = str(cover_file_path)
                metadata.cover_image_mime_type = cover.mime_type
            except Exception as exc:
                metadata.has_errors = True
                _emit(f"  Cover extraction failed for {book_path.name}: {exc}")

            for session in get_db_session():
                repo = get_ebook_repository(session)
                row = repo.add_from_metadata(metadata)
                _emit(f"  Stored id={row.id} file_name={row.file_name}")

            succeeded += 1

        except Exception as exc:
            failed += 1
            _emit(f"  Failed to process {book_path.name}: {exc}")

    _emit(f"Done — succeeded: {succeeded}, failed: {failed}")
    return {"succeeded": succeeded, "failed": failed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan a directory for ebooks.")
    parser.add_argument("path", type=str, help="Directory path to scan for ebooks.")
    parser.add_argument(
        "extension", type=str, help="File extension to filter by (e.g. pdf, epub)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of ebooks to process (default: all).",
    )

    args = parser.parse_args()

    result = run_ingestion(
        path=args.path,
        extension=args.extension,
        limit=args.limit,
        on_progress=print,
    )
    print(f"\nDone — succeeded: {result['succeeded']}, failed: {result['failed']}")
