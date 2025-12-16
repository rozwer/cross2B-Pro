"""
コンテンツ取得・抽出ツール

- page_fetch: ページ取得 + 本文抽出
- pdf_extract: PDFテキスト抽出
- primary_collector: 一次情報収集器
"""

import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from .base import ErrorCategory, ToolInterface
from .registry import ToolRegistry
from .schemas import Evidence, ToolResult

logger = logging.getLogger(__name__)

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1

# コンテンツ取得設定
DEFAULT_TIMEOUT = 30.0
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB


def _compute_hash(content: str | bytes) -> str:
    """コンテンツのSHA256ハッシュを計算"""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _extract_text_from_html(html: str) -> dict[str, Any]:
    """
    HTMLから本文を抽出

    簡易実装: <script>, <style>, <nav>, <header>, <footer>等を除去し、
    本文テキストを抽出する。
    本格的な実装では readability-lxml や trafilatura を使用する。
    """
    # script, style, nav, header, footer を除去
    patterns_to_remove = [
        r"<script[^>]*>.*?</script>",
        r"<style[^>]*>.*?</style>",
        r"<nav[^>]*>.*?</nav>",
        r"<header[^>]*>.*?</header>",
        r"<footer[^>]*>.*?</footer>",
        r"<aside[^>]*>.*?</aside>",
        r"<!--.*?-->",
    ]

    text = html
    for pattern in patterns_to_remove:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)

    # HTMLタグを除去
    text = re.sub(r"<[^>]+>", " ", text)
    # 連続する空白を整理
    text = re.sub(r"\s+", " ", text).strip()

    # タイトル抽出
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""

    # メタディスクリプション抽出
    desc_match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
        html,
        re.IGNORECASE,
    )
    if not desc_match:
        desc_match = re.search(
            r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']',
            html,
            re.IGNORECASE,
        )
    description = desc_match.group(1).strip() if desc_match else ""

    # H1抽出
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    h1 = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip() if h1_match else ""

    return {
        "title": title,
        "description": description,
        "h1": h1,
        "body_text": text,
        "word_count": len(text.split()),
    }


