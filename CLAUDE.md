# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Diafragma is a camera-equipment rental backend: FastAPI + synchronous SQLAlchemy 2 on PostgreSQL 18, managed with `uv` (Python >=3.12). The README is empty.

## Commands

```bash
uv sync --dev                          # install deps
docker compose up -d                   # local Postgres (needs POSTGRES_PASSWORD in .env)
uv run fastapi dev src/diafragma/main.py   # run the API
uv run alembic upgrade head            # apply migrations
uv run alembic revision --autogenerate -m "msg"
uv run alembic check                   # CI verifies models match migrations
uv run pytest                          # all tests (Docker required)
uv run pytest tests/products/test_routes.py::test_name   # single test
uv run ruff check --fix . && uv run ruff format .        # lint/format (also pre-commit + CI)
uv run python seed_admin.py EMAIL NAME # create admin (prompts for password, min 12 chars)
uv run python seed_products.py         # load produtos.json
```

Config comes from `.env` via pydantic-settings ([config.py](src/diafragma/config.py)): `DATABASE_URL` and `SECRET_KEY` (min 32 chars) are required at import time, so anything importing `diafragma.config` fails without them.

## Architecture

Layered by domain under `src/diafragma/`: `routes/<domain>/router.py` → `services/<domain>/service.py` → `models/<domain>/models.py`, with Pydantic `schemas/<domain>/schemas.py`. Domains: `products` and `auth`.

- **Services raise domain exceptions** (e.g. `ProductNotFoundError`, `InvalidRentalDaysError`); routers translate them to HTTP errors. Services take a `Session` and commit themselves.
- **DB session**: `SessionDep` in [db/dependencies.py](src/diafragma/db/dependencies.py). `Base` in [db/base.py](src/diafragma/db/base.py) defines a constraint naming convention — Alembic autogenerate relies on it, so keep new constraints unnamed and let it name them.
- **Auth**: OAuth2 password flow at `/auth/token`, JWT via pyjwt, argon2 via pwdlib. Use the `CurrentUser` / `AdminUser` dependencies from [auth/dependencies.py](src/diafragma/auth/dependencies.py). Users have a `UserRole` (ADMIN/CUSTOMER).
- **Double-booking prevention is enforced in the database**: `UnitBlock` uses a Postgres `ExcludeConstraint` on a `DATERANGE` (requires the `btree_gist` extension). Concurrency is tested with 20 threads in `tests/reservations/test_unit_block_concurrency.py`, expecting `ExclusionViolation`/`DeadlockDetected`. Preserve this approach rather than app-level checks.
- `User` is the only person entity: admins and customers (a customer may have just a phone or Telegram chat id; `has_contact` requires one). `Reservation.user_id` points to it. There is no separate client table.
- Shared column types (`UuidPk` = server-side `uuidv7()`, `CreatedAt`, `Cents`, `CountryCode`…) and the `one_of` CHECK helper live in [db/types.py](src/diafragma/db/types.py). Money is always integer cents.
- The products models module also contains Store, Unit, Reservation(Item), Payment, Maintenance, ProductPrice/Photo — not all have routes yet.
- Alembic autogenerate misses CHECK constraints, `server_default` changes and renames — review generated migrations and add those by hand (see `57b8f40828f9_merge_client_into_users.py`).

## Testing

[tests/conftest.py](tests/conftest.py) spins up a real Postgres via testcontainers (session-scoped), creates the schema with `Base.metadata.create_all` (not Alembic) and runs each test in a rolled-back transaction using savepoints. `anon_client` overrides `get_db` with that session; `client` is the same by default. `tests/products/conftest.py` overrides `client` to bypass auth with a fake admin via `require_admin` — use `anon_client` + `auth_headers`/`make_user` to test real auth. New models must be imported in conftest (or transitively) so `create_all` sees them. Because tests bypass migrations, always run `alembic check` after model changes.

## Conventions

- Ruff isort treats `diafragma` as first-party and `alembic` as third-party (matters for migration import ordering).
- CI (`.github/workflows/ci.yaml`) runs lint, tests, and a migrations job (`upgrade head` + `check`) against Postgres 18.
- Code and commit messages are in English (Conventional Commits: `fix(ci): ...`); some user-facing prompts in seed scripts are Portuguese.
