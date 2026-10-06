# Huntly backend

Run the API and PostgreSQL with Docker Desktop (including Docker Compose). Docker
installs the locked Python dependencies, so Python and `uv` are not required on
your computer for the commands below. Run all commands from `backend/`.

## Start development

From the repository root:

```sh
cd backend
test -f .env || cp .env.example .env
```

For a new installation, edit `.env` and choose a URL-safe database password
**before** the first start (see `.env.example`). Keep an existing `.env` and its
credentials: changing these values does not change the users or password inside
an existing database volume.
`ALLOWED_ORIGINS` must be a JSON list, as shown in `.env.example`.

Then start the API:

```sh
docker compose up --build -d backend
```

Starting `backend` also starts `db`, waits for PostgreSQL, applies the existing
Alembic revisions, and launches the API with automatic reload for code changes.
The development database uses the persistent `postgres_data` volume.

- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- API health: [http://localhost:8000/health](http://localhost:8000/health)
- Database connectivity: [http://localhost:8000/health/db](http://localhost:8000/health/db)

The API and development database are exposed only on your computer, at ports
8000 and 5433. Inside Docker, the database address is `db:5432`; tools running on your
computer use `localhost:5433`. The example's `DATABASE_URL` supports the latter;
Compose supplies the container's database URL separately.

## Everyday commands

```sh
docker compose ps
docker compose logs -f backend
docker compose restart backend
docker compose stop
```

Press Ctrl+C to leave the log view. To start again, use `docker compose up -d backend`.
After changing `pyproject.toml` or `uv.lock` (for example, with `uv add`), rebuild:

```sh
docker compose up --build -d backend
```

`docker compose down` also removes the development containers and network while
preserving the database volume. Do not add `--volumes` unless you intend to erase
that database.

## Run tests

```sh
./scripts/test.sh
```

The script builds the image and runs `backend_test` against `db_test` under the
separate Compose project `huntly-tests`. The test database is temporary and has
no host port. Development data and running development containers are separate.
The script returns the test process's exit status: zero means success.

The three tests check API health, database connectivity, and the response when
the database is unavailable. The test container applies migrations before running
them. There are no dedicated migration tests yet.

## Bring the schema in line with the models

Revision `22017b5e84d4` follows `6ba2d65b164c` and aligns an empty legacy database
with the current V1 models. It locks and checks the five legacy tables before any
schema changes, and refuses to upgrade if they contain records. Those records
need an explicit ownership/status conversion plan; the revision does not guess.
Its downgrade also requires all eight V1 tables to be empty. Existing historical
revisions remain unchanged. Docker does not generate revisions automatically.

For the guided explanation of what was changed and how to handle your next model
change, read [Working with Alembic in Huntly](docs/alembic-guide.md).

For a future model change, inspect the database and generate a candidate:

```sh
docker compose run --rm backend alembic current
docker compose run --rm backend alembic revision --autogenerate -m "describe the model change"
```

The generated file appears in `alembic/versions/`. Review and edit it before
applying it: autogeneration can interpret renamed tables or columns as drops and
new tables or columns. Preserve existing data, and plan how required ownership
fields will be populated. Back up valuable data before applying the revision.

Once the revision is ready:

```sh
docker compose run --rm backend alembic upgrade head
docker compose restart backend
./scripts/test.sh
```

These one-off `run` commands replace the API startup command; generating a
revision does not apply it. Normal API startup does apply pending revisions, so
review generated files before restarting the development service. An older
downgrade step also drops a unique constraint without its name; review that step
before relying on `alembic downgrade`.
