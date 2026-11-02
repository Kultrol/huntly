# Backend testing guide

The backend suite checks schemas, PostgreSQL constraints, services, HTTP endpoints,
authentication, ownership, and migrations. Database tests verify persistence or
rollback through a fresh session; mocks cover selected failure paths.

All commands below run from `backend/`. See the [backend setup guide](../README.md)
for Docker Desktop requirements and `.env` setup.

## Run the full suite

```sh
./scripts/test.sh
```

The script builds the test image, recreates the test containers, applies Alembic
migrations, and runs pytest. It uses the separate `huntly-tests` Compose project
and its `db_test` service. PostgreSQL test storage is temporary and disappears
when that database container stops. No host database port is exposed.

The development `huntly` project and its persistent database volume are separate.
The script returns pytest's exit status: zero indicates success.

## Run a focused Docker check

Build before the first focused run and whenever `pyproject.toml` or `uv.lock`
changes:

```sh
docker compose -p huntly-tests --profile test build backend_test
```

Then run a folder, file, or individual test against the current source:

```sh
docker compose -p huntly-tests --profile test run --rm \
  --volume "$PWD:/app:ro" backend_test \
  sh -c 'alembic upgrade head && pytest tests/services/company/ -q -p no:cacheprovider'
```

Compose starts `db_test` and waits for its health check. The source mount makes
code changes available without rebuilding the image; installed dependencies
still come from the image. The read-only mount and disabled pytest cache keep the
run from writing into the checkout. This command applies migrations before pytest
and uses the same isolated database service as the full-suite script.

Replace `tests/services/company/` in that command with a selector such as:

| Selector | Scope |
| --- | --- |
| `tests/schemas/event/` | Event schema validation. |
| `tests/api/test_auth.py` | Account and session HTTP behavior. |
| `tests/api/test_auth_races.py` | Password changes after concurrent credential or session changes. |
| `tests/services/event/test_lifecycle.py::test_event_create_requires_existing_parent` | One service behavior. |
| `tests/api/ -k 'expired_logout or password_change'` | API tests whose names match the expression. |

Remove the disposable test containers when finished:

```sh
docker compose -p huntly-tests --profile test down
```

This teardown targets only `huntly-tests`; it does not remove the development
containers or their database volume.

## Optional local Python workflow

The project selects Python 3.14 and manages dependencies with `uv`:

```sh
uv python install 3.14
uv sync --locked
```

Schema and password-helper tests need no database or application settings:

```sh
uv run --locked pytest tests/schemas/ tests/core/test_security.py -q
```

Database-backed tests must use a disposable PostgreSQL database created solely
for testing. Never run the full suite against the development `DATABASE_URL`:
fixtures commit and delete records, and migration tests create and drop schemas.
The test database role needs permission to create those schemas.

Local Python needs a test database reachable from the host. The Compose
`db_test` service has no host port; use a separate reachable test instance or
keep using the Docker workflow above. Create the database before running Alembic;
Alembic creates its tables, not the PostgreSQL database itself.

Set an explicit test URL. The following value is a placeholder to replace with
that disposable database's connection details:

```sh
export HUNTLY_TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:PORT/DISPOSABLE_TEST_DATABASE'
```

Apply migrations and run tests with the test URL overriding `.env`. The subshell
keeps these application settings local to this run:

```sh
(
  export DATABASE_URL="${HUNTLY_TEST_DATABASE_URL:?Set an explicit disposable test database URL}"
  export ALLOWED_ORIGINS='[]'
  export SESSION_COOKIE_SECURE=false
  uv run --locked alembic upgrade head &&
    uv run --locked pytest tests/ -q
)
```

Replace `tests/` with a focused selector when needed. Tests that import the app or
use database fixtures load settings; the full suite requires both the configured
PostgreSQL database and its migrated schema.

## Test layout

Paths in this table are relative to `backend/tests/`.

