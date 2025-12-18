# Worktree: helpers-parsing 要件定義書

> **ブランチ名**: `feat/helpers-parsing`
> **担当**: OutputParser + Shared Schemas
> **優先度**: 最高（他ヘルパーの基盤）

---

## 目的

LLM出力のJSON/Markdownパースを堅牢化する共通ヘルパーを実装する。
全ステップで使用されるため、最初に実装する必要がある。

---

## 成果物

### ファイル構成

```
apps/worker/helpers/
├── __init__.py           # エクスポート定義
├── output_parser.py      # OutputParser クラス
├── schemas.py            # 共通Pydanticモデル
tests/unit/helpers/
├── __init__.py
├── test_output_parser.py
├── test_schemas.py
```

---

## 1. Shared Schemas (`schemas.py`)

### 1.1 品質関連スキーマ

```python
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class QualityResult(BaseModel):
    """品質検証結果（全バリデータ共通）"""
    is_acceptable: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class InputValidationResult(BaseModel):
    """入力検証結果"""
    is_valid: bool
    missing_required: list[str] = Field(default_factory=list)
    missing_recommended: list[str] = Field(default_factory=list)
    quality_issues: list[str] = Field(default_factory=list)


class CompletenessResult(BaseModel):
    """完全性チェック結果"""
    is_complete: bool
    is_truncated: bool = False
    issues: list[str] = Field(default_factory=list)
```

### 1.2 パース関連スキーマ

```python
class ParseResult(BaseModel):
    """JSONパース結果"""
    success: bool
    data: dict[str, Any] | None = None
    raw: str = ""
    format_detected: str = ""  # "json", "markdown", "unknown"
    fixes_applied: list[str] = Field(default_factory=list)
```

### 1.3 メトリクス関連スキーマ

```python
class TextMetrics(BaseModel):
    """テキストメトリクス"""
    char_count: int
    word_count: int
    paragraph_count: int
    sentence_count: int


class MarkdownMetrics(BaseModel):
    """Markdownメトリクス"""
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    h4_count: int = 0
    list_count: int = 0
    code_block_count: int = 0
    link_count: int = 0
    image_count: int = 0
```

### 1.4 チェックポイント関連スキーマ

```python
class CheckpointMetadata(BaseModel):
    """チェックポイントメタデータ"""
    phase: str
    created_at: datetime
    input_digest: str | None = None
    step_id: str = ""
```

### 1.5 Activity出力基底クラス

```python
class StepOutputBase(BaseModel):
    """ステップ出力の基底クラス"""
    step: str
    keyword: str
    execution_time_ms: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
```

---

## 2. OutputParser (`output_parser.py`)

### 2.1 クラス定義

````python
class OutputParser:
    """LLM出力のパーサー"""

    def parse_json(self, content: str) -> ParseResult:
        """
        JSONをパース（コードブロック対応）

        処理フロー:
        1. コードブロック除去（```json ... ``` or ``` ... ```）
        2. JSONパース試行
        3. 失敗時は決定的修正を適用して再試行
        4. 結果をParseResultで返す

        Returns:
            ParseResult: パース結果（成功/失敗、データ、適用した修正）
        """

    def extract_json_block(self, content: str) -> str:
        """
        JSONコードブロックを抽出

        対応パターン:
        - ```json\n{...}\n```
        - ```\n{...}\n```
        - {...} (コードブロックなし)
        """

    def apply_deterministic_fixes(self, content: str) -> tuple[str | None, list[str]]:
        """
        決定的な修正を適用（ログ必須）

        許可される修正:
        - 末尾カンマ除去: ,} → }, ,] → ]

        禁止される修正:
        - 値の推測・補完
        - 構造の変更
        - フォールバック値の挿入

        Returns:
            tuple[修正後文字列 | None, 適用した修正名リスト]
        """

    def looks_like_markdown(self, content: str) -> bool:
        """
        Markdown形式かどうか判定

        判定基準:
        - ^#\s (H1)
        - ^##\s (H2)
        - ^###\s (H3)
        - ^\*\s or ^\-\s (リスト)
        - ^\d+\.\s (番号付きリスト)
        """

    def looks_like_json(self, content: str) -> bool:
        """
        JSON形式かどうか判定

        判定基準:
        - { で始まり } で終わる
        - [ で始まり ] で終わる
        """
