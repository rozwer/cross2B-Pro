"""
検証ツール

- url_verify: URL実在確認
"""

import hashlib
import logging
import re
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from .base import ErrorCategory, ToolInterface
from .registry import ToolRegistry
from .schemas import Evidence, ToolResult

logger = logging.getLogger(__name__)

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1


def _compute_hash(content: str) -> str:
    """コンテンツのSHA256ハッシュを計算"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@ToolRegistry.register(
    tool_id="url_verify",
    description="URLの実在確認（ステータスコード、リダイレクト先、メタ情報を取得）",
    required_env=[],
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "確認するURL"},
            "follow_redirects": {
                "type": "boolean",
                "default": True,
                "description": "リダイレクトを追跡するか",
            },
            "timeout": {
                "type": "number",
                "default": 15.0,
                "description": "タイムアウト秒数",
            },
        },
        "required": ["url"],
    },
    output_description="ステータスコード、最終URL、メタ情報",
)
class UrlVerifyTool(ToolInterface):
    """
    URL実在確認ツール

    指定されたURLが実在するかを確認し、
    ステータスコード、最終URL（リダイレクト後）、メタ情報を返す。
    """

    tool_id = "url_verify"

    async def execute(  # type: ignore[override]
        self,
        url: str,
        follow_redirects: bool = True,
        timeout: float = 15.0,
    ) -> ToolResult:
        """URLの実在を確認"""
        # URL検証
        if not url or not url.strip():
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message="URL is required",
            )

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message=f"Invalid URL format: {url}",
            )

        if parsed.scheme not in ("http", "https"):
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message=f"Unsupported scheme: {parsed.scheme}",
            )

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; URLVerifier/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout,
                    follow_redirects=follow_redirects,
                ) as client:
                    # HEADリクエストを試行（軽量）
                    try:
                        response = await client.head(url, headers=headers)
                    except httpx.HTTPStatusError:
                        # HEADが拒否された場合はGETを試行
                        response = await client.get(url, headers=headers)

                status_code = response.status_code
                final_url = str(response.url)
                is_redirect = final_url != url

                # メタ情報を取得（GETの場合のみ）
                meta = {}
                if response.request.method == "GET" and status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type.lower():
                        html = response.text
                        # タイトル抽出
                        title_match = re.search(
                            r"<title[^>]*>(.*?)</title>",
                            html,
                            re.IGNORECASE | re.DOTALL,
                        )
                        if title_match:
                            meta["title"] = title_match.group(1).strip()

                        # canonical URL抽出
                        canonical_match = re.search(
                            r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
                            html,
                            re.IGNORECASE,
                        )
                        if canonical_match:
                            meta["canonical"] = canonical_match.group(1)

                # ステータス判定
                is_accessible = 200 <= status_code < 400
                is_permanent_redirect = status_code in (301, 308)
                is_temporary_redirect = status_code in (302, 303, 307)

                # Evidence作成
                evidence_content = f"{url}|{status_code}|{final_url}"
                evidence = Evidence(
                    url=final_url,
                    fetched_at=datetime.now(UTC),
                    excerpt=f"Status: {status_code}, Accessible: {is_accessible}",
                    content_hash=_compute_hash(evidence_content),
                )

                logger.info(f"url_verify: {url} -> {status_code} (final: {final_url})")

                return ToolResult(
                    success=True,
                    data={
                        "url": url,
                        "final_url": final_url,
                        "status_code": status_code,
                        "is_accessible": is_accessible,
                        "is_redirect": is_redirect,
                        "is_permanent_redirect": is_permanent_redirect,
                        "is_temporary_redirect": is_temporary_redirect,
                        "meta": meta,
                        "headers": {
                            "content-type": response.headers.get("content-type"),
                            "content-length": response.headers.get("content-length"),
                            "server": response.headers.get("server"),
                        },
                    },
                    evidence=[evidence],
                )

            except httpx.TimeoutException as e:
                logger.warning(
                    f"url_verify: Timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.RETRYABLE.value,
                    error_message=f"Request timed out: {url}",
                )

            except httpx.ConnectError as e:
                logger.warning(f"url_verify: Connection error: {e}")
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.NON_RETRYABLE.value,
                    error_message=f"Connection failed: {url}",
                )

            except httpx.RequestError as e:
                logger.warning(
                    f"url_verify: Network error (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.RETRYABLE.value,
                    error_message=f"Network error: {e}",
                )

        return ToolResult(
            success=False,
            error_category=ErrorCategory.RETRYABLE.value,
            error_message="Max retries exceeded",
        )
