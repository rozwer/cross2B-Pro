"""Tests for GitHubService.

Tests cover:
- Repository URL validation
- Access checking
- File push/pull operations
- Error handling (401, 403, 404, 422, rate limits)
"""

import base64
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.services.github import (
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubService,
    GitHubValidationError,
)


@pytest.fixture
def github_service():
    """Create GitHubService with test token."""
    return GitHubService(token="test-token")


class TestRepoUrlValidation:
    """Test repository URL validation."""

    def test_valid_url(self, github_service: GitHubService):
        """Valid GitHub URL should parse correctly."""
        owner, repo = github_service._parse_repo_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_valid_url_with_dots(self, github_service: GitHubService):
        """Repository name with dots should parse correctly."""
        owner, repo = github_service._parse_repo_url("https://github.com/owner/repo.name")
        assert owner == "owner"
        assert repo == "repo.name"

    def test_valid_url_with_underscores(self, github_service: GitHubService):
        """Repository name with underscores should parse correctly."""
        owner, repo = github_service._parse_repo_url("https://github.com/owner/repo_name")
        assert owner == "owner"
        assert repo == "repo_name"

    def test_invalid_url_missing_owner(self, github_service: GitHubService):
        """URL without owner should raise ValidationError."""
        with pytest.raises(GitHubValidationError):
            github_service._parse_repo_url("https://github.com/repo")

    def test_invalid_url_wrong_host(self, github_service: GitHubService):
        """Non-GitHub URL should raise ValidationError."""
        with pytest.raises(GitHubValidationError):
            github_service._parse_repo_url("https://gitlab.com/owner/repo")

    def test_invalid_url_with_path(self, github_service: GitHubService):
        """URL with extra path should raise ValidationError."""
        with pytest.raises(GitHubValidationError):
            github_service._parse_repo_url("https://github.com/owner/repo/tree/main")


class TestCheckAccess:
    """Test repository access checking."""

    @pytest.mark.asyncio
    async def test_check_access_success(self, github_service: GitHubService):
        """Successful access check should return permissions."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "permissions": {
                "pull": True,
                "push": True,
                "admin": False,
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            permissions = await github_service.check_access("https://github.com/owner/repo")

            assert permissions.read is True
            assert permissions.write is True
            assert permissions.admin is False

    @pytest.mark.asyncio
    async def test_check_access_401(self, github_service: GitHubService):
        """401 response should raise AuthenticationError."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(GitHubAuthenticationError):
                await github_service.check_access("https://github.com/owner/repo")

    @pytest.mark.asyncio
    async def test_check_access_404(self, github_service: GitHubService):
        """404 response should raise NotFoundError."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(GitHubNotFoundError):
                await github_service.check_access("https://github.com/owner/repo")


class TestPushFile:
    """Test file push operations."""

    @pytest.mark.asyncio
    async def test_push_file_new(self, github_service: GitHubService):
        """Pushing a new file should return commit SHA."""
        # Mock get file SHA (not found)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 404

        # Mock put file response
        mock_put_response = MagicMock()
        mock_put_response.status_code = 201
        mock_put_response.json.return_value = {"commit": {"sha": "abc123def456"}}

        async def mock_request(method: str, *args, **kwargs):  # noqa: ARG001
            if method == "get":
                return mock_get_response
            return mock_put_response

        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.get = AsyncMock(return_value=mock_get_response)
            instance.put = AsyncMock(return_value=mock_put_response)

            sha = await github_service.push_file(
                "https://github.com/owner/repo",
                "path/to/file.json",
                b'{"key": "value"}',
                "Add new file",
            )

            assert sha == "abc123def456"

    @pytest.mark.asyncio
    async def test_push_file_permission_denied(self, github_service: GitHubService):
        """403 response should raise PermissionError."""
        mock_get_response = MagicMock()
        mock_get_response.status_code = 404

        mock_put_response = MagicMock()
        mock_put_response.status_code = 403
        mock_put_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.get = AsyncMock(return_value=mock_get_response)
            instance.put = AsyncMock(return_value=mock_put_response)

            with pytest.raises(GitHubPermissionError):
                await github_service.push_file(
                    "https://github.com/owner/repo",
                    "path/to/file.json",
                    b'{"key": "value"}',
                    "Add new file",
                )


class TestGetFile:
    """Test file retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_file_success(self, github_service: GitHubService):
        """Successful file retrieval should return decoded content."""
        content = b'{"key": "value"}'
        content_base64 = base64.b64encode(content).decode("utf-8")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": content_base64}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await github_service.get_file("https://github.com/owner/repo", "path/to/file.json")

            assert result == content

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, github_service: GitHubService):
        """File not found should return None."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await github_service.get_file("https://github.com/owner/repo", "path/to/missing.json")

            assert result is None


class TestRateLimit:
    """Test rate limit handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, github_service: GitHubService):
        """Rate limit response should raise RateLimitError with reset time."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1700000000",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            with pytest.raises(GitHubRateLimitError) as exc_info:
                await github_service.check_access("https://github.com/owner/repo")

            assert exc_info.value.reset_at is not None


class TestCompareDigest:
    """Test digest comparison."""

    @pytest.mark.asyncio
    async def test_compare_digest_match(self, github_service: GitHubService):
        """Matching digests should return True."""
        content = b'{"key": "value"}'
        content_base64 = base64.b64encode(content).decode("utf-8")
        local_digest = hashlib.sha256(content).hexdigest()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": content_base64}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await github_service.compare_digest(
                "https://github.com/owner/repo",
                "path/to/file.json",
                local_digest,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_compare_digest_mismatch(self, github_service: GitHubService):
        """Different digests should return False."""
        content = b'{"key": "value"}'
        content_base64 = base64.b64encode(content).decode("utf-8")
        different_digest = hashlib.sha256(b"different content").hexdigest()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": content_base64}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await github_service.compare_digest(
                "https://github.com/owner/repo",
                "path/to/file.json",
                different_digest,
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_compare_digest_file_not_found(self, github_service: GitHubService):
        """File not found should return False."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await github_service.compare_digest(
                "https://github.com/owner/repo",
                "path/to/missing.json",
                "some-digest",
            )

            assert result is False


class TestPushFiles:
    """Test multi-file push operations."""

    @pytest.mark.asyncio
    async def test_push_files_empty(self, github_service: GitHubService):
        """Pushing empty file list should raise ValidationError."""
        with pytest.raises(GitHubValidationError):
            await github_service.push_files(
                "https://github.com/owner/repo",
                [],
                "Empty commit",
            )
