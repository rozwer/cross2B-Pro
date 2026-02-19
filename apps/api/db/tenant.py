"""Tenant database connection management.

TenantDBManager handles:
- Connection pooling per tenant
- Database creation for new tenants
- Migration management

VULN-004 + REVIEW-007: SQLインジェクション対策
- tenant_id のバリデーション（安全な文字のみ許可）
- 識別子のエスケープ
"""

import asyncio
import logging
import os
import re
import time
from collections import OrderedDict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base, Tenant

logger = logging.getLogger(__name__)

# Maximum number of tenant engines to cache (LRU eviction beyond this limit)
MAX_CACHED_ENGINES = int(os.getenv("MAX_TENANT_ENGINES", "50"))

# VULN-004: tenant_id に許可する文字パターン（英数字とハイフン、アンダースコアのみ）
SAFE_TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_tenant_id(tenant_id: str) -> bool:
    """tenant_id が安全な形式かを検証（VULN-004: SQLインジェクション対策）

    Args:
        tenant_id: 検証対象のテナントID

    Returns:
        bool: 安全な形式の場合True
    """
    if not tenant_id:
        return False
    return bool(SAFE_TENANT_ID_PATTERN.match(tenant_id))


def escape_identifier(name: str) -> str:
    """PostgreSQL識別子をエスケープ（VULN-004: SQLインジェクション対策）

    二重引用符内での識別子エスケープ
    """
    # 二重引用符を二重化してエスケープ
    return name.replace('"', '""')


class TenantDBError(Exception):
    """Error in tenant database operations."""

    pass


class TenantNotFoundError(TenantDBError):
    """Tenant does not exist."""

    pass


class TenantIdValidationError(TenantDBError):
    """Invalid tenant ID format."""

    pass


