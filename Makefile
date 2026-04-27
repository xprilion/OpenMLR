# OpenMLR Makefile
# Backend:  Python / FastAPI   (backend/)
# Frontend: React  / Vite      (frontend/)

SHELL         := /bin/bash
BACKEND       := backend
FRONTEND      := frontend
PORT          ?= 3000
DOCKER_USER   ?= xprilion
VERSION       := $(shell cat VERSION 2>/dev/null || echo 0.0.0)
DOCKER_COMPOSE := docker compose
LOGO_SRC      := assets/full-logo.png

# ─── Versioning ───────────────────────────────────────────
# Single source of truth: VERSION file at repo root.
# Bump targets compute the new version, write it, then sync everywhere.

MAJOR := $(word 1,$(subst ., ,$(VERSION)))
MINOR := $(word 2,$(subst ., ,$(VERSION)))
PATCH := $(word 3,$(subst ., ,$(VERSION)))

.PHONY: version
version: ## Print current version
	@echo $(VERSION)

.PHONY: version-major
version-major: ## Bump major version (e.g. 0.3.1 -> 1.0.0)
	@NEW=$$(( $(MAJOR) + 1 )).0.0; \
	echo "$$NEW" > VERSION; \
	$(MAKE) _version-sync; \
	echo "Version bumped: $(VERSION) -> $$NEW"

.PHONY: version-minor
version-minor: ## Bump minor version (e.g. 0.3.1 -> 0.4.0)
	@NEW=$(MAJOR).$$(( $(MINOR) + 1 )).0; \
	echo "$$NEW" > VERSION; \
	$(MAKE) _version-sync; \
	echo "Version bumped: $(VERSION) -> $$NEW"

.PHONY: version-patch
version-patch: ## Bump patch version (e.g. 0.3.0 -> 0.3.1)
	@NEW=$(MAJOR).$(MINOR).$$(( $(PATCH) + 1 )); \
	echo "$$NEW" > VERSION; \
	$(MAKE) _version-sync; \
	echo "Version bumped: $(VERSION) -> $$NEW"

.PHONY: version-set
version-set: ## Set explicit version (V=1.2.3)
	@if [ -z "$(V)" ]; then echo "Usage: make version-set V=1.2.3"; exit 1; fi
	@echo "$(V)" > VERSION
	@$(MAKE) _version-sync
	@echo "Version set: $(VERSION) -> $(V)"

.PHONY: _version-sync
_version-sync: # (internal) propagate VERSION file to all project files
	$(eval NEW_VERSION := $(shell cat VERSION))
	@# backend/pyproject.toml
	@sed -i '' 's/^version = ".*"/version = "$(NEW_VERSION)"/' $(BACKEND)/pyproject.toml
	@# package.json (root)
	@sed -i '' 's/"version": ".*"/"version": "$(NEW_VERSION)"/' package.json
	@# frontend/package.json
	@sed -i '' 's/"version": ".*"/"version": "$(NEW_VERSION)"/' $(FRONTEND)/package.json
	@echo "Synced version $(NEW_VERSION) to all project files"

# ─── Setup ────────────────────────────────────────────────

.PHONY: install
install: install-backend install-frontend ## Install all dependencies

.PHONY: install-backend
install-backend: ## Install Python backend dependencies
	cd $(BACKEND) && uv sync

.PHONY: install-frontend
install-frontend: ## Install frontend dependencies
	cd $(FRONTEND) && pnpm install

# ─── Git Hooks ────────────────────────────────────────────

.PHONY: hooks
hooks: ## Install pre-commit hooks (ruff + eslint)
	cd $(BACKEND) && uv run pre-commit install

.PHONY: hooks-run
hooks-run: ## Run all pre-commit hooks on entire repo
	cd $(BACKEND) && uv run pre-commit run --all-files

.PHONY: hooks-update
hooks-update: ## Update pre-commit hook versions
	cd $(BACKEND) && uv run pre-commit autoupdate

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

# ─── Linting ─────────────────────────────────────────────

.PHONY: lint
lint: lint-backend lint-frontend ## Run all linters

.PHONY: lint-backend
lint-backend: ## Lint backend with ruff
	cd $(BACKEND) && uv run ruff check openmlr/ tests/

.PHONY: lint-frontend
lint-frontend: ## Lint frontend with ESLint
	cd $(FRONTEND) && pnpm lint

.PHONY: lint-fix
lint-fix: lint-fix-backend lint-fix-frontend ## Auto-fix linting issues

.PHONY: lint-fix-backend
lint-fix-backend: ## Auto-fix backend linting issues
	cd $(BACKEND) && uv run ruff check openmlr/ tests/ --fix

.PHONY: lint-fix-frontend
lint-fix-frontend: ## Auto-fix frontend linting issues
	cd $(FRONTEND) && pnpm lint:fix

# ─── Testing ─────────────────────────────────────────────

.PHONY: test
test: test-backend test-frontend test-docs ## Run all tests (backend + frontend + docs)

.PHONY: test-backend
test-backend: ## Run backend pytest suite
	cd $(BACKEND) && uv run pytest tests/ -q

.PHONY: test-frontend
test-frontend: ## Run frontend vitest suite
	cd $(FRONTEND) && pnpm test

.PHONY: test-docs
test-docs: ## Verify docs site builds cleanly
	cd site && npx vitepress build docs

.PHONY: test-coverage
test-coverage: test-coverage-backend test-coverage-frontend ## Run all tests with coverage reports

.PHONY: test-coverage-backend
test-coverage-backend: ## Backend tests with coverage
	cd $(BACKEND) && uv run pytest tests/ --cov --cov-report=term-missing --tb=short -v

