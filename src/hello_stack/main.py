"""HTTP API: a health check that reaches the database, and a simple echo."""

import logging
import os

import psycopg  # Python driver for talking to Postgres.
from fastapi import FastAPI, Response, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# The application object. Uvicorn, the web server, loads this: see CMD in the Dockerfile.
app = FastAPI(title="hello-stack")


# Pydantic models define the shape of the JSON going in and out.
# FastAPI uses them to validate requests, format responses and build the /docs page.
class HealthResponse(BaseModel):
    status: str
    database: str
    pgvector: str | None = None  # Empty (null in JSON) when no version could be read.


class EchoRequest(BaseModel):
    # Limits are checked before our code runs. A bad request gets a 422 automatically.
    message: str = Field(min_length=1, max_length=1000)


class EchoResponse(BaseModel):
    echo: str


def get_pgvector_version() -> str | None:
    """Return the installed pgvector version, or None if the extension is missing."""
    # DATABASE_URL comes from compose.yaml, so no connection details live in the code.
    # The timeout makes a dead database fail after 3 seconds instead of hanging.
    # "with" closes the connection automatically when the block ends.
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3) as conn:
        # pg_extension is Postgres's own list of installed extensions.
        # This proves two things at once: the database answers, and pgvector is installed.
        row = conn.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
    # No row means the database works but pgvector isn't installed.
    return row[0] if row else None


# A plain "def" (not "async def") makes FastAPI run this in a worker thread,
# so the blocking database call doesn't hold up other requests.
@app.get("/health", response_model=HealthResponse)
def health(response: Response) -> HealthResponse:
    """Report healthy only if the database answers and pgvector is installed."""
    try:
        version = get_pgvector_version()
    # psycopg.Error: the database couldn't be reached or the query failed.
    # KeyError: DATABASE_URL isn't set.
    except (psycopg.Error, KeyError):
        # Details go to the logs only, because connection errors can reveal host and user names.
        logger.exception("Health check could not reach the database")
        # 503 means "not able to serve right now", which monitoring tools can act on.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="unreachable")

    # The database answered, but this app also needs pgvector, so it still isn't healthy.
    if version is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database="ok")

    return HealthResponse(status="ok", database="ok", pgvector=version)


# FastAPI reads the JSON body into EchoRequest, so "request" is already validated here.
@app.post("/echo", response_model=EchoResponse)
def echo(request: EchoRequest) -> EchoResponse:
    """Return the message that was sent."""
    return EchoResponse(echo=request.message)
