FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv

WORKDIR /app

# Copy only what the app needs, and install exactly what uv.lock specifies.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# Don't run the app as root.
RUN useradd --create-home app
USER app

EXPOSE 8000
CMD [".venv/bin/uvicorn", "hello_stack.main:app", "--host", "0.0.0.0", "--port", "8000"]
