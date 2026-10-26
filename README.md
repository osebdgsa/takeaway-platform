# Takeaway Platform

A small takeaway platform: customers browse restaurants and menus, place orders
and track them; staff with the internal **admin** role manage menus and advance
order statuses. It ships with a React console for manual testing, which is built
by Nginx and served from the same origin as the API.

Backend: **FastAPI**, **PostgreSQL**, **SQLAlchemy 2 + Alembic**, **Pydantic v2**,
**JWT auth**, **Docker Compose** and **Nginx** in front of **Uvicorn**.
Dependencies are managed with **uv** (`pyproject.toml` + `uv.lock`).
Frontend: **React 18 + TypeScript + Vite**.

---

## Contents

- [Requirements mapping](#requirements-mapping)
- [Quick start](#quick-start)
- [If something does not start](#if-something-does-not-start)
- [Demo accounts](#demo-accounts)
- [Frontend console](#frontend-console)
- [Hot reload (development)](#hot-reload-development)
- [Architecture](#architecture)
- [Data model](#data-model)
- [Order lifecycle](#order-lifecycle)
- [Authentication & authorisation](#authentication--authorisation)
- [API reference](#api-reference)
- [OpenAPI schema](#openapi-schema)
- [Running locally without Docker](#running-locally-without-docker)
- [Dependency management (uv)](#dependency-management-uv)
- [Migrations](#migrations)
- [Tests](#tests)
- [Design decisions & trade-offs](#design-decisions--trade-offs)
- [Possible next steps](#possible-next-steps)

---

## Requirements mapping

| Brief | Where it lives | How to check |
| --- | --- | --- |
| Customers browse restaurants & menus | `GET /api/restaurants`, `GET /api/restaurants/{id}/menu-items` (public, paginated) | open `/restaurants`, or `curl` without a token |
| Place orders | `POST /api/orders` — validates restaurant/item ownership, availability, duplicates; snapshots prices; total computed server-side | UI basket → “Place order”, or the `curl` below |
| Track order status | `GET /api/orders/{id}` + `GET /api/orders`; statuses `pending → accepted → out_for_delivery → delivered`, plus `cancelled` | `/orders`, or the Guard lab |
| Staff/admin manages menus | `POST/PATCH/DELETE` on `/api/restaurants`, `/api/restaurants/{id}/menu-items`, `/api/menu-items/{id}`, all behind `AdminUser` | sign in as admin → `/admin`; as customer the same calls return `403` |
| Staff/admin updates order status | `PATCH /api/orders/{id}/status`, admin-only, enforced by `ALLOWED_TRANSITIONS` (illegal jumps → `409`) | admin `/orders` buttons; customer → `403` |
| FastAPI | `app/main.py`, `app/controllers/` | `/docs` |
| PostgreSQL | `postgres:16-alpine`, `psycopg2`, migrations in Alembic | `docker compose exec db psql -U takeaway -d takeaway -c '\dt'` |
| SQLAlchemy + Alembic | `app/models/`, `app/repositories/`, single initial revision applied by the entrypoint | `docker compose exec api alembic current` → `4071c36c4d9f (head)` |
| Pydantic request/response models | `app/schemas/`, response models on all business endpoints | OpenAPI schemas at `/api/openapi.json` |
| JWT auth | `PyJWT` in `app/core/security.py`, `OAuth2PasswordBearer` in `app/controllers/deps.py` | `POST /api/auth/login`, then `/api/auth/me` |
| Docker & docker-compose | `Dockerfile`, `docker-compose.yml` (db + api + nginx, healthchecks, named volume, non-root user) | `docker compose ps` |
| Nginx in front of Uvicorn | `nginx/default.conf` upstream `api:8000`; Nginx is the only port published to all interfaces | `docker compose exec nginx cat /etc/nginx/conf.d/default.conf` |

Two notes on interpretation:

- The brief calls internal staff “admin”, so there are exactly two roles:
  `customer` and `admin`. Public sign-up can only create `customer`.
- No `/v1` prefix: this is one unversioned API. See
  [Architecture](#architecture) for the reasoning.

---

## Quick start

**Prerequisites:** Docker with Compose v2 (`docker compose version`), ~2 GB of
free disk space, and ports `8080` (and optionally `8000` / `5432`) free. Python,
Node and Postgres are **not** required on the host — everything runs in
containers.

```bash
git clone https://github.com/osebdgsa/takeaway-platform.git
cd takeaway-platform

cp .env.example .env          # set SECRET_KEY in anything but local dev
docker compose up --build -d  # first build: a few minutes (pulls base images)
docker compose exec -T api python -m scripts.seed
```

That is the whole install. `docker compose ps` should show `db` and `api`
healthy and `nginx` up, and the seed step prints the demo logins. Nothing else
needs to be installed, no manual migration step: the API container waits for
Postgres, runs `alembic upgrade head`, then starts Uvicorn.

| What | URL |
| --- | --- |
| React console | http://localhost:8080/ |
| API through Nginx | http://localhost:8080/api |
| Swagger UI | http://localhost:8080/docs |
| OpenAPI JSON | http://localhost:8080/api/openapi.json |
| Health | http://localhost:8080/health |

The first build takes a few minutes: it pulls the Python, Node and Postgres base
images and installs both dependency sets. Later starts take seconds, and seeding
takes about two seconds. The stack is exercised end-to-end as part of this work:
build → migrations → seed → `/health` → order placement.

Nginx builds the SPA from `frontend/` and proxies `/api`, `/docs`, `/redoc` and
`/health` to the API container, so the browser only ever talks to one origin
(no CORS in production).

> **Port notes.** The supported entrypoint is Nginx on `8080`. The API (`:8000`)
> and PostgreSQL (`:5433` here, `5432` by default) are bound to `127.0.0.1` only,
> as debugging conveniences — they are not reachable from other machines. The
> non-default `POSTGRES_PORT` avoids clashing with a local Postgres; the API
> always reaches the database at `db:5432` inside the Compose network. Change
> `HTTP_PORT` / `POSTGRES_PORT` / `API_PORT` in `.env` before `up` if those are
> taken.

### If something does not start

```bash
docker compose ps                 # db/api healthy, nginx up?
docker compose logs -f api        # migration/auth errors show up here
docker compose down -v            # wipe DB volume and start over
```

| Symptom | Cause / fix |
| --- | --- |
| `port is already allocated` on 8080/8000/5432 | Something else is bound. Set `HTTP_PORT=8081` (etc.) in `.env`, or stop the other service. |
| `up` hangs on `Waiting for database` | Postgres failed to start; check `docker compose logs db`. If you changed `POSTGRES_*` after the volume was created, the old credentials persist — `docker compose down -v`. |
| Login fails with 401 after `up` | The seed step was skipped. Run `docker compose exec -T api python -m scripts.seed`. |
| Console loads but API calls fail | Open `/health`; if it is not `{"status":"ok",...}`, the API container is unhealthy — check `docker compose logs api`. |
| First build takes minutes | Expected: it pulls Python and Node base images and runs `uv sync` + `npm ci`. Later starts are seconds. |

The `curl` example below uses [`jq`](https://jqlang.github.io/jq/); without it,
read `access_token` from the login response by eye or with `python -c`.

```bash
# place an order as the seeded customer
TOKEN=$(curl -s -X POST localhost:8080/api/auth/login \
  -d 'username=customer@example.com&password=customer12345' | jq -r .access_token)

RESTAURANT=$(curl -s localhost:8080/api/restaurants | jq -r '.items[0].id')
ITEM=$(curl -s "localhost:8080/api/restaurants/$RESTAURANT/menu-items" | jq -r '.items[0].id')

curl -s -X POST localhost:8080/api/orders \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"restaurant_id\":\"$RESTAURANT\",\"items\":[{\"menu_item_id\":\"$ITEM\",\"quantity\":2}]}" | jq
```

---

## Demo accounts

`docker compose exec -T api python -m scripts.seed` (or `make seed-docker`) is
idempotent and creates these accounts plus a restaurant with three menu items:

| Role | Email | Password | What it demonstrates |
| --- | --- | --- | --- |
| admin | `admin@example.com` | `admin12345` | Full access: create restaurants/menu items, advance any order |
| customer | `customer@example.com` | `customer12345` | Own orders only; admin endpoints return `403` |
| customer | `customer2@example.com` | `customer212345` | Cannot read customer 1's orders (`404`, not `403`) |
| disabled | `blocked@example.com` | `blocked12345` | Login is refused with `403` |

The login page lists these accounts with a **Use** button that fills the form.

---

## Frontend console

`frontend/` is a small React + TypeScript SPA used to exercise the API by hand:

| Page | Purpose |
| --- | --- |
| `/login` | Sign in / register, plus one-click demo credentials |
| `/restaurants` | Browse restaurants and menus, build a basket, place an order |
| `/orders` | Track orders; customers cancel pending orders, admins advance statuses |
| `/admin` | Admin-only restaurant and menu management (customers see a 403 screen) |
| `/guard-lab` | Runs real HTTP calls and shows expected vs actual status codes |

**Guard lab** is the fastest way to see the guards. Sign in as a customer, open
`/guard-lab`, and press the buttons: the page performs genuine requests and
tabulates `expected` vs `actual`, for example

- `GET /api/orders` with no token / a garbage token → `401`
- login as the disabled account → `403`
- `POST /api/restaurants` and `PATCH /api/orders/{id}/status` as a customer → `403`
- reading another customer's order id → `404` (owners and admins get `200`)

The same holds outside the UI — `curl` with a customer token gets the same
`403`, because authorisation is enforced by FastAPI dependencies, not by the
SPA.

## Hot reload (development)

The default `docker compose up` is **production-like**: code is baked into the
images, so nothing reloads. That is intentional, but it is not what you want
while editing. There are two dev workflows:

| Workflow | Backend reload | Frontend HMR | UI URL |
| --- | --- | --- | --- |
| `docker compose up` (default) | no | no | :8080 |
| `make dev` (Docker only) | yes (Uvicorn `--reload`) | yes (Vite) | :5173 |
| `make run` (host Python) | yes | no | API only on :8000 |

### Everything in Docker

```bash
make dev        # db + api (reload) + Vite dev server, Ctrl-C to stop
make dev-down   # stop, keeping the database volume
make up         # back to the production-like stack on :8080
```

`compose.dev.yml` is an **opt-in override** — plain `docker compose up` is
unaffected. It mounts `./app` into the API container and switches the command to
Uvicorn with `--reload`, adds a `frontend` service running Vite with polling
enabled (reliable with Docker Desktop bind mounts), and leaves Nginx out so
there is only one UI on :5173. The Vite server proxies `/api` to the API
container, so cookies/tokens and relative URLs behave the same as through Nginx.

Verified: touching `app/main.py` restarts the reloader, and editing
`frontend/src/pages/LoginPage.tsx` produced `[vite] hmr update …` with the DOM
updated in place (no page reload).

### Host tools (optional)

```bash
make frontend-install
make frontend-dev        # Vite on :5173, proxies /api to the compose stack on :8080
make frontend-build      # type-check + production bundle in frontend/dist
```

`make frontend-dev` expects the Compose stack to be up. To point it at a backend
started on the host with `make run` instead, override the proxy target:

```bash
VITE_API_TARGET=http://localhost:8000 make frontend-dev
```

After changing `frontend/`, the Nginx image only picks the build up on rebuild:

```bash
docker compose up --build -d nginx
```


---

## Architecture

```
browser ──► Nginx :8080 ──┬─► static React build (frontend/dist)
                          └─► Uvicorn :8000 ──► FastAPI app ──► SQLAlchemy ──► PostgreSQL
                                                   │
                                                   └── Alembic migrations run by the container entrypoint
```

Inside the app, each layer has one job and only depends downwards:

| Layer | Package | Responsibility |
| --- | --- | --- |
| HTTP controllers | `app/controllers/` | routing, status codes, request/response schemas, dependency wiring |
| Services | `app/services/` | business rules: totals, state machine, ownership, conflicts |
| Repositories | `app/repositories/` | SQL queries; no business logic |
| Models | `app/models/` | SQLAlchemy mappings, constraints, relationships |

```
app/
├── controllers/        # HTTP layer (routes live here, not in app/api)
│   ├── auth.py
│   ├── restaurants.py  # browse + admin CRUD + nested menu create
│   ├── menu_items.py
│   ├── orders.py
│   ├── deps.py         # DB session, current user, admin guard, pagination
│   └── router.py
├── services/           # business rules
├── repositories/       # persistence
├── models/             # ORM mappings + enums + state machine table
├── schemas/            # Pydantic request/response models
├── core/               # settings, JWT/password hashing, domain exceptions
├── db/                 # Base, engine, session factory
└── main.py             # app assembly, health check, exception handlers
alembic/                # migration environment + versions
openapi.json            # committed OpenAPI 3.1 schema (generated, see below)
pyproject.toml + uv.lock # dependencies and the exact resolved lockfile
scripts/seed.py         # idempotent demo data
tests/                  # API tests against an in-memory DB (incl. OpenAPI drift check)
frontend/               # React + TypeScript console (built into the Nginx image)
docker/                 # api + nginx Dockerfiles
nginx/default.conf      # SPA fallback + /api, /docs, /redoc, /health proxies
```

There is deliberately **no `/v1` URL segment**: this is a single, unversioned
consumer API. If breaking changes ever need a parallel API, a new prefix can be
introduced then; versioning everything up front only adds noise.

---

## Data model

```
users ──1:N──► orders ──1:N──► order_items ──N:1──► menu_items ──N:1──► restaurants
  │                                                                    ▲
  └──────────────────────── owner_id ──────────────────────────────────┘
```

| Table | Notes |
| --- | --- |
| `users` | unique lower-cased email, bcrypt hash, `role` (`customer`/`admin`), `is_active` |
| `restaurants` | owner (admin who created it), name, address, optional phone/cuisine |
| `menu_items` | price `NUMERIC(10,2)`, `is_available`; deleting a restaurant cascades its menu |
| `orders` | status, `total_amount`, `ordered_at` |
| `order_items` | `quantity`, `unit_price` **snapshot**, unique per `(order, menu_item)`, `quantity > 0` CHECK |

Money is `NUMERIC`, never floats, and is serialised as a decimal **string**
(`"30.00"`) so clients never lose precision.

`menu_item_id` on `order_items` is nullable with `ON DELETE SET NULL`: deleting a
menu item must not destroy order history.

---

## Order lifecycle

```
pending ──► accepted ──► out_for_delivery ──► delivered
   │            │
   └────────────┴──────► cancelled
```

- Enforced in `ALLOWED_TRANSITIONS` (`app/models/enums.py`); illegal jumps return
  `409 Conflict` (e.g. `pending → delivered`).
- Same-state updates are idempotent (`pending → pending` is a no-op).
- Customers may cancel their own order only while it is `pending`.
- Admins cancel through the status endpoint (`accepted → cancelled` allowed).
- Only admins may call the status endpoint; only the owner (or an admin) may read
  an order. A non-owner gets `404`, not `403`, so order ids cannot be probed.

---

## Authentication & authorisation

- `POST /api/auth/register` always creates a **customer**. There is no public way
  to self-assign `admin`; the field is rejected (`422`). The first admin comes
  from `scripts/seed.py`.
- `POST /api/auth/login` accepts `application/x-www-form-urlencoded`
  (`username`/`password`, the OAuth2 password flow) and returns a bearer JWT with
  `sub` (user id), `role`, `iat`, `exp`.
- Every protected request re-loads the user from the database, so disabling or
  demoting an account takes effect immediately — the token's role claim is never
  trusted for authorisation.
- Passwords are bcrypt-hashed. Login uses the same error for unknown email and
  wrong password to avoid account enumeration.
- Admin-only routes depend on `AdminUser`, which returns `403` for customers.

---

## API reference

All business endpoints below are under `/api`. Auth is `Authorization: Bearer <token>`.

| Method | Path | Access | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | public | Create customer account |
| `POST` | `/auth/login` | public | Get JWT |
| `GET` | `/auth/me` | any user | Current account |
| `GET` | `/restaurants` | public | Paginated restaurant list |
| `GET` | `/restaurants/{restaurant_id}` | public | Restaurant detail |
| `GET` | `/restaurants/{restaurant_id}/menu-items` | public | Paginated menu |
| `POST` | `/restaurants` | admin | Create restaurant |
| `PATCH` | `/restaurants/{restaurant_id}` | admin | Update restaurant |
| `DELETE` | `/restaurants/{restaurant_id}` | admin | Delete restaurant + menu |
| `POST` | `/restaurants/{restaurant_id}/menu-items` | admin | Add menu item |
| `GET` | `/menu-items/{menu_item_id}` | public | Menu item detail |
| `PATCH` | `/menu-items/{menu_item_id}` | admin | Update menu item |
| `DELETE` | `/menu-items/{menu_item_id}` | admin | Delete menu item |
| `POST` | `/orders` | customer/admin | Place order |
| `GET` | `/orders` | any user | Own orders (all orders for admin) |
| `GET` | `/orders/{order_id}` | owner/admin | Track order |
| `POST` | `/orders/{order_id}/cancel` | owner | Cancel pending order |
| `PATCH` | `/orders/{order_id}/status` | admin | Advance status |

Operational endpoints live outside `/api`: `GET /health` (checks the database),
`GET /docs`, `GET /redoc` and `GET /api/openapi.json`.

List endpoints take `limit` (1–100, default 20) and `offset` (default 0) and
return `{items, total, limit, offset}`.

Error shape is `{"detail": ...}`: a string for application errors, and FastAPI's
list of field errors for `422` validation failures.

| Status | When |
| --- | --- |
| `401` | missing/invalid/expired token, bad credentials |
| `403` | authenticated but not an admin, or a disabled account |
| `404` | resource missing, or order not owned by caller |
| `409` | duplicate email, unavailable item, illegal status transition, deleting a restaurant that has orders |
| `422` | schema validation or a business validation failure (unknown/foreign item, duplicate lines) |

---

## OpenAPI schema

The schema is generated from the routes and Pydantic models — there is no
hand-written spec to drift out of sync:

| Where | What |
| --- | --- |
| `openapi.json` (repo root) | committed OpenAPI 3.1 document, 12 paths / 22 schemas |
| `GET /api/openapi.json` | the same document, generated live by the running app |
| `GET /docs` | Swagger UI with the OAuth2 password flow wired up (“Authorize”) |
| `GET /redoc` | ReDoc rendering |

After changing a route or a schema, regenerate and commit the file:

```bash
make openapi
```

`tests/test_openapi.py` asserts the committed `openapi.json` matches
`app.openapi()`, so a stale spec fails the test run instead of shipping quietly.
Generate it from the same code the server runs, never by editing JSON by hand.

---

## Running locally without Docker

Requires Python 3.10+, [uv](https://docs.astral.sh/uv/) and a running PostgreSQL
(`make` is convenient but optional — the equivalent `uv run …` commands are
shown in comments). `uv sync` creates `.venv` from `uv.lock`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # install uv, if needed

uv sync             # production + dev dependencies into .venv (no activation needed)

cp .env.example .env
# .env points DATABASE_URL at localhost:5432

make migrate        # uv run alembic upgrade head
make seed           # optional demo data
make run            # uv run uvicorn --reload on :8000
```

Every `make` target wraps `uv run`, so the virtualenv does not need activating.
The app starts **without** migrations applied but every data endpoint will fail;
run `make migrate` first. `AUTO_CREATE_TABLES=true` exists as an escape hatch for
throwaway local databases only.

---

## Dependency management (uv)

| File | Role |
| --- | --- |
| `pyproject.toml` | direct dependencies, dev group, tool config |
| `uv.lock` | exact resolved versions + hashes for every transitive package |
| `Dockerfile` | `uv sync --frozen --no-dev` from the lockfile only |

```bash
uv add httpx                     # add a runtime dependency
uv add --dev respx               # add a dev dependency
uv remove httpx
uv lock --check                  # fail if pyproject and uv.lock disagree
uv sync                          # create/refresh .venv from the lock
uv run <command>                 # run inside the project environment
```

Rules of thumb:

- `uv.lock` is **committed**; the image builds with `--frozen`, so a lock that
  does not match `pyproject.toml` fails the build rather than silently
  re-resolving.
- The Docker image installs with `--no-dev`; tests and ruff stay on the host/CI.
- `[tool.uv] package = false` — this is an application, so uv syncs dependencies
  without trying to build and install the project itself.
- uv itself is not required on a machine that only runs `docker compose up`.

---

## Migrations

```bash
make migrate                       # upgrade to head
make revision m="add reviews"      # autogenerate a new revision
uv run alembic downgrade -1        # roll back one revision
uv run alembic check               # fail if models drift from migrations
```

The container entrypoint waits for PostgreSQL, runs `alembic upgrade head`, then
execs Uvicorn — migrations are never skipped in a deployment.

The initial revision (`alembic/versions/4071c36c4d9f_initial_schema.py`) was
autogenerated with `alembic revision --autogenerate`, verified with
upgrade → downgrade → upgrade, and `alembic check` reports no drift against the
running PostgreSQL 16 container.

---

## Tests

```bash
make test                       # uv run pytest — 43 tests, ~1s
make test ARGS="--cov=app"      # with coverage (96% lines)
uv run pytest tests/test_orders.py -q   # single file
```

- Tests run on an in-memory SQLite database with a single shared connection, and
  override the `get_db` dependency, so they need no running PostgreSQL.
- Models use portable types (`Uuid`, non-native `Enum`) so the same mappings work
  on PostgreSQL and SQLite.
- bcrypt cost is lowered via `BCRYPT_ROUNDS=4` in the test environment.
- Covered: registration/login/JWT failures, disabled accounts, RBAC on every
  admin route, pagination, price snapshots, total calculation, cross-restaurant
  items, unavailable items, duplicate lines, ownership isolation, the full status
  workflow and rejected transitions.

---

## Design decisions & trade-offs

- **uv for Python dependencies.** One tool resolves, locks and installs; the
  commit contains `uv.lock`, so builds are reproducible and the Docker image
  installs with `--frozen` instead of resolving at build time. `requirements.txt`
  and pip were removed rather than kept as a second source of truth.
- **Uvicorn, not Gunicorn.** FastAPI is ASGI-native; Uvicorn is the supported
  server. Gunicorn's `UvicornWorker` is the scaling option if multiple processes
  are ever needed — but one process plus `async` I/O is plenty here, and the
  container can be horizontally scaled instead. Nginx terminates the client
  connection and forwards proxy headers.
- **Synchronous SQLAlchemy with `def` endpoints.** SQLAlchemy 2's sync API is
  simpler to read and its session lifecycle is easier to get right than async
  sessions. FastAPI runs `def` endpoints in its threadpool, so the event loop is
  not blocked. Every endpoint is consistently synchronous rather than a mix.
- **Prices snapshotted onto order lines.** Menu edits must never change the
  historical total; totals are computed server-side and never accepted from the
  client.
- **Role read from the database per request.** Tokens carry a role claim for
  convenience, but authorisation uses the current DB row, so revocation is
  immediate.
- **404 instead of 403 for another customer's order.** Avoids leaking which order
  ids exist.
- **`DELETE /restaurants/{id}` refuses when orders exist (409).** The FK on
  `orders.restaurant_id` is `RESTRICT`, so a restaurant with order history is
  rejected cleanly instead of cascading history away; the menu would have
  cascaded, order lines survive with `menu_item_id` set to `NULL`.
- **Row locks on status changes.** `update_status` and `cancel` read the order
  `FOR UPDATE` (PostgreSQL; SQLite ignores it, so tests are unaffected), so two
  concurrent admin PATCHes cannot race a stale transition check.
- **Tokens in `sessionStorage`, 30-minute expiry.** The SPA keeps the token for
  the tab's lifetime only, limiting what a hypothetical XSS could steal; with no
  refresh-token flow yet this means re-signing in after closing the tab.
- **Non-native enums (VARCHAR + app-level validation).** Portable across
  PostgreSQL and SQLite and avoids painful `ALTER TYPE` migrations. A CHECK
  constraint can be added later if DB-level enforcement is preferred.
- **No `/v1` prefix.** See [Architecture](#architecture).
- **OAuth2 password flow as form data.** It is the standard for `OAuth2PasswordBearer`
  and works directly with Swagger's “Authorize” button.

---

## Possible next steps

- Refresh tokens + server-side revocation list (or httpOnly-cookie sessions).
- Rate-limit login and order creation (Nginx `limit_req` or app middleware).
- `Idempotency-Key` support on `POST /orders` to make retries safe.
- Scope menus per restaurant owner (staff sub-role) rather than one global admin.
- Cursor-based pagination and menu filtering (`?available=true`).
- Structured JSON logging, request ids, metrics and OpenTelemetry tracing.
- Docker build job in CI (lint + tests + `alembic check` already run there).
