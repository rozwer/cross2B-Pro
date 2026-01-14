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


class DiffResponse(BaseModel):
    """Response with diff between GitHub and MinIO."""

    has_diff: bool
    diff: str | None = None
    github_sha: str | None = None
    minio_digest: str | None = None


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
    async with db_manager.session(user.tenant_id) as session:
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
    async with db_manager.session(user.tenant_id) as session:
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

    try:
        diff = await github.get_diff(
            repo_url=repo_url,
            path=file_path,
            local_content=minio_content,
        )

        # Get GitHub file SHA
        github_sha = await github.get_file_sha(repo_url, file_path)

        # Calculate MinIO digest
        import hashlib

        minio_digest = hashlib.sha256(minio_content).hexdigest()

        return DiffResponse(
            has_diff=diff is not None and len(diff) > 0,
            diff=diff,
            github_sha=github_sha,
            minio_digest=minio_digest,
        )

    except GitHubNotFoundError:
        return DiffResponse(
            has_diff=True,
            diff="GitHub file not found",
            github_sha=None,
            minio_digest=hashlib.sha256(minio_content).hexdigest(),
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
    async with db_manager.session(user.tenant_id) as session:
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
        async with db_manager.session(user.tenant_id) as session:
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

    async with db_manager.session(user.tenant_id) as session:
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
