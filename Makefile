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

.PHONY: docs-publish
docs-publish: docs-build ## Deploy docs to gh-pages branch
	@echo "Publishing docs to gh-pages..."
	@TMPDIR=$$(mktemp -d) && \
	cp -r site/docs/.vitepress/dist/* "$$TMPDIR/" && \
	cd "$$TMPDIR" && \
	git init && \
	git checkout -b gh-pages && \
	git add -A && \
	git commit -m "docs: publish $$(date +%Y-%m-%d)" && \
	git remote add origin git@github.com:xprilion/OpenMLR.git && \
	git push -f origin gh-pages && \
	rm -rf "$$TMPDIR" && \
	echo "Docs published to gh-pages."

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
