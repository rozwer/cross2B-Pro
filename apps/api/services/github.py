"""GitHub integration service for artifact management.

Provides GitHub API operations for:
- Repository access verification
- Repository creation
- File push/pull operations
- Sync status management

Uses GitHub App authentication for API access.
"""

import base64
import hashlib
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# GitHub API base URL
GITHUB_API_URL = "https://api.github.com"

# URL validation pattern
GITHUB_REPO_URL_PATTERN = re.compile(r"^https://github\.com/(?P<owner>[a-zA-Z0-9_-]+)/(?P<repo>[a-zA-Z0-9._-]+)$")

# Claude Code Action workflow template
CLAUDE_CODE_WORKFLOW = """# Claude Code Action Workflow
#
# This workflow enables Claude Code to automatically edit files when @claude is mentioned
# in GitHub Issues or PR comments.
#
# Requirements:
# - ANTHROPIC_API_KEY must be set in repository secrets

name: Claude Code

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened]

jobs:
  claude:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'issues' && contains(github.event.issue.body, '@claude'))

    runs-on: ubuntu-latest

    permissions:
      contents: write
      issues: write
      pull-requests: write
      id-token: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Claude Code
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
"""

# Codex Action workflow template (more cost-effective alternative)
CODEX_WORKFLOW = """# Codex Action Workflow
#
# This workflow enables Codex to automatically edit files when @codex is mentioned
# in GitHub Issues or PR comments.
#
# Requirements:
# - OPENAI_API_KEY must be set in repository secrets (for Codex)

name: Codex

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened]

jobs:
  codex:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@codex')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@codex')) ||
      (github.event_name == 'issues' && contains(github.event.issue.body, '@codex'))

    runs-on: ubuntu-latest

    permissions:
      contents: write
      issues: write
      pull-requests: write
      id-token: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Codex
        uses: openai/codex-action@v1
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
"""


class GitHubError(Exception):
    """Base exception for GitHub operations."""

    pass


class GitHubAuthenticationError(GitHubError):
    """Authentication failed (401)."""

    pass


class GitHubPermissionError(GitHubError):
    """Permission denied (403)."""

    pass


class GitHubNotFoundError(GitHubError):
    """Resource not found (404)."""

    pass


class GitHubRateLimitError(GitHubError):
    """Rate limit exceeded (403 with rate limit headers)."""

    def __init__(self, message: str, reset_at: datetime | None = None):
        super().__init__(message)
        self.reset_at = reset_at


class GitHubValidationError(GitHubError):
    """Validation failed (422)."""

    pass


@dataclass
class FileEntry:
    """Represents a file to be pushed to GitHub."""

    path: str
    content: bytes
    encoding: str = "utf-8"


@dataclass
class RepoPermissions:
    """Repository access permissions."""

    read: bool = False
    write: bool = False
    admin: bool = False


@dataclass
class SyncStatus:
    """Sync status between GitHub and MinIO."""

    github_sha: str | None
    minio_digest: str | None
    synced: bool
    last_synced_at: datetime | None


