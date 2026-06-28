# ==========================
# Stage 1 - Build dependencies
# ==========================

# Official Python image (Python 3.12 on Debian 12 Slim)
FROM python:3.12-slim-bookworm AS builder

# Install packages needed only while building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy uv executable
COPY --from=ghcr.io/astral-sh/uv:0.4.10 /uv /bin/uv

# All future commands run inside /app
WORKDIR /app

# Create a virtual environment
RUN uv venv .venv

# Use the virtual environment automatically
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy dependency files first
# Docker won't reinstall packages if only your source code changes
COPY pyproject.toml uv.lock ./

# Install production dependencies
RUN uv sync --frozen --no-dev


# ==========================
# Stage 2 - Runtime
# ==========================

FROM python:3.12-slim-bookworm As runner

# Only runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Create a non-root user
RUN useradd -m appuser

# Copy installed packages
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --chown=appuser backend ./backend
COPY --chown=appuser alembic.ini .

USER appuser

EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]


