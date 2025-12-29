# Batch 1: Step4 Strategic Outline - ヘルパー統合

> **優先度**: 高（後続全ステップの品質に直結）

## 対象ファイル

- `apps/worker/activities/step4.py`

## 改善ポイント

### 1. 入力データの品質チェック強化

Step4 は Step3a/3b/3c の出力を統合するステップ。入力の欠損が後続に影響。

## 統合するヘルパー

### 1. InputValidator

```python
from apps.worker.helpers import InputValidator

class Step4StrategicOutline(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_validator = InputValidator(
            required_fields=[
                "step3a.query_analysis",  # 検索意図・ペルソナは必須
                "step3b.cooccurrence_analysis",  # 共起キーワードは必須
            ],
            recommended_fields=[
                "step0.analysis",  # キーワード分析
                "step3c.competitor_analysis",  # 競合分析は推奨
            ],
        )

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 各ステップのデータロード
        step0_data = await load_step_data(...) or {}
        step3a_data = await load_step_data(...) or {}
        step3b_data = await load_step_data(...) or {}
        step3c_data = await load_step_data(...) or {}

        # 入力検証
        validation = self.input_validator.validate({
            "step0": step0_data,
            "step3a": step3a_data,
            "step3b": step3b_data,
            "step3c": step3c_data,
        })

        if not validation.is_valid:
            raise ActivityError(
                f"Critical inputs missing: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": validation.missing_required},
            )

        if validation.missing_recommended:
            activity.logger.warning(
                f"Recommended inputs missing: {validation.missing_recommended}"
            )

        if validation.quality_issues:
            activity.logger.warning(f"Input quality issues: {validation.quality_issues}")
```

### 2. OutputParser

```python
from apps.worker.helpers import OutputParser

class Step4StrategicOutline(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = OutputParser()

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # LLM呼び出し
        response = await llm.generate(...)

        # 出力パース
        parse_result = self.parser.parse_json(response.content)

        if parse_result.success:
            data = parse_result.data
            outline = data.get("raw_outline", data.get("outline", ""))
        else:
            # JSONパース失敗時はMarkdownとして処理
            if self.parser.looks_like_markdown(response.content):
                activity.logger.info("Treating response as markdown (JSON parse failed)")
                outline = response.content
            else:
                raise ActivityError(
                    "Failed to parse outline response",
                    category=ErrorCategory.RETRYABLE,
                    details={"format": parse_result.format_detected},
                )

        if parse_result.fixes_applied:
            activity.logger.info(f"JSON fixes applied: {parse_result.fixes_applied}")
```

### 3. QualityValidator

```python
from apps.worker.helpers import QualityValidator
from apps.worker.helpers.quality_validator import (
    MinCountValidator,
    MinLengthValidator,
    KeywordPresenceValidator,
    CompositeValidator,
)

class Step4StrategicOutline(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # アウトライン品質検証
        self.outline_validator = CompositeValidator([
            MinLengthValidator(field="outline", min_length=500, issue_code="outline_too_short"),
            MinCountValidator(field="h2_sections", min_count=3, issue_code="too_few_sections"),
        ])

    def _validate_outline_quality(self, outline: str, keyword: str) -> QualityResult:
        """アウトライン品質の検証"""
        import re

        # セクション数カウント
        h2_count = len(re.findall(r'^##\s', outline, re.M))
        h3_count = len(re.findall(r'^###\s', outline, re.M))

        # バリデータで検証
        quality = self.outline_validator.validate({
            "outline": outline,
            "h2_sections": h2_count,
        })

        # 追加のカスタム検証
        if keyword.lower() not in outline.lower():
            quality.issues.append("keyword_not_in_outline")

        if h2_count > 0 and h3_count == 0:
            quality.warnings.append("no_h3_subsections")

        # 結論セクションの存在確認
        conclusion_keywords = ["まとめ", "結論", "おわり", "conclusion"]
        has_conclusion = any(kw in outline.lower() for kw in conclusion_keywords)
        if not has_conclusion:
            quality.warnings.append("no_conclusion_section")

        quality.is_acceptable = len(quality.issues) <= 2
        quality.scores["h2_count"] = h2_count
        quality.scores["h3_count"] = h3_count

        return quality
```

### 4. ContentMetrics

```python
from apps.worker.helpers import ContentMetrics

class Step4StrategicOutline(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics = ContentMetrics()

    def _structure_output(self, outline: str, keyword: str, quality: QualityResult) -> dict:
        text_metrics = self.metrics.compute_text_metrics(outline)
        md_metrics = self.metrics.compute_markdown_metrics(outline)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "outline": outline,
            "metrics": {
                "word_count": text_metrics.word_count,
                "char_count": text_metrics.char_count,
                "h2_count": md_metrics.h2_count,
                "h3_count": md_metrics.h3_count,
                "h4_count": md_metrics.h4_count,
            },
            "quality": {
                "is_acceptable": quality.is_acceptable,
                "issues": quality.issues,
                "warnings": quality.warnings,
                "scores": quality.scores,
            },
        }
```

