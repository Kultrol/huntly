# Working with Alembic

SQLAlchemy models define the expected schema. Alembic revisions apply those
changes to PostgreSQL. Commit model changes, reviewed revisions, and their tests
together.

## Connections and command location

Run the commands below from `backend/` with Docker Desktop running. Compose runs
Alembic in a temporary backend container connected to the development database.
The backend directory is mounted at `/app`, so generated revisions appear locally
in `alembic/versions/`.

| Connecting program | PostgreSQL address | Configuration |
| --- | --- | --- |
| Backend container | `db:5432` | Compose's `backend.environment.DATABASE_URL` |
| Local Python or database client | `localhost:5433` | `.env` `DATABASE_URL` |

Inside a container, `localhost` refers to that container. Use the service name
`db` to reach the development PostgreSQL service.

## Inspect migration state

```sh
docker compose up -d db
docker compose run --rm backend alembic current
docker compose run --rm backend alembic heads
docker compose run --rm backend alembic history
docker compose run --rm backend alembic check
```

- `current` reads the connected database's applied revision.
- `heads` lists the latest revisions in the migration files.
- `history` shows the revision chain.
- `check` compares the connected schema with model metadata using autogeneration.

`run --rm backend` replaces the normal API startup command and removes the
temporary backend container when finished. The database and persistent volume
remain. `exec backend` requires an already running backend container.

## Create a revision

Normal API startup applies pending revisions automatically. Stop the backend
before drafting a revision, and review it before restarting the service:

```sh
docker compose stop backend
```

Start from a development or disposable database at the existing migration head.
After editing the models, generate a candidate revision:

```sh
docker compose run --rm backend alembic revision --autogenerate -m "describe the model change"
```

Generation creates a file without applying it. Review its `revision`,
`down_revision`, `upgrade()`, and `downgrade()` before proceeding. Check for
unrelated operations, lost data, required-field backfills, and named constraints.
Autogeneration can represent a rename as a drop and an addition; it does not
design data conversions. A required column on a populated table may need to be
nullable while existing rows are populated, then made non-nullable.

## Apply and verify

Back up valuable data before applying a schema change. After reviewing the
revision:

```sh
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic current
docker compose run --rm backend alembic check
./scripts/test.sh
docker compose up -d backend
```

`current` should match the intended head. `check` should report no new upgrade
operations, but it shares autogeneration's limitations. Add tests for changed
constraints and for any populated-data conversion the revision supports.

The test script uses a separate Compose project and temporary PostgreSQL storage.
The [migration tests](../tests/migrations/test_v1_schema.py) exercise actual
upgrades and downgrades in isolated schemas, populated-schema guards, constraints,
deletion rules, and agreement with model metadata. See the
[test guide](../tests/README.md) for the full workflow.

Run downgrades only against a disposable database unless data loss has been
explicitly planned. `alembic downgrade -1` reverses the latest applied revision;
it does not restore deleted values. Once a revision has been shared or applied
elsewhere, correct it with a new revision rather than changing recorded history.

## Legacy-to-V1 transition

Revision
[`22017b5e84d4`](../alembic/versions/22017b5e84d4_align_empty_legacy_schema_with_huntly_v1.py)
follows `6ba2d65b164c`. It replaces the empty legacy schema with the V1 schema.
The legacy tables lack the ownership and status information required for an
automatic conversion of existing records.

The revision locks and checks all five legacy tables before changing them. It
refuses to upgrade a populated legacy database. Its downgrade likewise requires
all eight V1 tables to be empty. Preserve populated databases and define explicit
owner, status, and field mappings before writing a data migration; removing the
guard would discard records without converting them.

An older
[company-name revision](../alembic/versions/b8cd22a31fee_updated_companies_table_column_name_so_.py)
drops an unnamed unique constraint during downgrade. Review that step before
attempting a downgrade further into the legacy chain.