class GitHubService:
    """Service for GitHub API operations.

    Uses GitHub App or Personal Access Token for authentication.
    Supports repository management, file operations, and sync tracking.
    """

    def __init__(
        self,
        token: str | None = None,
        app_id: str | None = None,
        private_key: str | None = None,
    ):
        """Initialize GitHub service.

        Args:
            token: Personal Access Token (if using PAT auth)
            app_id: GitHub App ID (if using App auth)
            private_key: GitHub App private key (if using App auth)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.app_id = app_id or os.getenv("GITHUB_APP_ID")
        self.private_key = private_key or os.getenv("GITHUB_APP_PRIVATE_KEY")

        if not self.token and not (self.app_id and self.private_key):
            logger.warning("No GitHub authentication configured")

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Parse GitHub repository URL into owner and repo name.

        Args:
            repo_url: Full GitHub repository URL

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            GitHubValidationError: If URL format is invalid
        """
        match = GITHUB_REPO_URL_PATTERN.match(repo_url)
        if not match:
            raise GitHubValidationError(f"Invalid GitHub repository URL: {repo_url}. Expected format: https://github.com/owner/repo")
        return match.group("owner"), match.group("repo")

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle GitHub API response and raise appropriate errors.

        Args:
            response: HTTP response from GitHub API

        Returns:
            Parsed JSON response

        Raises:
            GitHubAuthenticationError: For 401 responses
            GitHubPermissionError: For 403 responses (non-rate-limit)
            GitHubRateLimitError: For 403 responses with rate limit
            GitHubNotFoundError: For 404 responses
            GitHubValidationError: For 422 responses
            GitHubError: For other error responses
        """
        if response.status_code == 401:
            raise GitHubAuthenticationError("GitHub authentication failed")

        if response.status_code == 403:
            # Check if rate limited
            remaining = response.headers.get("X-RateLimit-Remaining")
            if remaining == "0":
                reset_timestamp = response.headers.get("X-RateLimit-Reset")
                reset_at = None
                if reset_timestamp:
                    reset_at = datetime.fromtimestamp(int(reset_timestamp))
                raise GitHubRateLimitError(
                    "GitHub API rate limit exceeded",
                    reset_at=reset_at,
                )
            raise GitHubPermissionError("Permission denied for this operation")

        if response.status_code == 404:
            raise GitHubNotFoundError("Repository or resource not found")

        if response.status_code == 422:
            error_data = response.json()
            message = error_data.get("message", "Validation failed")
            raise GitHubValidationError(f"GitHub validation error: {message}")

        if response.status_code >= 500:
            raise GitHubError(f"GitHub server error: {response.status_code}")

        if response.status_code >= 400:
            raise GitHubError(f"GitHub API error: {response.status_code}")

        if response.status_code == 204:
            return {}

        return response.json()

    async def check_access(self, repo_url: str) -> RepoPermissions:
        """Check access permissions for a repository.

        Args:
            repo_url: Full GitHub repository URL

        Returns:
            RepoPermissions with read/write/admin flags

        Raises:
            GitHubValidationError: If URL format is invalid
            GitHubAuthenticationError: If authentication fails
            GitHubNotFoundError: If repository doesn't exist
        """
        owner, repo = self._parse_repo_url(repo_url)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}",
                headers=self._get_headers(),
                timeout=30.0,
            )
            data = await self._handle_response(response)

        permissions = data.get("permissions", {})
        return RepoPermissions(
            read=permissions.get("pull", False),
            write=permissions.get("push", False),
            admin=permissions.get("admin", False),
        )

    async def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = True,
        setup_claude_workflow: bool = True,
    ) -> str:
        """Create a new GitHub repository.

        Args:
            name: Repository name
            description: Repository description
            private: Whether the repository should be private
            setup_claude_workflow: Whether to add claude-code-action workflow

        Returns:
            URL of the created repository

        Raises:
            GitHubValidationError: If name is invalid or repo exists
            GitHubAuthenticationError: If authentication fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/user/repos",
                headers=self._get_headers(),
                json={
                    "name": name,
                    "description": description,
                    "private": private,
                    "auto_init": True,  # Initialize with README
                },
                timeout=30.0,
            )
            data = await self._handle_response(response)

        repo_url = data["html_url"]

        # Setup Claude Code Action workflow if requested
        if setup_claude_workflow:
            try:
                await self.push_file(
                    repo_url=repo_url,
                    path=".github/workflows/claude-code.yml",
                    content=CLAUDE_CODE_WORKFLOW.encode("utf-8"),
                    message="chore: add claude-code-action workflow",
                )
                logger.info(f"Claude Code workflow added to {repo_url}")
            except Exception as e:
                # Log but don't fail repo creation
                logger.warning(f"Failed to add Claude Code workflow: {e}")

            # Also setup Codex workflow (more cost-effective alternative)
            try:
                await self.push_file(
                    repo_url=repo_url,
                    path=".github/workflows/codex.yml",
                    content=CODEX_WORKFLOW.encode("utf-8"),
                    message="chore: add codex-action workflow",
                )
                logger.info(f"Codex workflow added to {repo_url}")
            except Exception as e:
                # Log but don't fail repo creation
                logger.warning(f"Failed to add Codex workflow: {e}")

        return repo_url

    async def push_file(
        self,
        repo_url: str,
        path: str,
        content: bytes,
        message: str,
        branch: str = "main",
    ) -> str:
        """Push a single file to a repository.

        Args:
            repo_url: Full GitHub repository URL
            path: File path within the repository
            content: File content as bytes
            message: Commit message
            branch: Target branch (default: main)

        Returns:
            Commit SHA

        Raises:
            GitHubPermissionError: If write access is denied
            GitHubNotFoundError: If repository doesn't exist
        """
        owner, repo = self._parse_repo_url(repo_url)

        # Get current file SHA if exists (for update)
        existing_sha = await self.get_file_sha(repo_url, path, branch)

        # Encode content as base64
        content_base64 = base64.b64encode(content).decode("utf-8")

        request_body: dict[str, Any] = {
            "message": message,
            "content": content_base64,
            "branch": branch,
        }

        if existing_sha:
            request_body["sha"] = existing_sha

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
                headers=self._get_headers(),
                json=request_body,
                timeout=30.0,
            )
            data = await self._handle_response(response)

        return data["commit"]["sha"]

    async def push_files(
        self,
        repo_url: str,
        files: list[FileEntry],
        message: str,
        branch: str = "main",
    ) -> str:
        """Push multiple files to a repository in a single commit.

        Uses Git Data API for efficient multi-file commits.

        Args:
            repo_url: Full GitHub repository URL
            files: List of FileEntry objects to push
            message: Commit message
            branch: Target branch (default: main)

        Returns:
            Commit SHA

        Raises:
            GitHubPermissionError: If write access is denied
            GitHubNotFoundError: If repository doesn't exist
        """
        if not files:
            raise GitHubValidationError("No files to push")

        owner, repo = self._parse_repo_url(repo_url)

        async with httpx.AsyncClient() as client:
            # 1. Get current branch reference
            ref_response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/ref/heads/{branch}",
                headers=self._get_headers(),
                timeout=30.0,
            )
            ref_data = await self._handle_response(ref_response)
            base_sha = ref_data["object"]["sha"]

            # 2. Get base tree
            tree_response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/commits/{base_sha}",
                headers=self._get_headers(),
                timeout=30.0,
            )
            tree_data = await self._handle_response(tree_response)
            base_tree_sha = tree_data["tree"]["sha"]

            # 3. Create blobs for each file
            tree_items = []
            for file_entry in files:
                content_base64 = base64.b64encode(file_entry.content).decode("utf-8")
                blob_response = await client.post(
                    f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/blobs",
                    headers=self._get_headers(),
                    json={
                        "content": content_base64,
                        "encoding": "base64",
                    },
                    timeout=30.0,
                )
                blob_data = await self._handle_response(blob_response)
                tree_items.append(
                    {
                        "path": file_entry.path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_data["sha"],
                    }
                )

            # 4. Create new tree
            new_tree_response = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees",
                headers=self._get_headers(),
                json={
                    "base_tree": base_tree_sha,
                    "tree": tree_items,
                },
                timeout=30.0,
            )
            new_tree_data = await self._handle_response(new_tree_response)
            new_tree_sha = new_tree_data["sha"]

            # 5. Create commit
            commit_response = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/commits",
                headers=self._get_headers(),
                json={
                    "message": message,
                    "tree": new_tree_sha,
                    "parents": [base_sha],
                },
                timeout=30.0,
            )
            commit_data = await self._handle_response(commit_response)
            new_commit_sha = commit_data["sha"]

            # 6. Update branch reference
            await client.patch(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs/heads/{branch}",
                headers=self._get_headers(),
                json={"sha": new_commit_sha},
                timeout=30.0,
            )

        return new_commit_sha

    async def get_file(
        self,
        repo_url: str,
        path: str,
        branch: str = "main",
    ) -> bytes | None:
        """Get file content from a repository.

        Args:
            repo_url: Full GitHub repository URL
            path: File path within the repository
            branch: Target branch (default: main)

        Returns:
            File content as bytes, or None if not found
        """
        owner, repo = self._parse_repo_url(repo_url)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
                    headers=self._get_headers(),
                    params={"ref": branch},
                    timeout=30.0,
                )
                data = await self._handle_response(response)

            # Decode base64 content
            content_base64 = data.get("content", "")
            return base64.b64decode(content_base64)

        except GitHubNotFoundError:
            return None

    async def get_file_sha(
        self,
        repo_url: str,
        path: str,
        branch: str = "main",
    ) -> str | None:
        """Get file SHA from a repository.

        Args:
            repo_url: Full GitHub repository URL
            path: File path within the repository
            branch: Target branch (default: main)

        Returns:
            File SHA, or None if not found
        """
        owner, repo = self._parse_repo_url(repo_url)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
                    headers=self._get_headers(),
                    params={"ref": branch},
                    timeout=30.0,
                )
                data = await self._handle_response(response)

            return data.get("sha")

        except GitHubNotFoundError:
            return None

    async def compare_digest(
        self,
        repo_url: str,
        path: str,
        local_digest: str,
        branch: str = "main",
    ) -> bool:
        """Compare local digest with GitHub file content.

        Args:
            repo_url: Full GitHub repository URL
            path: File path within the repository
            local_digest: SHA256 digest of local content
            branch: Target branch (default: main)

        Returns:
            True if digests match, False otherwise
        """
        content = await self.get_file(repo_url, path, branch)
        if content is None:
            return False

        github_digest = hashlib.sha256(content).hexdigest()
        return github_digest == local_digest

    async def create_issue(
        self,
        repo_url: str,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an issue in a repository.

        Args:
            repo_url: Full GitHub repository URL
            title: Issue title
            body: Issue body (supports @claude mention)
            labels: Optional list of labels

        Returns:
            Issue data including number and URL
        """
        owner, repo = self._parse_repo_url(repo_url)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues",
                headers=self._get_headers(),
                json={
                    "title": title,
                    "body": body,
                    "labels": labels or [],
                },
                timeout=30.0,
            )
            return await self._handle_response(response)

    async def get_diff(
        self,
        repo_url: str,
        path: str,
        local_content: bytes,
        branch: str = "main",
    ) -> str | None:
        """Get unified diff between local content and GitHub file.

        Args:
            repo_url: Full GitHub repository URL
            path: File path within the repository
            local_content: Local file content
            branch: Target branch (default: main)

        Returns:
            Unified diff string, or None if files are identical
        """
        import difflib

        github_content = await self.get_file(repo_url, path, branch)
        if github_content is None:
            return None

        # Decode contents for diff
        try:
            github_lines = github_content.decode("utf-8").splitlines(keepends=True)
            local_lines = local_content.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            # Binary files - can't diff
            return "Binary files differ"

        diff = difflib.unified_diff(
            local_lines,
            github_lines,
            fromfile=f"local/{path}",
            tofile=f"github/{path}",
        )

        diff_text = "".join(diff)
        return diff_text if diff_text else None

    async def add_issue_comment(
        self,
        repo_url: str,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Add a comment to a GitHub issue.

        Args:
            repo_url: Full GitHub repository URL
            issue_number: Issue number to comment on
            body: Comment body text

        Returns:
            Comment data including id and URL
        """
        owner, repo = self._parse_repo_url(repo_url)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self._get_headers(),
                json={"body": body},
                timeout=30.0,
            )
            return await self._handle_response(response)

    async def get_issue_status(
        self,
        repo_url: str,
        issue_number: int,
    ) -> dict[str, Any]:
        """Get issue status including linked PRs.

        Args:
            repo_url: Full GitHub repository URL
            issue_number: Issue number to check

        Returns:
            Issue status data including:
            - state: "open" or "closed"
            - updated_at: ISO timestamp
            - pr_url: URL of linked PR (if any)
            - last_comment: Most recent comment body
        """
        owner, repo = self._parse_repo_url(repo_url)

        async with httpx.AsyncClient() as client:
            # 1. Get issue info
            issue_response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=self._get_headers(),
                timeout=30.0,
            )
            issue_data = await self._handle_response(issue_response)

            # 2. Get comments to find latest
            comments_response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments",
                headers=self._get_headers(),
                params={"per_page": 5, "sort": "created", "direction": "desc"},
                timeout=30.0,
            )
            comments_data = await self._handle_response(comments_response)

            # 3. Get timeline events to find linked PRs
            timeline_response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}/timeline",
                headers={**self._get_headers(), "Accept": "application/vnd.github+json"},
                timeout=30.0,
            )
            timeline_data = await self._handle_response(timeline_response)

        # Find PR URL from timeline (cross-referenced or connected events)
        pr_url = None
        for event in timeline_data:
            event_type = event.get("event")
            # cross-referenced: PR mentions this issue
            if event_type == "cross-referenced":
                source = event.get("source", {})
                issue_ref = source.get("issue", {})
                if issue_ref.get("pull_request"):
                    pr_url = issue_ref.get("html_url")
                    break
            # connected: PR is linked to this issue via "fixes #N" etc.
            elif event_type == "connected":
                subject = event.get("subject", {})
                if subject.get("type") == "PullRequest":
                    # Need to construct PR URL from event data
                    pr_number = subject.get("number")
                    if pr_number:
                        pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
                        break

        # Get last comment
        last_comment = None
        if comments_data and len(comments_data) > 0:
            last_comment = comments_data[0].get("body", "")[:200]  # Truncate to 200 chars

        # Determine status based on issue state and activity
        state = issue_data.get("state", "open")
        status = "open"
        if state == "closed":
            status = "closed"
        elif last_comment and ("claude" in last_comment.lower() or "working" in last_comment.lower()):
            status = "in_progress"

        return {
            "state": state,
            "status": status,
            "updated_at": issue_data.get("updated_at"),
            "pr_url": pr_url,
            "last_comment": last_comment,
            "issue_url": issue_data.get("html_url"),
        }

    async def get_prs_for_file(
        self,
        repo_url: str,
        file_path: str,
        state: str = "open",
    ) -> list[dict[str, Any]]:
        """Get pull requests that modify a specific file.

        Args:
            repo_url: Full GitHub repository URL
            file_path: Path to the file within the repository
            state: PR state filter ("open", "closed", "all")

        Returns:
            List of PRs with number, title, url, state, and branch info
        """
        owner, repo = self._parse_repo_url(repo_url)

        async with httpx.AsyncClient() as client:
            # Get open PRs
            prs_response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls",
                headers=self._get_headers(),
                params={"state": state, "per_page": 20},
                timeout=30.0,
            )
            prs_data = await self._handle_response(prs_response)

            # Check each PR to see if it modifies the target file
            matching_prs = []
            for pr in prs_data:
                pr_number = pr.get("number")
                try:
                    files_response = await client.get(
                        f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files",
                        headers=self._get_headers(),
                        params={"per_page": 100},
                        timeout=30.0,
                    )
                    files_data = await self._handle_response(files_response)

                    # Check if any file matches (exact match or directory prefix match)
                    for file in files_data:
                        filename = file.get("filename", "")
                        if filename == file_path or filename.startswith(file_path.rsplit("/", 1)[0] + "/"):
                            matching_prs.append(
                                {
                                    "number": pr_number,
                                    "title": pr.get("title"),
                                    "url": pr.get("html_url"),
                                    "state": pr.get("state"),
                                    "head_branch": pr.get("head", {}).get("ref"),
                                    "base_branch": pr.get("base", {}).get("ref"),
                                    "user": pr.get("user", {}).get("login"),
                                    "created_at": pr.get("created_at"),
                                    "updated_at": pr.get("updated_at"),
                                    "additions": file.get("additions", 0),
                                    "deletions": file.get("deletions", 0),
                                    "status": file.get("status"),  # added, modified, removed
                                }
                            )
                            break
                except Exception as e:
                    logger.warning(f"Failed to check files for PR #{pr_number}: {e}")
                    continue

            return matching_prs

    async def get_branches_for_file(
        self,
        repo_url: str,
        file_path: str,
        prefix: str = "claude/",
    ) -> list[dict[str, Any]]:
        """Get branches that may contain changes to a specific file.

        Searches for branches with the given prefix (e.g., claude/) and checks
        if they have changes to the target file compared to main.
        Excludes branches that have already been merged via PR.

        Args:
            repo_url: Full GitHub repository URL
            file_path: Path to the file within the repository
            prefix: Branch name prefix to filter (default: "claude/")

        Returns:
            List of branches with name, url, last_commit info, and file diff stats
        """
        owner, repo = self._parse_repo_url(repo_url)
        matching_branches = []

        async with httpx.AsyncClient() as client:
            # First, get all merged PRs to filter out already-processed branches
            merged_branch_names: set[str] = set()
            try:
                # Get merged PRs (closed PRs with merged state)
                prs_response = await client.get(
                    f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls",
                    headers=self._get_headers(),
                    params={"state": "closed", "per_page": 100},
                    timeout=30.0,
                )
                prs_data = await self._handle_response(prs_response)
                for pr in prs_data:
                    if pr.get("merged_at"):  # PR was merged
                        head_ref = pr.get("head", {}).get("ref", "")
                        if head_ref:
                            merged_branch_names.add(head_ref)
                logger.debug(f"Found {len(merged_branch_names)} merged branches to exclude")
            except Exception as e:
                logger.warning(f"Failed to get merged PRs: {e}")

            # Get all branches
            branches_response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/branches",
                headers=self._get_headers(),
                params={"per_page": 50},
                timeout=30.0,
            )
            branches_data = await self._handle_response(branches_response)

            # Filter branches by prefix and check for file changes
            for branch in branches_data:
                branch_name = branch.get("name", "")
                if not branch_name.startswith(prefix):
                    continue

                # Skip if it's the main branch
                if branch_name in ("main", "master"):
                    continue

                # Skip if this branch has already been merged via PR
                if branch_name in merged_branch_names:
                    logger.debug(f"Skipping merged branch: {branch_name}")
                    continue

                try:
                    # Compare branch to main to see file changes
                    compare_response = await client.get(
                        f"{GITHUB_API_URL}/repos/{owner}/{repo}/compare/main...{branch_name}",
                        headers=self._get_headers(),
                        timeout=30.0,
                    )
                    compare_data = await self._handle_response(compare_response)

                    # Check if any file in the changed files matches the path
                    # Support both exact match and directory prefix match
                    files = compare_data.get("files", [])
                    for file in files:
                        filename = file.get("filename", "")
                        # Match if exact path or if file is under the directory path
                        if filename == file_path or filename.startswith(file_path.rsplit("/", 1)[0] + "/"):
                            # Get commit info
                            commits = compare_data.get("commits", [])
                            last_commit = commits[-1] if commits else None

                            matching_branches.append(
                                {
                                    "name": branch_name,
                                    "url": f"https://github.com/{owner}/{repo}/tree/{branch_name}",
                                    "compare_url": f"https://github.com/{owner}/{repo}/compare/main...{branch_name}",
                                    "last_commit_sha": last_commit.get("sha", "")[:8] if last_commit else None,
                                    "last_commit_message": last_commit.get("commit", {}).get("message", "")[:100] if last_commit else None,
                                    "last_commit_date": last_commit.get("commit", {}).get("committer", {}).get("date")
                                    if last_commit
                                    else None,
                                    "author": last_commit.get("author", {}).get("login") if last_commit else None,
                                    "additions": file.get("additions", 0),
                                    "deletions": file.get("deletions", 0),
                                    "status": file.get("status"),  # added, modified, removed
                                    "ahead_by": compare_data.get("ahead_by", 0),
                                    "behind_by": compare_data.get("behind_by", 0),
                                }
                            )
                            break
                except Exception as e:
                    logger.warning(f"Failed to check branch {branch_name}: {e}")
                    continue

        return matching_branches

    async def create_pull_request(
        self,
        repo_url: str,
        head_branch: str,
        base_branch: str = "main",
        title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Create a pull request from head_branch to base_branch.

        Args:
            repo_url: Full GitHub repository URL
            head_branch: Source branch name
            base_branch: Target branch name (default: "main")
            title: PR title (auto-generated if not provided)
            body: PR description (auto-generated if not provided)

        Returns:
            Created PR data including number, url, state
        """
        owner, repo = self._parse_repo_url(repo_url)

        # Auto-generate title from branch name if not provided
        if not title:
            # claude/issue-2-20260116-1126 -> Issue #2: Edit step4
            if head_branch.startswith("claude/issue-"):
                parts = head_branch.split("-")
                if len(parts) >= 2:
                    issue_num = parts[1]
                    title = f"Issue #{issue_num}: Changes from Claude Code"
                else:
                    title = f"Changes from {head_branch}"
            else:
                title = f"Changes from {head_branch}"

        if not body:
            body = f"""## Summary
This PR was created automatically from branch `{head_branch}`.

## Changes
See the diff for details.

---
_Created via SEO Article Generator_
"""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls",
                headers=self._get_headers(),
                json={
                    "title": title,
                    "body": body,
                    "head": head_branch,
                    "base": base_branch,
                },
                timeout=30.0,
            )
            pr_data = await self._handle_response(response)

        return {
            "number": pr_data.get("number"),
            "title": pr_data.get("title"),
            "url": pr_data.get("html_url"),
            "state": pr_data.get("state"),
            "head_branch": pr_data.get("head", {}).get("ref"),
            "base_branch": pr_data.get("base", {}).get("ref"),
            "user": pr_data.get("user", {}).get("login"),
            "created_at": pr_data.get("created_at"),
        }

    async def merge_pull_request(
        self,
        repo_url: str,
        pr_number: int,
        merge_method: str = "squash",
        commit_title: str | None = None,
        commit_message: str | None = None,
    ) -> dict[str, Any]:
        """Merge a pull request.

        Args:
            repo_url: Full GitHub repository URL
            pr_number: Pull request number to merge
            merge_method: Merge method ("merge", "squash", "rebase")
            commit_title: Optional custom commit title (for squash/merge)
            commit_message: Optional custom commit message (for squash/merge)

        Returns:
            Merge result including sha, merged status, and message
        """
        owner, repo = self._parse_repo_url(repo_url)

        body: dict[str, Any] = {
            "merge_method": merge_method,
        }
        if commit_title:
            body["commit_title"] = commit_title
        if commit_message:
            body["commit_message"] = commit_message

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                headers=self._get_headers(),
                json=body,
                timeout=30.0,
            )
            merge_data = await self._handle_response(response)

        return {
            "sha": merge_data.get("sha"),
            "merged": merge_data.get("merged", False),
            "message": merge_data.get("message", ""),
        }

    async def get_pull_request(
        self,
        repo_url: str,
        pr_number: int,
    ) -> dict[str, Any]:
        """Get pull request details.

        Args:
            repo_url: Full GitHub repository URL
            pr_number: Pull request number

        Returns:
            PR data including number, title, state, mergeable, etc.
        """
        owner, repo = self._parse_repo_url(repo_url)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._get_headers(),
                timeout=30.0,
            )
            pr_data = await self._handle_response(response)

        return {
            "number": pr_data.get("number"),
            "title": pr_data.get("title"),
            "state": pr_data.get("state"),
            "merged": pr_data.get("merged", False),
            "mergeable": pr_data.get("mergeable"),
            "mergeable_state": pr_data.get("mergeable_state"),
            "url": pr_data.get("html_url"),
            "head_branch": pr_data.get("head", {}).get("ref"),
            "base_branch": pr_data.get("base", {}).get("ref"),
            "user": pr_data.get("user", {}).get("login"),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0),
            "changed_files": pr_data.get("changed_files", 0),
        }
