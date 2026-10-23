"""Upload validation that rejects a request before it ever reaches the database.

The paths that do touch the database (success, duplicate) need a real
PostgreSQL and are covered by integration tests.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import get_db
from app.routers import documents
from tests.pdf_factory import make_pdf


async def _no_database():
    # Any of these tests reaching the database would be a bug in the
    # validation order, and a None session makes that fail loudly.
    yield None


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = _no_database
    yield TestClient(app)
    app.dependency_overrides.clear()


def _upload(client: TestClient, content: bytes, filename: str = "file.pdf"):
    return client.post("/documents", files={"file": (filename, content, "application/pdf")})


def test_file_over_the_size_limit_is_rejected_with_413(client, monkeypatch):
    monkeypatch.setattr(documents, "MAX_UPLOAD_BYTES", 100)

    response = _upload(client, b"%PDF-" + b"x" * 200)

    assert response.status_code == 413


def test_file_that_is_not_a_pdf_is_rejected_with_415_even_if_it_claims_to_be(client):
    response = _upload(client, b"PK\x03\x04 this is a zip file", filename="disguised.pdf")

    assert response.status_code == 415


def test_corrupted_pdf_is_rejected_with_422(client):
    response = _upload(client, b"%PDF-1.7\nthe header is right but nothing else is")

    assert response.status_code == 422
    assert "could not be read" in response.json()["detail"]


def test_pdf_without_any_text_is_rejected_with_422(client):
    response = _upload(client, make_pdf(["", ""]))

    assert response.status_code == 422
    assert "no extractable text" in response.json()["detail"]
