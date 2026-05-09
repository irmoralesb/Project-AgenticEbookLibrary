"""Minimal publisher catalog API tests with mocked DB session."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.dependencies import get_db
from api.main import app


def test_list_publishers_empty_with_mock_session() -> None:
    mock_session = MagicMock()
    scalar_result = MagicMock()
    scalar_result.all.return_value = []
    mock_session.scalars.return_value = scalar_result

    def fake_db():
        yield mock_session

    app.dependency_overrides[get_db] = fake_db
    try:
        client = TestClient(app)
        response = client.get("/api/publishers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
