# PythonTrio Development Makefile
# Run 'make' or 'make help' to see all available commands

.PHONY: help install install-dev install-hooks \
        db-start db-stop db-reset db-migrate db-revision db-downgrade db-history \
        run dev start serve mcp-local \
        lint lint-fix format check \
        test test-unit test-integration test-cov test-fast \
        setup setup-ci clean

# Default target
.DEFAULT_GOAL := help

# Variables (can be overridden: make dev PORT=3000)
PYTHON := venv/bin/python
HOST := 0.0.0.0
PORT := 8000
DOCKER_COMPOSE := docker compose
DB_SERVICE := db_live_demo
COVERAGE_DIR := htmlcov

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "PythonTrio Development Commands"
	@echo "================================"
	@echo ""
	@echo "Usage: make [target] [VAR=value]"
	@echo ""
	@echo "Variables:"
	@echo "  HOST           Server host (default: $(HOST))"
	@echo "  PORT           Server port (default: $(PORT))"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# Installation
# ============================================================================

install: ## Install production dependencies
	$(PYTHON) -m pip install -r requirements.txt

install-dev: ## Install all dependencies (prod + dev)
	$(PYTHON) -m pip install -r requirements-dev.txt

install-hooks: ## Set up pre-commit hooks
	$(PYTHON) -m pre_commit install

# ============================================================================
# Database (Docker + Alembic)
# ============================================================================

db-start: ## Start PostgreSQL via docker-compose
	$(DOCKER_COMPOSE) up -d $(DB_SERVICE)
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 2
	@echo "PostgreSQL is running on port 5432"

db-stop: ## Stop PostgreSQL container
	$(DOCKER_COMPOSE) stop $(DB_SERVICE)

db-reset: ## Reset database (remove volume, start fresh)
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d $(DB_SERVICE)
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 2
	@echo "Database reset complete"

db-migrate: ## Run alembic upgrade head
	$(PYTHON) -m alembic upgrade head

db-revision: ## Create new migration (usage: make db-revision msg="Add users table")
	@if [ -z "$(msg)" ]; then \
		echo "Error: Please provide a migration message"; \
		echo "Usage: make db-revision msg=\"Your migration message\""; \
		exit 1; \
	fi
	$(PYTHON) -m alembic revision --autogenerate -m "$(msg)"

db-downgrade: ## Rollback one migration
	$(PYTHON) -m alembic downgrade -1

db-history: ## Show migration history
	$(PYTHON) -m alembic history --verbose

# ============================================================================
# Running
# ============================================================================

run: ## Production mode (no reload)
	$(PYTHON) -m uvicorn app.main:app --host $(HOST) --port $(PORT)

dev: ## Development mode (auto-reload) with price sync running in background
	$(PYTHON) scripts/sync_prices.py & sync_pid=$$!; \
	$(PYTHON) -m uvicorn app.main:app --host $(HOST) --port $(PORT) --reload; \
	kill $$sync_pid 2>/dev/null || true

serve: ## Run server (serves both REST and MCP at /mcp)
	$(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

mcp-local: ## Run MCP server standalone (stdio mode for local testing)
	$(PYTHON) -m app.mcp_server

start: db-start dev ## Start database and app (dev mode)

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run ruff check
	$(PYTHON) -m ruff check app tests

lint-fix: ## Run ruff check with auto-fix
	$(PYTHON) -m ruff check app tests --fix

format: ## Format code with ruff
	$(PYTHON) -m ruff format app tests

check: ## Run lint + format-check (CI-friendly)
	$(PYTHON) -m ruff check app tests
	$(PYTHON) -m ruff format app tests --check

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests with coverage
	$(PYTHON) -m pytest

test-unit: ## Run unit tests only
	$(PYTHON) -m pytest tests/unit -v

test-integration: ## Run integration tests only
	$(PYTHON) -m pytest tests/integration -v

test-cov: ## Generate HTML coverage report
	$(PYTHON) -m pytest --cov-report=html
	@echo "Coverage report generated in $(COVERAGE_DIR)/"

test-fast: ## Quick test run without coverage
	$(PYTHON) -m pytest --no-cov -q

# ============================================================================
# Utilities
# ============================================================================

setup: install-dev install-hooks db-start db-migrate ## Full bootstrap: install + hooks + db + migrate
	@echo ""
	@echo "Setup complete! Run 'make dev' to start the development server."

setup-ci: install-dev ## CI setup (no hooks or db)
	@echo "CI setup complete"

clean: ## Remove caches and generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf $(COVERAGE_DIR) 2>/dev/null || true
	@echo "Cleaned up cache and generated files"
