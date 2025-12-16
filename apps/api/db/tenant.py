"""Tenant database connection management.

TenantDBManager handles:
- Connection pooling per tenant
- Database creation for new tenants
- Migration management
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .models import Base, CommonBase, Tenant


class TenantDBError(Exception):
    """Error in tenant database operations."""

    pass


class TenantNotFoundError(TenantDBError):
    """Tenant does not exist."""

    pass


class TenantDBManager:
    """Manages connections to tenant-specific databases.

    Each tenant has a physically isolated database.
    Connection strings are stored in the common management DB.
    """

    def __init__(
        self,
        common_db_url: str | None = None,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """Initialize tenant DB manager.

        Args:
            common_db_url: URL for common management DB
            pool_size: Connection pool size per tenant
            max_overflow: Max overflow connections
        """
        self.common_db_url: str = common_db_url or os.getenv(
            "COMMON_DATABASE_URL"
        ) or "postgresql+asyncpg://postgres:postgres@localhost:5432/seo_gen_common"
        self.pool_size = pool_size
        self.max_overflow = max_overflow

        # Cache of tenant engines and session factories
        self._engines: dict[str, AsyncEngine] = {}
        self._session_factories: dict[str, async_sessionmaker[AsyncSession]] = {}

        # Common DB engine
        self._common_engine: AsyncEngine = create_async_engine(
            self.common_db_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )
        self._common_session_factory = async_sessionmaker(
            self._common_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def _get_tenant_db_url(self, tenant_id: str) -> str:
        """Fetch tenant database URL from common DB."""
        async with self._common_session_factory() as session:
            result = await session.execute(
                text("SELECT database_url, is_active FROM tenants WHERE id = :id"),
                {"id": tenant_id},
            )
            row = result.fetchone()
            if not row:
                raise TenantNotFoundError(f"Tenant not found: {tenant_id}")
            if not row.is_active:
                raise TenantDBError(f"Tenant is inactive: {tenant_id}")
            return str(row.database_url)

    def _get_or_create_engine(self, tenant_id: str, db_url: str) -> AsyncEngine:
        """Get or create engine for tenant."""
        if tenant_id not in self._engines:
            engine = create_async_engine(
                db_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
            )
            self._engines[tenant_id] = engine
            self._session_factories[tenant_id] = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._engines[tenant_id]

    @asynccontextmanager
    async def get_session(self, tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
        """Get a session for the specified tenant's database.

        Args:
            tenant_id: Tenant identifier

        Yields:
            AsyncSession for the tenant's database

        Raises:
            TenantNotFoundError: If tenant does not exist
            TenantDBError: If tenant is inactive or connection fails
        """
        db_url = await self._get_tenant_db_url(tenant_id)
        self._get_or_create_engine(tenant_id, db_url)

        async with self._session_factories[tenant_id]() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def get_common_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a session for the common management database.

        Yields:
            AsyncSession for the common database
        """
        async with self._common_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_tenant_db(
        self,
        tenant_id: str,
        name: str,
        db_host: str | None = None,
        db_port: int = 5432,
        db_user: str | None = None,
        db_password: str | None = None,
    ) -> str:
        """Create a new tenant database.

        Args:
            tenant_id: Unique tenant identifier
            name: Human-readable tenant name
            db_host: Database host (default from env)
            db_port: Database port (default: 5432)
            db_user: Database user (default from env)
            db_password: Database password (default from env)

        Returns:
            The database URL for the new tenant

        Raises:
            TenantDBError: If database creation fails
        """
        db_host = db_host or os.getenv("DB_HOST", "localhost")
        db_user = db_user or os.getenv("DB_USER", "postgres")
        db_password = db_password or os.getenv("DB_PASSWORD", "postgres")

        db_name = f"seo_gen_tenant_{tenant_id}"
        db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        # Create database using common DB connection
        # Note: Need to use raw connection for CREATE DATABASE
        from sqlalchemy import create_engine

        sync_url = self.common_db_url.replace("+asyncpg", "")
        sync_engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")

        with sync_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not result.fetchone():
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))

        # Run migrations on new database
        await self._run_tenant_migrations(db_url)

        # Register tenant in common DB
        async with self._common_session_factory() as session:
            session.add(
                Tenant(
                    id=tenant_id,
                    name=name,
                    database_url=db_url,
                    is_active=True,
                )
            )
            await session.commit()

        return db_url

    async def _run_tenant_migrations(self, db_url: str) -> None:
        """Run all migrations on a tenant database.

        Creates all tables defined in Base.
        """
        sync_url = db_url.replace("+asyncpg", "")
        from sqlalchemy import create_engine

        engine = create_engine(sync_url)
        Base.metadata.create_all(engine)
        engine.dispose()

    async def delete_tenant_db(self, tenant_id: str, confirm: bool = False) -> None:
        """Delete a tenant database (GDPR compliance).

        Args:
            tenant_id: Tenant identifier
            confirm: Must be True to proceed

        Raises:
            TenantDBError: If confirm is False or deletion fails
        """
        if not confirm:
            raise TenantDBError("Must confirm=True to delete tenant database")

        db_url = await self._get_tenant_db_url(tenant_id)
        db_name = db_url.split("/")[-1]

        # Close any existing connections
        if tenant_id in self._engines:
            await self._engines[tenant_id].dispose()
            del self._engines[tenant_id]
            del self._session_factories[tenant_id]

        # Drop database
        from sqlalchemy import create_engine

        sync_url = self.common_db_url.replace("+asyncpg", "")
        sync_engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")

        with sync_engine.connect() as conn:
            # Terminate existing connections
            conn.execute(
                text(
                    """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :name AND pid <> pg_backend_pid()
            """
                ),
                {"name": db_name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))

        # Mark tenant as inactive (keep audit trail)
        async with self._common_session_factory() as session:
            await session.execute(
                text("UPDATE tenants SET is_active = false WHERE id = :id"),
                {"id": tenant_id},
            )
            await session.commit()

    async def close(self) -> None:
        """Close all database connections."""
        for engine in self._engines.values():
            await engine.dispose()
        await self._common_engine.dispose()
        self._engines.clear()
        self._session_factories.clear()
