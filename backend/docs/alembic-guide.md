# Working with Alembic

SQLAlchemy models describe the expected schema; Alembic revisions change the
database to match it. Treat model changes, reviewed revisions, and their tests as
one change. For local setup, start with the [backend README](../README.md).

## Command location and database connections

Run every command below from `backend/`, with Docker Desktop running. The
one-off backend container connects to the development database and mounts this
directory at `/app`, so generated files appear locally in `alembic/versions/`.

| Connecting program | PostgreSQL address | Configuration |
| --- | --- | --- |
| Backend or migration container | `db:5432` | Compose's `backend.environment.DATABASE_URL` |
| Local Python or database client | `localhost:5433` | `.env` `DATABASE_URL` |

Inside a container, `localhost` refers to that container. Use `db` for the
development database. Alembic reads the same application settings as the API;
[`alembic/env.py`](../alembic/env.py) supplies its database URL.

`docker compose run --rm backend alembic ...` replaces the normal API command:
it runs the requested Alembic operation and removes the temporary container.
It does not start the API. Inspecting or generating revisions therefore skips
the normal startup upgrade; an explicit `upgrade` command applies changes.
The database and its persistent volume remain. `docker compose exec backend ...`
instead needs an already running backend container.

## 1. Inspect the current state

Normal backend startup applies pending revisions before starting the API. Stop
the backend before drafting a migration so a restart cannot apply unfinished
work; the database can stay running.

```sh
docker compose stop backend
docker compose up -d db
docker compose run --rm backend alembic current
docker compose run --rm backend alembic heads
docker compose run --rm backend alembic history
```

`current` reads the database's applied revision; `heads` shows the latest revision
in the files; `history` shows their chain. The current head is `a6d4f9b2c813`.
Before generating another revision, the development or disposable database must
be at the existing head. If it is behind, review the pending revisions and follow
the apply step first.

## 2. Generate a candidate

Edit the models. Import new model classes in
[`app/models/__init__.py`](../app/models/__init__.py): Alembic imports this package
and compares `Base.metadata` with the database. A missing import can omit a new
table or make an existing table appear to need deletion.

```sh
docker compose run --rm backend alembic revision --autogenerate -m "describe the model change"
```

This writes a candidate revision without applying it. Model edits do not generate
revisions automatically, and API startup only applies revisions that already
exist.

## 3. Review the revision

Read its `revision`, `down_revision`, `upgrade()`, and `downgrade()`. Check that the
parent revision is correct and the operations cover only the intended change.
Review constraints, indexes, defaults, nullability, and deletion rules against the
models and existing data.

Autogeneration cannot design a data conversion. A rename can appear as a drop
and an addition; a new required field may need a nullable column, a deliberate
backfill, and a later non-null constraint. Name new constraints so later revisions
can target them reliably. Add tests for changed constraints and any supported
upgrade of populated tables.

Once a revision has been applied elsewhere or shared, correct it with a new
revision rather than rewriting its history.

## 4. Apply the reviewed change

Back up valuable data before applying a schema change. With the API still stopped:

```sh
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic current
docker compose run --rm backend alembic check
```

`current` should match the intended head. `check` compares the schema with model
metadata and should report no new upgrade operations; it has the same limits as
autogeneration. If a data guard refuses the migration, preserve the records and
resolve the required conversion instead of removing the guard.

## 5. Test and resume development

```sh
./scripts/test.sh
docker compose up -d backend
```

The test script builds the current source, applies migrations, and runs pytest
against the separate `huntly-tests` project and temporary PostgreSQL storage.
It does not use the development database. Migration tests use isolated database
schemas to check upgrades, downgrades, data preservation, constraints, and
agreement with model metadata. See the [test guide](../tests/README.md) for
focused runs and fixture isolation.

## Existing revisions and downgrade limits

The [authentication revision](../alembic/versions/a6d4f9b2c813_add_credentials_and_auth_sessions.py),
`a6d4f9b2c813`, follows `22017b5e84d4`. It adds nullable email/password-hash columns
and the `auth_sessions` table while preserving existing users and owned records.
Legacy users retain null credentials and cannot log in without an explicit
trusted provisioning or linking process. Registration creates a new account; it
does not claim old records. See [authentication](authentication.md) for the
account flow and [architecture](architecture.md) for ownership and transactions.

That revision's downgrade locks `users` and `auth_sessions`, then refuses to
discard any stored credentials or sessions. The locks prevent concurrent writes
from invalidating the check. Credential-free legacy owners and their domain
records can remain when this auth revision is reversed.

The earlier [V1 revision](../alembic/versions/22017b5e84d4_align_empty_legacy_schema_with_huntly_v1.py),
`22017b5e84d4`, follows `6ba2d65b164c`. It replaces the legacy schema and requires
all five legacy tables to be empty before upgrade; its downgrade requires all
eight V1 tables to be empty. It locks those tables before checking. Populated
legacy records need explicit owner, status, and field mappings in a separate
conversion plan.

Run downgrades on a disposable database unless the data consequences have been
planned. `alembic downgrade -1` reverses the latest applied revision; it cannot
restore deleted values. An older
[company-name revision](../alembic/versions/b8cd22a31fee_updated_companies_table_column_name_so_.py)
drops an unnamed unique constraint in its downgrade, so review that operation
before attempting to move further back through the legacy chain.
