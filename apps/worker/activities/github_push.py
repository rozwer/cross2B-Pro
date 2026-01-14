"""GitHub Push Activity - pushes artifacts to GitHub repository.

This activity is called after each step completion to sync artifacts
to the configured GitHub repository for Claude Code editing.

Non-blocking: Failures are logged but don't block workflow execution.
Idempotent: Same content = skip push (uses digest comparison).
"""

import logging
from typing import Any

from temporalio import activity

from apps.api.services.github import (
    GitHubAuthenticationError,
    GitHubError,
    GitHubNotFoundError,
    GitHubPermissionError,
    GitHubRateLimitError,
    GitHubService,
    GitHubValidationError,
)
from apps.api.storage.artifact_store import ArtifactStore

logger = logging.getLogger(__name__)


class GitHubPushActivity:
    """Activity to push step outputs to GitHub.

    Features:
    - Pushes step output JSON to GitHub repository
    - Creates CLAUDE.md on first push for Claude Code context
    - Idempotent: skips if content already exists with same digest
    - Non-blocking: failures logged but don't stop workflow
    """

    def __init__(
        self,
        store: ArtifactStore | None = None,
        github: GitHubService | None = None,
    ):
        self.store = store or ArtifactStore()
        self.github = github or GitHubService()

    async def push_step_output(
        self,
        tenant_id: str,
        run_id: str,
        step: str,
        repo_url: str,
        dir_path: str,
        content: bytes,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        """Push step output to GitHub repository.

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier
            step: Step identifier (e.g., 'step0', 'step3a')
            repo_url: GitHub repository URL
            dir_path: Directory path within repo (e.g., 'keyword_20260114_123456')
            content: Output content to push
            content_type: MIME type of content

        Returns:
            dict with push result (pushed, skipped, error)
        """
        logger.info(f"[GitHubPush] Starting push for {step} to {repo_url}")

        try:
            # Build file path: {dir_path}/{step}/output.json
            file_path = f"{dir_path}/{step}/output.json"

            # Check if file already exists with same content (idempotency)
            import hashlib

            local_digest = hashlib.sha256(content).hexdigest()

            try:
                is_same = await self.github.compare_digest(repo_url, file_path, local_digest)
                if is_same:
                    logger.info(f"[GitHubPush] Skipping {step}: content unchanged")
                    return {
                        "pushed": False,
                        "skipped": True,
                        "reason": "content_unchanged",
                        "path": file_path,
                    }
            except GitHubNotFoundError:
                # File doesn't exist yet, proceed with push
                pass

            # Push file
            commit_message = f"step{step.replace('step', '')}: output\n\nRun: {run_id}\nTenant: {tenant_id}"
            sha = await self.github.push_file(
                repo_url=repo_url,
                path=file_path,
                content=content,
                message=commit_message,
            )

            logger.info(f"[GitHubPush] Pushed {step} successfully: {sha[:8]}")
            return {
                "pushed": True,
                "skipped": False,
                "path": file_path,
                "commit_sha": sha,
            }

        except GitHubAuthenticationError as e:
            logger.warning(f"[GitHubPush] Auth failed for {step}: {e}")
            return {"pushed": False, "error": "authentication_failed", "message": str(e)}

        except GitHubPermissionError as e:
            logger.warning(f"[GitHubPush] Permission denied for {step}: {e}")
            return {"pushed": False, "error": "permission_denied", "message": str(e)}

        except GitHubRateLimitError as e:
            logger.warning(f"[GitHubPush] Rate limited for {step}: {e}")
            return {"pushed": False, "error": "rate_limited", "message": str(e)}

        except GitHubValidationError as e:
            logger.warning(f"[GitHubPush] Validation error for {step}: {e}")
            return {"pushed": False, "error": "validation_error", "message": str(e)}

        except GitHubError as e:
            logger.error(f"[GitHubPush] GitHub error for {step}: {e}")
            return {"pushed": False, "error": "github_error", "message": str(e)}

        except Exception as e:
            logger.error(f"[GitHubPush] Unexpected error for {step}: {e}")
            return {"pushed": False, "error": "unexpected_error", "message": str(e)}

    async def setup_claude_assets(
        self,
        repo_url: str,
        dir_path: str,
        run_id: str,
        tenant_id: str,
        keyword: str,
    ) -> dict[str, Any]:
        """Create initial CLAUDE.md for Claude Code context.

        Called once when workflow starts (if GitHub repo is configured).

        Args:
            repo_url: GitHub repository URL
            dir_path: Directory path within repo
            run_id: Run identifier
            tenant_id: Tenant identifier
            keyword: Target keyword for the article

        Returns:
            dict with setup result
        """
        logger.info(f"[GitHubPush] Setting up Claude assets for {dir_path}")

        try:
            # CLAUDE.md content
            claude_md = f"""# SEO Article Generation - {keyword}

> This directory contains outputs from an automated SEO article generation workflow.
> You can edit these files and the changes will be synced back to the system.

## Run Information

- **Run ID**: {run_id}
- **Keyword**: {keyword}
- **Directory**: {dir_path}

## Directory Structure

```
{dir_path}/
├── .claude/
│   └── CLAUDE.md (this file)
├── step0/
│   └── output.json  # 準備（競合URL等の入力データ）
├── step1/
│   └── output.json  # 競合分析結果
├── step1_5/
│   └── output.json  # 関連キーワード抽出
├── step2/
│   └── output.json  # 検証結果
├── step3a/
│   └── output.json  # クエリ分析
├── step3b/
│   └── output.json  # 構成ベース
├── step3c/
│   └── output.json  # 競合構成分析
├── step3_5/
│   └── output.json  # 人間味付け
├── step4/
│   └── output.json  # 執筆準備
├── step5/
│   └── output.json  # 一次情報
├── step6/
│   └── output.json  # 強化
├── step6_5/
│   └── output.json  # 統合
├── step7a/
│   └── output.json  # 本文生成
├── step7b/
│   └── output.json  # ブラッシュアップ
├── step8/
│   └── output.json  # 検証
├── step9/
│   └── output.json  # 最終調整
├── step10/
│   └── output.json  # 記事出力（Markdown）
├── step11/
│   ├── output.json  # 画像生成メタデータ
│   └── images/      # 生成された画像
└── step12/
    └── output.html  # WordPress HTML
```

## Editing Guidelines

### JSON Files
- Keep the JSON structure intact
- Modify content within existing fields
- Don't add or remove required fields

### Article Content (step10)
- `main_article.content` contains the article in Markdown
- Preserve heading structure (H2, H3)
- Keep CTA placeholders (`[CTA]`) in place

### Images (step11)
- Images are in `step11/images/`
- Update `step11/output.json` if changing image references

## Workflow Commands

To apply changes back to the system:
1. Commit your changes to this repository
2. Create an Issue mentioning @claude with your request
3. Or use the "Sync from GitHub" button in the UI

## Support

For issues or questions, refer to the main documentation or create an Issue.
"""

            # Push CLAUDE.md
            claude_path = f"{dir_path}/.claude/CLAUDE.md"
            commit_message = f"Initial setup: CLAUDE.md\n\nRun: {run_id}\nTenant: {tenant_id}"

            # Check if already exists
            existing = await self.github.get_file(repo_url, claude_path)
            if existing:
                logger.info("[GitHubPush] CLAUDE.md already exists, skipping")
                return {
                    "created": False,
                    "skipped": True,
                    "reason": "already_exists",
                    "path": claude_path,
                }

            sha = await self.github.push_file(
                repo_url=repo_url,
                path=claude_path,
                content=claude_md.encode("utf-8"),
                message=commit_message,
            )

            logger.info(f"[GitHubPush] Created CLAUDE.md: {sha[:8]}")
            return {
                "created": True,
                "skipped": False,
                "path": claude_path,
                "commit_sha": sha,
            }

        except Exception as e:
            logger.error(f"[GitHubPush] Failed to setup Claude assets: {e}")
            return {"created": False, "error": str(e)}


# Temporal activity function
@activity.defn(name="github_push_step")
async def github_push_step(
    tenant_id: str,
    run_id: str,
    step: str,
    repo_url: str,
    dir_path: str,
    content: bytes,
) -> dict[str, Any]:
    """Temporal activity wrapper for pushing step output to GitHub.

    Non-blocking: Returns result dict, never raises.
    """
    push_activity = GitHubPushActivity()
    return await push_activity.push_step_output(
        tenant_id=tenant_id,
        run_id=run_id,
        step=step,
        repo_url=repo_url,
        dir_path=dir_path,
        content=content,
    )


@activity.defn(name="github_setup_claude")
async def github_setup_claude(
    repo_url: str,
    dir_path: str,
    run_id: str,
    tenant_id: str,
    keyword: str,
) -> dict[str, Any]:
    """Temporal activity wrapper for setting up Claude Code assets.

    Non-blocking: Returns result dict, never raises.
    """
    push_activity = GitHubPushActivity()
    return await push_activity.setup_claude_assets(
        repo_url=repo_url,
        dir_path=dir_path,
        run_id=run_id,
        tenant_id=tenant_id,
        keyword=keyword,
    )
