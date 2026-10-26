PYTHON ?= python3
VENV := .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python

.PHONY: install run test lint fmt migrate revision seed up down logs clean \
	seed-docker frontend-install frontend-build frontend-dev openapi

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

run:
	$(VENV)/bin/uvicorn app.main:app --reload --port 8000

test:
	$(PY) -m pytest $(ARGS)

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

fmt:
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

migrate:
	$(VENV)/bin/alembic upgrade head

revision:
	$(VENV)/bin/alembic revision --autogenerate -m "$(m)"

# Regenerate the committed OpenAPI schema after changing routes or schemas.
openapi:
	$(PY) -m scripts.export_openapi

seed:
	$(PY) -m scripts.seed

seed-docker:
	docker compose exec -T api python -m scripts.seed

up:
	docker compose up --build -d

down:
	docker compose down

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
	rm -rf $(VENV) .pytest_cache .ruff_cache htmlcov .coverage __pycache__
