# Working with Alembic in Huntly

An Alembic revision is a Python file describing how the database changes. Editing
an SQLAlchemy model changes what Python expects; applying a revision changes what
PostgreSQL actually has. Keep those two changes together.

Use this guide a section at a time. The commands are examples to understand and
choose from, rather than one script to run all at once.

## Your starting point for this change

The development database was inspected before the new revision was written. It
was at `6ba2d65b164c`, and all five legacy domain tables were empty. That allowed
an explicit migration to replace the empty legacy schema with the schema your
current models expect. The existing migration files remain unchanged.

The new revision is
[`22017b5e84d4`](../alembic/versions/22017b5e84d4_align_empty_legacy_schema_with_huntly_v1.py),
and its `down_revision` is `6ba2d65b164c`. After applying it, `alembic current`
should report `22017b5e84d4` as the head.

The new revision first locks and checks the old tables, then changes the schema
only if they contain no records. Locking prevents another connection from
inserting a record between the check and the replacement. A populated database
receives an explanation instead of having its records discarded or assigned
invented owners. Downgrade has the same restriction for all eight new tables.

The connection setup now uses Mac port **5433**, while the container still uses
**5432**. Your local database URL points to `localhost:5433`; Compose supplies
`db:5432` for commands running inside Docker.

For your first practice session, read the new revision, then use `current`,
`heads`, and `check` to understand the result. You do not need to generate another
revision to repeat the work already done.

## First, know where your command runs

You type all the Docker commands below into your normal Mac terminal, from
Huntly's `backend/` folder. Docker then runs Alembic inside a temporary backend
container. You do not need to open a shell inside that container first.

```text
Mac terminal
  → Docker starts a temporary backend container
      → Alembic connects to the db container
          → PostgreSQL reads or changes the database
```

Your code remains on your Mac. The Compose setting `.:/app` shares the backend
folder with the container, so an Alembic revision created inside Docker appears
in the same `alembic/versions/` folder you edit locally.

There are two routes to Huntly's Docker database:

| Where the connecting program runs | Database host and port | Where the address comes from |
| --- | --- | --- |
| Inside the backend container | `db:5432` | Compose's `backend.environment.DATABASE_URL` |
| Directly on your Mac | `localhost:5433` | The local `.env` `DATABASE_URL` |

The port mapping `127.0.0.1:5433:5432` means “Mac port 5433 forwards to container
port 5432.” An independent PostgreSQL server on your Mac can still use port 5432.
Those are separate servers and may contain completely different databases.