| Area | Location and coverage |
| --- | --- |
| Schemas | `schemas/`: create/read/update contracts, field validation, and shared example data. |
| Models | `models/`: PostgreSQL constraints, relationships, deletion rules, and model registration. |
| Domain services | `services/`: CRUD, ownership validation, status history, and transaction behavior. |
| Resource HTTP endpoints | `api/company/`, `api/event/`, `api/tracked_role/`, `api/test_contact.py`, and `api/test_user.py`: responses, validation, errors, and persistence. |
| Configuration and database sessions | `core/`: settings, request-session cleanup, rollback, and serialization after commit. |
| Application and health | `test_main.py`, `test_health.py`, and `api/test_health.py`: route registration, CORS, CSRF documentation, and health responses. |
| Migrations | `migrations/test_v1_schema.py`: real upgrades/downgrades, data-preservation guards, constraints, and agreement with model metadata. |

Authentication coverage is split by behavior:

| File | Coverage |
| --- | --- |
| `api/test_auth.py` | Registration, login, credential errors, cookies, expiry, CSRF/origins, password changes, and session revocation. |
| `api/test_auth_session_lifecycle.py` | Expired logout, CSRF on active logout, session-list filtering/order, and revoking another device. |
| `api/test_auth_transactions.py` | Registration/login failures roll back account/session changes and preserve the previous cookie. |
| `api/test_auth_races.py` | Password changes reload the current hash and recheck a session changed after authentication. |
| `api/test_auth_unicode.py` | Invalid Unicode is rejected without changing credentials, sessions, or cookies; valid Unicode passwords remain usable. |
| `api/test_csrf_contract.py` | The documented CSRF header supports profile writes and logout. |
| `api/test_authorization.py` | Anonymous access, foreign resources/parents, and attempts to override the authenticated owner. |
| `core/test_security.py`, `schemas/test_auth.py`, and `models/test_auth_session.py` | Password hashing, token derivation, input contracts, and session persistence/cascades. |

## Fixtures and transaction boundaries

Shared fixtures live in `conftest.py` and are scoped to one test:

| Fixture | Behavior |
| --- | --- |
| `test_db`, `sessions`, `owner_ids` | Create a test engine/session factory and two owners. `sessions` is a factory; open a new session for setup or persistence checks. |
| `saved_company`, `saved_contact`, `saved_role`, `saved_event` | Persist related example records owned by `owner_ids[0]`. |
| `api_client` | An in-process HTTP client signed in as `owner_ids[0]` through a real stored session and CSRF header. |
| `anonymous_client` | Starts without a session; registration or login can establish one. |
| `client_factory(owner_id=None, *, raise_app_exceptions=True)` | An async context manager for an anonymous client or a client signed in as the chosen owner. `authenticated_client_factory` is an alias. |

The client factory seeds sessions directly for resource tests, so those tests can
focus on authorization. Account-flow tests instead start anonymously and use the
real registration/login endpoints. Clients call the ASGI app directly without
starting Uvicorn; their database operations still use real PostgreSQL.

Each HTTP request gets a fresh `AsyncSession` through a test override of `get_db`.
The fixture restores the previous override at teardown. Company service tests
have a local `saved_company` fixture in `services/company/conftest.py`; custom-event
API setup lives in `api/event/conftest.py`.

Services flush changes without committing. API routes own commit/rollback, and
the authentication dependency finishes its lookup transaction before a route
starts its transaction. Service tests choose their own transaction boundary with
`sessions.begin()`. Persistence checks open another session so they inspect saved
data rather than only an object already loaded in memory. Core database tests
also exercise the production session factory against the test database.

Isolation comes from unique owners and explicit cleanup, rather than one outer
transaction rolled back after every test. Cleanup removes the test owners' domain
records and users, with dependent histories and sessions removed by foreign-key
cascades. Tests creating additional accounts clean them up locally.

Migration tests create a uniquely named PostgreSQL schema, run upgrades and
downgrades through a supplied connection, and remove that schema afterward. This
keeps migration operations separate from the regular test tables; it does not
make a development database an appropriate full-suite target.

See [architecture](../docs/architecture.md) for the request/service/database flow,
[authentication](../docs/authentication.md) for the HTTP contract, and the
[Alembic guide](../docs/alembic-guide.md) for migration commands and review steps.
