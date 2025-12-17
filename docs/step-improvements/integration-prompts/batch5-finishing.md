# Batch 5: Finishing Steps (Step7b, Step8, Step9)

> **優先度**: 中〜低 - 仕上げフェーズの品質向上
> **特徴**: 品質検証、ファクトチェック、最終統合

---

## Step7b: Brush Up - 統合プロンプト

### 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step7b.py` |
| 目的 | ドラフトの自然言語ポリッシング・読みやすさ向上 |
| 使用LLM | Gemini（デフォルト） |
| 特記 | max_tokens=16000、temperature=0.8（創造性重視） |
| 主要改善 | ポリッシング品質検証、変更追跡 |

### 統合するヘルパー

1. **OutputParser** - Markdown解析
2. **InputValidator** - step7a ドラフト検証
3. **QualityValidator** - ポリッシング品質検証
4. **ContentMetrics** - 変更量メトリクス
5. **CheckpointManager** - セクション単位処理（オプション）

### InputValidator 設定

```python
from helpers.validation import InputValidator, InputRequirement

MIN_DRAFT_LENGTH = 500

step7b_validator = InputValidator(
    requirements=[
        InputRequirement(
            step="step7a",
            required=True,
            fields=["draft"],
            min_length={"draft": MIN_DRAFT_LENGTH},
        ),
    ]
)

# 使用
validation_result = await step7b_validator.validate(ctx)
if not validation_result.is_valid:
    raise ActivityError(
        f"Draft too short for polishing: {validation_result.details.get('draft_length', 0)} chars",
        category=ErrorCategory.NON_RETRYABLE,
    )
```

### QualityValidator 設定

```python
step7b_quality_validator = QualityValidator(
    rules=[
        QualityRule(
            name="not_reduced",
            check=lambda orig, polished: len(polished.split()) >= len(orig.split()) * 0.7,
            message="Polished content should not be significantly reduced (>30%)",
            severity="error",
        ),
        QualityRule(
            name="not_inflated",
            check=lambda orig, polished: len(polished.split()) <= len(orig.split()) * 1.5,
            message="Polished content should not be significantly inflated (>50%)",
            severity="warning",
        ),
        QualityRule(
            name="sections_preserved",
            check=lambda orig, polished: (
                len(re.findall(r'^##\s', polished, re.M))
                >= len(re.findall(r'^##\s', orig, re.M)) * 0.8
            ),
            message="Most sections should be preserved",
            severity="error",
        ),
        QualityRule(
            name="conclusion_preserved",
            check=lambda orig, polished: (
                any(ind in polished.lower() for ind in ["まとめ", "結論", "おわり"])
                if any(ind in orig.lower() for ind in ["まとめ", "結論", "おわり"])
                else True
            ),
            message="Conclusion section should be preserved",
            severity="error",
        ),
        QualityRule(
            name="not_truncated",
            check=lambda polished: not polished.rstrip().endswith(("...", "…", "、")),
            message="Polished content appears to be truncated",
            severity="error",
        ),
    ]
)
```

### ContentMetrics 使用（変更追跡）

```python
from helpers.metrics import ContentMetrics

metrics = ContentMetrics()

# 変更量の計算
polish_metrics = metrics.compare(original_draft, polished_draft)
# Returns:
# {
#     "original_word_count": 3500,
#     "polished_word_count": 3600,
#     "word_diff": 100,
#     "word_diff_percent": 2.86,
#     "sections_preserved": 7,
#     "sections_modified": 2,
# }
```

### 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class PolishChange(BaseModel):
    """ポリッシングによる変更"""
    change_type: str  # "wording", "flow", "clarity", "tone", "restructure"
    original_snippet: str
    polished_snippet: str
    section: str = ""

class PolishMetrics(BaseModel):
    """ポリッシングメトリクス"""
    original_word_count: int
    polished_word_count: int
    word_diff: int
    word_diff_percent: float
    sections_preserved: int
    sections_modified: int