@ToolRegistry.register(
    tool_id="page_fetch",
    description="Webページを取得し、本文テキストを抽出",
    required_env=[],
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "取得するURL"},
            "extract_links": {
                "type": "boolean",
                "default": False,
                "description": "リンク一覧も抽出するか",
            },
        },
        "required": ["url"],
    },
    output_description="抽出されたタイトル、本文テキスト、メタ情報",
)
class PageFetchTool(ToolInterface):
    """
    ページ取得 + 本文抽出ツール

    指定されたURLからHTMLを取得し、本文テキストを抽出する。
    """

    tool_id = "page_fetch"

    def __init__(self) -> None:
        self.timeout = DEFAULT_TIMEOUT
        self.max_content_length = MAX_CONTENT_LENGTH

    async def execute(  # type: ignore[override]
        self, url: str, extract_links: bool = False
    ) -> ToolResult:
        """ページを取得して本文を抽出"""
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
                error_message=f"Invalid URL: {url}",
            )

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SEOBot/1.0; +https://example.com/bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en;q=0.9",
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=True
                ) as client:
                    response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type.lower():
                        return ToolResult(
                            success=False,
                            error_category=ErrorCategory.VALIDATION_FAIL.value,
                            error_message=f"Not HTML content: {content_type}",
                        )

                    html = response.text
                    extracted = _extract_text_from_html(html)

                    # リンク抽出（オプション）
                    links = []
                    if extract_links:
                        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\']'
                        for match in re.finditer(link_pattern, html, re.IGNORECASE):
                            href = match.group(1)
                            if href.startswith(("http://", "https://")):
                                links.append(href)
                            elif href.startswith("/"):
                                links.append(urljoin(url, href))
                        extracted["links"] = links[:50]  # 上限50件

                    # Evidence作成
                    evidence = Evidence(
                        url=str(response.url),  # リダイレクト後のURL
                        fetched_at=datetime.now(UTC),
                        excerpt=extracted["body_text"][:200],
                        content_hash=_compute_hash(html),
                    )

                    logger.info(
                        f"page_fetch: Retrieved {url} ({extracted['word_count']} words)"
                    )

                    return ToolResult(
                        success=True,
                        data={
                            "url": str(response.url),
                            "original_url": url,
                            **extracted,
                        },
                        evidence=[evidence],
                    )

                elif response.status_code == 404:
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.NON_RETRYABLE.value,
                        error_message=f"Page not found: {url}",
                    )
                elif response.status_code == 403:
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.NON_RETRYABLE.value,
                        error_message=f"Access forbidden: {url}",
                    )
                elif response.status_code == 429:
                    logger.warning(
                        f"page_fetch: Rate limited (attempt {attempt + 1}/{MAX_RETRIES})"
                    )
                    if attempt < MAX_RETRIES - 1:
                        import asyncio

                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.RETRYABLE.value,
                        error_message="Rate limit exceeded after retries",
                    )
                elif response.status_code >= 500:
                    logger.warning(
                        "page_fetch: Server error %d (attempt %d/%d)",
                        response.status_code,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    if attempt < MAX_RETRIES - 1:
                        import asyncio

                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.RETRYABLE.value,
                        error_message=f"Server error: {response.status_code}",
                    )
                else:
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.NON_RETRYABLE.value,
                        error_message=f"HTTP error: {response.status_code}",
                    )

            except httpx.TimeoutException as e:
                logger.warning(
                    f"page_fetch: Timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.RETRYABLE.value,
                    error_message="Request timed out after retries",
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"page_fetch: Network error (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
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


@ToolRegistry.register(
    tool_id="pdf_extract",
    description="PDFファイルからテキストを抽出",
    required_env=[],
    input_schema={
        "type": "object",
        "properties": {
            "pdf_path": {"type": "string", "description": "PDFファイルパス"},
            "pdf_url": {"type": "string", "description": "PDFのURL（ダウンロード用）"},
            "max_pages": {
                "type": "integer",
                "default": 50,
                "description": "最大ページ数",
            },
        },
        "required": [],
    },
    output_description="抽出されたテキストとページ情報",
)
class PdfExtractTool(ToolInterface):
    """
    PDFテキスト抽出ツール

    PDFファイルからテキストを抽出する。
    ローカルファイルパスまたはURLを指定可能。
    """

    tool_id = "pdf_extract"

    async def execute(  # type: ignore[override]
        self,
        pdf_path: str | None = None,
        pdf_url: str | None = None,
        max_pages: int = 50,
    ) -> ToolResult:
        """PDFからテキストを抽出"""
        if not pdf_path and not pdf_url:
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message="Either pdf_path or pdf_url is required",
            )

        try:
            # pypdf をインポート（遅延インポート）
            try:
                from pypdf import PdfReader
            except ImportError:
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.NON_RETRYABLE.value,
                    error_message="pypdf is not installed. Run: pip install pypdf",
                )

            pdf_data = None
            source_url = ""

            # URLからダウンロード
            if pdf_url:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(pdf_url)
                    if response.status_code != 200:
                        return ToolResult(
                            success=False,
                            error_category=ErrorCategory.NON_RETRYABLE.value,
                            error_message=f"Failed to download PDF: {response.status_code}",
                        )
                    pdf_data = response.content
                    source_url = pdf_url

            # ローカルファイルから読み込み
            elif pdf_path:
                path = Path(pdf_path)
                if not path.exists():
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.NON_RETRYABLE.value,
                        error_message=f"PDF file not found: {pdf_path}",
                    )
                pdf_data = path.read_bytes()
                source_url = f"file://{path.absolute()}"

            # PDF解析
            import io

            if pdf_data is None:
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.NON_RETRYABLE.value,
                    error_message="Failed to read PDF data",
                )

            reader = PdfReader(io.BytesIO(pdf_data))
            total_pages = len(reader.pages)
            pages_to_extract = min(total_pages, max_pages)

            extracted_text = []
            for i in range(pages_to_extract):
                page = reader.pages[i]
                text = page.extract_text() or ""
                extracted_text.append({"page": i + 1, "text": text})

            full_text = "\n".join([str(p["text"]) for p in extracted_text])

            evidence = Evidence(
                url=source_url,
                fetched_at=datetime.now(UTC),
                excerpt=full_text[:200],
                content_hash=_compute_hash(pdf_data if pdf_data else b""),
            )

            logger.info(
                f"pdf_extract: Extracted {pages_to_extract}/{total_pages} pages"
            )

            return ToolResult(
                success=True,
                data={
                    "source": source_url,
                    "total_pages": total_pages,
                    "extracted_pages": pages_to_extract,
                    "pages": extracted_text,
                    "full_text": full_text,
                    "word_count": len(full_text.split()),
                },
                evidence=[evidence],
            )

        except Exception as e:
            logger.error(f"pdf_extract: Error extracting PDF: {e}")
            return ToolResult(
                success=False,
                error_category=ErrorCategory.NON_RETRYABLE.value,
                error_message=f"PDF extraction failed: {e}",
            )


