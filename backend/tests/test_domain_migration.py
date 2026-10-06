"""Exercise the migration against PostgreSQL, away from application data.

Each test uses its own schema on the configured database. Alembic receives that
same connection, so neither the application's public schema nor a development
database is reset. Inserts use SQL directly to test database rules independently
of the ORM's Python validation.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import Connection, create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from alembic import command
from app.core.config import settings

LEGACY_HEAD = "6ba2d65b164c"
LEGACY_TABLES = {
    "companies",
    "contacts",
    "job_applications",
    "application_status_history",
    "interviews",
}
DOMAIN_TABLES = {
    "users",
    "companies",
    "contacts",
    "tracked_roles",
    "tracked_role_events",
    "status_history",
    "event_status_histories",
    "tracked_role_contact_associations",
}


@dataclass
class MigrationDatabase:
    connection: Connection
    config: Config
    schema: str

    def upgrade(self, revision: str = "head") -> None:
        # Finish fixture inserts before Alembic owns its migration transaction.
        self.connection.commit()
        try:
            command.upgrade(self.config, revision)
        except BaseException:
            self.connection.rollback()
            raise
        self.connection.commit()

    def downgrade(self, revision: str = LEGACY_HEAD) -> None:
        self.connection.commit()
        try:
            command.downgrade(self.config, revision)
        except BaseException:
            self.connection.rollback()
            raise
        self.connection.commit()

    def tables(self) -> set[str]:
        return set(inspect(self.connection).get_table_names(schema=self.schema)) - {
            "alembic_version"
        }

    def revision(self) -> str:
        return self.connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()


@pytest.fixture
def migration_database() -> Iterator[MigrationDatabase]:
    engine = create_engine(settings.database_url)
    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.skip("Migration integration tests require PostgreSQL")

    # The name is generated here, never provided by a caller or user.
    schema = f"migration_test_{uuid4().hex}"
    with engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(text(f'SET search_path TO "{schema}"'))
        connection.commit()

        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.attributes["connection"] = connection
        try:
            yield MigrationDatabase(connection, config, schema)
        finally:
            connection.rollback()
            connection.execute(text("SET search_path TO public"))
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            connection.commit()
    engine.dispose()


def insert(database: MigrationDatabase, table: str, **values: Any) -> UUID:
    """Insert a fixture without invoking model validators or application defaults."""
    values.setdefault("id", uuid4())
    columns = ", ".join(values)
    parameters = ", ".join(f":{column}" for column in values)
    database.connection.execute(
        text(f"INSERT INTO {table} ({columns}) VALUES ({parameters})"), values
    )
    return values["id"]


def count(database: MigrationDatabase, table: str) -> int:
    return database.connection.execute(
        text(f"SELECT count(*) FROM {table}")
    ).scalar_one()


def snapshot(database: MigrationDatabase, tables: set[str]) -> dict[str, list[Any]]:
    return {
        table: list(
            database.connection.execute(text(f"SELECT * FROM {table} ORDER BY id"))
        )
        for table in tables
    }


def seed_legacy(database: MigrationDatabase, deepest_table: str) -> None:
    company_id = insert(database, "companies", name="Legacy Company")
    if deepest_table == "companies":
        return
    if deepest_table == "contacts":
        insert(database, "contacts", company_id=company_id, name="Recruiter")
        return
    application_id = insert(
        database,
        "job_applications",
        company_id=company_id,
        job_title="Engineer",
        job_type="full_time",
    )
    if deepest_table == "application_status_history":
        insert(
            database,
            "application_status_history",
            application_id=application_id,
            status="applied",
        )
    elif deepest_table == "interviews":
        insert(
            database,
            "interviews",
            application_id=application_id,
            scheduled_at=datetime(2026, 10, 1, 12, tzinfo=UTC),
            interview_type="video",
        )


def seed_domain(database: MigrationDatabase) -> dict[str, UUID]:
    user_id = insert(database, "users", name="First user")
    company_id = insert(
        database,
        "companies",
        user_id=user_id,
        name="Example",
        normalized_name="example",
    )
    role_id = insert(
        database,
        "tracked_roles",
        user_id=user_id,
        company_id=company_id,
        title="Engineer",
        status="saved",
    )
    contact_id = insert(
        database,
        "contacts",
        user_id=user_id,
        company_id=company_id,
        name="Recruiter",
    )
    event_id = insert(
        database,
        "tracked_role_events",
        tracked_role_id=role_id,
        title="Interview",
        event_type="interview",
        event_date=date(2026, 10, 2),
        status="scheduled",
    )
    insert(
        database,
        "status_history",
        tracked_role_id=role_id,
        to_status="saved",
        occurred_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    insert(
        database,
        "event_status_histories",
        event_id=event_id,
        to_status="scheduled",
        occurred_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    insert(
        database,
        "tracked_role_contact_associations",
        tracked_role_id=role_id,
        contact_id=contact_id,
        relationship_type="recruiter",
    )
    return {
        "user_id": user_id,
        "company_id": company_id,
        "role_id": role_id,
        "contact_id": contact_id,
        "event_id": event_id,
    }


def test_fresh_install_matches_models_and_empty_rollback(
    migration_database: MigrationDatabase,
) -> None:
    database = migration_database
    database.upgrade()
    assert database.tables() == DOMAIN_TABLES
    domain_head = database.revision()
    database.connection.commit()
    command.check(database.config)
    database.connection.commit()

    database.downgrade()
    assert database.revision() == LEGACY_HEAD
    assert database.tables() == LEGACY_TABLES
    database.upgrade()
    assert database.revision() == domain_head
    assert database.tables() == DOMAIN_TABLES
    database.connection.commit()
    command.check(database.config)


@pytest.mark.parametrize("deepest_table", sorted(LEGACY_TABLES))
def test_populated_legacy_upgrade_fails_without_changing_schema_or_rows(
    migration_database: MigrationDatabase, deepest_table: str
) -> None:
    database = migration_database
    database.upgrade(LEGACY_HEAD)
    seed_legacy(database, deepest_table)
    before = snapshot(database, LEGACY_TABLES)

    with pytest.raises(DBAPIError, match="Cannot upgrade populated schema") as caught:
        database.upgrade()

    assert "design an explicit data conversion" in str(caught.value)
    assert database.revision() == LEGACY_HEAD
    assert database.tables() == LEGACY_TABLES
    assert snapshot(database, LEGACY_TABLES) == before


def test_populated_domain_downgrade_fails_without_changing_schema_or_rows(
    migration_database: MigrationDatabase,
) -> None:
    database = migration_database
    database.upgrade()
    domain_head = database.revision()
    seed_domain(database)
    before = snapshot(database, DOMAIN_TABLES)

    with pytest.raises(DBAPIError, match="Cannot downgrade populated schema") as caught:
        database.downgrade()

    assert "design an explicit data conversion" in str(caught.value)
    assert database.revision() == domain_head
    assert database.tables() == DOMAIN_TABLES
    assert snapshot(database, DOMAIN_TABLES) == before


def test_company_uniqueness_is_per_user_and_old_global_limits_are_removed(
    migration_database: MigrationDatabase,
) -> None:
    database = migration_database
    database.upgrade()
    first_user = insert(database, "users", name="First user")
    second_user = insert(database, "users", name="Second user")
    company_ids = []
    for user_id in (first_user, second_user):
        company_ids.append(
            insert(
                database,
                "companies",
                user_id=user_id,
                name="Same company",
                normalized_name="same company",
                website="https://example.com",
                linkedin_url="https://example.com/company",
            )
        )
    with pytest.raises(IntegrityError), database.connection.begin_nested():
        insert(
            database,
            "companies",
            user_id=first_user,
            name="SAME COMPANY",
            normalized_name="same company",
        )
    assert count(database, "companies") == 2

    for user_id, company_id in zip((first_user, second_user), company_ids, strict=True):
        insert(
            database,
            "contacts",
            user_id=user_id,
            company_id=company_id,
            name="Shared contact",
            email="contact@example.com",
            phone_number="555-0100",
            linkedin_url="https://example.com/contact",
        )
    # Identical titles and URLs are allowed; duplicate warnings belong to the app.
    for _ in range(2):
        insert(
            database,
            "tracked_roles",
            user_id=first_user,
            company_id=company_ids[0],
            title="Engineer",
            listing_url="https://example.com/role",
            status="saved",
        )
    assert count(database, "contacts") == 2
    assert count(database, "tracked_roles") == 2


def test_database_rejects_invalid_domain_values_and_duplicate_associations(
    migration_database: MigrationDatabase,
) -> None:
    database = migration_database
    database.upgrade()
    ids = seed_domain(database)
    role = {"user_id": ids["user_id"], "title": "Engineer", "status": "saved"}
    event = {
        "tracked_role_id": ids["role_id"],
        "title": "Meeting",
        "event_type": "interview",
        "event_date": date(2026, 10, 2),
        "status": "scheduled",
    }
    invalid_rows = [
        ("tracked_roles", role | {"status": "unknown"}),
        ("tracked_roles", role | {"priority": "bad"}),
        ("tracked_roles", role | {"role_type": "unknown"}),
        ("tracked_roles", role | {"title": "   "}),
        ("tracked_roles", role | {"salary_min": -1}),
        ("tracked_roles", role | {"salary_min": 100, "salary_max": 50}),
        ("tracked_role_events", event | {"event_type": "unknown"}),
        ("tracked_role_events", event | {"status": "unknown"}),
        ("tracked_role_events", event | {"event_type": "custom"}),
        (
            "tracked_role_events",
            event | {"event_type": "custom", "custom_type_name": "   "},
        ),
        ("tracked_role_events", event | {"custom_type_name": "Extra"}),
        (
            "status_history",
            {
                "tracked_role_id": ids["role_id"],
                "to_status": "unknown",
                "occurred_at": datetime(2026, 10, 1, tzinfo=UTC),
            },
        ),
        (
            "event_status_histories",
            {
                "event_id": ids["event_id"],
                "to_status": "unknown",
                "occurred_at": datetime(2026, 10, 1, tzinfo=UTC),
            },
        ),
        (
            "tracked_role_contact_associations",
            {"tracked_role_id": ids["role_id"], "contact_id": ids["contact_id"]},
        ),
    ]
    for table, values in invalid_rows:
        with pytest.raises(IntegrityError), database.connection.begin_nested():
            insert(database, table, **values)

    # A correctly labelled custom event and nullable optional role fields work.
    insert(
        database,
        "tracked_role_events",
        **(event | {"event_type": "custom", "custom_type_name": "Office visit"}),
    )
    insert(database, "tracked_roles", **role)


def test_company_delete_keeps_roles_and_contacts_and_role_delete_cascades(
    migration_database: MigrationDatabase,
) -> None:
    database = migration_database
    database.upgrade()
    ids = seed_domain(database)
    database.connection.execute(
        text("DELETE FROM companies WHERE id = :id"), {"id": ids["company_id"]}
    )
    for table in ("contacts", "tracked_roles"):
        assert count(database, table) == 1
        assert (
            database.connection.execute(
                text(f"SELECT company_id FROM {table}")
            ).scalar_one()
            is None
        )

    database.connection.execute(
        text("DELETE FROM tracked_roles WHERE id = :id"), {"id": ids["role_id"]}
    )
    for table in (
        "tracked_roles",
        "tracked_role_events",
        "status_history",
        "event_status_histories",
        "tracked_role_contact_associations",
    ):
        assert count(database, table) == 0
    assert count(database, "contacts") == 1
    assert count(database, "users") == 1


def test_contact_delete_removes_associations_and_keeps_roles(
    migration_database: MigrationDatabase,
) -> None:
    database = migration_database
    database.upgrade()
    ids = seed_domain(database)
    database.connection.execute(
        text("DELETE FROM contacts WHERE id = :id"), {"id": ids["contact_id"]}
    )
    assert count(database, "tracked_role_contact_associations") == 0
    assert count(database, "tracked_roles") == 1
    assert count(database, "tracked_role_events") == 1
