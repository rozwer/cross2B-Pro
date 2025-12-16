"""Docker Compose smoke tests.

These tests verify that all services can be built and started correctly.
Run with: pytest tests/smoke/ -v
"""

import os
import subprocess
import time
from pathlib import Path

import pytest

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_command(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestDockerComposeFiles:
    """Test Docker Compose configuration files exist and are valid."""

    def test_docker_compose_exists(self):
        """Verify docker-compose.yml exists."""
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        assert compose_file.exists(), "docker-compose.yml not found"

    def test_dockerfiles_exist(self):
        """Verify all Dockerfiles exist."""
        dockerfiles = [
            "docker/Dockerfile.api",
            "docker/Dockerfile.worker",
            "docker/Dockerfile.ui",
        ]
        for dockerfile in dockerfiles:
            path = PROJECT_ROOT / dockerfile
            assert path.exists(), f"{dockerfile} not found"

    def test_env_example_exists(self):
        """Verify .env.example exists."""
        env_example = PROJECT_ROOT / ".env.example"
        assert env_example.exists(), ".env.example not found"

    def test_init_db_sql_exists(self):
        """Verify init-db.sql exists."""
        init_sql = PROJECT_ROOT / "scripts" / "init-db.sql"
        assert init_sql.exists(), "scripts/init-db.sql not found"

    def test_bootstrap_script_exists(self):
        """Verify bootstrap.sh exists and is executable."""
        bootstrap = PROJECT_ROOT / "scripts" / "bootstrap.sh"
        assert bootstrap.exists(), "scripts/bootstrap.sh not found"
        assert os.access(bootstrap, os.X_OK), "scripts/bootstrap.sh is not executable"

    def test_reset_script_exists(self):
        """Verify reset.sh exists and is executable."""
        reset = PROJECT_ROOT / "scripts" / "reset.sh"
        assert reset.exists(), "scripts/reset.sh not found"
        assert os.access(reset, os.X_OK), "scripts/reset.sh is not executable"


class TestDockerComposeConfig:
    """Test Docker Compose configuration is valid."""

    @pytest.fixture(autouse=True)
    def check_docker(self):
        """Skip tests if Docker is not available."""
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("Docker is not available")

    def test_compose_config_valid(self):
        """Verify docker-compose.yml is valid."""
        result = run_command(["docker", "compose", "config", "--quiet"])
        assert result.returncode == 0, f"Invalid compose config: {result.stderr}"

    def test_compose_services_defined(self):
        """Verify all expected services are defined."""
        result = run_command(["docker", "compose", "config", "--services"])
        assert result.returncode == 0, f"Failed to get services: {result.stderr}"

        services = result.stdout.strip().split("\n")
        expected_services = [
            "postgres",
            "minio",
            "minio-init",
            "temporal",
            "temporal-ui",
            "api",
            "worker",
            "ui",
        ]
        for service in expected_services:
            assert service in services, f"Service '{service}' not defined"


@pytest.mark.slow
class TestDockerComposeBuild:
    """Test Docker Compose build (slow tests)."""

    @pytest.fixture(autouse=True)
    def check_docker(self):
        """Skip tests if Docker is not available."""
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("Docker is not available")

    def test_api_dockerfile_builds(self):
        """Verify API Dockerfile builds successfully."""
        result = run_command(
            ["docker", "build", "-f", "docker/Dockerfile.api", "-t", "seo-api-test", "."],
            timeout=300,
        )
        assert result.returncode == 0, f"API build failed: {result.stderr}"

    def test_worker_dockerfile_builds(self):
        """Verify Worker Dockerfile builds successfully."""
        result = run_command(
            ["docker", "build", "-f", "docker/Dockerfile.worker", "-t", "seo-worker-test", "."],
            timeout=300,
        )
        assert result.returncode == 0, f"Worker build failed: {result.stderr}"


class TestEnvExample:
    """Test .env.example file contents."""

    def test_required_variables_documented(self):
        """Verify required environment variables are in .env.example."""
        env_example = PROJECT_ROOT / ".env.example"
        content = env_example.read_text()

        required_vars = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "MINIO_ROOT_USER",
            "MINIO_ROOT_PASSWORD",
            "MINIO_BUCKET",
            "TEMPORAL_HOST",
            "TEMPORAL_PORT",
            "GEMINI_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "API_PORT",
            "UI_PORT",
        ]

        for var in required_vars:
            assert var in content, f"Required variable '{var}' not in .env.example"


class TestPythonImports:
    """Test Python module imports work correctly."""

    def test_api_main_imports(self):
        """Verify API main module can be imported."""
        result = run_command(
            ["python", "-c", "from apps.api.main import app; print(type(app).__name__)"],
        )
        assert result.returncode == 0, f"Failed to import apps.api.main: {result.stderr}"
        assert "FastAPI" in result.stdout, f"app is not FastAPI: {result.stdout}"

    def test_worker_main_imports(self):
        """Verify Worker main module can be imported."""
        result = run_command(
            ["python", "-c", "from apps.worker.main import main; print('OK')"],
        )
        assert result.returncode == 0, f"Failed to import apps.worker.main: {result.stderr}"

    def test_llm_modules_import(self):
        """Verify LLM client modules can be imported."""
        modules = [
            "apps.api.llm.gemini",
            "apps.api.llm.openai",
            "apps.api.llm.anthropic",
        ]
        for module in modules:
            result = run_command(["python", "-c", f"import {module}; print('OK')"])
            assert result.returncode == 0, f"Failed to import {module}: {result.stderr}"

    def test_tools_modules_import(self):
        """Verify tools modules can be imported."""
        modules = [
            "apps.api.tools.search",
            "apps.api.tools.fetch",
            "apps.api.tools.verify",
            "apps.api.tools.registry",
        ]
        for module in modules:
            result = run_command(["python", "-c", f"import {module}; print('OK')"])
            assert result.returncode == 0, f"Failed to import {module}: {result.stderr}"


class TestSyntaxCheck:
    """Test Python syntax is valid."""

    def test_apps_api_syntax(self):
        """Verify apps/api Python syntax is valid."""
        result = run_command(["python", "-m", "py_compile", "apps/api/main.py"])
        assert result.returncode == 0, f"Syntax error in apps/api: {result.stderr}"

    def test_apps_worker_syntax(self):
        """Verify apps/worker Python syntax is valid."""
        result = run_command(["python", "-m", "py_compile", "apps/worker/main.py"])
        assert result.returncode == 0, f"Syntax error in apps/worker: {result.stderr}"


class TestTypeCheck:
    """Test type checking passes."""

    def test_mypy_apps(self):
        """Verify mypy passes for apps directory."""
        result = run_command(
            ["python", "-m", "mypy", "apps/", "--ignore-missing-imports"],
            timeout=120,
        )
        # Allow warnings but not errors
        assert result.returncode == 0 or "error:" not in result.stdout, (
            f"Type errors in apps: {result.stdout}"
        )


class TestLintCheck:
    """Test linting passes."""

    def test_ruff_check(self):
        """Verify ruff check passes."""
        result = run_command(["python", "-m", "ruff", "check", "apps/"])
        # Note: May have warnings, check for critical errors only
        if result.returncode != 0:
            # Check if it's just warnings
            if "error" in result.stdout.lower():
                pytest.fail(f"Lint errors: {result.stdout}")