class Step7bOutput(BaseModel):
    """Step7b の構造化出力"""
    keyword: str
    polished: str
    changes_summary: str = ""
    change_count: int = 0
    polish_metrics: PolishMetrics
    quality_warnings: list[str] = Field(default_factory=list)
```

### テスト要件

```python
@pytest.mark.unit
def test_step7b_quality_check():
    """ポリッシング品質検証"""
    original = "## Section 1\nLong content here..." * 100
    polished = "## Section 1\nShort"  # 大幅短縮
    result = step7b_quality_validator.validate(original, polished)
    assert not result.is_acceptable
    assert "not_reduced" in result.failed_rules

@pytest.mark.unit
def test_step7b_structure_preserved():
    """構造維持の検証"""
    original = "## Section 1\n## Section 2\n## まとめ"
    polished = "## Section 1\n## Section 2\n## まとめ"  # 構造維持
    result = step7b_quality_validator.validate(original, polished)
    assert result.is_acceptable
```

---

## Step8: Fact Check - 統合プロンプト

### 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step8.py` |
| 目的 | 記事内の事実・主張の検証 + FAQ生成 |
| 使用LLM | Gemini（グラウンディング対応） |
| 特記 | 3回のLLM呼び出し（claims抽出 → 検証 → FAQ生成） |
| 主要改善 | 構造化出力、確信度評価、チェックポイント |

### 統合するヘルパー

1. **OutputParser** - JSON解析（3つの出力形式）
2. **InputValidator** - step7b ポリッシュ済みコンテンツ検証
3. **QualityValidator** - claims品質、検証結果品質
4. **CheckpointManager** - 3回のLLM呼び出し間のキャッシュ

### InputValidator 設定

```python
step8_validator = InputValidator(
    requirements=[
        InputRequirement(
            step="step7b",
            required=True,
            fields=["polished"],
            min_length={"polished": 500},
        ),
    ]
)
```

### OutputParser 設定（3つの形式）

```python
from helpers.parsing import OutputParser, ParseConfig

# Claims抽出用
claims_parser = OutputParser(
    config=ParseConfig(
        output_type="json",
        schema=ClaimsOutput,
        allow_code_blocks=True,
    )
)

# 検証結果用
verification_parser = OutputParser(
    config=ParseConfig(
        output_type="json",
        schema=VerificationOutput,
        allow_code_blocks=True,
    )
)

# FAQ用
faq_parser = OutputParser(
    config=ParseConfig(
        output_type="json",
        schema=FAQOutput,
        allow_code_blocks=True,
    )
)
```

### QualityValidator 設定

```python
MIN_CLAIMS_COUNT = 3

step8_quality_validator = QualityValidator(
    rules=[
        QualityRule(
            name="claims_count",
            check=lambda claims: len(claims) >= MIN_CLAIMS_COUNT,
            message=f"At least {MIN_CLAIMS_COUNT} claims should be extracted",
            severity="warning",
        ),
        QualityRule(
            name="claims_specific",
            check=lambda claims_text: any(
                kw in claims_text
                for kw in ["数値", "統計", "調査", "%", "円", "年"]
            ),
            message="Claims should include specific/quantifiable statements",
            severity="warning",
        ),
        QualityRule(
            name="verification_complete",
            check=lambda results, claims: len(results) == len(claims),
            message="All claims should be verified",
            severity="error",
        ),
        QualityRule(
            name="faq_count",
            check=lambda faq_items: 3 <= len(faq_items) <= 7,
            message="FAQ should have 3-7 items",
            severity="warning",
        ),
    ]
)
```

### 構造化出力スキーマ

