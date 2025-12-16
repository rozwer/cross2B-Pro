# Session 4: Tools (SERP/Fetch/Verify)

## Phase 2（Phase 1完了後、並列実行可能: Session 4, 5）

---

## 作業開始手順

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop

# Phase 1 のマージ確認
git log --oneline develop | head -5
# feat/llm-gemini, feat/llm-openai, feat/llm-anthropic がマージ済みであること

# Worktree作成
TOPIC="tools"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
```

---

## 前提確認

Phase 1 (LLMクライアント) が完了済みであること:

```bash
# LLM モジュールが存在するか確認
ls apps/api/llm/base.py apps/api/llm/schemas.py
```

---

## 実装指示

あなたはSEO記事自動生成システムのバックエンド実装者です。

### 実装対象

LLM以外の外部ツール群

### 前提

- 仕様書/ROADMAP.md の Step 3 を参照
- 仕様書/backend/api.md#tools を参照
- フォールバック禁止（失敗時に別ツールへ自動切替しない）
- **Google Ads API は未取得のため、`search_volume` と `related_keywords` はモック実装とする**

### 成果物

```
apps/api/tools/
├── __init__.py
├── base.py          # 共通 Tool インターフェース
├── schemas.py       # Evidence型、ToolResult型
├── exceptions.py    # ツール関連例外
├── registry.py      # Tool Manifest（tool_id 明示呼び出し用）
├── search.py        # serp_fetch, search_volume(モック), related_keywords(モック)
├── fetch.py         # page_fetch, pdf_extract, primary_collector
├── verify.py        # url_verify
└── mocks/           # モックデータ
    ├── __init__.py
    ├── search_volume_data.json
    └── related_keywords_data.json

tests/unit/tools/
├── __init__.py
├── conftest.py
├── test_search.py
├── test_fetch.py
├── test_verify.py
└── test_registry.py
```

### base.py の実装

```python
from abc import ABC, abstractmethod
from typing import Any
from enum import Enum

