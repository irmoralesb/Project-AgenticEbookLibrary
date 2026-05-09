from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import fitz
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.dependencies import get_repository
from api.main import app
from api.routers import ebooks as ebooks_router
from api.services import field_reextract_service


def _create_pdf(path: Path) -> None:
    doc = fitz.open()
    for index in range(12):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {index + 1}")
    doc.save(path)
    doc.close()


def test_reextract_service_maps_back_to_front_range(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    book_path = tmp_path / "book.pdf"
    _create_pdf(book_path)
    ebook = SimpleNamespace(file_path=str(book_path))

    monkeypatch.setattr(
        field_reextract_service,
        "_extract_pdf_range_text",
        lambda *_args, **_kwargs: "stub text",
    )
    monkeypatch.setattr(
        field_reextract_service,
        "_resolve_field_value",
        lambda field, _text: "9781111111111" if field == "isbn" else None,
    )

    result = field_reextract_service.reextract_field_for_ebook(
        ebook=ebook,
        field="isbn",
        page_range="5-10",
        direction="back_to_front",
    )

    assert result.used_start_page == 3
    assert result.used_end_page == 8
    assert result.value == "9781111111111"


def test_reextract_service_rejects_out_of_bounds_range(tmp_path: Path) -> None:
    book_path = tmp_path / "book.pdf"
    _create_pdf(book_path)
    ebook = SimpleNamespace(file_path=str(book_path))

    with pytest.raises(HTTPException) as exc:
        field_reextract_service.reextract_field_for_ebook(
            ebook=ebook,
            field="publisher",
            page_range="1-40",
            direction="front_to_back",
        )

    assert "Maximum page is 12" in str(exc.value)


def test_reextract_service_rejects_invalid_range_format(tmp_path: Path) -> None:
    book_path = tmp_path / "book.pdf"
    _create_pdf(book_path)
    ebook = SimpleNamespace(file_path=str(book_path))

    with pytest.raises(HTTPException) as exc:
        field_reextract_service.reextract_field_for_ebook(
            ebook=ebook,
            field="authors",
            page_range="abc",
            direction="front_to_back",
        )

    assert "Invalid page_range format" in str(exc.value)


def test_reextract_endpoint_returns_preview_without_persist(monkeypatch: pytest.MonkeyPatch) -> None:
    ebook_id = uuid4()
    repo = SimpleNamespace(
        get_by_id=lambda _id: SimpleNamespace(id=_id, file_path="C:/tmp/book.pdf"),
        update=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("update must not be called")),
    )
    app.dependency_overrides[get_repository] = lambda: repo

    monkeypatch.setattr(
        ebooks_router,
        "reextract_field_for_ebook",
        lambda **_kwargs: field_reextract_service.ReextractResult(
            field="authors",
            value=["A One", "B Two"],
            used_start_page=1,
            used_end_page=5,
            direction="front_to_back",
            message="Field extracted successfully.",
        ),
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/ebooks/{ebook_id}/reextract-field",
            json={
                "field": "authors",
                "page_range": "1-5",
                "direction": "front_to_back",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["field"] == "authors"
    assert payload["value"] == ["A One", "B Two"]


def test_reextract_endpoint_year_returns_integer_value(monkeypatch: pytest.MonkeyPatch) -> None:
    ebook_id = uuid4()
    repo = SimpleNamespace(
        get_by_id=lambda _id: SimpleNamespace(id=_id, file_path="C:/tmp/book.pdf"),
        update=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("update must not be called")),
    )
    app.dependency_overrides[get_repository] = lambda: repo

    monkeypatch.setattr(
        ebooks_router,
        "reextract_field_for_ebook",
        lambda **_kwargs: field_reextract_service.ReextractResult(
            field="year",
            value=2020,
            used_start_page=2,
            used_end_page=6,
            direction="front_to_back",
            message="Field extracted successfully.",
        ),
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/ebooks/{ebook_id}/reextract-field",
            json={
                "field": "year",
                "page_range": "2-6",
                "direction": "front_to_back",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["field"] == "year"
    assert payload["value"] == 2020
