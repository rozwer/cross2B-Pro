"""Pytest configuration and fixtures for tests."""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def tenant_id():
    """Test tenant ID."""
    return "test_tenant"


@pytest.fixture
def run_id():
    """Test run ID."""
    return "test_run_001"


@pytest.fixture
def mock_pack_id():
    """Mock prompt pack ID for testing."""
    return "mock_pack"


@pytest.fixture
def base_config(mock_pack_id):
    """Base configuration for workflow tests."""
    return {
        "pack_id": mock_pack_id,
        "keyword": "テストキーワード",
        "llm_provider": "gemini",
        "max_tokens": 2000,
        "temperature": 0.7,
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    from unittest.mock import MagicMock

    response = MagicMock()
    response.content = "Mock LLM response content for testing"
    response.model = "mock-model"
    response.input_tokens = 100
    response.output_tokens = 200
    return response


@pytest.fixture
def mock_artifact_store():
    """Mock ArtifactStore for testing."""
    from unittest.mock import AsyncMock, MagicMock
    from apps.api.storage.schemas import ArtifactRef
    from datetime import datetime

    store = MagicMock()
    store.put = AsyncMock(return_value=ArtifactRef(
        path="storage/test/test_run/step0/output.json",
        digest="abc123def456",
        content_type="application/json",
        size_bytes=1024,
        created_at=datetime.now(),
    ))
    store.get = AsyncMock(return_value=b'{"test": "data"}')
    store.exists = AsyncMock(return_value=False)
    store.build_path = MagicMock(return_value="storage/test/test_run/step0/output.json")
    return store


@pytest.fixture
def mock_event_emitter():
    """Mock EventEmitter for testing."""
    from unittest.mock import AsyncMock, MagicMock

    emitter = MagicMock()
    emitter.emit = AsyncMock()
    emitter.emit_step_started = MagicMock()
    emitter.emit_step_succeeded = MagicMock()
    emitter.emit_step_failed = MagicMock()
    return emitter


# Environment configuration
def pytest_configure(config):
    """Configure pytest environment."""
    # Register custom markers
    config.addinivalue_line("markers", "smoke: mark test as smoke test")
    config.addinivalue_line("markers", "slow: mark test as slow (may take > 30s)")
    config.addinivalue_line("markers", "docker: mark test as requiring Docker")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")

    # Set test environment variables
    os.environ.setdefault("USE_MOCK_LLM", "true")
    os.environ.setdefault("MOCK_PACK_ID", "mock_pack")
    os.environ.setdefault("TEMPORAL_HOST", "localhost")
    os.environ.setdefault("TEMPORAL_PORT", "7233")
    os.environ.setdefault("ENVIRONMENT", "test")
