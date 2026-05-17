"""List ebooks query-parameter tests with mocked repository."""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_repository
from api.main import app


@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.list_all.return_value = []
    return repo


@pytest.fixture
def client(mock_repo: MagicMock) -> TestClient:
    app.dependency_overrides[get_repository] = lambda: mock_repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_list_ebooks_passes_tags_contains(client: TestClient, mock_repo: MagicMock) -> None:
    response = client.get("/api/ebooks", params={"tags": "python"})

    assert response.status_code == 200
    mock_repo.list_all.assert_called_once()
    kwargs = mock_repo.list_all.call_args.kwargs
    assert kwargs["tags_contains"] == "python"
    assert kwargs["tags_empty"] is None


def test_list_ebooks_passes_tags_empty(client: TestClient, mock_repo: MagicMock) -> None:
    response = client.get("/api/ebooks", params={"tags_empty": "true"})

    assert response.status_code == 200
    kwargs = mock_repo.list_all.call_args.kwargs
    assert kwargs["tags_empty"] is True
    assert kwargs["tags_contains"] is None


def test_list_ebooks_tags_empty_ignores_tags_text(client: TestClient, mock_repo: MagicMock) -> None:
    response = client.get(
        "/api/ebooks",
        params={"tags_empty": "true", "tags": "python"},
    )

    assert response.status_code == 200
    kwargs = mock_repo.list_all.call_args.kwargs
    assert kwargs["tags_empty"] is True
    assert kwargs["tags_contains"] == "python"


def test_repository_tags_empty_filter() -> None:
    from persistence.repositories.ebook_repository import SqlAlchemyEbookRepository

    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    repo = SqlAlchemyEbookRepository(session)

    repo.list_all(tags_empty=True)

    stmt = session.execute.call_args[0][0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "cardinality" in compiled.lower() or "tags" in compiled.lower()


def test_repository_tags_contains_filter() -> None:
    from persistence.repositories.ebook_repository import SqlAlchemyEbookRepository

    session = MagicMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    repo = SqlAlchemyEbookRepository(session)

    repo.list_all(tags_contains="fast")

    stmt = session.execute.call_args[0][0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "fast" in compiled.lower() or "array_to_string" in compiled.lower()
