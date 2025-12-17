# Batch 4: Content Generation Steps (Step6, Step6.5, Step7a)

> **優先度**: 中 - コンテンツ生成フェーズの品質向上
> **特徴**: 長文生成、統合パッケージ、チェックポイント重要

---

## Step6: Enhanced Outline - 統合プロンプト

### 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step6.py` |
| 目的 | 一次資料を統合してアウトラインを拡張・詳細化 |
| 主要改善 | 拡張品質チェック、ソース引用追跡 |

### 統合するヘルパー

1. **OutputParser** - LLM出力のJSON/Markdown解析
2. **InputValidator** - step4/step5入力の検証
3. **QualityValidator** - アウトライン拡張品質の検証
4. **CheckpointManager** - ソースサマリーキャッシュ

### InputValidator 設定

```python
from helpers.validation import InputValidator, InputRequirement

step6_validator = InputValidator(
    requirements=[
        InputRequirement(
            step="step4",
            required=True,
            fields=["outline"],
            min_length={"outline": 200},
        ),
        InputRequirement(
            step="step5",
            required=False,  # 警告のみ
            fields=["sources"],
            min_items={"sources": 1},
        ),
    ]
)

# 使用
validation_result = await step6_validator.validate(ctx)
if not validation_result.is_valid:
    if validation_result.has_critical_failures:
        raise ActivityError(...)
    else:
        activity.logger.warning(f"Missing recommended inputs: {validation_result.warnings}")
```

### QualityValidator 設定

```python
from helpers.validation import QualityValidator, QualityRule

step6_quality_validator = QualityValidator(
    rules=[
        QualityRule(
            name="enhancement_length",
            check=lambda orig, enhanced: len(enhanced) >= len(orig),
            message="Enhanced outline should be longer than original",
            severity="error",
        ),
        QualityRule(
            name="h2_preserved",
            check=lambda orig, enhanced: (
                set(re.findall(r'^##\s+(.+)$', orig, re.M))
                <= set(re.findall(r'^##\s+(.+)$', enhanced, re.M))
            ),
            message="All H2 sections from original should be preserved",
            severity="error",
        ),
        QualityRule(
            name="h3_added",
            check=lambda orig, enhanced: (
                len(re.findall(r'^###\s', enhanced, re.M))
                > len(re.findall(r'^###\s', orig, re.M))
            ),
            message="Enhanced outline should have more H3 subsections",
            severity="warning",
        ),
    ]
)
```

### 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class EnhancedSection(BaseModel):
    """拡張されたセクション"""
    level: int
    title: str
    original_content: str = ""
    enhanced_content: str
    sources_referenced: list[str] = Field(default_factory=list)
    enhancement_type: str = "detail"  # elaboration|detail|evidence|example

class EnhancementSummary(BaseModel):
    """拡張サマリー"""
    sections_enhanced: int
    sections_added: int
    sources_integrated: int
    total_word_increase: int

class Step6Output(BaseModel):
    """Step6 の構造化出力"""
    keyword: str
    enhanced_outline: str
    sections: list[EnhancedSection] = Field(default_factory=list)
    enhancement_summary: EnhancementSummary
    source_citations: dict[str, list[str]] = Field(default_factory=dict)
    original_outline_hash: str
    warnings: list[str] = Field(default_factory=list)
```

### CheckpointManager 使用

```python
from helpers.metrics import CheckpointManager

checkpoint_manager = CheckpointManager(store, ctx.tenant_id, ctx.run_id, "step6")

# ソースサマリーのキャッシュ
source_checkpoint = await checkpoint_manager.load("source_summaries")
if source_checkpoint:
    source_summaries = source_checkpoint["summaries"]
    url_to_id = source_checkpoint["url_to_id"]
else:
    source_summaries, url_to_id = self._prepare_source_summaries(sources)
    await checkpoint_manager.save("source_summaries", {
        "summaries": source_summaries,
        "url_to_id": url_to_id,
    })
```

### テスト要件

```python
@pytest.mark.unit
def test_step6_enhancement_quality():
    """拡張品質の検証"""
    original = "## Section 1\nContent"
    enhanced = "## Section 1\nContent\n### 1.1 Detail\nMore content"
    result = step6_quality_validator.validate(original, enhanced)
    assert result.is_acceptable

