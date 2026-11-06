"""API tests. The database call is replaced, so these run without Docker."""

import psycopg
import pytest
from fastapi.testclient import TestClient

from hello_stack import main

# Sends requests straight to the app, with no real server or network involved.
client = TestClient(main.app)


# monkeypatch swaps a function for a fake during one test, then restores it afterwards.
# Here each fake stands in for the database, so we can create any situation we want.
def test_health_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend the database answered and pgvector is installed.
    monkeypatch.setattr(main, "get_pgvector_version", lambda: "0.8.0")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "pgvector": "0.8.0"}


def test_health_reports_unreachable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend the connection failed, with a sensitive detail in the error message.
    def fail() -> str:
        raise psycopg.OperationalError("secret-host refused the connection")

    monkeypatch.setattr(main, "get_pgvector_version", fail)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"
    # Security check: the internal error details must not reach the caller.
    assert "secret-host" not in response.text


def test_health_reports_missing_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    # Pretend the database works but the extension isn't installed.
    monkeypatch.setattr(main, "get_pgvector_version", lambda: None)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "ok", "pgvector": None}


def test_echo_returns_message() -> None:
    response = client.post("/echo", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json() == {"echo": "hello"}


# parametrize runs this test once per payload: missing, too short (empty) and too long.
# 422 is the status FastAPI returns when a request fails validation.
@pytest.mark.parametrize("payload", [{}, {"message": ""}, {"message": "x" * 1001}])
def test_echo_rejects_invalid_message(payload: dict[str, str]) -> None:
    assert client.post("/echo", json=payload).status_code == 422
