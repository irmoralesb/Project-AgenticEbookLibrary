from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import ebooks as ebooks_router
from api.schemas import BatchReextractFieldJobRequest
from api.services import batch_reextract_field_service


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_batch_reextract_start_returns_job_id(client: TestClient) -> None:
    ebook_id = uuid4()
    res = client.post(
        "/api/ebooks/batch-reextract-field/start",
        json={
            "ebook_ids": [str(ebook_id)],
            "field": "authors",
            "page_range": "1-2",
            "direction": "front_to_back",
        },
    )
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["job_id"]


def test_batch_reextract_stream_unknown_job_contains_error(client: TestClient) -> None:
    with client.stream(
        "GET",
        "/api/ebooks/batch-reextract-field/stream",
        params={"job_id": str(uuid4())},
    ) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    assert "Unknown job_id" in body


def test_batch_reextract_stream_runs_job(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    lines: list[str] = []

    def fake_run(job: BatchReextractFieldJobRequest, on_progress) -> None:  # noqa: ANN001
        assert len(job.ebook_ids) == 1
        on_progress("step-one")
        on_progress("step-two")

    monkeypatch.setattr(ebooks_router, "run_batch_reextract_field_job", fake_run)

    start = client.post(
        "/api/ebooks/batch-reextract-field/start",
        json={
            "ebook_ids": [str(uuid4())],
            "field": "isbn",
            "page_range": "1-5",
            "direction": "back_to_front",
        },
    )
    job_id = start.json()["job_id"]

    with client.stream(
        "GET",
        "/api/ebooks/batch-reextract-field/stream",
        params={"job_id": job_id},
    ) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())

    assert "step-one" in body
    assert "step-two" in body
    assert "stream-end" in body


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("authors", ["A", "B"], {"authors": ["A", "B"]}),
        ("tags", ["x"], {"tags": ["x"]}),
        ("isbn", " 978-1 ", {"isbn": "978-1"}),
        ("publisher", " ACME ", {"publisher": "ACME"}),
        ("year", 2001, {"year": 2001}),
        ("year", "1999", {"year": 1999}),
    ],
)
def test_reextract_value_to_repo_update_maps(
    field: str, value: object, expected: dict
) -> None:
    out = batch_reextract_field_service.reextract_value_to_repo_update(field, value)  # type: ignore[arg-type]
    assert out == expected


def test_reextract_value_to_repo_update_skips_empty() -> None:
    assert batch_reextract_field_service.reextract_value_to_repo_update("authors", []) is None
    assert batch_reextract_field_service.reextract_value_to_repo_update("tags", []) is None
    assert batch_reextract_field_service.reextract_value_to_repo_update("isbn", "") is None
    assert batch_reextract_field_service.reextract_value_to_repo_update("year", 1800) is None
    assert batch_reextract_field_service.reextract_value_to_repo_update("year", None) is None
