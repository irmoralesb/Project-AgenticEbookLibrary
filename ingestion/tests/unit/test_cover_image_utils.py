from pathlib import Path

import pytest

from extractors.tools.cover_image_utils import find_existing_cover, guess_mime_type_from_suffix


# ---------------------------------------------------------------------------
# guess_mime_type_from_suffix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "suffix, expected",
    [
        (".png", "image/png"),
        (".PNG", "image/png"),
        (".jpg", "image/jpeg"),
        (".JPG", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".webp", "image/webp"),
        (".gif", "image/gif"),
        (".bmp", None),
        (".tiff", None),
        ("", None),
    ],
)
def test_guess_mime_type_from_suffix(suffix: str, expected: str | None, tmp_path: Path) -> None:
    path = tmp_path / f"image{suffix}"
    assert guess_mime_type_from_suffix(path) == expected


# ---------------------------------------------------------------------------
# find_existing_cover
# ---------------------------------------------------------------------------

def test_find_existing_cover_returns_prior_path_when_it_exists(tmp_path: Path) -> None:
    book_path = tmp_path / "mybook.pdf"
    cover_dir = tmp_path / "covers"
    cover_dir.mkdir()

    prior_cover = tmp_path / "prior.png"
    prior_cover.write_bytes(b"prior")

    result = find_existing_cover(book_path, cover_dir, str(prior_cover))

    assert result == prior_cover.resolve()


def test_find_existing_cover_ignores_prior_path_when_it_does_not_exist(tmp_path: Path) -> None:
    book_path = tmp_path / "mybook.pdf"
    cover_dir = tmp_path / "covers"
    cover_dir.mkdir()

    cover_in_dir = cover_dir / "mybook.png"
    cover_in_dir.write_bytes(b"cover")

    result = find_existing_cover(book_path, cover_dir, str(tmp_path / "ghost.png"))

    assert result == cover_in_dir.resolve()


def test_find_existing_cover_returns_glob_match_when_no_prior_path(tmp_path: Path) -> None:
    book_path = tmp_path / "mybook.epub"
    cover_dir = tmp_path / "covers"
    cover_dir.mkdir()

    cover_file = cover_dir / "mybook.jpeg"
    cover_file.write_bytes(b"cover")

    result = find_existing_cover(book_path, cover_dir, None)

    assert result == cover_file.resolve()


def test_find_existing_cover_returns_none_when_nothing_found(tmp_path: Path) -> None:
    book_path = tmp_path / "mybook.pdf"
    cover_dir = tmp_path / "covers"
    cover_dir.mkdir()

    result = find_existing_cover(book_path, cover_dir, None)

    assert result is None


def test_find_existing_cover_returns_none_for_missing_prior_and_empty_dir(tmp_path: Path) -> None:
    book_path = tmp_path / "mybook.pdf"
    cover_dir = tmp_path / "covers"
    cover_dir.mkdir()

    result = find_existing_cover(book_path, cover_dir, str(tmp_path / "nonexistent.png"))

    assert result is None