````

### 2.2 使用例

```python
from apps.worker.helpers import OutputParser, ParseResult

parser = OutputParser()

# 基本的な使用
result = parser.parse_json(llm_response.content)
if result.success:
    data = result.data
    if result.fixes_applied:
        logger.info(f"Applied fixes: {result.fixes_applied}")
else:
    if parser.looks_like_markdown(llm_response.content):
        # Markdown形式として処理
        pass
    else:
        raise ActivityError("Failed to parse output")
```

---

## テスト要件

### test_output_parser.py

````python
import pytest
from apps.worker.helpers import OutputParser, ParseResult


class TestParseJson:
    """parse_json のテスト"""

    def test_parse_plain_json(self):
        """プレーンJSONをパースできる"""
        parser = OutputParser()
        result = parser.parse_json('{"key": "value"}')

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.format_detected == "json"
        assert result.fixes_applied == []

    def test_parse_json_with_code_block(self):
        """```json コードブロックをパースできる"""
        parser = OutputParser()
        content = '```json\n{"key": "value"}\n```'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}
        assert "code_block_removed" in result.fixes_applied

    def test_parse_json_with_generic_code_block(self):
        """``` コードブロック（言語指定なし）をパースできる"""
        parser = OutputParser()
        content = '```\n{"key": "value"}\n```'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}

    def test_fix_trailing_comma_in_object(self):
        """オブジェクト末尾のカンマを修正"""
        parser = OutputParser()
        content = '{"key": "value",}'
        result = parser.parse_json(content)

        assert result.success is True
        assert "trailing_comma_removed" in result.fixes_applied

    def test_fix_trailing_comma_in_array(self):
        """配列末尾のカンマを修正"""
        parser = OutputParser()
        content = '["a", "b",]'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == ["a", "b"]
        assert "trailing_comma_removed" in result.fixes_applied

    def test_parse_failure_returns_raw(self):
        """パース失敗時はraw文字列を返す"""
        parser = OutputParser()
        content = 'This is not JSON'
        result = parser.parse_json(content)

        assert result.success is False
        assert result.data is None
        assert result.raw == content
        assert result.format_detected == "unknown"

    def test_nested_json(self):
        """ネストしたJSONをパースできる"""
        parser = OutputParser()
        content = '{"outer": {"inner": [1, 2, 3]}}'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data["outer"]["inner"] == [1, 2, 3]

    def test_json_with_surrounding_text(self):
        """前後にテキストがあってもコードブロック内をパース"""
        parser = OutputParser()
        content = 'Here is the result:\n```json\n{"key": "value"}\n```\nDone.'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}


class TestLooksLikeMarkdown:
    """looks_like_markdown のテスト"""

    @pytest.mark.parametrize("content", [
        "# Title",
        "## Section",
        "### Subsection",
        "* list item",
        "- list item",
        "1. numbered item",
    ])
    def test_detects_markdown(self, content):
        """Markdown形式を検出"""
        parser = OutputParser()
        assert parser.looks_like_markdown(content) is True

    def test_plain_text_not_markdown(self):
        """プレーンテキストはMarkdownではない"""
        parser = OutputParser()
        assert parser.looks_like_markdown("Just plain text") is False


class TestLooksLikeJson:
    """looks_like_json のテスト"""

    def test_detects_json_object(self):
        """JSONオブジェクトを検出"""
        parser = OutputParser()
        assert parser.looks_like_json('{"key": "value"}') is True

    def test_detects_json_array(self):
        """JSON配列を検出"""
        parser = OutputParser()
        assert parser.looks_like_json('[1, 2, 3]') is True

    def test_not_json(self):
        """JSONでないものを判定"""
        parser = OutputParser()
        assert parser.looks_like_json("plain text") is False
        assert parser.looks_like_json("# Markdown") is False
