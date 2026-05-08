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


def _patch_ingestion_dependencies(
    monkeypatch,
    *,
    pdf_extractor,
    epub_extractor,
    scanner_paths_by_extension: dict[str, list[str]],
    repo,
):
    monkeypatch.setattr("ingestion.main.get_pdf_data_extractor", lambda: pdf_extractor)
    monkeypatch.setattr("ingestion.main.get_epub_data_extractor", lambda: epub_extractor)
    monkeypatch.setattr(
        "ingestion.main.get_ebook_scanner",
        lambda: Mock(
            get_ebooks_from_path=lambda **kwargs: scanner_paths_by_extension.get(
                kwargs["extension"], []
            )
        ),
    )
    monkeypatch.setattr("ingestion.main.get_db_session", lambda: iter([object()]))
    monkeypatch.setattr("ingestion.main.get_ebook_repository", lambda _session: repo)


def test_run_ingestion_calls_extract_metadata_with_resolved_book_path(
    tmp_path: Path, monkeypatch
) -> None:
    book_path = tmp_path / "book.pdf"
    book_path.write_bytes(b"%PDF-1.4")
    book_resolved = book_path.resolve()

    metadata = SimpleNamespace(
        file_name=book_path.name,
        cover_image_path=str(book_resolved.parent / "book.png"),
        cover_image_mime_type="image/png",
        has_errors=False,
    )
    pdf_extractor = Mock()
    pdf_extractor.extract_metadata.return_value = metadata
    epub_extractor = Mock()

    repo = _RepoStub()
    _patch_ingestion_dependencies(
        monkeypatch,
        pdf_extractor=pdf_extractor,
        epub_extractor=epub_extractor,
        scanner_paths_by_extension={"pdf": [str(book_path)], "epub": []},
        repo=repo,
    )

    result = run_ingestion(str(tmp_path))

    assert result == {"succeeded": 1, "failed": 0}
    pdf_extractor.extract_metadata.assert_called_once_with(book_resolved)
    epub_extractor.extract_metadata.assert_not_called()


def test_run_ingestion_succeeds_when_extract_metadata_returns_cover_fields(
    tmp_path: Path, monkeypatch
) -> None:
    """Metadata returned by extract_metadata (including cover) is persisted as-is."""
    book_path = tmp_path / "book.pdf"
    book_path.write_bytes(b"%PDF-1.4")

    expected_cover = book_path.resolve().parent / "book.png"
    metadata = SimpleNamespace(
        file_name=book_path.name,
        cover_image_path=str(expected_cover),
        cover_image_mime_type="image/png",
        has_errors=False,
    )
    pdf_extractor = Mock()
    pdf_extractor.extract_metadata.return_value = metadata
    epub_extractor = Mock()

    repo = _RepoStub()
    _patch_ingestion_dependencies(
        monkeypatch,
        pdf_extractor=pdf_extractor,
        epub_extractor=epub_extractor,
        scanner_paths_by_extension={"pdf": [str(book_path)], "epub": []},
        repo=repo,
    )

    result = run_ingestion(str(tmp_path))

    assert result == {"succeeded": 1, "failed": 0}
    assert repo._rows[0].file_name == book_path.name


def test_run_ingestion_counts_failed_when_extract_metadata_raises(
    tmp_path: Path, monkeypatch
) -> None:
    """A failure in extract_metadata increments failed and does not crash."""
    book_path = tmp_path / "book.pdf"
    book_path.write_bytes(b"%PDF-1.4")

    pdf_extractor = Mock()
    pdf_extractor.extract_metadata.side_effect = RuntimeError("pdf broken")
    epub_extractor = Mock()

    repo = _RepoStub()
    _patch_ingestion_dependencies(
        monkeypatch,
        pdf_extractor=pdf_extractor,
        epub_extractor=epub_extractor,
        scanner_paths_by_extension={"pdf": [str(book_path)], "epub": []},
        repo=repo,
    )

    result = run_ingestion(str(tmp_path))

    assert result == {"succeeded": 0, "failed": 1}


def test_run_ingestion_routes_mixed_pdf_and_epub_files_to_matching_extractors(
    tmp_path: Path, monkeypatch
) -> None:
    """A single folder can contain both supported types and each uses its extractor."""
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    epub_path = tmp_path / "book.epub"
    epub_path.write_bytes(b"EPUB")

    pdf_metadata = SimpleNamespace(
        file_name=pdf_path.name,
        cover_image_path=str(pdf_path.resolve().parent / "book.png"),
        cover_image_mime_type="image/png",
        has_errors=False,
    )
    epub_metadata = SimpleNamespace(
        file_name=epub_path.name,
        cover_image_path=str(epub_path.resolve().parent / "book.png"),
        cover_image_mime_type="image/png",
        has_errors=False,
    )

    pdf_extractor = Mock()
    pdf_extractor.extract_metadata.return_value = pdf_metadata
    epub_extractor = Mock()
    epub_extractor.extract_metadata.return_value = epub_metadata

    repo = _RepoStub()
    _patch_ingestion_dependencies(
        monkeypatch,
        pdf_extractor=pdf_extractor,
        epub_extractor=epub_extractor,
        scanner_paths_by_extension={"pdf": [str(pdf_path)], "epub": [str(epub_path)]},
        repo=repo,
    )

    result = run_ingestion(str(tmp_path))

    assert result == {"succeeded": 2, "failed": 0}
    pdf_extractor.extract_metadata.assert_called_once()
    epub_extractor.extract_metadata.assert_called_once()
    assert pdf_extractor.extract_metadata.call_args.args[0] == pdf_path.resolve()
    assert epub_extractor.extract_metadata.call_args.args[0] == epub_path.resolve()
