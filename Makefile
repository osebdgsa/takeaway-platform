UV ?= uv

.PHONY: install run test lint fmt migrate revision seed up down logs clean \
	seed-docker frontend-install frontend-build frontend-dev openapi dev dev-down

DEV_COMPOSE := docker compose -f docker-compose.yml -f compose.dev.yml

install:
	$(UV) sync

run:
	$(UV) run uvicorn app.main:app --reload --port 8000

test:
	$(UV) run pytest $(ARGS)

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

fmt:
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

migrate:
	$(UV) run alembic upgrade head

revision:
	$(UV) run alembic revision --autogenerate -m "$(m)"

# Regenerate the committed OpenAPI schema after changing routes or schemas.
openapi:
	$(UV) run python -m scripts.export_openapi

seed:
	$(UV) run python -m scripts.seed

seed-docker:
	docker compose exec -T api python -m scripts.seed

up:
	docker compose up --build -d

down:
	docker compose down

# Development mode: backend reload + Vite HMR in containers (no nginx).
# Ctrl-C stops it; then run `make up` to return to the production-like stack.
dev:
	$(DEV_COMPOSE) up --build db api frontend

dev-down:
	$(DEV_COMPOSE) down

logs:
	docker compose logs -f api

# --- frontend ---------------------------------------------------------------
# The SPA is built and served by Nginx inside the compose stack. These targets
# are only for local frontend development against the running stack.

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

# Vite dev server on :5173, proxying /api to the compose stack on :8080.
frontend-dev:
	cd frontend && npm run dev

clean:
	rm -rf .venv .pytest_cache .ruff_cache htmlcov .coverage __pycache__