Inside Docker, `localhost` refers to the connecting container itself. Use the
service name `db` to reach PostgreSQL from the backend container. See
[Docker's explanation of Compose networking](https://docs.docker.com/compose/how-tos/networking/).

For now, use the Docker route consistently. If you later choose local Python,
you also need the project's Python dependencies and the local URL configured;
the Docker database must still be running.

**Self-check:** Where will Alembic run? Which PostgreSQL server will it contact?

## Start the database and inspect the situation

From the repository root, enter the backend folder:

```sh
cd backend
```

With Docker Desktop running, this starts PostgreSQL without starting the API:

```sh
docker compose up -d db
```

Then ask which revision that database has applied:

```sh
docker compose run --rm backend alembic current
```

Read the command in pieces:

- `docker compose`: use the services defined in `compose.yaml`.
- `run`: start a temporary container using the backend's configuration. Its
  database dependency starts if needed, and Compose waits for its health check.
- `--rm`: remove the temporary backend container after the command finishes.
- `backend`: choose the backend service.
- `alembic current`: ask the database about its applied migration revision.

The database container and its persistent data remain after this command.
`run` replaces the usual API startup command with the Alembic command you supply.
[Docker documents this behavior here](https://docs.docker.com/reference/cli/docker/compose/run/).

`docker compose exec backend ...` is another pattern you may see. It requires an
already running backend container. Keep using `run` while learning migrations so
that you can work with the API stopped.

Different Alembic commands answer different questions:

| Command after `docker compose run --rm backend` | What you learn | Reads the database? |
| --- | --- | --- |
| `alembic current` | What this database has applied | Yes |
| `alembic heads` | The latest revision or revisions in the files | No |
| `alembic history` | How the revision files connect | No |
| `alembic check` | Whether autogeneration detects remaining schema differences | Yes |

For example, if `current` shows an older revision and `heads` shows a newer one,
there is an unapplied revision. “Head” describes the end of the migration chain;
it does not mean the database has reached it. See
[Alembic's migration-history tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html#getting-information).

**Self-check:** Can you point to the database's revision and the migration files'
head, and explain whether they match?

## The revision added for this model transition

The older migrations describe companies, contacts, job applications, interviews,
and application status history. The current models use users, tracked roles,
events, separate histories, and role/contact associations.

This is a substantial change in meaning, not just a new optional column. The
older tables do not provide all the required owner and status information for
the new schema. A migration must not guess who owns an existing company or
invent a tracked role's status.

Here are concrete examples you can find in the source:

| Old structure | What the new structure requires | Decision a data migration would need |
| --- | --- | --- |
| `companies` and `contacts` have no `user_id` | Both have a required owner | Which real user owns each record? |
| `job_applications` has `job_title` and `job_type`, but no current `status` | `tracked_roles` needs a title and a valid current status | Which old field maps directly, and how is status established when no history exists? |
| `interviews` has `scheduled_at`, `interview_type`, and optional `outcome` | Events need a title, date, event type, and status | How should timezones and old outcomes become these values? |

Compare the
[old table definitions](../alembic/versions/bb99e7312ea9_full_domain_models_cleanup.py)
with [Company](../app/models/company.py),
[TrackedRole](../app/models/tracked_role/tracked_role.py), and
[TrackedRoleEvent](../app/models/tracked_role/event.py). The current enum values
are defined in [enums.py](../app/models/enums.py).

The new alignment revision therefore checks for legacy records before changing
tables. It supports an empty legacy schema and refuses a populated legacy schema
with an explanation. If it refuses, preserve those records and design the owner,
status, and field mappings before creating a data migration. Do not remove the
guard just to make the command succeed.

For this particular revision, read the opening explanation and the preflight
guard before reading the table definitions. Then compare one table—`companies`
is a good starting point—with its model. Look for its required `user_id`,
`normalized_name`, foreign key, and owner-scoped unique constraint.

Its downgrade also checks for records before replacing the new schema with the
old one. Recreating old tables would not recover discarded data.

**Self-check:** What information would be missing if we tried to move an old
company or job application into the new tables?

## Your next small model change

Start with a modest change, such as adding an optional field. Before touching
Alembic, write one sentence describing the desired result and answer:

1. Which table or constraint changes?
2. What happens to records already in that table?
3. Can the change be reversed without losing values?

Use a development or disposable database whose current revision matches the
existing head before making the next model change. If there are unapplied files,
review them before bringing the database forward.

After editing the model, generate a draft. Replace the example message with
what your change actually does:

```sh
docker compose run --rm backend alembic revision --autogenerate -m "add optional company field"
```

This creates a file; it does not apply the schema change. Autogeneration compares
the connected database to the SQLAlchemy metadata imported in `alembic/env.py`.

Open the new file in `alembic/versions/` and identify four parts:

| Part | Meaning |
| --- | --- |
| `revision` | The identifier of this change |
| `down_revision` | The preceding revision |
| `upgrade()` | How to move forward |
| `downgrade()` | How to move backward |

Read every operation. For an optional field, would you expect to see unrelated
tables being dropped? If so, investigate before applying the file. Alembic often
represents a rename as a drop plus an addition, and it does not design data
backfills for you. Some constraint changes also need manual attention. Read
[the official autogeneration limitations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect).

A required field on a populated table often needs several deliberate operations:
allow empty values temporarily, populate the existing records, verify them, and
then require a value. Populating the existing records is called a **backfill**.
[Alembic's data migration guidance](https://alembic.sqlalchemy.org/en/latest/cookbook.html#data-migrations-general-techniques)
describes ways to coordinate that work.

**Self-check:** Can you explain what each operation changes and why it belongs
in this revision?

## Apply and verify a reviewed revision

Huntly's normal API startup runs `alembic upgrade head` automatically. Stop the
backend before drafting or editing a revision, and review the file before
restarting the service. A running backend may continue until restarted, but
another start of the service would apply pending migrations.

After review, apply the revision deliberately to your development database:

```sh
docker compose run --rm backend alembic upgrade head
```

Then inspect the result:

```sh
docker compose run --rm backend alembic current
docker compose run --rm backend alembic check
```

`current` should match the intended head. `check` should report no new upgrade
operations. It shares autogeneration's limitations, so also verify the rules you
changed. For a uniqueness change, try the duplicate case that should fail and
the distinct case that should succeed. See
[Alembic's explanation of check](https://alembic.sqlalchemy.org/en/latest/autogenerate.html#running-alembic-check-to-test-for-new-upgrade-operations).

The project test command is:

```sh
./scripts/test.sh
```

It uses a separate Compose project and a temporary PostgreSQL database. It applies
the migrations to a fresh database, then runs the three health tests. There are
no dedicated migration tests yet. These health tests do not check rollback,
existing data, or database constraints.

Practice downgrades only on a disposable database. `alembic downgrade -1` means
undo the latest applied revision; it is not a backup restore. For an additive
field migration, dropping the field also removes its values. This alignment
revision deliberately refuses a downgrade when the new tables contain records.
An older revision contains an unnamed constraint drop, as noted in the README;
review earlier revisions before attempting further downgrades.

Once checks pass, restart the backend to use the updated schema. Keep the model
change, reviewed revision, and relevant tests together in version control.
After a revision has been shared or applied elsewhere, normally fix mistakes
with a new revision so everyone's recorded history stays consistent.

**Self-check:** Did you verify only an empty database, or also the populated
case your migration promises to support? What would a downgrade discard?
