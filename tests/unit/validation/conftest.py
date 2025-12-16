"""Pytest configuration and fixtures for validation tests."""

from pathlib import Path

import pytest

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_FIXTURES_DIR = FIXTURES_DIR / "valid"
INVALID_FIXTURES_DIR = FIXTURES_DIR / "invalid"


@pytest.fixture
def valid_json() -> str:
    """Load valid sample JSON."""
    return (VALID_FIXTURES_DIR / "sample.json").read_text()


@pytest.fixture
def valid_csv() -> str:
    """Load valid sample CSV."""
    return (VALID_FIXTURES_DIR / "sample.csv").read_text()


@pytest.fixture
def json_with_trailing_comma() -> str:
    """Load JSON with trailing commas."""
    return (INVALID_FIXTURES_DIR / "trailing_comma.json").read_text()


@pytest.fixture
def json_with_unescaped_quotes() -> str:
    """Load JSON with unescaped quotes."""
    return (INVALID_FIXTURES_DIR / "unescaped_quotes.json").read_text()


@pytest.fixture
def truncated_json() -> str:
    """Load truncated JSON."""
    return (INVALID_FIXTURES_DIR / "truncated.json").read_text()


@pytest.fixture
def csv_with_column_mismatch() -> str:
    """Load CSV with column count mismatch."""
    return (INVALID_FIXTURES_DIR / "column_mismatch.csv").read_text()


@pytest.fixture
def csv_with_unbalanced_quotes() -> str:
    """Load CSV with unbalanced quotes."""
    return (INVALID_FIXTURES_DIR / "unbalanced_quotes.csv").read_text()


@pytest.fixture
def csv_with_invalid_utf8() -> bytes:
    """Load CSV with invalid UTF-8 encoding."""
    return (INVALID_FIXTURES_DIR / "invalid_utf8.csv").read_bytes()


@pytest.fixture
def simple_json_schema() -> dict:
    """Simple JSON schema for testing."""
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["title"],
    }


@pytest.fixture
def csv_schema() -> dict:
    """CSV schema for testing."""
    return {
        "columns": ["id", "title", "description", "status"],
        "required_columns": ["id", "title"],
        "strict": False,
    }


@pytest.fixture
def strict_csv_schema() -> dict:
    """Strict CSV schema for testing."""
    return {
        "columns": ["id", "title", "description"],
        "required_columns": ["id", "title"],
        "strict": True,
    }