````

### test_schemas.py

```python
import pytest
from datetime import datetime
from apps.worker.helpers.schemas import (
    QualityResult,
    ParseResult,
    TextMetrics,
    CheckpointMetadata,
)


class TestQualityResult:
    """QualityResult のテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        result = QualityResult(is_acceptable=True)

        assert result.is_acceptable is True
        assert result.issues == []
        assert result.warnings == []
        assert result.scores == {}

    def test_with_issues(self):
        """issues を設定できる"""
        result = QualityResult(
            is_acceptable=False,
            issues=["missing_keyword", "too_short"],
        )

        assert result.is_acceptable is False
        assert len(result.issues) == 2


class TestParseResult:
    """ParseResult のテスト"""

    def test_successful_parse(self):
        """成功したパース結果"""
        result = ParseResult(
            success=True,
            data={"key": "value"},
            format_detected="json",
        )

        assert result.success is True
        assert result.data == {"key": "value"}

    def test_failed_parse(self):
        """失敗したパース結果"""
        result = ParseResult(
            success=False,
            raw="invalid content",
            format_detected="unknown",
        )

        assert result.success is False
        assert result.data is None
        assert result.raw == "invalid content"


class TestTextMetrics:
    """TextMetrics のテスト"""

    def test_all_fields_required(self):
        """全フィールドが必須"""
        metrics = TextMetrics(
            char_count=100,
            word_count=20,
            paragraph_count=3,
            sentence_count=5,
        )

        assert metrics.char_count == 100
        assert metrics.word_count == 20


class TestCheckpointMetadata:
    """CheckpointMetadata のテスト"""

    def test_with_required_fields(self):
        """必須フィールドのみで作成"""
        meta = CheckpointMetadata(
            phase="queries_generated",
            created_at=datetime.utcnow(),
        )

        assert meta.phase == "queries_generated"
        assert meta.input_digest is None

    def test_with_optional_fields(self):
        """オプションフィールド付きで作成"""
        meta = CheckpointMetadata(
            phase="queries_generated",
            created_at=datetime.utcnow(),
            input_digest="abc123",
            step_id="step5",
        )

        assert meta.input_digest == "abc123"
        assert meta.step_id == "step5"
```

---

## 実装上の注意

### フォールバック禁止

```python
# ❌ 禁止: フォールバック値の挿入
def parse_json(self, content: str) -> ParseResult:
    try:
        return json.loads(content)
    except:
        return {"default": "value"}  # 禁止！

# ✅ 正しい: 失敗を明示
def parse_json(self, content: str) -> ParseResult:
    try:
        data = json.loads(content)
        return ParseResult(success=True, data=data, ...)
    except json.JSONDecodeError:
        return ParseResult(success=False, raw=content, ...)
```

### 決定的修正のログ

```python
# ✅ 修正を適用したら必ずログに記録
if "trailing_comma_removed" in fixes_applied:
    activity.logger.info(f"Applied JSON fix: trailing_comma_removed")
```

---

## 完了条件

- [ ] `apps/worker/helpers/__init__.py` にエクスポート定義
- [ ] `apps/worker/helpers/schemas.py` 全スキーマ実装
- [ ] `apps/worker/helpers/output_parser.py` 全メソッド実装
- [ ] `tests/unit/helpers/test_schemas.py` 全テスト通過
- [ ] `tests/unit/helpers/test_output_parser.py` 全テスト通過
- [ ] `uv run mypy apps/worker/helpers/` 型エラーなし
- [ ] `uv run ruff check apps/worker/helpers/` リントエラーなし

---

## 依存関係

### このworktreeが依存するもの

- なし（最初に実装）

### このworktreeに依存するもの

- `helpers-validation` (QualityResult, InputValidationResult を使用)
- `helpers-metrics` (TextMetrics, MarkdownMetrics, CheckpointMetadata を使用)
- 全ステップ (ParseResult, OutputParser を使用)
