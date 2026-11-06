# Recipe for the app image. Each instruction below adds a layer on top of the last.

# Start from a small official Linux image that already has Python 3.12.
FROM python:3.12-slim

# Copy the uv program out of uv's own image. The version is pinned so builds stay repeatable.
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv

# All the following instructions run inside /app, which is created if needed.
WORKDIR /app

# Copy only what the app needs, and install exactly what uv.lock specifies.
# README.md is included because pyproject.toml refers to it.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# --frozen: use uv.lock exactly as committed, without updating it.
# --no-dev: leave out test and lint tools, which production doesn't need.
# --no-editable: install the app as a normal package into .venv.
RUN uv sync --frozen --no-dev --no-editable

# Don't run the app as root. If it were ever compromised, the attacker would have fewer rights.
RUN useradd --create-home app
USER app

# Documents the port the app listens on. Publishing it happens in compose.yaml.
EXPOSE 8000
# The command that runs when the container starts: Uvicorn serving "app" from main.py.
# --host 0.0.0.0 accepts connections from outside the container. With the default,
# 127.0.0.1, the port mapping in compose.yaml couldn't reach the app.
CMD [".venv/bin/uvicorn", "hello_stack.main:app", "--host", "0.0.0.0", "--port", "8000"]
