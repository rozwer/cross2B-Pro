"""Alembic migration environment configuration.

Supports both common DB and tenant DB migrations.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import models to ensure they're registered with Base
from apps.api.db.models import Base, CommonBase

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Determine which base to use based on migration mode
MIGRATION_MODE = os.getenv("MIGRATION_MODE", "tenant")  # "common" or "tenant"

if MIGRATION_MODE == "common":
    target_metadata = CommonBase.metadata
else:
    target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment."""
    if MIGRATION_MODE == "common":
        return os.getenv(
            "COMMON_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:25432/seo_gen_common",
        )
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:25432/seo_gen_tenant_default",
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
