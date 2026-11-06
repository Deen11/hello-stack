"""HTTP API: a health check that reaches the database, and a simple echo."""

import logging
import os

import psycopg
from fastapi import FastAPI, Response, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="hello-stack")


class HealthResponse(BaseModel):
    status: str
    database: str
    pgvector: str | None = None


class EchoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class EchoResponse(BaseModel):
    echo: str


def get_pgvector_version() -> str | None:
    """Return the installed pgvector version, or None if the extension is missing."""
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3) as conn:
        row = conn.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
    return row[0] if row else None


@app.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    """Report healthy only if the database answers and pgvector is installed."""
    try:
        version = get_pgvector_version()
    except (psycopg.Error, KeyError):
        # Details go to the logs only, because connection errors can reveal host and user names.
        logger.exception("Health check could not reach the database")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="unreachable")

    if version is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="ok")

    return HealthResponse(status="ok", database="ok", pgvector=version)


@app.post("/echo", response_model=EchoResponse)
def echo(request: EchoRequest) -> EchoResponse:
    """Return the message that was sent."""
    return EchoResponse(echo=request.message)
