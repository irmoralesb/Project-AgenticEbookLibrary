import argparse
from pathlib import Path

from dotenv import load_dotenv

from dependency_injection.dependency_utils import (
    get_db_session,
    get_ebook_repository,
    get_ebook_scanner,
    get_pdf_data_extractor,
)
from domain.ebook_metadata import EbookMetadata

load_dotenv()

PAGES_TO_ANALIZE = 15
COVER_IMAGE_DPI = 160
COVER_IMAGE_FORMAT = "png"
COVER_IMAGE_FOLDER = "cover_images"

_pdf_data_extractor = get_pdf_data_extractor()


def get_ebooks_from_path(path: str, extension: str) -> list[str]:
    ebook_scanner = get_ebook_scanner()
    return ebook_scanner.get_ebooks_from_path(path=path, extension=extension)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan a directory for ebooks.")
    parser.add_argument(
        "path", type=str, help="Directory path to scan for ebooks."
    )
    parser.add_argument(
        "extension", type=str, help="File extension to filter by (e.g. pdf)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of ebooks to process (default: all).",
    )

    args = parser.parse_args()

    ebook_path_list = get_ebooks_from_path(path=args.path, extension=args.extension)

    total_books_found = len(ebook_path_list)
    print(f"Books found {total_books_found}")

    ebook_paths_to_process = (
        ebook_path_list[: args.limit]
        if args.limit is not None
        else ebook_path_list
    )
    cover_output_dir = Path(COVER_IMAGE_FOLDER).resolve()
    cover_output_dir.mkdir(parents=True, exist_ok=True)

    paths_to_extract: list[str] = []
    for session in get_db_session():
        repo = get_ebook_repository(session)
        for ebook_path in ebook_paths_to_process:
            file_name = Path(ebook_path).name
            if repo.exists_by_file_name(file_name):
                print(f"Skip metadata (already in DB): {file_name}")
                continue
            paths_to_extract.append(ebook_path)

    ebooks_with_metadata: list[EbookMetadata] = []
    for ebook_path in paths_to_extract:
        path = Path(ebook_path)
        metadata = _pdf_data_extractor.extract_metadata(path, PAGES_TO_ANALIZE)
        try:
            cover = _pdf_data_extractor.extract_cover_image(
                path,
                render_dpi=COVER_IMAGE_DPI,
                render_format=COVER_IMAGE_FORMAT,
                use_embedded_image_fallback=False,
            )
            ext = cover.mime_type.split("/")[-1]
            cover_file_name = f"{path.stem}.{ext}"
            cover_file_path = cover_output_dir / cover_file_name
            cover_file_path.write_bytes(cover.data)
            metadata.cover_image_path = str(cover_file_path)
            metadata.cover_image_mime_type = cover.mime_type
        except Exception as exc:
            metadata.has_errors = True
            print(f"Failed to extract cover for {path.name}: {exc}")

        ebooks_with_metadata.append(metadata)

    for session in get_db_session():
        repo = get_ebook_repository(session)
        for metadata in ebooks_with_metadata:
            row = repo.add_from_metadata(metadata)
            print(f"Stored metadata id={row.id} file_name={row.file_name}")

    print(ebooks_with_metadata)
