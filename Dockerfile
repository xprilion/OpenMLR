# Production Dockerfile
# Builds frontend and backend into a single container image
# Usage: docker build -t openmlr . && docker run -p 3000:3000 openmlr

# ── Stage 1: Build frontend ──────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Install pnpm directly for speed and reliability
RUN npm install -g pnpm@latest

# Install dependencies (cached layer)
COPY frontend/package.json ./
RUN pnpm install

# Copy frontend source and build production SPA
COPY frontend/ ./
RUN pnpm build


# ── Stage 2: Python backend runtime ───────────────────────
FROM python:3.12-slim AS runtime

# System dependencies for asyncpg, lxml, cryptography, git
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libpq-dev libxml2-dev libxslt1-dev curl git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create non-root openmlr user
RUN groupadd --gid 1000 openmlr && \
    useradd --uid 1000 --gid openmlr --shell /bin/bash --create-home openmlr

WORKDIR /app

# Copy backend source and install dependencies
COPY backend/ ./backend/
RUN cd backend && uv sync --no-dev

# Copy built frontend static bundle
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create runtime directories with non-root ownership
RUN mkdir -p /app/data /app/.workspaces /app/.keys && chown -R openmlr:openmlr /app

# Switch to non-root user
USER openmlr

ENV PORT=3000
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONPATH="/app/backend"
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

CMD ["sh", "-c", "uvicorn openmlr.app:app --host 0.0.0.0 --port ${PORT:-3000} --app-dir backend"]
