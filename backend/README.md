# Huntly backend

FastAPI backend for tracking job opportunities, companies, contacts, and related
activities. It uses PostgreSQL, async SQLAlchemy, Alembic, Pydantic, and
cookie-based authentication. The backend is under active development.

## Quick start

Docker Desktop with Docker Compose is the only required local runtime for this
workflow. Start Docker Desktop before continuing. Python and `uv` are installed
inside the backend image.

From the repository root:

```sh
cd backend
test -f .env || cp .env.example .env
```

For a new database, edit `.env` and replace `POSTGRES_PASSWORD=replace-me` with a
URL-safe development password before starting. Keep existing credentials when
reusing a database volume: changing `.env` does not change the PostgreSQL role
inside an initialized database.

Then, from `backend/`:

```sh
docker compose up --build -d --wait backend
```

This starts PostgreSQL, applies pending migrations, starts the API with code
reload, and waits for the services to become healthy. PostgreSQL data persists
in the `postgres_data` volume. Startup can refuse a populated legacy schema;
see [migration compatibility](docs/alembic-guide.md) before changing that data.

| URL | Purpose |
| --- | --- |
| [localhost:8000/docs](http://localhost:8000/docs) | Interactive API documentation and requests |
| [localhost:8000/health](http://localhost:8000/health) | API liveness |
| [localhost:8000/health/db](http://localhost:8000/health/db) | Database connectivity |

The health endpoints are public. Resource endpoints require a signed-in session.
The database health check runs `SELECT 1`; it does not validate the schema.

## Make the first authenticated request

Use [Swagger UI](http://localhost:8000/docs) to exercise the backend directly:

1. Execute `POST /auth/register` with a new account:

   ```json
   {
     "name": "Example Developer",
     "email": "developer@example.com",
     "password": "a long local password 42!"
   }
   ```

2. Copy `csrf_token` from the response. The browser stores the session cookie
   automatically. For an existing account, use `POST /auth/login` instead.
3. Execute `POST /companies/`. Paste the token into its `X-CSRF-Token` header
   field and submit `{"name": "Example company"}`. Ownership comes from the
   session, so a `user_id` is unnecessary.
4. Execute `GET /companies/` to retrieve the signed-in account's companies.

The example environment allows the API's own `http://localhost:8000` origin and
uses HTTP-compatible development cookies. Existing `.env` files must include
that origin in `ALLOWED_ORIGINS` for Swagger writes. Keep `localhost` consistent
across the browser and API URLs. See [Authentication](docs/authentication.md)
for frontend integration, session management, and error responses.

## Navigate the backend

| Task | Start here |
| --- | --- |
| Understand the layout, request flow, and transaction rules | [Architecture](docs/architecture.md) |
| Locate routes, middleware, and application setup | [Application entry point](app/main.py), then [API routes](app/api/) |
| Change account or domain behavior | [Services](app/services/), called by the relevant route |
| Change accepted inputs or returned fields | [Schemas](app/schemas/) |
| Inspect tables, relationships, and constraints | [Models](app/models/) |
| Change the database schema | [Alembic workflow](docs/alembic-guide.md) |
| Run or extend tests | [Testing guide](tests/README.md) |
| Work with cookies, passwords, or CSRF | [Authentication guide](docs/authentication.md) |
| Check domain requirements and relationships | [V1 specification](docs/domain-v1.md), [domain ER diagram](docs/huntly-v1-er-diagram.md) |

The architecture guide describes current behavior. The specification and domain
ER diagram describe intended business rules and include requirements that are
not yet fully exposed by the API.

## Common development commands

Run these commands from `backend/`.

| Action | Command |
| --- | --- |
| Start existing development services | `docker compose up -d --wait backend` |
| Check service status | `docker compose ps` |
| Follow API logs | `docker compose logs -f backend` |
| Rebuild after dependency or Dockerfile changes | `docker compose up --build -d --wait backend` |
| Stop development services | `docker compose stop` |
| Run the isolated test suite | `./scripts/test.sh` |
| Remove disposable test containers | `docker compose -p huntly-tests --profile test down` |

Python source changes reload automatically. Recreate the backend service after
changing environment values; rebuilding also refreshes locked dependencies.
`docker compose down` removes development containers while retaining the data
volume. Adding `--volumes` removes that data.

The test script uses a separate Compose project, a temporary PostgreSQL database,
and no database host port. See the [testing guide](tests/README.md) for focused
runs and local Python alternatives.

## Connection and configuration reference

| Client | PostgreSQL address |
| --- | --- |
| Backend container | `db:5432` |
| Host database tools or local Python | `localhost:5433` |
| Test container | `db_test:5432` inside the isolated test project |

The API listens at `localhost:8000`; development ports bind to `127.0.0.1`.
Compose supplies container database URLs. The example `.env` supplies the host
URL for local Python. Inside a container, `localhost` refers to that container.

[`.env.example`](.env.example) lists development settings. `ALLOWED_ORIGINS` is a
JSON array of exact origins, without paths or wildcards. HTTP development uses
`SESSION_COOKIE_SECURE=false`; HTTPS deployments use `true`. Authentication
settings and deployment limitations are documented in the
[authentication guide](docs/authentication.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Services do not become healthy | Read `docker compose logs backend db`; check Docker Desktop and ports 8000/5433. |
| Database authentication fails after an environment edit | An existing volume keeps its original database credentials. |
| A private endpoint returns 401 | Register or log in; keep the same hostname and use HTTP-compatible cookies locally. |
| A write returns 403 | Send the current `X-CSRF-Token` and allow the browser's exact origin. |
| Startup refuses a schema upgrade | Follow the [migration guide](docs/alembic-guide.md); legacy rows require an explicit conversion plan. |

The existing frontend demo requests need login, cookie, and CSRF integration
before they can use the protected API. Email verification, password recovery,
and application-side authentication throttling are not implemented; see the
authentication guide for the current scope.