class ErrorCategory(str, Enum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    VALIDATION_FAIL = "validation_fail"

class ToolInterface(ABC):
    tool_id: str

    @abstractmethod
    async def execute(self, **kwargs) -> "ToolResult":
        pass
```

### schemas.py の実装

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Any

class Evidence(BaseModel):
    """取得結果の証拠"""
    url: str
    fetched_at: datetime
    excerpt: str  # 抜粋
    content_hash: str  # sha256

class ToolResult(BaseModel):
    success: bool
    data: Any | None = None
    error_category: str | None = None
    error_message: str | None = None
    evidence: list[Evidence] | None = None
    is_mock: bool = False  # モックデータかどうかを明示
```

### registry.py の実装

```python
from typing import Type
from .base import ToolInterface

class ToolRegistry:
    _tools: dict[str, Type[ToolInterface]] = {}

    @classmethod
    def register(cls, tool_id: str):
        def decorator(tool_class: Type[ToolInterface]):
            cls._tools[tool_id] = tool_class
            return tool_class
        return decorator

    @classmethod
    def get(cls, tool_id: str) -> ToolInterface:
        if tool_id not in cls._tools:
            raise ValueError(f"Unknown tool: {tool_id}")
        return cls._tools[tool_id]()

    @classmethod
    def list_tools(cls) -> list[str]:
        return list(cls._tools.keys())
```

### 各ツールの実装

| tool_id | ファイル | 機能 | I/O | 備考 |
|---------|---------|------|-----|------|
| `serp_fetch` | search.py | SERP取得（上位N件URL） | query → urls[] | 実API |
| `search_volume` | search.py | 検索ボリューム取得 | keyword → volume | **モック** |
| `related_keywords` | search.py | 関連語取得 | keyword → keywords[] | **モック** |
| `page_fetch` | fetch.py | ページ取得 + 本文抽出 | url → structured_content | 実API |
| `pdf_extract` | fetch.py | PDFテキスト抽出 | pdf_path → text | 実装 |
| `primary_collector` | fetch.py | 一次情報収集器 | query → evidence_refs[] | 実API |
| `url_verify` | verify.py | URL実在確認 | url → status, final_url, meta | 実API |

---

## Google Ads API モック実装（重要）

### search.py のモック部分

```python
import os
import json
import logging
from pathlib import Path
from .base import ToolInterface, ErrorCategory
from .schemas import ToolResult
from .registry import ToolRegistry

logger = logging.getLogger(__name__)

# モックデータのパス
MOCK_DATA_DIR = Path(__file__).parent / "mocks"


@ToolRegistry.register("search_volume")
class SearchVolumeTool(ToolInterface):
    """
    検索ボリューム取得ツール

    注意: Google Ads API が未取得のため、現在はモック実装
    将来的に実API実装に切り替える際は USE_MOCK_GOOGLE_ADS=false を設定
    """
    tool_id = "search_volume"

    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_GOOGLE_ADS", "true").lower() == "true"
        if self.use_mock:
            logger.warning(
                "SearchVolumeTool: Running in MOCK mode. "
                "Set USE_MOCK_GOOGLE_ADS=false when Google Ads API is available."
            )

    async def execute(self, keyword: str) -> ToolResult:
        if self.use_mock:
            return await self._execute_mock(keyword)
        else:
            return await self._execute_real(keyword)

    async def _execute_mock(self, keyword: str) -> ToolResult:
        """モック実行: 静的データまたは推定値を返す"""
        mock_data = self._load_mock_data("search_volume_data.json")

        # キーワードが事前定義されていれば使用、なければ推定値を生成
        if keyword in mock_data:
            volume = mock_data[keyword]
        else:
            # 簡易的な推定（キーワード長に基づく擬似値）
            volume = max(100, 10000 - len(keyword) * 500)

        logger.info(f"SearchVolume (MOCK): {keyword} -> {volume}")

        return ToolResult(
            success=True,
            data={"keyword": keyword, "volume": volume, "source": "mock"},
            is_mock=True,
        )

    async def _execute_real(self, keyword: str) -> ToolResult:
        """実API実行: Google Ads API を使用"""
        # TODO: Google Ads API 取得後に実装
        raise NotImplementedError(
            "Real Google Ads API not implemented. "
            "Set USE_MOCK_GOOGLE_ADS=true or implement _execute_real()"
        )

    def _load_mock_data(self, filename: str) -> dict:
        filepath = MOCK_DATA_DIR / filename
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return {}


@ToolRegistry.register("related_keywords")
class RelatedKeywordsTool(ToolInterface):
    """
    関連キーワード取得ツール

    注意: Google Ads API が未取得のため、現在はモック実装
    将来的に実API実装に切り替える際は USE_MOCK_GOOGLE_ADS=false を設定
    """
    tool_id = "related_keywords"

    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_GOOGLE_ADS", "true").lower() == "true"
        if self.use_mock:
            logger.warning(
                "RelatedKeywordsTool: Running in MOCK mode. "
                "Set USE_MOCK_GOOGLE_ADS=false when Google Ads API is available."
            )

    async def execute(self, keyword: str, limit: int = 10) -> ToolResult:
        if self.use_mock:
            return await self._execute_mock(keyword, limit)
        else:
            return await self._execute_real(keyword, limit)

    async def _execute_mock(self, keyword: str, limit: int) -> ToolResult:
        """モック実行: 静的データまたはパターン生成"""
        mock_data = self._load_mock_data("related_keywords_data.json")

        if keyword in mock_data:
            keywords = mock_data[keyword][:limit]
        else:
            # パターンベースの擬似関連キーワード生成
            keywords = [
                f"{keyword} とは",
                f"{keyword} 方法",
                f"{keyword} おすすめ",
                f"{keyword} 比較",
                f"{keyword} 選び方",
                f"{keyword} メリット",
                f"{keyword} デメリット",
                f"{keyword} 費用",
                f"{keyword} 口コミ",
                f"{keyword} ランキング",
            ][:limit]

        logger.info(f"RelatedKeywords (MOCK): {keyword} -> {len(keywords)} keywords")

        return ToolResult(
            success=True,
            data={"keyword": keyword, "related": keywords, "source": "mock"},
            is_mock=True,
        )

    async def _execute_real(self, keyword: str, limit: int) -> ToolResult:
        """実API実行: Google Ads API を使用"""
        # TODO: Google Ads API 取得後に実装
        raise NotImplementedError(
            "Real Google Ads API not implemented. "
            "Set USE_MOCK_GOOGLE_ADS=true or implement _execute_real()"
        )

    def _load_mock_data(self, filename: str) -> dict:
        filepath = MOCK_DATA_DIR / filename
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return {}
```

### モックデータファイル

#### mocks/search_volume_data.json

```json
{
  "SEO対策": 12000,
  "ホームページ制作": 8500,
  "Web制作": 6200,
  "コンテンツマーケティング": 3400,
  "リスティング広告": 4800,
  "MEO対策": 2900,
  "WordPress": 18000,
  "ランディングページ": 5100
}
```

#### mocks/related_keywords_data.json

```json
{
  "SEO対策": [
    "SEO対策 とは",
    "SEO対策 費用",
    "SEO対策 やり方",
    "SEO対策 会社",
    "SEO対策 自分で",
    "SEO対策 ツール",
    "SEO対策 効果",
    "SEO対策 初心者",
    "SEO対策 2024",
    "SEO対策 キーワード"
  ],
  "ホームページ制作": [
    "ホームページ制作 費用",
    "ホームページ制作 会社",
    "ホームページ制作 相場",
    "ホームページ制作 自分で",
    "ホームページ制作 流れ",
    "ホームページ制作 おすすめ",
    "ホームページ制作 WordPress",
    "ホームページ制作 補助金",
    "ホームページ制作 フリーランス",
    "ホームページ制作 比較"
  ]
}
```

---

### 共通設計要件

- I/O は原則 JSON
- 取得結果は「証拠」として追跡可能（URL / 取得日時 / 抜粋 / ハッシュ）
- エラー分類を統一: RETRYABLE / NON_RETRYABLE / VALIDATION_FAIL
- リトライ上限3回、ログ必須
- **フォールバック禁止**（失敗時に別ツールへ自動切替しない）
- **モックデータ使用時は `is_mock=True` を必ず設定**
- **モック使用時はログで警告を出力**

---

### DoD（完了条件）

- [ ] Tool Manifest により「何が呼べるか/必要ENVは何か/何が返るか」が一意
- [ ] SERP → 取得 → 抽出 → 保存（参照可能な形）まで一連で通る
- [ ] 失敗時に自動で別手段へ切替しない
- [ ] 全ツールのエラー分類が統一フォーマット
- [ ] Evidence（証拠）が記録される
- [ ] `search_volume`, `related_keywords` がモックで動作する
- [ ] モック使用時に `is_mock=True` が設定される
- [ ] モック使用時にログで警告が出力される
- [ ] pytest が通過
- [ ] mypy が通過

### 禁止事項

- 別ツールへの自動フォールバック
- 失敗を黙って無視
- Evidence なしでの結果返却
- **モックを本番データとして扱う（`is_mock` フラグで明示必須）**

---

## 環境変数

```bash
# .env に追加
USE_MOCK_GOOGLE_ADS=true  # Google Ads API 未取得のため true
```

将来 Google Ads API を取得した場合:
1. `.env` で `USE_MOCK_GOOGLE_ADS=false` に変更
2. `_execute_real()` メソッドを実装
3. Google Ads API の環境変数を設定

---

## 完了後

```bash
# smokeテスト
pytest tests/unit/tools/ -v

# 型チェック
mypy apps/api/tools/

# コミット
git add .
git commit -m "feat(tools): 外部ツール群実装 (SERP/Fetch/Verify + Google Ads モック)"

# push & PR作成
git push -u origin feat/tools
gh pr create --base develop --title "feat(tools): 外部ツール群" --body "## 概要
- ToolRegistry (Manifest)
- serp_fetch (実API)
- search_volume, related_keywords (**モック実装** - Google Ads API未取得)
- page_fetch, pdf_extract, primary_collector (実API)
- url_verify (実API)
- Evidence 追跡

## モックについて
- Google Ads API が未取得のため search_volume, related_keywords はモック
- USE_MOCK_GOOGLE_ADS=true で制御
- is_mock フラグで明示
- 将来の実装切替に対応済み

## 依存
- Phase 1 完了済み

## テスト
- [x] pytest通過
- [x] mypy通過"
```
