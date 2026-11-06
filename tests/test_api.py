"""API tests. The database call is replaced, so these run without Docker."""

import psycopg
import pytest
from fastapi.testclient import TestClient

from hello_stack import main

client = TestClient(main.app)


def test_health_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "get_pgvector_version", lambda: "0.8.0")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "pgvector": "0.8.0"}


def test_health_reports_unreachable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> str:
        raise psycopg.OperationalError("secret-host refused the connection")

    monkeypatch.setattr(main, "get_pgvector_version", fail)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"
    assert "secret-host" not in response.text


def test_health_reports_missing_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "get_pgvector_version", lambda: None)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "ok", "pgvector": None}


def test_echo_returns_message() -> None:
    response = client.post("/echo", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json() == {"echo": "hello"}


@pytest.mark.parametrize("payload", [{}, {"message": ""}, {"message": "x" * 1001}])
def test_echo_rejects_invalid_message(payload: dict[str, str]) -> None:
    assert client.post("/echo", json=payload).status_code == 422
