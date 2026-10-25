from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base

LEGACY_REVISION = "6ba2d65b164c"
V1_REVISION = "22017b5e84d4"
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
    "status_history",
    "tracked_role_events",
    "event_status_histories",
    "tracked_role_contact_associations",
}


@pytest.fixture
def migration_db():
    # A private search path keeps destructive revision tests away from app tables.
    schema = f"migration_test_{uuid4().hex}"
    engine = create_engine(settings.database_url, poolclass=NullPool)
    with engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        connection.execute(text(f'SET search_path TO "{schema}"'))
        connection.commit()
        backend = Path(__file__).resolve().parents[2]
        config = Config(str(backend / "alembic.ini"))
        config.set_main_option("script_location", str(backend / "alembic"))
        config.attributes["connection"] = connection
        try:
            yield connection, config
        finally:
            connection.rollback()
            connection.execute(text("SET search_path TO public"))
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            connection.commit()
    engine.dispose()


# Upgrading an empty old database produces the tables and columns required by the current
# models.
def test_empty_legacy_upgrade_matches_current_models(migration_db):
    connection, config = migration_db
    command.upgrade(config, LEGACY_REVISION)
    assert set(inspect(connection).get_table_names()) == LEGACY_TABLES | {
        "alembic_version"
    }
    connection.commit()
    command.upgrade(config, "head")
    assert set(inspect(connection).get_table_names()) == DOMAIN_TABLES | {
        "alembic_version"
    }
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version"))
        == V1_REVISION
    )
    context = MigrationContext.configure(
        connection, opts={"compare_server_default": True}
    )
    assert compare_metadata(context, Base.metadata) == []


# An empty database can move back to the old revision and then upgrade again.
def test_empty_v1_downgrade_and_reupgrade(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    command.downgrade(config, LEGACY_REVISION)
    assert set(inspect(connection).get_table_names()) == LEGACY_TABLES | {
        "alembic_version"
    }
    connection.commit()
    command.upgrade(config, "head")
    assert set(inspect(connection).get_table_names()) == DOMAIN_TABLES | {
        "alembic_version"
    }


# Upgrading an old database containing records is refused without losing its data or revision.
def test_populated_legacy_upgrade_is_refused_without_data_loss(migration_db):
    connection, config = migration_db
    command.upgrade(config, LEGACY_REVISION)
    company_id = uuid4()
    connection.execute(
        text("INSERT INTO companies (id, name) VALUES (:id, 'Preserve me')"),
        {"id": company_id},
    )
    connection.commit()
    with pytest.raises(DBAPIError, match="Cannot upgrade populated schema"):
        command.upgrade(config, "head")
    connection.rollback()
    assert (
        connection.scalar(
            text("SELECT name FROM companies WHERE id = :id"), {"id": company_id}
        )
        == "Preserve me"
    )
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version"))
        == LEGACY_REVISION
    )
    assert set(inspect(connection).get_table_names()) == LEGACY_TABLES | {
        "alembic_version"
    }


# Downgrading a current database containing records is refused without losing its data or
# revision.
def test_populated_v1_downgrade_is_refused_without_data_loss(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    user_id = uuid4()
    connection.execute(
        text("INSERT INTO users (id, name) VALUES (:id, 'Preserve me')"),
        {"id": user_id},
    )
    connection.commit()
    with pytest.raises(DBAPIError, match="Cannot downgrade populated schema"):
        command.downgrade(config, LEGACY_REVISION)
    connection.rollback()
    assert (
        connection.scalar(
            text("SELECT name FROM users WHERE id = :id"), {"id": user_id}
        )
        == "Preserve me"
    )
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version"))
        == V1_REVISION
    )
    assert set(inspect(connection).get_table_names()) == DOMAIN_TABLES | {
        "alembic_version"
    }


# The migrated tables enforce company uniqueness, valid fields, and the expected deletion
# rules.
def test_migrated_schema_has_owner_uniqueness_and_deletion_rules(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    inspector = inspect(connection)
    unique = inspector.get_unique_constraints("companies")
    assert any(
        item["name"] == "uq_company_user_name"
        and item["column_names"] == ["user_id", "normalized_name"]
        for item in unique
    )
    for table in ("contacts", "tracked_roles"):
        company_fk = next(
            item
            for item in inspector.get_foreign_keys(table)
            if item["constrained_columns"] == ["company_id"]
        )
        assert company_fk["options"]["ondelete"] == "SET NULL"
    for table in (
        "status_history",
        "tracked_role_events",
        "event_status_histories",
        "tracked_role_contact_associations",
    ):
        foreign_keys = inspector.get_foreign_keys(table)
        expected_columns = {
            "status_history": {("tracked_role_id",)},
            "tracked_role_events": {("tracked_role_id",)},
            "event_status_histories": {("event_id",)},
            "tracked_role_contact_associations": {
                ("tracked_role_id",),
                ("contact_id",),
            },
        }
        assert {
            tuple(item["constrained_columns"]) for item in foreign_keys
        } == expected_columns[table]
        assert all(
            item["options"].get("ondelete") == "CASCADE" for item in foreign_keys
        )
    role_checks = {
        item["name"] for item in inspector.get_check_constraints("tracked_roles")
    }
    assert {
        "ck_tracked_roles_salary_range",
        "ck_tracked_roles_title",
        "ck_tracked_roles_status",
    } <= role_checks
    event_checks = {
        item["name"] for item in inspector.get_check_constraints("tracked_role_events")
    }
    assert "ck_tracked_role_events_custom_type_name" in event_checks
