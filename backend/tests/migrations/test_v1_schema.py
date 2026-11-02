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
AUTH_REVISION = "a6d4f9b2c813"
LEGACY_TABLES = {
    "companies",
    "contacts",
    "job_applications",
    "application_status_history",
    "interviews",
}
DOMAIN_TABLES = {
    "users",
    "auth_sessions",
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
        == AUTH_REVISION
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
    command.upgrade(config, V1_REVISION)
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
    assert set(inspect(connection).get_table_names()) == DOMAIN_TABLES - {
        "auth_sessions"
    } | {"alembic_version"}


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


def test_auth_upgrade_preserves_existing_user_and_company(migration_db):
    connection, config = migration_db
    command.upgrade(config, V1_REVISION)
    user_id, company_id = uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, name) VALUES (:id, 'Existing owner')"),
        {"id": user_id},
    )
    connection.execute(
        text(
            "INSERT INTO companies (id, user_id, name, normalized_name) "
            "VALUES (:id, :user_id, 'Existing company', 'existing company')"
        ),
        {"id": company_id, "user_id": user_id},
    )
    connection.commit()

    command.upgrade(config, "head")

    user = connection.execute(
        text("SELECT name, email, password_hash FROM users WHERE id = :id"),
        {"id": user_id},
    ).one()
    assert tuple(user) == ("Existing owner", None, None)
    company = connection.execute(
        text("SELECT name, user_id FROM companies WHERE id = :id"),
        {"id": company_id},
    ).one()
    assert tuple(company) == ("Existing company", user_id)
    assert connection.scalar(text("SELECT COUNT(*) FROM auth_sessions")) == 0


@pytest.mark.parametrize(
    "email, password_hash", [("owner@example.com", None), (None, "password-hash")]
)
def test_auth_migration_requires_credentials_together(
    migration_db, email, password_hash
):
    connection, config = migration_db
    command.upgrade(config, "head")
    with pytest.raises(DBAPIError, match="ck_users_credentials_pair"):
        connection.execute(
            text(
                "INSERT INTO users (id, name, email, password_hash) "
                "VALUES (:id, 'Owner', :email, :password_hash)"
            ),
            {"id": uuid4(), "email": email, "password_hash": password_hash},
        )


def test_auth_migration_rejects_duplicate_emails(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    connection.execute(
        text(
            "INSERT INTO users (id, name, email, password_hash) "
            "VALUES (:id, 'Owner', 'owner@example.com', 'password-hash')"
        ),
        {"id": uuid4()},
    )
    connection.commit()
    with pytest.raises(DBAPIError, match="uq_users_email"):
        connection.execute(
            text(
                "INSERT INTO users (id, name, email, password_hash) "
                "VALUES (:id, 'Other owner', 'owner@example.com', 'other-hash')"
            ),
            {"id": uuid4()},
        )


def test_auth_session_foreign_key_cascades_and_hash_is_unique(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    user_id, session_id = uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, name) VALUES (:id, 'Owner')"),
        {"id": user_id},
    )
    statement = text(
        "INSERT INTO auth_sessions "
        "(id, user_id, token_hash, csrf_token_hash, created_at, expires_at) "
        "VALUES (:id, :user_id, :token_hash, :csrf_token_hash, "
        "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '1 day')"
    )
    fields = {
        "id": session_id,
        "user_id": user_id,
        "token_hash": "a" * 64,
        "csrf_token_hash": "b" * 64,
    }
    connection.execute(statement, fields)
    connection.commit()
    with pytest.raises(DBAPIError, match="auth_sessions_token_hash_key"):
        connection.execute(statement, {**fields, "id": uuid4()})
    connection.rollback()
    connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    assert connection.scalar(text("SELECT COUNT(*) FROM auth_sessions")) == 0


def test_auth_session_rejects_nonexistent_owner(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    with pytest.raises(DBAPIError, match="auth_sessions_user_id_fkey"):
        connection.execute(
            text(
                "INSERT INTO auth_sessions "
                "(id, user_id, token_hash, csrf_token_hash, created_at, expires_at) "
                "VALUES (:id, :user_id, :token_hash, :csrf_token_hash, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '1 day')"
            ),
            {
                "id": uuid4(),
                "user_id": uuid4(),
                "token_hash": "a" * 64,
                "csrf_token_hash": "b" * 64,
            },
        )


def test_auth_downgrade_refuses_to_discard_credentials(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    user_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO users (id, name, email, password_hash) "
            "VALUES (:id, 'Owner', 'owner@example.com', 'preserve-hash')"
        ),
        {"id": user_id},
    )
    connection.commit()
    with pytest.raises(DBAPIError, match="Cannot downgrade populated authentication"):
        command.downgrade(config, V1_REVISION)
    connection.rollback()
    assert (
        connection.scalar(
            text("SELECT password_hash FROM users WHERE id = :id"), {"id": user_id}
        )
        == "preserve-hash"
    )
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version"))
        == AUTH_REVISION
    )


def test_auth_downgrade_refuses_to_discard_sessions(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    user_id, session_id = uuid4(), uuid4()
    connection.execute(
        text("INSERT INTO users (id, name) VALUES (:id, 'Existing owner')"),
        {"id": user_id},
    )
    connection.execute(
        text(
            "INSERT INTO auth_sessions "
            "(id, user_id, token_hash, csrf_token_hash, created_at, expires_at) "
            "VALUES (:id, :user_id, :token_hash, :csrf_token_hash, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '1 day')"
        ),
        {
            "id": session_id,
            "user_id": user_id,
            "token_hash": "a" * 64,
            "csrf_token_hash": "b" * 64,
        },
    )
    connection.commit()
    with pytest.raises(DBAPIError, match="Cannot downgrade populated authentication"):
        command.downgrade(config, V1_REVISION)
    connection.rollback()
    assert (
        connection.scalar(
            text("SELECT token_hash FROM auth_sessions WHERE id = :id"),
            {"id": session_id},
        )
        == "a" * 64
    )
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version"))
        == AUTH_REVISION
    )


def test_auth_downgrade_preserves_credentialless_users(migration_db):
    connection, config = migration_db
    command.upgrade(config, "head")
    user_id = uuid4()
    connection.execute(
        text("INSERT INTO users (id, name) VALUES (:id, 'Existing owner')"),
        {"id": user_id},
    )
    connection.commit()

    command.downgrade(config, V1_REVISION)

    assert (
        connection.scalar(
            text("SELECT name FROM users WHERE id = :id"), {"id": user_id}
        )
        == "Existing owner"
    )
    assert "auth_sessions" not in inspect(connection).get_table_names()
    assert "email" not in {
        column["name"] for column in inspect(connection).get_columns("users")
    }
