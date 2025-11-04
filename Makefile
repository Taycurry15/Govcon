.PHONY: help install dev-install sync format lint mypy tests coverage clean docker-up docker-down docker-logs init-db migrate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	uv pip install -e .

dev-install: ## Install development dependencies
	uv pip install -e ".[dev,docs]"

sync: ## Sync all dependencies (recommended for development)
	uv sync --all-extras

format: ## Format code with ruff and black
	uv run ruff format .
	uv run black src/ tests/

format-check: ## Check code formatting
	uv run ruff format --check .
	uv run black --check src/ tests/

lint: ## Run linter
	uv run ruff check src/ tests/

mypy: ## Run type checker
	uv run mypy src/

tests: ## Run tests
	uv run pytest tests/ -v

tests-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=govcon --cov-report=html --cov-report=term

coverage: ## Generate coverage report
	uv run pytest tests/ --cov=govcon --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

check: format-check lint mypy tests ## Run all checks (format, lint, type, tests)

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-up: ## Start all Docker services
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-rebuild: ## Rebuild and restart Docker services
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

init-db: ## Initialize database
	uv run python -m govcon.cli init-db

migrate: ## Run database migrations
	uv run alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	uv run alembic revision --autogenerate -m "$(MESSAGE)"

discover: ## Run discovery agent (usage: make discover DAYS=7)
	uv run python -m govcon.cli discover --days-back $(or $(DAYS),7)

analyze: ## Analyze opportunity (usage: make analyze ID=opp-123)
	uv run python -m govcon.cli analyze-opportunity $(ID)

proposal: ## Generate proposal (usage: make proposal ID=opp-123)
	uv run python -m govcon.cli generate-proposal $(ID)

price: ## Generate pricing (usage: make price ID=opp-123)
	uv run python -m govcon.cli price-proposal $(ID)

export: ## Export submission package (usage: make export ID=opp-123)
	uv run python -m govcon.cli export-submission $(ID)

shell: ## Start Python shell with project context
	uv run python

docs-serve: ## Serve documentation locally
	uv run mkdocs serve

docs-build: ## Build documentation
	uv run mkdocs build

docs-deploy: ## Deploy documentation to GitHub Pages
	uv run mkdocs gh-deploy --force

run-api: ## Run API server locally
	uv run uvicorn govcon.api.main:app --reload --host 0.0.0.0 --port 8000

run-worker: ## Run background worker
	uv run python -m govcon.worker

setup: sync docker-up init-db ## Complete setup (sync deps, start docker, init db)
	@echo "✅ Setup complete! Run 'make run-api' to start the API server."

reset: docker-down clean docker-up init-db ## Reset everything (clean slate)
	@echo "✅ Reset complete! All data cleared and services restarted."