@pytest.mark.unit
def test_step6_missing_section_detection():
    """セクション欠落検出"""
    original = "## Section 1\n## Section 2"
    enhanced = "## Section 1 Only"
    result = step6_quality_validator.validate(original, enhanced)
    assert not result.is_acceptable
    assert "h2_preserved" in result.failed_rules
```

---

## Step6.5: Integration Package - 統合プロンプト

### 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step6_5.py` |
| 目的 | 全分析・アウトラインを統合パッケージ化 |
| 特記 | **Step7a へのハンドオフポイント** |
| 主要改善 | 入力網羅性チェック、JSONパース改善 |

### 統合するヘルパー

1. **OutputParser** - JSONパース（修復機能付き）
2. **InputValidator** - 7ステップ分の入力検証
3. **QualityValidator** - 統合パッケージの完全性検証
4. **CheckpointManager** - 全データロードのキャッシュ

### InputValidator 設定

```python
step6_5_validator = InputValidator(
    requirements=[
        # 必須
        InputRequirement(step="step4", required=True, fields=["outline"]),
        InputRequirement(step="step6", required=True, fields=["enhanced_outline"]),
        # 推奨
        InputRequirement(step="step0", required=False, fields=["analysis"]),
        InputRequirement(step="step3a", required=False, fields=["query_analysis"]),
        InputRequirement(step="step3b", required=False, fields=["cooccurrence_analysis"]),
        InputRequirement(step="step3c", required=False, fields=["competitor_analysis"]),
        InputRequirement(step="step5", required=False, fields=["sources"]),
    ]
)
```

### OutputParser 設定（JSON修復付き）

```python
from helpers.parsing import OutputParser, ParseConfig

step6_5_parser = OutputParser(
    config=ParseConfig(
        output_type="json",
        schema=IntegrationPackageOutput,
        allow_code_blocks=True,
        json_repair=True,  # 末尾カンマ除去等
        max_repair_attempts=2,
    )
)

# 使用
try:
    parsed = step6_5_parser.parse(llm_response.content)
except ParseError as e:
    raise ActivityError(
        f"Integration package parse failed: {e}",
        category=ErrorCategory.RETRYABLE,
        details={"content_preview": e.content_preview},
    )
```

### QualityValidator 設定

```python
step6_5_quality_validator = QualityValidator(
    rules=[
        QualityRule(
            name="integration_package_exists",
            check=lambda pkg: bool(pkg.get("integration_package")),
            message="integration_package is required",
            severity="error",
        ),
        QualityRule(
            name="outline_summary_exists",
            check=lambda pkg: bool(pkg.get("outline_summary")),
            message="outline_summary is required",
            severity="error",
        ),
        QualityRule(
            name="section_count_reasonable",
            check=lambda pkg: pkg.get("section_count", 0) >= 3,
            message="At least 3 sections required",
            severity="warning",
        ),
        QualityRule(
            name="sources_integrated",
            check=lambda pkg, all_data: (
                pkg.get("total_sources", 0) > 0
                if len(all_data.get("step5", {}).get("sources", [])) > 0
                else True
            ),
            message="Sources should be integrated",
            severity="warning",
        ),
    ]
)
```

### 構造化出力スキーマ

```python
class InputSummary(BaseModel):
    """入力データサマリー"""
    step_id: str
    available: bool
    key_points: list[str] = Field(default_factory=list)
    data_quality: str = "unknown"

class SectionBlueprint(BaseModel):
    """セクション設計図"""
    level: int
    title: str
    target_words: int
    key_points: list[str]
    sources_to_cite: list[str] = Field(default_factory=list)
    keywords_to_include: list[str] = Field(default_factory=list)

class IntegrationPackageOutput(BaseModel):
    """Step6.5 の構造化出力"""
    keyword: str
    integration_package: str
    article_blueprint: dict[str, Any] = Field(default_factory=dict)
    section_blueprints: list[SectionBlueprint] = Field(default_factory=list)
    outline_summary: str
    section_count: int
    total_sources: int
    input_summaries: list[InputSummary] = Field(default_factory=list)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    handoff_notes: list[str] = Field(default_factory=list)
```

### CheckpointManager 使用

```python
# 全データロードのキャッシュ
data_checkpoint = await checkpoint_manager.load("all_data_loaded")
if data_checkpoint:
    all_data = data_checkpoint["all_data"]
    integration_input = data_checkpoint["integration_input"]
else:
    all_data = await self._load_all_step_data(ctx)
    integration_input = self._prepare_integration_input(all_data, keyword)
    await checkpoint_manager.save("all_data_loaded", {
        "all_data": all_data,
        "integration_input": integration_input,
    })
```

