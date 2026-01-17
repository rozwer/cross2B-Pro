"""GitHub integration API router.

Endpoints for:
- Repository access checking
- Repository creation
- File sync operations
- Issue creation for Claude Code integration
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import Run
from apps.api.services.github import (
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubService,
    GitHubValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/github", tags=["github"])


# =============================================================================
# Lazy imports
# =============================================================================


def _get_github_service() -> GitHubService:
    """Get GitHub service instance."""
    return GitHubService()


def _get_tenant_db_manager() -> "TenantDBManager":
    """Get tenant DB manager."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


# Type alias for lazy import
TenantDBManager = object  # Actual type imported lazily


def _get_artifact_store() -> "ArtifactStore":
    """Get artifact store instance."""
    from apps.api.main import get_artifact_store

    return get_artifact_store()


# Type alias for lazy import
ArtifactStore = object  # Actual type imported lazily


# =============================================================================
# Request/Response Models
# =============================================================================


class CheckAccessRequest(BaseModel):
    """Request to check repository access."""

    repo_url: str = Field(..., description="GitHub repository URL")


class CheckAccessResponse(BaseModel):
    """Response with repository permissions."""

    accessible: bool
    permissions: list[str] = Field(default_factory=list)
    error: str | None = None


class CreateRepoRequest(BaseModel):
    """Request to create a new repository."""

    name: str = Field(..., min_length=1, max_length=100, description="Repository name")
    description: str = Field(default="", description="Repository description")
    private: bool = Field(default=True, description="Whether repository should be private")


class CreateRepoResponse(BaseModel):
    """Response with created repository URL."""

    repo_url: str


class CreateIssueRequest(BaseModel):
    """Request to create an issue for Claude Code."""

    run_id: UUID
    step: str = Field(..., description="Step name (e.g., step5)")
    instruction: str = Field(..., min_length=1, description="Instruction for Claude Code")


class CreateIssueResponse(BaseModel):
    """Response with created issue details."""

    issue_number: int
    issue_url: str


class SyncRequest(BaseModel):
    """Request to sync from GitHub to MinIO."""

    run_id: UUID
    step: str


class SyncResponse(BaseModel):
    """Response with sync result."""

    synced: bool
    github_sha: str | None = None
    minio_digest: str | None = None
    message: str


class PullRequestInfo(BaseModel):
    """Information about a pull request."""

    number: int
    title: str
    url: str
    state: str
    head_branch: str | None = None
    base_branch: str | None = None
    user: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    additions: int = 0
    deletions: int = 0
    status: str | None = None  # added, modified, removed


class BranchInfo(BaseModel):
    """Information about a branch with pending changes (not yet a PR)."""

    name: str
    url: str
    compare_url: str
    last_commit_sha: str | None = None
    last_commit_message: str | None = None
    last_commit_date: str | None = None
    author: str | None = None
    additions: int = 0
    deletions: int = 0
    status: str | None = None  # added, modified, removed
    ahead_by: int = 0
    behind_by: int = 0


class DiffResponse(BaseModel):
    """Response with diff between GitHub and MinIO."""

    has_diff: bool
    diff: str | None = None
    github_sha: str | None = None
    minio_digest: str | None = None
    open_prs: list[PullRequestInfo] = Field(default_factory=list)
    pending_branches: list[BranchInfo] = Field(default_factory=list)


class SetupWorkflowsRequest(BaseModel):
    """Request to setup AI workflows for an existing repository."""

    repo_url: str = Field(..., description="GitHub repository URL")


class WorkflowSetupResult(BaseModel):
    """Result for a single workflow setup."""

    status: str  # created, skipped, error
    reason: str | None = None
    commit_sha: str | None = None
    error: str | None = None


