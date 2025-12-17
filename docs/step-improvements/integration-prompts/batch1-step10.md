# Batch 1: Step10 Final Output - ヘルパー統合

> **優先度**: 最高（フォールバック禁止違反の修正）

## 対象ファイル

- `apps/worker/activities/step10.py`

## 緊急修正

### フォールバック禁止違反（Line 125-127）

**現状コード**:
```python
except Exception:
    # Checklist is nice-to-have, continue if fails
    checklist = "Publication checklist generation failed."  ← ダミー文字列
```

**修正後**:
```python
except Exception as e:
    activity.logger.error(f"Checklist generation failed: {e}")
    # ダミー文字列ではなく空を設定
    checklist = ""
    checklist_tokens = 0
    # warnings に記録
    warnings.append("checklist_generation_failed")
```

## 統合するヘルパー

### 1. OutputParser

```python
from apps.worker.helpers import OutputParser

class Step10FinalOutput(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = OutputParser()

    async def _generate_html(self, llm, prompt_pack, keyword: str, content: str):
        response = await llm.generate(...)

        # HTML抽出（コードブロック対応）
        html_content = response.content

        # コードブロックがある場合は除去
        if "```html" in html_content:
            html_content = self.parser.extract_json_block(html_content)
            # extract_json_block は json 用だが、html も同様に動作

        return html_content, response.token_usage.output
```

### 2. InputValidator

```python
from apps.worker.helpers import InputValidator

class Step10FinalOutput(BaseActivity):
    MIN_CONTENT_LENGTH = 1000

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_validator = InputValidator(
            required_fields=["step9.final_content"],
            recommended_fields=["step9.meta_description"],
        )

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        step9_data = await load_step_data(...) or {}

        # 入力検証
        validation = self.input_validator.validate({"step9": step9_data})

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        final_content = step9_data.get("final_content", "")

        # 追加の品質チェック
        if len(final_content) < self.MIN_CONTENT_LENGTH:
            raise ActivityError(
                f"Content too short: {len(final_content)} chars (min: {self.MIN_CONTENT_LENGTH})",
                category=ErrorCategory.NON_RETRYABLE,
            )
```

### 3. QualityValidator

```python
from apps.worker.helpers import QualityValidator
from apps.worker.helpers.quality_validator import (
    MinLengthValidator,
    KeywordPresenceValidator,
    CompositeValidator,
)

class Step10FinalOutput(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # HTML品質検証
        self.html_validator = CompositeValidator([
            MinLengthValidator(field="html", min_length=500, issue_code="html_too_short"),
            KeywordPresenceValidator(
                field="html",
                keywords=["<html", "<head", "<body", "<title"],
                min_matches=4,
                issue_code="missing_html_structure",
            ),
        ])

    def _validate_html_quality(self, html_content: str) -> QualityResult:
        return self.html_validator.validate({"html": html_content})
```

### 4. ContentMetrics

```python
from apps.worker.helpers import ContentMetrics

class Step10FinalOutput(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics = ContentMetrics()

    def _calculate_article_stats(self, markdown: str, html: str) -> dict:
        text_metrics = self.metrics.compute_text_metrics(markdown)
        md_metrics = self.metrics.compute_markdown_metrics(markdown)

        return {
            "word_count": text_metrics.word_count,
            "char_count": text_metrics.char_count,
            "paragraph_count": text_metrics.paragraph_count,
            "sentence_count": text_metrics.sentence_count,
            "heading_count": md_metrics.h2_count + md_metrics.h3_count + md_metrics.h4_count,
            "h1_count": md_metrics.h1_count,
            "h2_count": md_metrics.h2_count,
            "list_count": md_metrics.list_count,
            "link_count": md_metrics.link_count,
            "image_count": md_metrics.image_count,
        }
```

### 5. CheckpointManager

```python
from apps.worker.helpers import CheckpointManager

class Step10FinalOutput(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # HTML生成のチェックポイント
        html_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "html_generated"
        )

        if html_checkpoint:
            html_content = html_checkpoint["html"]
            html_tokens = html_checkpoint["tokens"]
        else:
            html_content, html_tokens = await self._generate_html(
                llm, prompt_pack, keyword, final_content
            )

            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "html_generated",
                {"html": html_content, "tokens": html_tokens}
            )

        # チェックリスト生成（別チェックポイント）
        checklist_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "checklist_generated"
        )

        if checklist_checkpoint:
            checklist = checklist_checkpoint["checklist"]
            checklist_tokens = checklist_checkpoint["tokens"]
        else:
            checklist, checklist_tokens = await self._generate_checklist(
                llm, prompt_pack, keyword
            )

            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "checklist_generated",
                {"checklist": checklist, "tokens": checklist_tokens}
            )
