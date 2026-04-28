from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from ingestion.main import run_ingestion


class _RepoStub:
    def __init__(self) -> None:
        self._rows: list[SimpleNamespace] = []

    def exists_by_file_name(self, file_name: str) -> bool:
        return False

    def add_from_metadata(self, metadata):
        row = SimpleNamespace(id=len(self._rows) + 1, file_name=metadata.file_name)
        self._rows.append(row)
        return row


def _patch_ingestion_dependencies(monkeypatch, *, extractor, scanner_paths: list[str], repo):
    monkeypatch.setattr("ingestion.main.get_pdf_data_extractor", lambda: extractor)
    monkeypatch.setattr(
        "ingestion.main.get_ebook_scanner",
        lambda: Mock(get_ebooks_from_path=lambda **_: scanner_paths),
    )
    monkeypatch.setattr("ingestion.main.get_db_session", lambda: iter([object()]))
    monkeypatch.setattr("ingestion.main.get_ebook_repository", lambda _session: repo)


def test_run_ingestion_passes_cover_output_dir_to_extract_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    """extract_metadata must be called with the resolved cover_output_dir."""
    book_path = tmp_path / "book.pdf"
    book_path.write_bytes(b"%PDF-1.4")

    cover_dir = tmp_path / "covers"
    metadata = SimpleNamespace(
        file_name=book_path.name,
        cover_image_path=str(cover_dir / "book.png"),
        cover_image_mime_type="image/png",
        has_errors=False,
    )
    extractor = Mock()
    extractor.extract_metadata.return_value = metadata

    repo = _RepoStub()
    _patch_ingestion_dependencies(
        monkeypatch, extractor=extractor, scanner_paths=[str(book_path)], repo=repo
    )

    result = run_ingestion(str(tmp_path), "pdf", cover_image_path=str(cover_dir))

    assert result == {"succeeded": 1, "failed": 0}
    extractor.extract_metadata.assert_called_once_with(
        book_path,
        5,  # PAGES_TO_ANALIZE
        cover_dir.resolve(),
    )


def test_run_ingestion_succeeds_when_extract_metadata_returns_cover_fields(
    tmp_path: Path, monkeypatch
) -> None:
    """Metadata returned by extract_metadata (including cover) is persisted as-is."""
    book_path = tmp_path / "book.pdf"
    book_path.write_bytes(b"%PDF-1.4")

    cover_dir = tmp_path / "covers"
    expected_cover = cover_dir / "book.png"
    metadata = SimpleNamespace(
        file_name=book_path.name,
        cover_image_path=str(expected_cover),
        cover_image_mime_type="image/png",
        has_errors=False,
    )
    extractor = Mock()
    extractor.extract_metadata.return_value = metadata

    repo = _RepoStub()
    _patch_ingestion_dependencies(
        monkeypatch, extractor=extractor, scanner_paths=[str(book_path)], repo=repo
    )

    result = run_ingestion(str(tmp_path), "pdf", cover_image_path=str(cover_dir))

    assert result == {"succeeded": 1, "failed": 0}
    assert repo._rows[0].file_name == book_path.name


def test_run_ingestion_counts_failed_when_extract_metadata_raises(
    tmp_path: Path, monkeypatch
) -> None:
    """A failure in extract_metadata increments failed and does not crash."""
    book_path = tmp_path / "book.pdf"
    book_path.write_bytes(b"%PDF-1.4")

    extractor = Mock()
    extractor.extract_metadata.side_effect = RuntimeError("pdf broken")

    repo = _RepoStub()
    _patch_ingestion_dependencies(
        monkeypatch, extractor=extractor, scanner_paths=[str(book_path)], repo=repo
    )

    result = run_ingestion(str(tmp_path), "pdf", cover_image_path=str(tmp_path / "covers"))

    assert result == {"succeeded": 0, "failed": 1}