class SetupWorkflowsResponse(BaseModel):
    """Response with workflow setup results."""

    claude_code: WorkflowSetupResult
    codex: WorkflowSetupResult


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/check-access", response_model=CheckAccessResponse)
async def check_access(
    request: CheckAccessRequest,
    user: AuthUser = Depends(get_current_user),
) -> CheckAccessResponse:
    """Check access permissions for a GitHub repository.

    Verifies that the authenticated user has access to the specified repository
    and returns the available permissions (read, write, admin).
    """
    github = _get_github_service()

    try:
        permissions = await github.check_access(request.repo_url)

        permission_list = []
        if permissions.read:
            permission_list.append("read")
        if permissions.write:
            permission_list.append("write")
        if permissions.admin:
            permission_list.append("admin")

        return CheckAccessResponse(
            accessible=True,
            permissions=permission_list,
        )

    except GitHubValidationError as e:
        return CheckAccessResponse(
            accessible=False,
            error=str(e),
        )
    except GitHubAuthenticationError:
        return CheckAccessResponse(
            accessible=False,
            error="GitHub authentication failed. Please check your token.",
        )
    except GitHubNotFoundError:
        return CheckAccessResponse(
            accessible=False,
            error="Repository not found or you don't have access.",
        )
    except GitHubRateLimitError as e:
        reset_msg = ""
        if e.reset_at:
            reset_msg = f" Resets at {e.reset_at.isoformat()}"
        return CheckAccessResponse(
            accessible=False,
            error=f"GitHub API rate limit exceeded.{reset_msg}",
        )


@router.post("/create-repo", response_model=CreateRepoResponse)
async def create_repo(
    request: CreateRepoRequest,
    user: AuthUser = Depends(get_current_user),
) -> CreateRepoResponse:
    """Create a new GitHub repository.

    Creates a private repository by default with auto-initialization.
    """
    github = _get_github_service()

    try:
        repo_url = await github.create_repo(
            name=request.name,
            description=request.description,
            private=request.private,
        )
        return CreateRepoResponse(repo_url=repo_url)

    except GitHubValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed. Please check your token.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot create repository.",
        )
    except GitHubRateLimitError as e:
        reset_msg = ""
        if e.reset_at:
            reset_msg = f" Resets at {e.reset_at.isoformat()}"
        raise HTTPException(
            status_code=429,
            detail=f"GitHub API rate limit exceeded.{reset_msg}",
        )


@router.post("/setup-workflows", response_model=SetupWorkflowsResponse)
async def setup_workflows(
    request: SetupWorkflowsRequest,
    user: AuthUser = Depends(get_current_user),
) -> SetupWorkflowsResponse:
    """Setup AI workflows for an existing GitHub repository.

    Adds both Claude Code (@claude) and Codex (@codex) GitHub Actions workflows.
    This is idempotent - existing workflows are skipped.

    Use this endpoint when:
    - Connecting an existing repository that doesn't have the workflows
    - Updating a repository that only has the Claude workflow (adds Codex)
    """
    github = _get_github_service()

    try:
        # First check access
        permissions = await github.check_access(request.repo_url)
        if not permissions.write:
            raise HTTPException(
                status_code=403,
                detail="Write permission required to setup workflows",
            )

        # Setup workflows
        results = await github.setup_workflows(request.repo_url)

        return SetupWorkflowsResponse(
            claude_code=WorkflowSetupResult(
                status=results["claude_code"].get("status", "error"),
                reason=results["claude_code"].get("reason"),
                commit_sha=results["claude_code"].get("commit_sha"),
                error=results["claude_code"].get("error"),
            ),
            codex=WorkflowSetupResult(
                status=results["codex"].get("status", "error"),
                reason=results["codex"].get("reason"),
                commit_sha=results["codex"].get("commit_sha"),
                error=results["codex"].get("error"),
            ),
        )

    except GitHubValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed. Please check your token.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Repository not found or you don't have access.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot setup workflows.",
        )
    except GitHubRateLimitError as e:
        reset_msg = ""
        if e.reset_at:
            reset_msg = f" Resets at {e.reset_at.isoformat()}"
        raise HTTPException(
            status_code=429,
            detail=f"GitHub API rate limit exceeded.{reset_msg}",
        )


@router.post("/create-issue", response_model=CreateIssueResponse)
async def create_issue(
    request: CreateIssueRequest,
    user: AuthUser = Depends(get_current_user),
) -> CreateIssueResponse:
    """Create a GitHub issue for Claude Code to process.

    Creates an issue with @claude mention and file reference.
    """
    github = _get_github_service()
    db_manager = _get_tenant_db_manager()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == request.run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url
        dir_path = run.github_dir_path or str(request.run_id)

    # Build issue body with Claude mention
    file_path = f"{dir_path}/{request.step}/output.json"
    issue_body = f"""@claude

**File:** `{file_path}`

**Instruction:**
{request.instruction}

---
*This issue was created automatically from the SEO Article Generator.*
*Run ID: {request.run_id}*
"""

    try:
        issue_data = await github.create_issue(
            repo_url=repo_url,
            title=f"[Claude Code] Edit {request.step} - {dir_path}",
            body=issue_body,
            labels=["claude-code", "auto-generated"],
        )

        return CreateIssueResponse(
            issue_number=issue_data["number"],
            issue_url=issue_data["html_url"],
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot create issue.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )


@router.get("/diff/{run_id}/{step}", response_model=DiffResponse)
async def get_diff(
    run_id: UUID,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> DiffResponse:
    """Get diff between GitHub and MinIO content for a step.

    Compares the file in GitHub with the artifact in MinIO storage.
    """
    github = _get_github_service()
    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url
        dir_path = run.github_dir_path or str(run_id)

    # Get MinIO content
    minio_content = await store.get_by_path(
        tenant_id=user.tenant_id,
        run_id=str(run_id),
        step=step,
    )

    if not minio_content:
        raise HTTPException(
            status_code=404,
            detail=f"Artifact not found in storage for step {step}",
        )

    # Get diff from GitHub
    file_path = f"{dir_path}/{step}/output.json"

    import hashlib

    try:
        diff = await github.get_diff(
            repo_url=repo_url,
            path=file_path,
            local_content=minio_content,
        )

        # Get GitHub file SHA
        github_sha = await github.get_file_sha(repo_url, file_path)

        # Calculate MinIO digest
        minio_digest = hashlib.sha256(minio_content).hexdigest()

        # Get open PRs that modify this file
        open_prs: list[PullRequestInfo] = []
        try:
            prs_data = await github.get_prs_for_file(repo_url, file_path, state="open")
            open_prs = [
                PullRequestInfo(
                    number=pr["number"],
                    title=pr["title"],
                    url=pr["url"],
                    state=pr["state"],
                    head_branch=pr.get("head_branch"),
                    base_branch=pr.get("base_branch"),
                    user=pr.get("user"),
                    created_at=pr.get("created_at"),
                    updated_at=pr.get("updated_at"),
                    additions=pr.get("additions", 0),
                    deletions=pr.get("deletions", 0),
                    status=pr.get("status"),
                )
                for pr in prs_data
            ]
        except Exception as e:
            logger.warning(f"Failed to get PRs for file: {e}")

        # Get branches with pending changes (not yet PRs)
        pending_branches: list[BranchInfo] = []
        try:
            # Get branches with claude/ prefix that modify this file
            branches_data = await github.get_branches_for_file(repo_url, file_path, prefix="claude/")
            # Filter out branches that already have PRs
            pr_branch_names = {pr.head_branch for pr in open_prs}
            pending_branches = [
                BranchInfo(
                    name=branch["name"],
                    url=branch["url"],
                    compare_url=branch["compare_url"],
                    last_commit_sha=branch.get("last_commit_sha"),
                    last_commit_message=branch.get("last_commit_message"),
                    last_commit_date=branch.get("last_commit_date"),
                    author=branch.get("author"),
                    additions=branch.get("additions", 0),
                    deletions=branch.get("deletions", 0),
                    status=branch.get("status"),
                    ahead_by=branch.get("ahead_by", 0),
                    behind_by=branch.get("behind_by", 0),
                )
                for branch in branches_data
                if branch["name"] not in pr_branch_names
            ]
        except Exception as e:
            logger.warning(f"Failed to get branches for file: {e}")

        return DiffResponse(
            has_diff=diff is not None and len(diff) > 0,
            diff=diff,
            github_sha=github_sha,
            minio_digest=minio_digest,
            open_prs=open_prs,
            pending_branches=pending_branches,
        )

    except GitHubNotFoundError:
        # Still try to get PRs and branches even if main branch file not found
        fallback_prs: list[PullRequestInfo] = []
        fallback_branches: list[BranchInfo] = []
        try:
            prs_data = await github.get_prs_for_file(repo_url, file_path, state="open")
            fallback_prs = [
                PullRequestInfo(
                    number=pr["number"],
                    title=pr["title"],
                    url=pr["url"],
                    state=pr["state"],
                    head_branch=pr.get("head_branch"),
                    base_branch=pr.get("base_branch"),
                    user=pr.get("user"),
                    created_at=pr.get("created_at"),
                    updated_at=pr.get("updated_at"),
                    additions=pr.get("additions", 0),
                    deletions=pr.get("deletions", 0),
                    status=pr.get("status"),
                )
                for pr in prs_data
            ]
        except Exception as e:
            logger.warning(f"Failed to get PRs for file: {e}")

        try:
            branches_data = await github.get_branches_for_file(repo_url, file_path, prefix="claude/")
            pr_branch_names = {pr.head_branch for pr in fallback_prs}
            fallback_branches = [
                BranchInfo(
                    name=branch["name"],
                    url=branch["url"],
                    compare_url=branch["compare_url"],
                    last_commit_sha=branch.get("last_commit_sha"),
                    last_commit_message=branch.get("last_commit_message"),
                    last_commit_date=branch.get("last_commit_date"),
                    author=branch.get("author"),
                    additions=branch.get("additions", 0),
                    deletions=branch.get("deletions", 0),
                    status=branch.get("status"),
                    ahead_by=branch.get("ahead_by", 0),
                    behind_by=branch.get("behind_by", 0),
                )
                for branch in branches_data
                if branch["name"] not in pr_branch_names
            ]
        except Exception as e:
            logger.warning(f"Failed to get branches for file: {e}")

        return DiffResponse(
            has_diff=True,
            diff="GitHub file not found",
            github_sha=None,
            minio_digest=hashlib.sha256(minio_content).hexdigest(),
            open_prs=fallback_prs,
            pending_branches=fallback_branches,
        )


class CreatePRRequest(BaseModel):
    """Request to create a pull request."""

    branch_name: str
    title: str | None = None
    body: str | None = None


class CreatePRResponse(BaseModel):
    """Response with created PR info."""

    number: int
    title: str
    url: str
    state: str
    head_branch: str | None = None
    base_branch: str | None = None


class MergePRRequest(BaseModel):
    """Request to merge a pull request."""

    merge_method: str = Field(
        default="squash",
        description="Merge method: merge, squash, or rebase",
    )
    commit_title: str | None = None
    commit_message: str | None = None


class MergePRResponse(BaseModel):
    """Response with merge result."""

    merged: bool
    sha: str | None = None
    message: str


class PRDetailResponse(BaseModel):
    """Response with PR details."""

    number: int
    title: str
    state: str
    merged: bool
    mergeable: bool | None = None
    mergeable_state: str | None = None
    url: str
    head_branch: str | None = None
    base_branch: str | None = None
    user: str | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0


@router.post("/create-pr/{run_id}", response_model=CreatePRResponse)
async def create_pull_request(
    run_id: UUID,
    request: CreatePRRequest,
    user: AuthUser = Depends(get_current_user),
) -> CreatePRResponse:
    """Create a pull request from a branch.

    Creates a PR from the specified branch to main.
    Used for creating PRs from Claude Code edit branches.
    """
    github = _get_github_service()
    db_manager = _get_tenant_db_manager()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url

    try:
        pr_data = await github.create_pull_request(
            repo_url=repo_url,
            head_branch=request.branch_name,
            base_branch="main",
            title=request.title,
            body=request.body,
        )

        return CreatePRResponse(
            number=pr_data["number"],
            title=pr_data["title"],
            url=pr_data["url"],
            state=pr_data["state"],
            head_branch=pr_data.get("head_branch"),
            base_branch=pr_data.get("base_branch"),
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed.",
        )
    except Exception as e:
        logger.error(f"Failed to create PR: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create pull request: {str(e)}",
        )


@router.get("/pr/{run_id}/{pr_number}", response_model=PRDetailResponse)
async def get_pull_request(
    run_id: UUID,
    pr_number: int,
    user: AuthUser = Depends(get_current_user),
) -> PRDetailResponse:
    """Get pull request details.

    Returns PR details including mergeable status.
    """
    github = _get_github_service()
    db_manager = _get_tenant_db_manager()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url

    try:
        pr_data = await github.get_pull_request(repo_url, pr_number)

        return PRDetailResponse(
            number=pr_data["number"],
            title=pr_data["title"],
            state=pr_data["state"],
            merged=pr_data.get("merged", False),
            mergeable=pr_data.get("mergeable"),
            mergeable_state=pr_data.get("mergeable_state"),
            url=pr_data["url"],
            head_branch=pr_data.get("head_branch"),
            base_branch=pr_data.get("base_branch"),
            user=pr_data.get("user"),
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            changed_files=pr_data.get("changed_files", 0),
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Pull request #{pr_number} not found.",
        )


@router.post("/merge-pr/{run_id}/{pr_number}", response_model=MergePRResponse)
async def merge_pull_request(
    run_id: UUID,
    pr_number: int,
    request: MergePRRequest,
    user: AuthUser = Depends(get_current_user),
) -> MergePRResponse:
    """Merge a pull request.

    Merges the specified PR using the given merge method (squash, merge, or rebase).
    After merge, syncs the content to MinIO.
    """
    github = _get_github_service()
    db_manager = _get_tenant_db_manager()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url

    # Validate merge method
    if request.merge_method not in ("merge", "squash", "rebase"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid merge method: {request.merge_method}. Must be merge, squash, or rebase.",
        )

    try:
        merge_result = await github.merge_pull_request(
            repo_url=repo_url,
            pr_number=pr_number,
            merge_method=request.merge_method,
            commit_title=request.commit_title,
            commit_message=request.commit_message,
        )

        return MergePRResponse(
            merged=merge_result.get("merged", False),
            sha=merge_result.get("sha"),
            message=merge_result.get("message", "Pull request merged successfully"),
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Pull request #{pr_number} not found.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot merge this pull request.",
        )
    except GitHubValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to merge PR: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to merge pull request: {str(e)}",
        )


