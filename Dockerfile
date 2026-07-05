# syntax=docker/dockerfile:1.7

############################
# Stage 1: build deps
############################
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/cache/uv \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

WORKDIR /app

RUN uv venv .venv

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,id=uv-cache,target=/cache/uv,sharing=locked \
    uv sync --frozen --no-dev --no-install-project

COPY backend ./backend
COPY alembic.ini ./

RUN --mount=type=cache,id=uv-cache,target=/cache/uv,sharing=locked \
    uv sync --frozen --no-dev


############################
# Stage 2: runtime
############################
FROM python:3.12-slim-bookworm AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/backend /app/backend
COPY --from=builder --chown=appuser:appuser /app/alembic.ini /app/alembic.ini

USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]