@ToolRegistry.register(
    tool_id="primary_collector",
    description="一次情報収集器 - 複数のソースから関連情報を収集",
    required_env=["SERP_API_KEY"],
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "検索クエリ"},
            "num_sources": {
                "type": "integer",
                "default": 5,
                "description": "収集するソース数",
            },
            "include_pdfs": {
                "type": "boolean",
                "default": True,
                "description": "PDFも収集対象に含めるか",
            },
        },
        "required": ["query"],
    },
    output_description="収集した一次情報のリストと証拠参照",
)
class PrimaryCollectorTool(ToolInterface):
    """
    一次情報収集器

    指定されたクエリに対して、SERP取得 + ページ取得 + 抽出を
    一連の流れで実行し、一次情報を収集する。
    """

    tool_id = "primary_collector"

    async def execute(  # type: ignore[override]
        self,
        query: str,
        num_sources: int = 5,
        include_pdfs: bool = True,
    ) -> ToolResult:
        """一次情報を収集"""
        if not query or not query.strip():
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message="Query is required",
            )

        # SERPツールを取得して実行
        serp_tool = ToolRegistry.get("serp_fetch")
        serp_result = await serp_tool.execute(
            query=query, num_results=num_sources * 2  # 余分に取得
        )

        if not serp_result.success:
            return ToolResult(
                success=False,
                error_category=serp_result.error_category,
                error_message=f"SERP fetch failed: {serp_result.error_message}",
            )

        data = serp_result.data or {}
        results = data.get("results", [])
        if not results:
            return ToolResult(
                success=True,
                data={"query": query, "sources": [], "total": 0},
                evidence=[],
            )

        # ページを取得して本文抽出
        page_tool = ToolRegistry.get("page_fetch")
        pdf_tool = ToolRegistry.get("pdf_extract")

        collected_sources = []
        all_evidence = list(serp_result.evidence or [])

        for item in results[:num_sources]:
            url = item.get("url", "")
            if not url:
                continue

            # PDF判定
            is_pdf = url.lower().endswith(".pdf")

            if is_pdf and include_pdfs:
                result = await pdf_tool.execute(pdf_url=url)
            else:
                result = await page_tool.execute(url=url)

            if result.success:
                collected_sources.append(
                    {
                        "url": url,
                        "title": item.get("title", ""),
                        "type": "pdf" if is_pdf else "webpage",
                        "content": result.data,
                    }
                )
                if result.evidence:
                    all_evidence.extend(result.evidence)
            else:
                logger.warning(f"primary_collector: Failed to fetch {url}: {result.error_message}")

        logger.info(
            f"primary_collector: Collected {len(collected_sources)} sources for '{query}'"
        )

        return ToolResult(
            success=True,
            data={
                "query": query,
                "sources": collected_sources,
                "total": len(collected_sources),
            },
            evidence=all_evidence,
        )