```python
from pydantic import BaseModel, Field
from typing import Literal

class Claim(BaseModel):
    """検証対象の主張"""
    claim_id: str
    text: str
    source_section: str = ""
    claim_type: Literal["statistic", "fact", "opinion", "definition"]

class ClaimsOutput(BaseModel):
    """Claims抽出の出力"""
    claims: list[Claim]

class VerificationResult(BaseModel):
    """検証結果"""
    claim_id: str
    status: Literal["verified", "unverified", "contradicted", "partially_verified"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str = ""
    source: str = ""
    recommendation: str = ""

class VerificationOutput(BaseModel):
    """検証の出力"""
    verification_results: list[VerificationResult]

class FAQItem(BaseModel):
    """FAQ項目"""
    question: str
    answer: str
    related_claims: list[str] = Field(default_factory=list)

class FAQOutput(BaseModel):
    """FAQ生成の出力"""
    faq_items: list[FAQItem]

class Step8Output(BaseModel):
    """Step8 の構造化出力"""
    keyword: str
    claims: list[Claim]
    verification_results: list[VerificationResult]
    faq_items: list[FAQItem]
    summary: dict[str, int] = Field(
        default_factory=dict,
        description="status別の集計"
    )
    has_contradictions: bool = False
    critical_issues: list[str] = Field(default_factory=list)
    recommend_rejection: bool = False
```

### CheckpointManager 使用（3段階）

```python
from helpers.metrics import CheckpointManager

checkpoint_manager = CheckpointManager(store, ctx.tenant_id, ctx.run_id, "step8")

# Step 8.1: Claims抽出
claims_checkpoint = await checkpoint_manager.load("claims_extracted")
if claims_checkpoint:
    extracted_claims = claims_checkpoint["claims"]
    activity.logger.info(f"Loaded {len(extracted_claims)} claims from checkpoint")
else:
    claims_response = await llm.generate(...)
    extracted_claims = claims_parser.parse(claims_response.content)
    await checkpoint_manager.save("claims_extracted", {
        "claims": extracted_claims,
        "raw_response": claims_response.content,
    })

# Step 8.2: 検証
verify_checkpoint = await checkpoint_manager.load("verification_done")
if verify_checkpoint:
    verification_results = verify_checkpoint["results"]
else:
    verify_response = await llm.generate(...)
    verification_results = verification_parser.parse(verify_response.content)
    await checkpoint_manager.save("verification_done", {
        "results": verification_results,
        "raw_response": verify_response.content,
    })

# Step 8.3: FAQ生成（チェックポイント不要 - 最後のステップ）
faq_response = await llm.generate(...)
faq_items = faq_parser.parse(faq_response.content)
```

### 矛盾検出と却下推奨

```python
def _determine_rejection_recommendation(
    verification_results: list[VerificationResult],
) -> tuple[bool, list[str]]:
    """却下推奨の判定"""
    critical_issues = []

    contradicted_count = sum(
        1 for r in verification_results
        if r.status == "contradicted"
    )

    if contradicted_count >= 2:
        critical_issues.append(f"{contradicted_count} contradictions found")

    # 高確信度の矛盾
    high_confidence_contradictions = [
        r for r in verification_results
        if r.status == "contradicted" and r.confidence > 0.8
    ]
    if high_confidence_contradictions:
        critical_issues.append("High-confidence contradictions detected")

    recommend_rejection = len(critical_issues) > 0

    return recommend_rejection, critical_issues
```

### テスト要件

```python
@pytest.mark.unit
def test_step8_claims_extraction():
    """Claims抽出の構造化"""
    llm_response = '''```json
    {"claims": [{"claim_id": "C1", "text": "統計によると...", "claim_type": "statistic"}]}
    ```'''
    parsed = claims_parser.parse(llm_response)
    assert len(parsed.claims) == 1
    assert parsed.claims[0].claim_type == "statistic"

@pytest.mark.unit
def test_step8_contradiction_detection():
    """矛盾検出"""
    results = [
        VerificationResult(claim_id="C1", status="verified", confidence=0.9),
        VerificationResult(claim_id="C2", status="contradicted", confidence=0.85),
        VerificationResult(claim_id="C3", status="contradicted", confidence=0.9),
    ]
    recommend, issues = _determine_rejection_recommendation(results)
    assert recommend
    assert "2 contradictions found" in issues[0]

@pytest.mark.integration
async def test_step8_checkpoint_recovery():
    """チェックポイントからの復旧"""
    # claims抽出後に失敗 → 再実行時に検証から開始
```