class _CachedEngine(NamedTuple):
    """Cached engine with metadata for LRU tracking."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    last_used: float


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
        self.common_db_url: str = (
            common_db_url or os.getenv("COMMON_DATABASE_URL") or "postgresql+asyncpg://postgres:postgres@localhost:25432/seo_gen_common"
        )
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.max_cached_engines = MAX_CACHED_ENGINES

        # LRU cache of tenant engines (OrderedDict maintains insertion/access order)
        # Structure: {tenant_id: _CachedEngine}
        self._engine_cache: OrderedDict[str, _CachedEngine] = OrderedDict()

        # Lock for thread-safe engine creation (prevents race condition creating duplicate engines)
        self._engine_lock = asyncio.Lock()

        # Pending engine disposals (to avoid blocking during cache eviction)
        self._pending_disposals: list[AsyncEngine] = []

        # Common DB engine
        self._common_engine: AsyncEngine = create_async_engine(
            self.common_db_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Health check before each connection use
        )
        self._common_session_factory = async_sessionmaker(
            self._common_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def _get_tenant_db_url(self, tenant_id: str) -> str:
        """Fetch tenant database URL from common DB.

        Args:
            tenant_id: Tenant identifier (validated before DB query)

        Returns:
            Database URL for the tenant

        Raises:
            TenantIdValidationError: If tenant_id format is invalid
            TenantNotFoundError: If tenant does not exist
            TenantDBError: If tenant is inactive
        """
        # Double validation: ensure tenant_id is validated even if called directly
        if not validate_tenant_id(tenant_id):
            logger.warning(f"Invalid tenant_id format in _get_tenant_db_url: {tenant_id[:20]}...")
            raise TenantIdValidationError(f"Invalid tenant_id format. Must match pattern: {SAFE_TENANT_ID_PATTERN.pattern}")

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

    async def _get_or_create_engine(self, tenant_id: str, db_url: str) -> _CachedEngine:
        """Get or create engine for tenant (thread-safe with asyncio.Lock).

        Uses double-checked locking pattern: first check without lock for fast path,
        then acquire lock and check again to prevent race condition.

        LRU eviction: When cache exceeds max_cached_engines, oldest unused engines are disposed.

        Returns:
            _CachedEngine containing engine, session_factory, and last_used timestamp
        """
        # Fast path: check without lock and update last_used
        if tenant_id in self._engine_cache:
            # Move to end (most recently used) and update timestamp
            cached = self._engine_cache[tenant_id]
            self._engine_cache.move_to_end(tenant_id)
            self._engine_cache[tenant_id] = _CachedEngine(
                engine=cached.engine,
                session_factory=cached.session_factory,
                last_used=time.time(),
            )
            return self._engine_cache[tenant_id]

        # Slow path: acquire lock and check again
        async with self._engine_lock:
            # Double-check after acquiring lock (another coroutine may have created it)
            if tenant_id in self._engine_cache:
                cached = self._engine_cache[tenant_id]
                self._engine_cache.move_to_end(tenant_id)
                self._engine_cache[tenant_id] = _CachedEngine(
                    engine=cached.engine,
                    session_factory=cached.session_factory,
                    last_used=time.time(),
                )
                return self._engine_cache[tenant_id]

            # Evict oldest engines if cache is full
            await self._evict_oldest_engines()

            # Create new engine
            engine = create_async_engine(
                db_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,  # Health check before each connection use
            )
            session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            cached_engine = _CachedEngine(
                engine=engine,
                session_factory=session_factory,
                last_used=time.time(),
            )
            self._engine_cache[tenant_id] = cached_engine
            logger.debug(f"Created engine for tenant {tenant_id}, cache size: {len(self._engine_cache)}")
            return cached_engine

    async def _evict_oldest_engines(self) -> None:
        """Evict oldest engines when cache exceeds limit.

        Must be called while holding _engine_lock.
        """
        while len(self._engine_cache) >= self.max_cached_engines:
            # Pop oldest (first) item
            oldest_tenant_id, oldest_cached = self._engine_cache.popitem(last=False)
            logger.info(f"Evicting engine for tenant {oldest_tenant_id} (LRU cache full)")

            # Schedule disposal without blocking (to avoid deadlock)
            self._pending_disposals.append(oldest_cached.engine)

        # Process pending disposals asynchronously
        if self._pending_disposals:
            engines_to_dispose = self._pending_disposals.copy()
            self._pending_disposals.clear()
            for engine in engines_to_dispose:
                try:
                    await engine.dispose()
                except Exception as e:
                    logger.warning(f"Error disposing engine: {e}")

    @asynccontextmanager
    async def get_session(
        self,
        tenant_id: str,
        isolation_level: str | None = None,
    ) -> AsyncGenerator[AsyncSession, None]:
        """Get a session for the specified tenant's database.

        Args:
            tenant_id: Tenant identifier
            isolation_level: Optional transaction isolation level.
                Valid values: "SERIALIZABLE", "REPEATABLE READ", "READ COMMITTED", "READ UNCOMMITTED"
                Default: Uses database default (typically "READ COMMITTED" for PostgreSQL)

        Yields:
            AsyncSession for the tenant's database

        Raises:
            TenantIdValidationError: If tenant_id format is invalid
            TenantNotFoundError: If tenant does not exist
            TenantDBError: If tenant is inactive or connection fails
        """
        # VULN-004: tenant_id のバリデーション
        if not validate_tenant_id(tenant_id):
            logger.warning(f"Invalid tenant_id format in get_session: {tenant_id[:20]}...")
            raise TenantIdValidationError(f"Invalid tenant_id format. Must match pattern: {SAFE_TENANT_ID_PATTERN.pattern}")

        db_url = await self._get_tenant_db_url(tenant_id)
        cached_engine = await self._get_or_create_engine(tenant_id, db_url)

        async with cached_engine.session_factory() as session:
            try:
                if isolation_level:
                    # Set isolation level for this transaction
                    await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
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
            TenantIdValidationError: If tenant_id format is invalid
            TenantDBError: If database creation fails
        """
        # VULN-004: tenant_id のバリデーション
        if not validate_tenant_id(tenant_id):
            logger.warning(f"Invalid tenant_id format rejected: {tenant_id[:20]}...")
            raise TenantIdValidationError(f"Invalid tenant_id format. Must match pattern: {SAFE_TENANT_ID_PATTERN.pattern}")

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

        # VULN-004: 識別子をエスケープしてSQL実行
        escaped_db_name = escape_identifier(db_name)

        with sync_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not result.fetchone():
                conn.execute(text(f'CREATE DATABASE "{escaped_db_name}"'))

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
            TenantIdValidationError: If tenant_id format is invalid
            TenantDBError: If confirm is False or deletion fails
        """
        # VULN-004: tenant_id のバリデーション
        if not validate_tenant_id(tenant_id):
            logger.warning(f"Invalid tenant_id format in delete_tenant_db: {tenant_id[:20]}...")
            raise TenantIdValidationError(f"Invalid tenant_id format. Must match pattern: {SAFE_TENANT_ID_PATTERN.pattern}")

        if not confirm:
            raise TenantDBError("Must confirm=True to delete tenant database")

        db_url = await self._get_tenant_db_url(tenant_id)
        db_name = db_url.split("/")[-1]

        # VULN-004: db_name のバリデーション（追加の安全策）
        expected_prefix = "seo_gen_tenant_"
        if not db_name.startswith(expected_prefix):
            logger.error(f"Unexpected database name format: {db_name}")
            raise TenantDBError("Unexpected database name format")

        # Close any existing connections
        if tenant_id in self._engine_cache:
            cached = self._engine_cache.pop(tenant_id)
            await cached.engine.dispose()

        # Drop database
        from sqlalchemy import create_engine

        sync_url = self.common_db_url.replace("+asyncpg", "")
        sync_engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")

        # VULN-004: 識別子をエスケープ
        escaped_db_name = escape_identifier(db_name)

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
            conn.execute(text(f'DROP DATABASE IF EXISTS "{escaped_db_name}"'))

        # Mark tenant as inactive (keep audit trail)
        async with self._common_session_factory() as session:
            await session.execute(
                text("UPDATE tenants SET is_active = false WHERE id = :id"),
                {"id": tenant_id},
            )
            await session.commit()

    async def close(self) -> None:
        """Close all database connections."""
        for cached in self._engine_cache.values():
            await cached.engine.dispose()
        await self._common_engine.dispose()
        self._engine_cache.clear()

    async def get_engine(self, tenant_id: str) -> AsyncEngine:
        """Get or create engine for tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            AsyncEngine for the tenant's database

        Raises:
            TenantIdValidationError: If tenant_id format is invalid
            TenantNotFoundError: If tenant does not exist
        """
        if not validate_tenant_id(tenant_id):
            raise TenantIdValidationError(f"Invalid tenant_id format. Must match pattern: {SAFE_TENANT_ID_PATTERN.pattern}")

        db_url = await self._get_tenant_db_url(tenant_id)
        cached = await self._get_or_create_engine(tenant_id, db_url)
        return cached.engine


# =============================================================================
# Module-level convenience functions
# =============================================================================

# Global manager instance (lazy initialized)
_tenant_manager: TenantDBManager | None = None


def get_tenant_manager() -> TenantDBManager:
    """Get the global TenantDBManager instance."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantDBManager()
    return _tenant_manager


async def get_tenant_engine(tenant_id: str) -> AsyncEngine:
    """Get engine for a tenant (convenience function).

    Args:
        tenant_id: Tenant identifier

    Returns:
        AsyncEngine for the tenant's database
    """
    manager = get_tenant_manager()
    return await manager.get_engine(tenant_id)
