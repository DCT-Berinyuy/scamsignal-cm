import pytest
from fastapi.testclient import TestClient

from app.config import GEMINI_API_KEY_ENV
from app.main import app


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch) -> None:
    """Tests never call the real Gemini API, even if the developer's shell has a key."""
    monkeypatch.delenv(GEMINI_API_KEY_ENV, raising=False)


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
