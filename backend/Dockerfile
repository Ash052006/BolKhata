# Backend Dockerfile — multi-stage, Python 3.11 slim
FROM python:3.11-slim AS base

WORKDIR /app

# Install uv for fast dependency resolution inside Docker
RUN pip install --no-cache-dir uv==0.13.3

# Copy dependency manifests first to leverage layer caching
COPY pyproject.toml ./
COPY src/ ./src/

# Install production dependencies only (no dev group)
RUN uv sync --no-dev --python 3.11

# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

COPY --from=base /app/.venv /app/.venv
COPY --from=base /usr/local/bin/uv /usr/local/bin/uv
COPY pyproject.toml ./
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Non-root user with home directory; ensure /data is writable for SQLite
RUN addgroup --system bolkhata && \
    adduser --system --ingroup bolkhata --home /home/bolkhata bolkhata && \
    mkdir -p /data /home/bolkhata /tmp/uv-cache && \
    chown -R bolkhata:bolkhata /data /home/bolkhata /tmp/uv-cache /app

USER bolkhata

EXPOSE 8000

# Run Alembic migrations then start Uvicorn with exec to replace PID 1 for graceful SIGTERM signal handling
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn bolkhata.api.app:app --host 0.0.0.0 --port 8000"]