### テスト要件

```python
@pytest.mark.unit
def test_step6_5_required_inputs():
    """必須入力の検証"""
    all_data = {"step0": {"analysis": "..."}}  # step4, step6 なし
    result = step6_5_validator.validate(all_data)
    assert not result.is_valid
    assert "step4" in result.missing_required

@pytest.mark.unit
def test_step6_5_json_repair():
    """JSON修復機能"""
    broken_json = '{"key": "value",}'  # 末尾カンマ
    parsed = step6_5_parser.parse(broken_json)
    assert parsed == {"key": "value"}
```

---

## Step7a: Draft Generation - 統合プロンプト

### 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step7a.py` |
| 目的 | 統合パッケージに基づく記事ドラフト生成 |
| 特記 | **最長ステップ**（600秒タイムアウト）、長文生成 |
| 主要改善 | 完全性チェック、分割生成戦略、品質メトリクス |

### 統合するヘルパー

1. **OutputParser** - JSON/Markdownハイブリッド解析
2. **InputValidator** - integration_package検証
3. **QualityValidator** - ドラフト完全性・品質検証
4. **ContentMetrics** - 文字数・セクション数・キーワード密度
5. **CheckpointManager** - 部分生成の保存・再開

### InputValidator 設定

```python
step7a_validator = InputValidator(
    requirements=[
        InputRequirement(
            step="step6_5",
            required=True,
            fields=["integration_package"],
            min_length={"integration_package": 500},
        ),
    ]
)
```

### OutputParser 設定（ハイブリッド）

```python
step7a_parser = OutputParser(
    config=ParseConfig(
        output_type="hybrid",  # JSON優先、失敗時はMarkdown
        schema=Step7aOutput,
        allow_code_blocks=True,
        markdown_fallback=True,  # JSONパース失敗時にMarkdownとして扱う
    )
)

# 使用
try:
    parsed = step7a_parser.parse(llm_response.content)
except ParseError:
    # マークダウンフォールバック
    if step7a_parser.looks_like_markdown(llm_response.content):
        parsed = {
            "draft": llm_response.content,
            "word_count": len(llm_response.content.split()),
            "section_count": len(re.findall(r'^##\s', llm_response.content, re.M)),
            "format": "markdown_fallback",
        }
    else:
        raise ActivityError(...)
```

### QualityValidator 設定

```python
# 定数
MIN_WORD_COUNT = 1000
MIN_SECTION_COUNT = 3

step7a_quality_validator = QualityValidator(
    rules=[
        QualityRule(
            name="word_count",
            check=lambda draft: len(draft.split()) >= MIN_WORD_COUNT,
            message=f"Draft should have at least {MIN_WORD_COUNT} words",
            severity="error",
        ),
        QualityRule(
            name="section_count",
            check=lambda draft: len(re.findall(r'^##\s', draft, re.M)) >= MIN_SECTION_COUNT,
            message=f"Draft should have at least {MIN_SECTION_COUNT} sections",
            severity="error",
        ),
        QualityRule(
            name="has_conclusion",
            check=lambda draft: any(
                ind in draft.lower()
                for ind in ["まとめ", "結論", "おわり", "conclusion"]
            ),
            message="Draft should have a conclusion section",
            severity="warning",
        ),
        QualityRule(
            name="not_truncated",
            check=lambda draft: not draft.rstrip().endswith(("...", "…", "、")),
            message="Draft appears to be truncated",
            severity="error",
        ),
    ]
)
```

### ContentMetrics 使用

```python
from helpers.metrics import ContentMetrics

metrics = ContentMetrics()

draft_metrics = metrics.analyze(draft, keyword)
# Returns:
# {
#     "word_count": 3500,
#     "char_count": 10500,
#     "section_count": 7,
#     "avg_section_length": 500,
#     "keyword_density": 1.2,
#     "has_introduction": True,
#     "has_conclusion": True,
#     "readability_indicators": {...}
# }
```

### 構造化出力スキーマ

