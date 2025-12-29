# Batch 1: Step5 Primary Collection - ヘルパー統合

> **優先度**: 最高（フォールバック禁止違反の修正）

## 対象ファイル

- `apps/worker/activities/step5.py`

## 緊急修正

### フォールバック禁止違反（Line 92-98）

**現状コード**:

```python
except Exception:
    # Fall back to basic queries if parsing fails  ← 禁止違反
    search_queries = [
        f"{keyword} research statistics",
        f"{keyword} official data",
        f"{keyword} academic study",
    ]
```

**修正後**:

```python
from apps.worker.helpers import OutputParser, ParseResult
from apps.worker.helpers.schemas import QualityResult

# フォールバックではなく、失敗を明示
except Exception as e:
    raise ActivityError(
        f"Query generation failed: {e}",
        category=ErrorCategory.RETRYABLE,
        details={"error": str(e)},
    ) from e
```

## 統合するヘルパー

### 1. OutputParser

```python
from apps.worker.helpers import OutputParser

class Step5PrimaryCollection(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = OutputParser()

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # クエリ生成後のパース
        query_response = await llm.generate(...)

        # OutputParser を使用
        parse_result = self.parser.parse_json(query_response.content)

        if not parse_result.success:
            # フォールバックせず失敗
            raise ActivityError(
                f"Failed to parse queries: format={parse_result.format_detected}",
                category=ErrorCategory.RETRYABLE,
                details={"raw": parse_result.raw[:500]},
            )

        search_queries = parse_result.data.get("queries", [])
        if parse_result.fixes_applied:
            activity.logger.info(f"JSON fixes applied: {parse_result.fixes_applied}")
```

### 2. InputValidator

```python
from apps.worker.helpers import InputValidator
from apps.worker.helpers.schemas import InputValidationResult

class Step5PrimaryCollection(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_validator = InputValidator(
            required_fields=["step4.outline"],
            recommended_fields=["step3b.cooccurrence_analysis"],
        )

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 入力検証
        step4_data = await load_step_data(...) or {}

        validation = self.input_validator.validate({
            "step4": step4_data,
        })

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation.missing_recommended:
            activity.logger.warning(f"Recommended inputs missing: {validation.missing_recommended}")
```

### 3. QualityValidator

```python
from apps.worker.helpers import QualityValidator
from apps.worker.helpers.quality_validator import (
    MinCountValidator,
    KeywordPresenceValidator,
    CompositeValidator,
)

class Step5PrimaryCollection(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ソース収集の品質検証
        self.source_validator = CompositeValidator([
            MinCountValidator(field="sources", min_count=2, issue_code="too_few_sources"),
        ])

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... 収集処理 ...

        # 品質検証
        quality = self.source_validator.validate({
            "sources": collected_sources,
        })

        if not quality.is_acceptable:
            raise ActivityError(
                f"Source collection quality insufficient: {quality.issues}",
                category=ErrorCategory.RETRYABLE,
                details={"issues": quality.issues},
            )
```

### 4. CheckpointManager

```python
from apps.worker.helpers import CheckpointManager

class Step5PrimaryCollection(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # クエリ生成のチェックポイント
        queries_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "queries_generated"
        )

        if queries_checkpoint:
            search_queries = queries_checkpoint["queries"]
        else:
            # クエリ生成
            search_queries = await self._generate_queries(llm, keyword, outline)

            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "queries_generated",
                {"queries": search_queries}
            )

        # 部分収集のチェックポイント
        collection_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "collection_progress"
        )

        if collection_checkpoint:
            completed_queries = set(collection_checkpoint["completed_queries"])
            collected_sources = collection_checkpoint["collected_sources"]
        else:
            completed_queries = set()
            collected_sources = []

        # 未完了クエリのみ実行
        for query in search_queries:
            if query in completed_queries:
                continue

            sources, error = await self._execute_query_with_retry(primary_collector, query)

            if sources:
                collected_sources.extend(sources)

            completed_queries.add(query)

            # 各クエリ完了後にチェックポイント保存
            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "collection_progress",
                {
                    "completed_queries": list(completed_queries),
                    "collected_sources": collected_sources,
                }
            )
```

## 構造化出力スキーマ

`apps/worker/activities/schemas/step5.py` を作成：

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal, Optional
from datetime import datetime

class PrimarySource(BaseModel):
    """一次資料"""
    url: HttpUrl
    title: str
    source_type: Literal[
        "academic_paper",
        "government_report",
        "statistics",
        "official_document",
        "industry_report",
        "news_article",
        "other"
    ] = "other"
    excerpt: str = Field(..., max_length=500)
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    verified: bool = False

class Step5Output(BaseModel):
    """Step5 の構造化出力"""
    keyword: str
    search_queries: list[str]
    sources: list[PrimarySource]
    failed_queries: list[dict]
    collection_stats: dict[str, int]
```

## テスト更新

`tests/unit/activities/test_step5.py` に追加：

```python
import pytest
from apps.worker.activities.step5 import Step5PrimaryCollection

class TestStep5Helpers:
    """ヘルパー統合のテスト"""

    def test_no_fallback_on_parse_failure(self):
        """パース失敗時にフォールバックしない"""
        # フォールバックではなくエラーが発生することを確認
        with pytest.raises(ActivityError) as exc_info:
            # パース失敗をシミュレート
            ...

        assert exc_info.value.category == ErrorCategory.RETRYABLE
        assert "fallback" not in str(exc_info.value).lower()

    def test_input_validation(self):
        """入力検証が機能する"""
        # step4.outline が欠落でエラー
        ...

    def test_checkpoint_resume(self):
        """チェックポイントから再開できる"""
        # 3クエリ中2クエリ完了状態から再開
        ...
```

## 完了条件

- [ ] フォールバックコード削除（Line 92-98）
- [ ] OutputParser 統合
- [ ] InputValidator 統合
- [ ] QualityValidator 統合
- [ ] CheckpointManager 統合
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過
- [ ] `uv run mypy apps/worker/activities/step5.py` 型エラーなし