---

## Step9: Final Rewrite - 統合プロンプト

### 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step9.py` |
| 目的 | ファクトチェック結果とFAQを反映した最終リライト |
| 使用LLM | Claude（デフォルト: anthropic） |
| 特記 | max_tokens=16000 |
| 主要改善 | FAQ統合検証、メタディスクリプション抽出 |

### 統合するヘルパー

1. **OutputParser** - Markdown解析 + メタディスクリプション抽出
2. **InputValidator** - step7b/step8入力検証
3. **QualityValidator** - リライト品質検証
4. **ContentMetrics** - 最終メトリクス
5. **CheckpointManager** - 入力データキャッシュ

### InputValidator 設定

```python
step9_validator = InputValidator(
    requirements=[
        # 必須
        InputRequirement(
            step="step7b",
            required=True,
            fields=["polished"],
            min_length={"polished": 500},
        ),
        # 推奨
        InputRequirement(
            step="step8",
            required=False,
            fields=["faq", "verification"],
        ),
    ]
)

# 使用
validation_result = await step9_validator.validate(ctx)
if not validation_result.is_valid:
    raise ActivityError(...)

# 推奨入力の警告
if "step8" in validation_result.missing_recommended:
    activity.logger.warning("No FAQ/verification data - proceeding without corrections")

# 矛盾警告
step8_data = validation_result.loaded_data.get("step8", {})
if step8_data.get("has_contradictions"):
    activity.logger.warning("Content has contradictions - ensure corrections are applied")
```

### QualityValidator 設定

```python
step9_quality_validator = QualityValidator(
    rules=[
        QualityRule(
            name="not_reduced",
            check=lambda polished, final: len(final) >= len(polished) * 0.8,
            message="Final content should not be significantly reduced",
            severity="warning",
        ),
        QualityRule(
            name="faq_integrated",
            check=lambda final, step8_data: (
                any(ind in final for ind in ["FAQ", "よくある質問", "Q&A", "Q:"])
                if step8_data.get("faq")
                else True
            ),
            message="FAQ should be integrated when available",
            severity="warning",
        ),
        QualityRule(
            name="sections_maintained",
            check=lambda polished, final: (
                len(re.findall(r'^##\s', final, re.M))
                >= len(re.findall(r'^##\s', polished, re.M))
            ),
            message="Section count should not decrease",
            severity="warning",
        ),
    ]
)
```

### OutputParser 設定（メタディスクリプション抽出）

```python
step9_parser = OutputParser(
    config=ParseConfig(
        output_type="markdown",
        extract_meta=True,  # <!--META_DESCRIPTION: ... --> を抽出
        meta_patterns=[
            r'<!--\s*META_DESCRIPTION:\s*(.+?)\s*-->',
        ],
    )
)

# 使用
parsed = step9_parser.parse(llm_response.content)
# parsed.content = マークダウン本文
# parsed.meta = {"description": "抽出されたメタディスクリプション"}
```

### メタディスクリプション生成（フォールバック）

```python
def _extract_or_generate_meta_description(content: str, parsed_meta: dict) -> str:
    """メタディスクリプションを抽出または生成"""
    # 明示的なメタタグがあればそれを使用
    if parsed_meta.get("description"):
        return parsed_meta["description"][:160]

    # なければ最初の段落から生成
    paragraphs = content.split('\n\n')
    for p in paragraphs:
        if not p.startswith('#') and len(p) > 50:
            sentences = p.split('。')
            description = ""
            for s in sentences:
                if len(description) + len(s) + 1 <= 160:
                    description += s + '。'
                else:
                    break
            return description or p[:160]

    return ""
```

### 構造化出力スキーマ

