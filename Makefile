.PHONY: dev dev-down test lint build airgap-package clean migrate

# --- Development ---
dev:
	docker compose up --build -d

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

dev-restart:
	docker compose down && docker compose up --build -d

# --- Database ---
migrate:
	docker compose exec postgres psql -U vaultmind -d vaultmind -f /docker-entrypoint-initdb.d/V001__initial_schema.sql

# --- Testing ---
test-ingestion:
	cd services/ingestion-worker && python -m pytest tests/ -v --asyncio-mode=auto

test-query:
	cd services/query-api && python -m pytest tests/ -v --asyncio-mode=auto

test:
	$(MAKE) test-ingestion
	$(MAKE) test-query

# --- Linting ---
lint-python:
	cd services/ingestion-worker && ruff check . && ruff format --check .
	cd services/query-api && ruff check . && ruff format --check .
	cd cli && ruff check . && ruff format --check .

lint-go:
	cd services/file-sentinel && go vet ./...

lint: lint-python lint-go

# --- Build ---
build-sentinel:
	cd services/file-sentinel && docker build -t vaultmind/file-sentinel:latest .

build-ingestion:
	cd services/ingestion-worker && docker build -t vaultmind/ingestion-worker:latest .

build-query:
	cd services/query-api && docker build -t vaultmind/query-api:latest .

build: build-sentinel build-ingestion build-query

# --- Air-Gapped Packaging ---
airgap-package:
	bash deploy/scripts/airgap-package.sh

airgap-deploy:
	bash deploy/scripts/airgap-deploy.sh

# --- Cleanup ---
clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
