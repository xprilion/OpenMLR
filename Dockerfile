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
        build-essential libpq-dev libxml2-dev libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

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

ENV PORT=3000
EXPOSE 3000

CMD ["backend/.venv/bin/uvicorn", "openmlr.app:app", "--host", "0.0.0.0", "--port", "3000", "--app-dir", "backend"]