```python
class DraftSection(BaseModel):
    """ドラフトセクション"""
    level: int
    title: str
    content: str
    word_count: int
    has_subheadings: bool = False

class DraftQualityMetrics(BaseModel):
    """ドラフト品質メトリクス"""
    word_count: int
    char_count: int
    section_count: int
    avg_section_length: int
    keyword_density: float = 0.0
    has_introduction: bool = False
    has_conclusion: bool = False

class Step7aOutput(BaseModel):
    """Step7a の構造化出力"""
    keyword: str
    draft: str
    sections: list[DraftSection] = Field(default_factory=list)
    cta_positions: list[str] = Field(default_factory=list)
    quality_metrics: DraftQualityMetrics
    generation_stats: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    continued: bool = False  # 分割生成で続きを生成した場合
```

### CheckpointManager 使用（分割生成対応）

```python
# 部分生成チェックポイント
draft_checkpoint = await checkpoint_manager.load("draft_progress")

if draft_checkpoint and draft_checkpoint.get("needs_continuation"):
    current_draft = draft_checkpoint["draft"]
    activity.logger.info(f"Resuming from checkpoint: {len(current_draft)} chars done")

    # 続きを生成
    continuation = await self._continue_generation(llm, current_draft, integration_package)
    current_draft += "\n\n" + continuation
else:
    # 最初から生成
    response = await llm.generate(...)
    current_draft = response.content

# 完全性チェック
completeness = step7a_quality_validator.check_completeness(current_draft)
if completeness.is_truncated:
    # チェックポイント保存して続き生成
    await checkpoint_manager.save("draft_progress", {
        "draft": current_draft,
        "needs_continuation": True,
    })
    continuation = await self._continue_generation(...)
    current_draft += "\n\n" + continuation

# 最終チェックポイント
await checkpoint_manager.save("draft_progress", {
    "draft": current_draft,
    "needs_continuation": False,
})
```

### 分割生成戦略

```python
async def _continue_generation(
    self,
    llm,
    current_draft: str,
    integration_package: str,
) -> str:
    """ドラフトの続きを生成"""
    continuation_prompt = f"""
以下は記事ドラフトの途中です。この続きから完成させてください。

## 現在のドラフト（最後の500文字）
{current_draft[-500:]}

## 統合パッケージ（参照用）
{integration_package[:2000]}

## 指示
- 既存の内容と自然につながるように続きを書いてください
- 必ず「まとめ」または「結論」セクションで締めくくってください
- JSON形式ではなく、マークダウン形式で出力してください
"""

    llm_config = LLMRequestConfig(max_tokens=4000, temperature=0.7)
    response = await llm.generate(
        messages=[{"role": "user", "content": continuation_prompt}],
        system_prompt="Continue the article draft.",
        config=llm_config,
    )

    return response.content
```

### テスト要件

```python
@pytest.mark.unit
def test_step7a_completeness_check():
    """完全性チェック"""
    truncated_draft = "## Section 1\nContent..."
    result = step7a_quality_validator.check_completeness(truncated_draft)
    assert result.is_truncated
    assert "has_conclusion" in result.failed_rules

@pytest.mark.unit
def test_step7a_markdown_fallback():
    """Markdownフォールバック"""
    markdown_content = "# Title\n## Section 1\nContent"
    parsed = step7a_parser.parse(markdown_content)
    assert parsed["format"] == "markdown_fallback"
    assert parsed["section_count"] == 1

@pytest.mark.integration
async def test_step7a_continuation():
    """分割生成テスト"""
    # 最初の生成が切れた場合に続きが生成されることを確認
```

---

## 完了チェックリスト

### Step6
- [ ] InputValidator 統合（step4, step5入力検証）
- [ ] QualityValidator 統合（拡張品質チェック）
- [ ] OutputParser 統合（構造化出力）
- [ ] CheckpointManager 統合（ソースサマリーキャッシュ）
- [ ] Step6Output スキーマ実装
- [ ] ユニットテスト追加

### Step6.5
- [ ] InputValidator 統合（7ステップ分の入力検証）
- [ ] OutputParser 統合（JSON修復機能付き）
- [ ] QualityValidator 統合（パッケージ完全性チェック）
- [ ] CheckpointManager 統合（全データキャッシュ）
- [ ] IntegrationPackageOutput スキーマ実装
- [ ] ユニットテスト追加

### Step7a
- [ ] InputValidator 統合（integration_package検証）
- [ ] OutputParser 統合（ハイブリッド解析）
- [ ] QualityValidator 統合（完全性・品質検証）
- [ ] ContentMetrics 統合（品質メトリクス）
- [ ] CheckpointManager 統合（分割生成対応）
- [ ] 分割生成ロジック実装
- [ ] Step7aOutput スキーマ実装
- [ ] ユニットテスト追加