.PHONY: test-coverage-frontend
test-coverage-frontend: ## Frontend tests with coverage
	cd $(FRONTEND) && pnpm test --coverage
	cd $(FRONTEND) && pnpm test

# ─── Docker (Development) ──────────────────────────────────
# Default: docker-compose.yml (development with live reload)

.PHONY: dev-up
dev-up: ## Start development stack with live reload
	$(DOCKER_COMPOSE) up -d

.PHONY: dev-build
dev-build: ## Build development images
	$(DOCKER_COMPOSE) build

.PHONY: dev-down
dev-down: ## Stop development stack
	$(DOCKER_COMPOSE) down

.PHONY: dev-logs
dev-logs: ## Tail development logs
	$(DOCKER_COMPOSE) logs -f

.PHONY: dev-clean
dev-clean: ## Stop development stack and remove volumes
	$(DOCKER_COMPOSE) down -v

.PHONY: infra
infra: ## Start only db + redis (for local dev without Docker app)
	$(DOCKER_COMPOSE) up -d db redis

# ─── Docker (Production) ───────────────────────────────────
# Uses docker-compose.prod.yml with pre-built images

PROD_COMPOSE := $(DOCKER_COMPOSE) -f docker-compose.prod.yml

.PHONY: up
up: ## Start production stack (pulls xprilion/openmlr)
	$(PROD_COMPOSE) up -d

.PHONY: down
down: ## Stop production stack
	$(PROD_COMPOSE) down

.PHONY: restart
restart: ## Restart production web + worker
	$(PROD_COMPOSE) up -d --build web worker

.PHONY: logs
logs: ## Tail production logs
	$(PROD_COMPOSE) logs -f

.PHONY: docker-build
docker-build: ## Build production Docker image
	docker build -t openmlr .

.PHONY: docker-run
docker-run: ## Run local production image (requires .env)
	docker run --rm -p $(PORT):$(PORT) --env-file .env openmlr

.PHONY: docker-tag
docker-tag: ## Tag production image for Docker Hub
	docker tag openmlr $(DOCKER_USER)/openmlr:$(VERSION)
	docker tag openmlr $(DOCKER_USER)/openmlr:latest

.PHONY: docker-push
docker-push: ## Push production tags to Docker Hub
	docker push $(DOCKER_USER)/openmlr:$(VERSION)
	docker push $(DOCKER_USER)/openmlr:latest

.PHONY: docker-publish
docker-publish: docker-build docker-tag docker-push ## Build, tag, and push to Docker Hub

# ─── Docs ─────────────────────────────────────────────────

.PHONY: docs-install
docs-install: ## Install docs site dependencies
	cd site && npm install

.PHONY: docs-dev
docs-dev: ## Preview docs locally (port 4000)
	cd site && npx vitepress dev docs --port 4000

.PHONY: docs-docker
docs-docker: ## Run docs in Docker (port 4000)
	$(DOCKER_COMPOSE) --profile docs up -d docs

.PHONY: docs-build
docs-build: ## Build docs to site/docs/.vitepress/dist
	cd site && npx vitepress build docs

# ─── Logo Generation ─────────────────────────────────────

.PHONY: logo
logo: ## Generate all logo sizes from assets/full-logo.png
	@echo "Generating logo sizes from $(LOGO_SRC)..."
	@mkdir -p $(FRONTEND)/public site/docs/public
	@# Favicons for webapp
	sips -z 16 16 $(LOGO_SRC) --out $(FRONTEND)/public/favicon-16x16.png
	sips -z 32 32 $(LOGO_SRC) --out $(FRONTEND)/public/favicon-32x32.png
	sips -z 180 180 $(LOGO_SRC) --out $(FRONTEND)/public/apple-touch-icon.png
	sips -z 192 192 $(LOGO_SRC) --out $(FRONTEND)/public/logo-192.png
	sips -z 512 512 $(LOGO_SRC) --out $(FRONTEND)/public/logo-512.png
	@# Generate .ico from 32x32 (copy as favicon.ico for browsers)
	cp $(FRONTEND)/public/favicon-32x32.png $(FRONTEND)/public/favicon.ico
	@# Logo for header/nav
	sips -z 64 64 $(LOGO_SRC) --out $(FRONTEND)/public/logo-64.png
	@# OG image (1200x630 for social sharing - pad/crop as needed)
	sips -z 630 630 $(LOGO_SRC) --out $(FRONTEND)/public/og-image-square.png
	sips -p 630 1200 $(FRONTEND)/public/og-image-square.png --out $(FRONTEND)/public/og-image.png
	rm $(FRONTEND)/public/og-image-square.png
	@# Copy to docs site
	cp $(FRONTEND)/public/favicon-16x16.png site/docs/public/
	cp $(FRONTEND)/public/favicon-32x32.png site/docs/public/
	cp $(FRONTEND)/public/favicon.ico site/docs/public/
	cp $(FRONTEND)/public/apple-touch-icon.png site/docs/public/
	cp $(FRONTEND)/public/logo-64.png site/docs/public/
	cp $(FRONTEND)/public/logo-192.png site/docs/public/
	cp $(FRONTEND)/public/logo-512.png site/docs/public/
	cp $(FRONTEND)/public/og-image.png site/docs/public/
	@# Full logo for README
	cp $(LOGO_SRC) assets/logo.png
	sips -z 200 200 $(LOGO_SRC) --out assets/logo-200.png
	@echo "Done! Logo sizes generated in frontend/public/, site/docs/public/, and assets/"

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