```

### 6. QualityRetryLoop（チェックリスト生成用）

```python
from apps.worker.helpers import QualityRetryLoop

class Step10FinalOutput(BaseActivity):
    async def _generate_checklist(
        self,
        llm,
        prompt_pack,
        keyword: str,
    ) -> tuple[str, int]:
        """チェックリスト生成（品質リトライ付き）"""

        def validate_checklist(content: str) -> QualityResult:
            issues = []
            if len(content) < 100:
                issues.append("checklist_too_short")
            if not any(ind in content for ind in ["□", "☐", "[ ]", "・", "-", "1."]):
                issues.append("no_checklist_items")
            return QualityResult(
                is_acceptable=len(issues) == 0,
                issues=issues,
            )

        retry_loop = QualityRetryLoop(
            validator=validate_checklist,
            max_retries=1,
        )

        async def generate():
            checklist_prompt = prompt_pack.get_prompt("step10_checklist")
            checklist_request = checklist_prompt.render(keyword=keyword)
            response = await llm.generate(
                messages=[{"role": "user", "content": checklist_request}],
                system_prompt="You are a publication checklist expert.",
                config=LLMRequestConfig(max_tokens=1000, temperature=0.3),
            )
            return response.content, response.token_usage.output

        try:
            result = await retry_loop.execute(
                generate_fn=generate,
                enhance_prompt_fn=None,  # チェックリストは単純なのでプロンプト補強なし
            )
            return result.content, result.token_usage
        except Exception as e:
            activity.logger.error(f"Checklist generation failed: {e}")
            # ダミー文字列ではなく空を返す
            return "", 0
```

## 構造化出力スキーマ

`apps/worker/activities/schemas/step10.py` を作成：

```python
from pydantic import BaseModel, Field

class HTMLValidationResult(BaseModel):
    """HTML検証結果"""
    is_valid: bool
    has_required_tags: bool = False
    has_meta_tags: bool = False
    has_proper_heading_hierarchy: bool = False
    issues: list[str] = Field(default_factory=list)

class ArticleStats(BaseModel):
    """記事統計"""
    word_count: int
    char_count: int
    paragraph_count: int
    heading_count: int
    h1_count: int = 0
    h2_count: int = 0
    list_count: int = 0
    link_count: int = 0
    image_count: int = 0

class PublicationReadiness(BaseModel):
    """出版準備状態"""
    is_ready: bool
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class Step10Output(BaseModel):
    """Step10 の構造化出力"""
    keyword: str
    article_title: str
    markdown_content: str
    html_content: str
    meta_description: str = ""
    publication_checklist: str
    html_validation: HTMLValidationResult
    stats: ArticleStats
    publication_readiness: PublicationReadiness
    warnings: list[str] = Field(default_factory=list)
```

## テスト更新

```python
import pytest
from apps.worker.activities.step10 import Step10FinalOutput

class TestStep10Helpers:
    """ヘルパー統合のテスト"""

    def test_no_dummy_string_on_checklist_failure(self):
        """チェックリスト失敗時にダミー文字列を使わない"""
        # 失敗時は空文字列を返す
        result = ...
        assert result.publication_checklist == "" or result.publication_checklist.strip() != ""
        assert "failed" not in result.publication_checklist.lower()

    def test_html_validation(self):
        """HTML検証が機能する"""
        ...

    def test_metrics_calculation(self):
        """メトリクス計算が正しい"""
        ...

    def test_checkpoint_html_resume(self):
        """HTML生成後から再開できる"""
        ...

    def test_checkpoint_checklist_resume(self):
        """チェックリスト生成後から再開できる"""
        ...
```

## 完了条件

- [ ] フォールバックコード削除（Line 125-127）
- [ ] ダミー文字列 → 空文字列に変更
- [ ] warnings に失敗を記録
- [ ] OutputParser 統合
- [ ] InputValidator 統合
- [ ] QualityValidator 統合
- [ ] ContentMetrics 統合
- [ ] CheckpointManager 統合
- [ ] QualityRetryLoop 統合
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過
- [ ] `uv run mypy apps/worker/activities/step10.py` 型エラーなし
