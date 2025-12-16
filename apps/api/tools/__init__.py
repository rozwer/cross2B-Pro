"""
外部ツールモジュール

SEO記事自動生成システムで使用する外部ツール群を提供する。

## 登録済みツール

| tool_id | 説明 | 状態 |
|---------|------|------|
| serp_fetch | SERP取得（上位N件URL） | 実API |
| search_volume | 検索ボリューム取得 | モック |
| related_keywords | 関連キーワード取得 | モック |
| page_fetch | ページ取得 + 本文抽出 | 実API |
| pdf_extract | PDFテキスト抽出 | 実装済み |
| primary_collector | 一次情報収集器 | 実API |
| url_verify | URL実在確認 | 実API |

## 使用例

```python
from apps.api.tools import ToolRegistry, ToolResult

# ツール一覧を取得
tools = ToolRegistry.list_tools()

# ツールを取得して実行
serp_tool = ToolRegistry.get("serp_fetch")
result = await serp_tool.execute(query="SEO対策", num_results=10)

# 結果を確認
if result.success:
    print(result.data)
    for evidence in result.evidence:
        print(f"  - {evidence.url}")
else:
    print(f"Error: {result.error_message}")
```

## 環境変数

- SERP_API_KEY: SerpApi のAPIキー（serp_fetch, primary_collector に必要）
- USE_MOCK_GOOGLE_ADS: Google Ads モックモード（true/false、デフォルト true）
"""

from .base import ErrorCategory, ToolInterface
from .exceptions import (
    ContentExtractionError,
    NonRetryableError,
    RateLimitError,
    RetryableError,
    ToolError,
    ToolNotFoundError,
    ValidationError,
)
from .registry import ToolManifest, ToolRegistry
from .schemas import Evidence, ToolResult

# ツールを登録（インポート時に自動登録）
from . import fetch, search, verify

__all__ = [
    # 基盤
    "ToolInterface",
    "ToolRegistry",
    "ToolManifest",
    "ErrorCategory",
    # スキーマ
    "ToolResult",
    "Evidence",
    # 例外
    "ToolError",
    "RetryableError",
    "NonRetryableError",
    "ValidationError",
    "ToolNotFoundError",
    "RateLimitError",
    "ContentExtractionError",
]