```python
class RewriteChange(BaseModel):
    """リライトによる変更"""
    change_type: str  # "factcheck_correction", "faq_addition", "style", "structure"
    section: str = ""
    description: str = ""

class RewriteMetrics(BaseModel):
    """リライトメトリクス"""
    original_word_count: int
    final_word_count: int
    word_diff: int
    sections_count: int
    faq_integrated: bool = False
    factcheck_corrections_applied: int = 0

class Step9Output(BaseModel):
    """Step9 の構造化出力"""
    keyword: str
    final_content: str
    meta_description: str = Field(default="", max_length=160)
    changes_summary: list[RewriteChange] = Field(default_factory=list)
    rewrite_metrics: RewriteMetrics
    internal_link_suggestions: list[str] = Field(default_factory=list)
    quality_warnings: list[str] = Field(default_factory=list)
```

### CheckpointManager 使用

```python
# 入力データのキャッシュ
input_checkpoint = await checkpoint_manager.load("inputs_loaded")
if input_checkpoint:
    polished_content = input_checkpoint["polished"]
    faq_content = input_checkpoint["faq"]
    verification = input_checkpoint["verification"]
else:
    step7b_data = await load_step_data(...) or {}
    step8_data = await load_step_data(...) or {}

    polished_content = step7b_data.get("polished", "")
    faq_content = step8_data.get("faq", "")
    verification = step8_data.get("verification", "")

    await checkpoint_manager.save("inputs_loaded", {
        "polished": polished_content,
        "faq": faq_content,
        "verification": verification,
        "has_contradictions": step8_data.get("has_contradictions", False),
    })
```

### テスト要件

```python
@pytest.mark.unit
def test_step9_faq_integration():
    """FAQ統合の検証"""
    polished = "## Section 1\nContent"
    final_with_faq = "## Section 1\nContent\n\n## よくある質問\nQ: 質問\nA: 回答"
    step8_data = {"faq": "Q: 質問\nA: 回答"}
    result = step9_quality_validator.validate(polished, final_with_faq, step8_data)
    assert result.is_acceptable

@pytest.mark.unit
def test_step9_meta_extraction():
    """メタディスクリプション抽出"""
    content = "# Title\n\n<!--META_DESCRIPTION: This is the description -->\n\n## Section"
    parsed = step9_parser.parse(content)
    assert parsed.meta.get("description") == "This is the description"

@pytest.mark.unit
def test_step9_meta_generation():
    """メタディスクリプション生成（フォールバック）"""
    content = "# Title\n\nこれは最初の段落です。重要な内容が含まれています。"
    meta = _extract_or_generate_meta_description(content, {})
    assert "最初の段落" in meta
    assert len(meta) <= 160
```

---

## 完了チェックリスト

### Step7b
- [ ] InputValidator 統合（step7aドラフト検証）
- [ ] QualityValidator 統合（ポリッシング品質検証）
- [ ] ContentMetrics 統合（変更追跡）
- [ ] OutputParser 統合（Markdown解析）
- [ ] Step7bOutput スキーマ実装
- [ ] ユニットテスト追加

### Step8
- [ ] InputValidator 統合（step7b検証）
- [ ] OutputParser 統合（3つの形式）
- [ ] QualityValidator 統合（claims/検証/FAQ品質）
- [ ] CheckpointManager 統合（3段階チェックポイント）
- [ ] 構造化スキーマ実装（Claim, VerificationResult, FAQItem）
- [ ] 矛盾検出ロジック実装
- [ ] ユニットテスト追加

### Step9
- [ ] InputValidator 統合（step7b/step8検証）
- [ ] QualityValidator 統合（リライト品質検証）
- [ ] OutputParser 統合（メタディスクリプション抽出）
- [ ] ContentMetrics 統合（最終メトリクス）
- [ ] CheckpointManager 統合（入力キャッシュ）
- [ ] メタディスクリプション生成ロジック実装
- [ ] Step9Output スキーマ実装
- [ ] ユニットテスト追加
