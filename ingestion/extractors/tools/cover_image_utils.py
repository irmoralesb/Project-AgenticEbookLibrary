from pathlib import Path

_MIME_BY_SUFFIX: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def guess_mime_type_from_suffix(path: Path) -> str | None:
    """Return the MIME type inferred from *path*'s file extension, or ``None``."""
    return _MIME_BY_SUFFIX.get(path.suffix.lower())


def find_existing_cover(
    book_path: Path,
    cover_output_dir: Path,
    prior_cover_path: str | None,
) -> Path | None:
    """Return the resolved path of an existing cover image, or ``None``.

    Search order:
    1. ``prior_cover_path`` when it exists on disk.
    2. Any file in ``cover_output_dir`` whose stem matches ``book_path.stem``.
    """
    if prior_cover_path:
        candidate = Path(prior_cover_path).expanduser()
        if candidate.exists():
            return candidate.resolve()

    for candidate in sorted(cover_output_dir.glob(f"{book_path.stem}.*")):
        if candidate.is_file():
            return candidate.resolve()

    return None