### 5. CheckpointManager

```python
from apps.worker.helpers import CheckpointManager

class Step4StrategicOutline(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 統合データのチェックポイント
        integrated_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "integrated_inputs"
        )

        if integrated_checkpoint:
            integrated_data = integrated_checkpoint["data"]
            input_digest = integrated_checkpoint["input_digest"]
        else:
            # 統合処理
            integrated_data = self._integrate_analysis_data(
                keyword=keyword,
                query_analysis=step3a_data.get("query_analysis", ""),
                cooccurrence=step3b_data.get("cooccurrence_analysis", ""),
                competitor=step3c_data.get("competitor_analysis", ""),
            )

            input_digest = self._compute_digest(integrated_data)

            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "integrated_inputs",
                {"data": integrated_data, "input_digest": input_digest}
            )

        # LLM呼び出し
        ...
```

### 6. QualityRetryLoop

```python
from apps.worker.helpers import QualityRetryLoop

class Step4StrategicOutline(BaseActivity):
    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... 入力処理 ...

        retry_loop = QualityRetryLoop(
            validator=lambda content: self._validate_outline_quality(content, keyword),
            max_retries=1,
        )

        async def generate():
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a content strategist.",
                config=LLMRequestConfig(max_tokens=4000, temperature=0.7),
            )
            return response.content, response.token_usage.output

        def enhance_prompt(original: str, issues: list[str]) -> str:
            guidance = []
            if "too_few_sections" in issues:
                guidance.append("- 最低3つのH2セクションを含めてください")
            if "keyword_not_in_outline" in issues:
                guidance.append(f"- キーワード「{keyword}」を見出しに含めてください")
            if "no_conclusion_section" in issues:
                guidance.append("- 「まとめ」または「結論」セクションを追加してください")

            return original + "\n\n追加の指示:\n" + "\n".join(guidance)

        result = await retry_loop.execute(
            generate_fn=generate,
            enhance_prompt_fn=lambda issues: enhance_prompt(prompt, issues),
        )

        return self._structure_output(result.content, keyword, result.quality)
```

## 構造化出力スキーマ

`apps/worker/activities/schemas/step4.py`:

```python
from pydantic import BaseModel, Field
from typing import Literal

class OutlineSection(BaseModel):
    """アウトラインセクション"""
    level: int = Field(..., ge=1, le=4)
    title: str
    description: str = ""
    target_word_count: int = 0
    keywords_to_include: list[str] = Field(default_factory=list)
    subsections: list["OutlineSection"] = Field(default_factory=list)

OutlineSection.model_rebuild()

class OutlineQuality(BaseModel):
    """アウトライン品質"""
    is_acceptable: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)

class OutlineMetrics(BaseModel):
    """アウトラインメトリクス"""
    word_count: int
    char_count: int
    h2_count: int
    h3_count: int
    h4_count: int

class Step4Output(BaseModel):
    """Step4 の構造化出力"""
    keyword: str
    article_title: str = ""
    meta_description: str = ""
    outline: str
    sections: list[OutlineSection] = Field(default_factory=list)
    key_differentiators: list[str] = Field(default_factory=list)
    metrics: OutlineMetrics
    quality: OutlineQuality
```

## テスト更新

```python
import pytest
from apps.worker.activities.step4 import Step4StrategicOutline

class TestStep4Helpers:
    """ヘルパー統合のテスト"""

    def test_input_validation_required(self):
        """必須入力欠落でエラー"""
        # step3a/step3b が欠落
        with pytest.raises(ActivityError) as exc_info:
            ...
        assert "step3a.query_analysis" in str(exc_info.value)

    def test_input_validation_recommended(self):
        """推奨入力欠落で警告のみ"""
        # step3c が欠落しても続行
        ...

    def test_outline_quality_validation(self):
        """アウトライン品質検証"""
        # セクション数、キーワード存在をチェック
        ...

    def test_quality_retry(self):
        """品質不足時のリトライ"""
        # 1回目セクション不足 → 2回目で成功
        ...

    def test_checkpoint_resume(self):
        """チェックポイントから再開"""
        ...
```

## 完了条件

- [ ] InputValidator 統合（必須: step3a/3b、推奨: step0/3c）
- [ ] OutputParser 統合（JSON/Markdown両対応）
- [ ] QualityValidator 統合（セクション数、キーワード存在）
- [ ] ContentMetrics 統合
- [ ] CheckpointManager 統合
- [ ] QualityRetryLoop 統合
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過
- [ ] `uv run mypy apps/worker/activities/step4.py` 型エラーなし