@router.post("/sync/{run_id}/{step}", response_model=SyncResponse)
async def sync_from_github(
    run_id: UUID,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> SyncResponse:
    """Sync content from GitHub to MinIO.

    Downloads the file from GitHub and overwrites the MinIO artifact.
    Updates the github_sync_status table.
    """
    github = _get_github_service()
    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url
        dir_path = run.github_dir_path or str(run_id)

    # Get file from GitHub
    file_path = f"{dir_path}/{step}/output.json"

    try:
        github_content = await github.get_file(repo_url, file_path)

        if github_content is None:
            raise HTTPException(
                status_code=404,
                detail=f"File not found in GitHub: {file_path}",
            )

        github_sha = await github.get_file_sha(repo_url, file_path)

        # Calculate digest
        import hashlib

        minio_digest = hashlib.sha256(github_content).hexdigest()

        # Save to MinIO
        path = store.build_path(user.tenant_id, str(run_id), step)
        await store.put(github_content, path, "application/json")

        # Update sync status
        async with db_manager.get_session(user.tenant_id) as session:
            await session.execute(
                text(
                    """
                INSERT INTO github_sync_status (run_id, step, github_sha, minio_digest, synced_at, status)
                VALUES (:run_id, :step, :github_sha, :minio_digest, NOW(), 'synced')
                ON CONFLICT (run_id, step)
                DO UPDATE SET
                    github_sha = EXCLUDED.github_sha,
                    minio_digest = EXCLUDED.minio_digest,
                    synced_at = NOW(),
                    status = 'synced'
            """
                ),
                {
                    "run_id": str(run_id),
                    "step": step,
                    "github_sha": github_sha,
                    "minio_digest": minio_digest,
                },
            )
            await session.commit()

        return SyncResponse(
            synced=True,
            github_sha=github_sha,
            minio_digest=minio_digest,
            message=f"Successfully synced {step} from GitHub",
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"File not found in GitHub: {file_path}",
        )


class SyncStatusItem(BaseModel):
    """Sync status for a single step."""

    step: str
    status: str  # 'synced', 'diverged', 'unknown', 'github_only', 'minio_only'
    github_sha: str | None = None
    minio_digest: str | None = None
    synced_at: str | None = None


class SyncStatusResponse(BaseModel):
    """Response with sync status for all steps."""

    run_id: str
    statuses: list[SyncStatusItem]


@router.get("/sync-status/{run_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    run_id: UUID,
    user: AuthUser = Depends(get_current_user),
) -> SyncStatusResponse:
    """Get sync status for all steps of a run.

    Returns the sync status between GitHub and MinIO for each step.
    Used to display warning badges when files are out of sync.
    """
    db_manager = _get_tenant_db_manager()

    async with db_manager.get_session(user.tenant_id) as session:
        # Check if run exists and has GitHub configured
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            # No GitHub configured, return empty statuses
            return SyncStatusResponse(run_id=str(run_id), statuses=[])

        # Get sync status from DB
        status_result = await session.execute(
            text(
                """
                SELECT step, status, github_sha, minio_digest, synced_at
                FROM github_sync_status
                WHERE run_id = :run_id
                ORDER BY step
            """
            ),
            {"run_id": str(run_id)},
        )
        rows = status_result.fetchall()

        statuses = [
            SyncStatusItem(
                step=row[0],
                status=row[1],
                github_sha=row[2],
                minio_digest=row[3],
                synced_at=row[4].isoformat() if row[4] else None,
            )
            for row in rows
        ]

        return SyncStatusResponse(run_id=str(run_id), statuses=statuses)


# =============================================================================
# Review API Models
# =============================================================================


class CreateReviewRequest(BaseModel):
    """Request to create a review issue for Claude Code or Codex."""

    review_type: str = Field(
        default="all",
        description="Review type: fact_check, seo, quality, or all",
    )
    ai_mention: str = Field(
        default="@codex",
        description="AI assistant to mention: @codex (recommended, cost-effective) or @claude",
    )


class CreateReviewResponse(BaseModel):
    """Response with created review issue details."""

    issue_number: int
    issue_url: str
    review_type: str
    output_path: str


class ReviewResultRequest(BaseModel):
    """Request to save review result."""

    review_data: dict[str, object] = Field(..., description="Review result JSON data")
    issue_number: int | None = Field(None, description="Issue number to comment on")


class ReviewResultResponse(BaseModel):
    """Response with saved review result."""

    saved: bool
    path: str
    digest: str
    comment_posted: bool = False


class ReviewStatusResponse(BaseModel):
    """Response with review status."""

    status: str  # pending, in_progress, completed, failed
    issue_number: int | None = None
    issue_url: str | None = None
    has_result: bool = False
    result_path: str | None = None


class IssueStatusResponse(BaseModel):
    """Response with GitHub issue status."""

    issue_number: int
    status: str  # open, in_progress, closed
    state: str  # GitHub state: open, closed
    issue_url: str | None = None
    updated_at: str | None = None
    pr_url: str | None = None
    last_comment: str | None = None


# =============================================================================
# Review API Endpoints
# =============================================================================


@router.post("/review/{run_id}/{step}", response_model=CreateReviewResponse)
async def create_review_issue(
    run_id: UUID,
    step: str,
    request: CreateReviewRequest,
    user: AuthUser = Depends(get_current_user),
) -> CreateReviewResponse:
    """Create a GitHub issue for Claude Code or Codex to review an article.

    Creates an issue with @codex (default, cost-effective) or @claude mention
    and review instructions.
    Supports different review types: fact_check, seo, quality, or all.
    """
    from apps.api.services.review_prompts import ReviewType, get_review_prompt, get_review_title

    github = _get_github_service()
    db_manager = _get_tenant_db_manager()

    # Validate review type
    try:
        review_type = ReviewType(request.review_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid review type: {request.review_type}. Must be one of: fact_check, seo, quality, all",
        )

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url
        dir_path = run.github_dir_path or str(run_id)

    # Build file paths
    file_path = f"{dir_path}/{step}/output.json"
    output_path = f"{dir_path}/{step}/review.json"

    # Validate ai_mention
    ai_mention = request.ai_mention
    if ai_mention not in ("@codex", "@claude"):
        ai_mention = "@codex"  # Default to cost-effective option

    # Generate review prompt
    issue_body = get_review_prompt(
        review_type=review_type,
        file_path=file_path,
        output_path=output_path,
        run_id=str(run_id),
        step=step,
        ai_mention=ai_mention,
    )

    # Generate issue title
    issue_title = get_review_title(review_type, step, dir_path)

    try:
        issue_data = await github.create_issue(
            repo_url=repo_url,
            title=issue_title,
            body=issue_body,
            labels=["claude-code", "review", f"review-{review_type.value}"],
        )

        return CreateReviewResponse(
            issue_number=issue_data["number"],
            issue_url=issue_data["html_url"],
            review_type=review_type.value,
            output_path=output_path,
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot create issue.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )


@router.post("/review-result/{run_id}/{step}", response_model=ReviewResultResponse)
async def save_review_result(
    run_id: UUID,
    step: str,
    request: ReviewResultRequest,
    user: AuthUser = Depends(get_current_user),
) -> ReviewResultResponse:
    """Save review result to MinIO and optionally post to GitHub issue.

    Saves the review result JSON to MinIO storage and optionally
    posts a summary comment to the associated GitHub issue.
    """
    import hashlib
    import json

    github = _get_github_service()
    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        repo_url = run.github_repo_url
        dir_path = run.github_dir_path or str(run_id)

    # Prepare review data
    review_json = json.dumps(request.review_data, ensure_ascii=False, indent=2)
    review_bytes = review_json.encode("utf-8")
    digest = hashlib.sha256(review_bytes).hexdigest()

    # Save to MinIO
    path = f"{user.tenant_id}/{run_id}/{step}/review.json"
    await store.put(review_bytes, path, "application/json")

    # Post comment to GitHub issue if issue_number provided
    comment_posted = False
    if request.issue_number and repo_url:
        try:
            summary = request.review_data.get("summary", {})
            total = summary.get("total_issues", 0)
            high = summary.get("high", 0)
            medium = summary.get("medium", 0)
            low = summary.get("low", 0)
            assessment = summary.get("overall_assessment", "レビュー完了")
            passed = request.review_data.get("passed", False)

            status_emoji = "✅" if passed else "⚠️"

            comment_body = f"""## {status_emoji} レビュー完了

**結果サマリー:**
- 総検出数: {total}件
- 🔴 高: {high}件 / 🟡 中: {medium}件 / 🟢 低: {low}件

**全体評価:** {assessment}

---
*詳細は `{dir_path}/{step}/review.json` を参照してください。*
"""
            await github.add_issue_comment(
                repo_url=repo_url,
                issue_number=request.issue_number,
                body=comment_body,
            )
            comment_posted = True
        except Exception as e:
            logger.warning(f"Failed to post review comment: {e}")

    return ReviewResultResponse(
        saved=True,
        path=path,
        digest=digest,
        comment_posted=comment_posted,
    )


@router.get("/review-status/{run_id}/{step}", response_model=ReviewStatusResponse)
async def get_review_status(
    run_id: UUID,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> ReviewStatusResponse:
    """Get review status for a step.

    Checks if a review issue exists and whether results have been saved.
    """
    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    # Check if review result exists in MinIO (use storage/ prefix to match actual MinIO paths)
    review_path = f"storage/{user.tenant_id}/{run_id}/{step}/review.json"
    has_result = await store.exists_by_path(review_path)

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # TODO: Track review issue number in database
        # For now, return status based on result file existence

    if has_result:
        return ReviewStatusResponse(
            status="completed",
            has_result=True,
            result_path=review_path,
        )

    # No result yet
    return ReviewStatusResponse(
        status="pending",
        has_result=False,
    )


@router.get("/issue-status/{run_id}/{issue_number}", response_model=IssueStatusResponse)
async def get_issue_status(
    run_id: UUID,
    issue_number: int,
    user: AuthUser = Depends(get_current_user),
) -> IssueStatusResponse:
    """Get GitHub issue status including linked PRs.

    Checks the issue state, latest comments, and any linked pull requests.
    Used for tracking Claude Code edit progress.
    """
    github = _get_github_service()
    db_manager = _get_tenant_db_manager()

    # Get run to find GitHub repo URL
    async with db_manager.get_session(user.tenant_id) as session:
        result = await session.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if not run.github_repo_url:
            raise HTTPException(
                status_code=400,
                detail="Run does not have a GitHub repository configured",
            )

        repo_url = run.github_repo_url

    try:
        status_data = await github.get_issue_status(repo_url, issue_number)

        return IssueStatusResponse(
            issue_number=issue_number,
            status=status_data.get("status", "open"),
            state=status_data.get("state", "open"),
            issue_url=status_data.get("issue_url"),
            updated_at=status_data.get("updated_at"),
            pr_url=status_data.get("pr_url"),
            last_comment=status_data.get("last_comment"),
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Issue #{issue_number} not found.",
        )


# =============================================================================
# Collaborator API Models
# =============================================================================


class AddCollaboratorRequest(BaseModel):
    """Request to add a collaborator to a repository."""

    repo_url: str = Field(..., description="GitHub repository URL")
    username: str = Field(..., description="GitHub username to add")
    permission: str = Field(
        default="push",
        description="Permission level: pull (read), push (write), admin, maintain, triage",
    )


class AddCollaboratorResponse(BaseModel):
    """Response with collaborator addition result."""

    invited: bool
    existing: bool
    permission: str
    invitation_id: int | None = None
    invitation_url: str | None = None
    invitee: str | None = None
    message: str | None = None


class RemoveCollaboratorRequest(BaseModel):
    """Request to remove a collaborator from a repository."""

    repo_url: str = Field(..., description="GitHub repository URL")
    username: str = Field(..., description="GitHub username to remove")


class RemoveCollaboratorResponse(BaseModel):
    """Response with collaborator removal result."""

    removed: bool
    username: str


class CollaboratorInfo(BaseModel):
    """Information about a collaborator."""

    login: str
    id: int | None = None
    avatar_url: str | None = None
    permissions: dict[str, bool] = Field(default_factory=dict)
    role_name: str | None = None


class ListCollaboratorsRequest(BaseModel):
    """Request to list collaborators."""

    repo_url: str = Field(..., description="GitHub repository URL")
    affiliation: str = Field(
        default="all",
        description="Filter: outside (external), direct (explicit access), all",
    )


class ListCollaboratorsResponse(BaseModel):
    """Response with list of collaborators."""

    collaborators: list[CollaboratorInfo]


# =============================================================================
# Collaborator API Endpoints
# =============================================================================


@router.post("/add-collaborator", response_model=AddCollaboratorResponse)
async def add_collaborator(
    request: AddCollaboratorRequest,
    user: AuthUser = Depends(get_current_user),
) -> AddCollaboratorResponse:
    """Add a collaborator to a GitHub repository.

    Adds a user with the specified permission level.
    Requires admin access to the repository.

    Permission levels:
    - pull: Read-only access
    - push: Read and write access (default)
    - admin: Full admin access
    - maintain: Manage repo without admin
    - triage: Manage issues and PRs
    """
    github = _get_github_service()

    try:
        # First check that the caller has admin access
        permissions = await github.check_access(request.repo_url)
        if not permissions.admin:
            raise HTTPException(
                status_code=403,
                detail="Admin access required to add collaborators",
            )

        result = await github.add_collaborator(
            repo_url=request.repo_url,
            username=request.username,
            permission=request.permission,
        )

        return AddCollaboratorResponse(
            invited=result.get("invited", False),
            existing=result.get("existing", False),
            permission=result.get("permission", request.permission),
            invitation_id=result.get("invitation_id"),
            invitation_url=result.get("invitation_url"),
            invitee=result.get("invitee"),
            message=result.get("message"),
        )

    except GitHubValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed. Please check your token.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Repository or user not found.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Admin access required to add collaborators.",
        )
    except GitHubRateLimitError as e:
        reset_msg = ""
        if e.reset_at:
            reset_msg = f" Resets at {e.reset_at.isoformat()}"
        raise HTTPException(
            status_code=429,
            detail=f"GitHub API rate limit exceeded.{reset_msg}",
        )


@router.post("/remove-collaborator", response_model=RemoveCollaboratorResponse)
async def remove_collaborator(
    request: RemoveCollaboratorRequest,
    user: AuthUser = Depends(get_current_user),
) -> RemoveCollaboratorResponse:
    """Remove a collaborator from a GitHub repository.

    Requires admin access to the repository.
    """
    github = _get_github_service()

    try:
        # First check that the caller has admin access
        permissions = await github.check_access(request.repo_url)
        if not permissions.admin:
            raise HTTPException(
                status_code=403,
                detail="Admin access required to remove collaborators",
            )

        result = await github.remove_collaborator(
            repo_url=request.repo_url,
            username=request.username,
        )

        return RemoveCollaboratorResponse(
            removed=result.get("removed", False),
            username=request.username,
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed. Please check your token.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Repository or user not found.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Admin access required to remove collaborators.",
        )


@router.post("/list-collaborators", response_model=ListCollaboratorsResponse)
async def list_collaborators(
    request: ListCollaboratorsRequest,
    user: AuthUser = Depends(get_current_user),
) -> ListCollaboratorsResponse:
    """List collaborators on a GitHub repository.

    Returns users with explicit access to the repository.
    """
    github = _get_github_service()

    try:
        collaborators = await github.list_collaborators(
            repo_url=request.repo_url,
            affiliation=request.affiliation,
        )

        return ListCollaboratorsResponse(
            collaborators=[
                CollaboratorInfo(
                    login=c["login"],
                    id=c.get("id"),
                    avatar_url=c.get("avatar_url"),
                    permissions=c.get("permissions", {}),
                    role_name=c.get("role_name"),
                )
                for c in collaborators
            ]
        )

    except GitHubAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed. Please check your token.",
        )
    except GitHubNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )
    except GitHubPermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot list collaborators.",
        )
