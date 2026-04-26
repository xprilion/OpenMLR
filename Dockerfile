# Production Dockerfile
# Builds frontend and backend into a single image
# Usage: docker build -t openmlr . && docker run -p 3000:3000 openmlr
#
# For development with live reload, use Dockerfile.dev instead:
#   make dev-docker

# ── Stage 1: Build frontend ──────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

COPY frontend/ .
RUN pnpm build


# ── Stage 2: Python backend ─────────────────────────────
FROM python:3.12-slim AS runtime

# System deps for asyncpg, lxml, bcrypt
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libpq-dev libxml2-dev libxslt1-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user for security
RUN groupadd --gid 1000 openmlr && \
    useradd --uid 1000 --gid openmlr --shell /bin/bash --create-home openmlr

WORKDIR /app

# Install Python dependencies (cached layer)
COPY backend/pyproject.toml backend/uv.lock* backend/.python-version ./backend/
COPY backend/openmlr/__init__.py ./backend/openmlr/__init__.py
RUN cd backend && uv sync --no-dev

# Copy backend source
COPY backend/ ./backend/

# Copy configs
COPY backend/configs/ ./backend/configs/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create data directory for SQLite (when not using Postgres)
RUN mkdir -p /app/data && chown -R openmlr:openmlr /app

# Switch to non-root user
USER openmlr

ENV PORT=3000
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

CMD ["backend/.venv/bin/uvicorn", "openmlr.app:app", "--host", "0.0.0.0", "--port", "3000", "--app-dir", "backend"]
