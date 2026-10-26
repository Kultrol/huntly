# Backend tests

The suite covers Pydantic schemas, PostgreSQL models and constraints, service
operations and transactions, HTTP requests and responses, configuration, session
cleanup, application routes, CORS, and V1 migrations.

Tests use explicit setup and direct assertions, with parameterization for related
inputs. Database tests verify committed changes or rollback through a new
session. Mocks cover failure paths and delegation; persistence checks use real
PostgreSQL.

## Finding a test

Tests are grouped by resource and behavior.

| Area | Location and groups |
| --- | --- |
| Schemas | `schemas/company/`, `contact/`, `event/`, `tracked_role/`: read, create, update, and validation cases. |
| Schema examples | Each resource's `data.py` holds shared IDs, dates, and example inputs. |
| Company services | `services/company/`: create, read, update, delete, transactions, and errors. |
| Event and role services | `services/event/`, `services/tracked_role/`: lifecycle, status history, transactions, errors, and role validation. |
| Owner rules | `services/owner_validation/`: one module per company, contact, or tracked-role resource. |
| Larger API groups | `api/company/`, `api/event/`, `api/tracked_role/`: read, write, and error responses, with custom-event cases separated. |

Run a resource folder to check all its behavior, or select one file to focus on
an area. From `backend/`, with a disposable database configured:

```sh
.venv/bin/python -m pytest tests/services/company/ -q
.venv/bin/python -m pytest tests/schemas/event/test_read.py -q
```

Select a test by name:

```sh
.venv/bin/python -m pytest tests/ -k test_event_create_requires_existing_parent -q
```

## Run the suite

From `backend/`:

```sh
./scripts/test.sh
```

This builds the current test image, applies migrations, and runs pytest against
the separate `huntly-tests` Compose project. Its PostgreSQL data lives in tmpfs;
the development database and persistent volume are separate.

For a focused run with current source files:

```sh
docker compose -p huntly-tests --profile test run --rm \
  --volume "$PWD:/app:ro" backend_test \
  sh -c 'alembic upgrade head && pytest tests/services/event/ -q -p no:cacheprovider'
```

Rebuild the image when dependencies change. To remove the disposable Compose
containers after testing:

```sh
docker compose -p huntly-tests --profile test down
```

Schema tests need no database or application settings. From the repository root:

```sh
backend/.venv/bin/python -m pytest backend/tests/schemas -q
```

## Fixtures and isolation

`conftest.py` provides function-scoped sessions, two owners, saved records, and
an in-process HTTP client. Each request gets a separate database session. The
client restores the previous `get_db` override on exit. Cleanup deletes only
records belonging to that test's owners, including dependent activity through
foreign-key cascades. Tests that create additional users clean them up locally.
Company metadata factories are in `services/company/conftest.py`, where the
local `saved_company` fixture applies only to Company service tests. The custom
event fixture lives in `api/event/conftest.py`. Database and HTTP client setup
remain shared across the suite; test modules do not import other test modules.

Database fixtures use `settings.database_url`; always select a disposable test
database before running database tests outside the Compose workflow.

Migration tests create a uniquely named PostgreSQL schema, run actual upgrades
and downgrades through a supplied connection, and remove that schema afterward.
They check empty-schema conversion, populated-schema guards, deletion rules,
constraints, and agreement with the current model metadata.

The core session tests use the production session factory, rebinding only its
connection to the disposable test engine. This checks that committed fields can
still be returned in an API response with the production session settings.

The owner IDs in these tests exercise filtering and affiliation rules. The
application does not yet provide an authentication boundary. Independent
transactions and history rollback are covered; simultaneous status changes do
not have a defined conflict-resolution contract in the current services.
