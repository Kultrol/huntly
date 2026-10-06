from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the app database URL instead of the placeholder in alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

# Register all model tables for autogenerate.
import app.models  # noqa: F401
from app.core.database import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL without connecting to the database."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations using a database connection."""

    def migrate(connection) -> None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    # Python callers can supply an existing connection.
    connection = config.attributes.get("connection")
    if connection is not None:
        migrate(connection)
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        migrate(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
