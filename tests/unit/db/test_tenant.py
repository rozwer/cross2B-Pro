"""Tests for tenant database management with race condition handling."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from apps.api.db.tenant import (
    TenantDBManager,
    TenantIdValidationError,
    validate_tenant_id,
)


class TestValidateTenantId:
    """Tests for tenant_id validation."""

    def test_valid_tenant_ids(self) -> None:
        """Test that valid tenant IDs pass validation."""
        valid_ids = [
            "tenant123",
            "my-tenant",
            "my_tenant",
            "Tenant-123_ABC",
            "a",
            "A" * 64,  # Max length
        ]
        for tenant_id in valid_ids:
            assert validate_tenant_id(tenant_id) is True, f"Expected {tenant_id} to be valid"

    def test_invalid_tenant_ids(self) -> None:
        """Test that invalid tenant IDs fail validation."""
        invalid_ids = [
            "",  # Empty
            " ",  # Whitespace
            "tenant.123",  # Dot not allowed
            "tenant/123",  # Slash not allowed
            "tenant@123",  # At sign not allowed
            "../etc/passwd",  # Path traversal
            "A" * 65,  # Too long
        ]
        for tenant_id in invalid_ids:
            assert validate_tenant_id(tenant_id) is False, f"Expected {tenant_id} to be invalid"


class TestTenantDBManagerEngineCache:
    """Tests for engine cache race condition handling."""

    @pytest.fixture
    def manager(self) -> TenantDBManager:
        """Create a TenantDBManager with mocked dependencies."""
        with patch("apps.api.db.tenant.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock()
            manager = TenantDBManager(common_db_url="postgresql+asyncpg://test:test@localhost/test")
            return manager

    @pytest.mark.asyncio
    async def test_engine_created_once_for_same_tenant(self, manager: TenantDBManager) -> None:
        """Test that engine is created only once even with concurrent requests."""
        tenant_id = "test-tenant"
        db_url = "postgresql+asyncpg://test:test@localhost/tenant_db"

        with patch("apps.api.db.tenant.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            # Simulate concurrent calls
            results = await asyncio.gather(
                manager._get_or_create_engine(tenant_id, db_url),
                manager._get_or_create_engine(tenant_id, db_url),
                manager._get_or_create_engine(tenant_id, db_url),
            )

            # All should return the same engine
            assert all(r == mock_engine for r in results)

            # Engine should be created only once (double-checked locking)
            assert mock_create.call_count == 1

    @pytest.mark.asyncio
    async def test_different_tenants_get_different_engines(self, manager: TenantDBManager) -> None:
        """Test that different tenants get different engines."""
        engines_created = []

        def create_engine_side_effect(*args, **kwargs):
            engine = MagicMock()
            engines_created.append(engine)
            return engine

        with patch("apps.api.db.tenant.create_async_engine") as mock_create:
            mock_create.side_effect = create_engine_side_effect

            engine1 = await manager._get_or_create_engine("tenant-1", "postgresql+asyncpg://localhost/db1")
            engine2 = await manager._get_or_create_engine("tenant-2", "postgresql+asyncpg://localhost/db2")

            assert engine1 != engine2
            assert len(engines_created) == 2

    @pytest.mark.asyncio
    async def test_fast_path_returns_cached_engine(self, manager: TenantDBManager) -> None:
        """Test that cached engine is returned without acquiring lock."""
        tenant_id = "cached-tenant"
        db_url = "postgresql+asyncpg://localhost/cached_db"

        with patch("apps.api.db.tenant.create_async_engine") as mock_create:
            mock_engine = MagicMock()
            mock_create.return_value = mock_engine

            # First call creates the engine
            await manager._get_or_create_engine(tenant_id, db_url)
            assert mock_create.call_count == 1

            # Pre-cache the engine manually to test fast path
            manager._engines[tenant_id] = mock_engine

            # Second call should use fast path (no lock acquisition needed)
            result = await manager._get_or_create_engine(tenant_id, db_url)
            assert result == mock_engine

            # Should still be 1 call (fast path doesn't create)
            assert mock_create.call_count == 1


class TestTenantDBManagerValidation:
    """Tests for tenant_id validation in TenantDBManager methods."""

    @pytest.mark.asyncio
    async def test_get_session_validates_tenant_id(self) -> None:
        """Test that get_session validates tenant_id format."""
        with patch("apps.api.db.tenant.create_async_engine"):
            manager = TenantDBManager(common_db_url="postgresql+asyncpg://test:test@localhost/test")

            with pytest.raises(TenantIdValidationError) as exc_info:
                async with manager.get_session("../invalid/tenant"):
                    pass

            assert "Invalid tenant_id format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_engine_validates_tenant_id(self) -> None:
        """Test that get_engine validates tenant_id format."""
        with patch("apps.api.db.tenant.create_async_engine"):
            manager = TenantDBManager(common_db_url="postgresql+asyncpg://test:test@localhost/test")

            with pytest.raises(TenantIdValidationError):
                await manager.get_engine("invalid@tenant")
