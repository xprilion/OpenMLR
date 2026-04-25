# OpenMLR Makefile
# Backend:  Python / FastAPI   (backend/)
# Frontend: React  / Vite      (frontend/)

SHELL       := /bin/bash
BACKEND     := backend
FRONTEND    := frontend
PORT        ?= 3000

# ─── Setup ────────────────────────────────────────────────

.PHONY: install
install: install-backend install-frontend ## Install all dependencies

.PHONY: install-backend
install-backend: ## Install Python backend dependencies
	cd $(BACKEND) && uv sync

.PHONY: install-frontend
install-frontend: ## Install frontend dependencies
	cd $(FRONTEND) && pnpm install

# ─── Development ──────────────────────────────────────────

.PHONY: dev
dev: ## Run backend + frontend dev servers in parallel
	@trap 'kill 0' EXIT; \
	$(MAKE) dev-backend & \
	$(MAKE) dev-frontend & \
	wait

.PHONY: dev-backend
dev-backend: ## Start backend with auto-reload (port=$(PORT))
	cd $(BACKEND) && uv run uvicorn openmlr.app:app \
		--host 0.0.0.0 --port $(PORT) --reload --reload-dir openmlr

.PHONY: dev-frontend
dev-frontend: ## Start Vite dev server (proxies /api to backend)
	cd $(FRONTEND) && pnpm dev

.PHONY: dev-full
dev-full: ## Run backend + frontend + celery worker (requires Redis)
	@trap 'kill 0' EXIT; \
	USE_BACKGROUND_JOBS=true USE_REDIS_PUBSUB=true $(MAKE) dev-backend & \
	$(MAKE) dev-frontend & \
	$(MAKE) worker & \
	wait

.PHONY: worker
worker: ## Start Celery worker for background jobs
	cd $(BACKEND) && uv run celery -A openmlr.celery_app worker \
		--loglevel=info --concurrency=2 -Q default,agent

# ─── Build & Production ──────────────────────────────────

.PHONY: build
build: build-frontend ## Build production frontend bundle

.PHONY: build-frontend
build-frontend: ## Compile frontend to frontend/dist/
	cd $(FRONTEND) && pnpm build

.PHONY: start
start: build ## Build frontend, then start production server
	cd $(BACKEND) && uv run uvicorn openmlr.app:app \
		--host 0.0.0.0 --port $(PORT)

# ─── Database ─────────────────────────────────────────────

.PHONY: db-create
db-create: ## Create missing tables (safe, no-op on existing)
	cd $(BACKEND) && uv run python -m openmlr.db.create_tables

.PHONY: db-fresh
db-fresh: ## Drop ALL tables and recreate (destroys data!)
	cd $(BACKEND) && uv run python -m openmlr.db.create_tables --fresh

.PHONY: db-migrate
db-migrate: ## Generate Alembic migration  (MSG="add users table")
	cd $(BACKEND) && uv run alembic revision --autogenerate -m "$(MSG)"

.PHONY: db-upgrade
db-upgrade: ## Apply pending Alembic migrations
	cd $(BACKEND) && uv run alembic upgrade head

# ─── Checks ──────────────────────────────────────────────

.PHONY: check
check: check-backend check-frontend ## Run all checks

.PHONY: check-backend
check-backend: ## Verify backend loads without errors
	cd $(BACKEND) && uv run python -c \
		"from openmlr.app import app; print(f'Backend OK: {app.title} v{app.version}, {len(app.routes)} routes')"

.PHONY: check-frontend
check-frontend: ## Type-check the frontend (tsc --noEmit)
	cd $(FRONTEND) && npx tsc --noEmit

.PHONY: test
test: ## Run backend tests (pytest)
	cd $(BACKEND) && uv run pytest -q

# ─── Docker ───────────────────────────────────────────────

.PHONY: docker-build
docker-build: ## Build Docker image
	docker build -t openmlr .

.PHONY: docker-run
docker-run: ## Run Docker container (pass DATABASE_URL via env)
	docker run --rm -p $(PORT):$(PORT) --env-file .env openmlr

# ─── Docker Compose ──────────────────────────────────────
# Uses `docker compose` (V2) by default, falls back to `docker-compose` (V1)
# Override with: make up DOCKER_COMPOSE="docker-compose"
DOCKER_COMPOSE ?= docker compose

.PHONY: up
up: ## Start all services (db, redis, web, worker)
	$(DOCKER_COMPOSE) up -d

.PHONY: down
down: ## Stop all services
	$(DOCKER_COMPOSE) down

.PHONY: restart
restart: ## Restart web + worker (quick rebuild)
	$(DOCKER_COMPOSE) up -d --build web worker

.PHONY: logs
logs: ## Tail logs from all services
	$(DOCKER_COMPOSE) logs -f

.PHONY: logs-web
logs-web: ## Tail logs from web service
	$(DOCKER_COMPOSE) logs -f web

.PHONY: logs-worker
logs-worker: ## Tail logs from worker service
	$(DOCKER_COMPOSE) logs -f worker

.PHONY: rebuild
rebuild: ## Full rebuild and restart all services
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) build --no-cache
	$(DOCKER_COMPOSE) up -d

.PHONY: shell-web
shell-web: ## Open shell in web container
	$(DOCKER_COMPOSE) exec web /bin/bash

.PHONY: shell-db
shell-db: ## Open psql in database container
	$(DOCKER_COMPOSE) exec db psql -U postgres -d openmlr

# ─── Docker Compose (Development) ────────────────────────

.PHONY: dev-docker
dev-docker: ## Start with live reload (mounts source code)
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

.PHONY: dev-docker-build
dev-docker-build: ## Build dev images and start with live reload
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up --build

.PHONY: dev-docker-down
dev-docker-down: ## Stop dev services
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml down

.PHONY: infra
infra: ## Start only db + redis (for local dev without Docker app)
	$(DOCKER_COMPOSE) up -d db redis

# ─── Docs ─────────────────────────────────────────────────

.PHONY: docs-install
docs-install: ## Install docs site dependencies
	cd site && npm install

.PHONY: docs-dev
docs-dev: ## Preview docs locally
	cd site && npx vitepress dev docs

.PHONY: docs-build
docs-build: ## Build docs to site/docs/.vitepress/dist
	cd site && npx vitepress build docs

# ─── Cleanup ─────────────────────────────────────────────

.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf $(FRONTEND)/dist
	find $(BACKEND) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND) -name '*.pyc' -delete 2>/dev/null || true

.PHONY: clean-all
clean-all: clean ## Remove all deps + build artifacts
	rm -rf $(FRONTEND)/node_modules
	rm -rf $(BACKEND)/.venv
	rm -rf node_modules
	rm -rf site/node_modules site/docs/.vitepress/dist site/docs/.vitepress/cache

# ─── Help ─────────────────────────────────────────────────

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
