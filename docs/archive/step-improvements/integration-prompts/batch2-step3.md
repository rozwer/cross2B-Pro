# Batch 2: Step3a/3b/3c - ヘルパー統合

> **並列ステップ**: Step3a（検索意図）、Step3b（共起キーワード）、Step3c（競合分析）

## 共通パターン

3つのステップは並列実行されるため、共通のヘルパー統合パターンを適用。

---

## Step3a: Query Analysis

### 対象ファイル

- `apps/worker/activities/step3a.py`

### 統合するヘルパー

```python
from apps.worker.helpers import (
    OutputParser,
    InputValidator,
    QualityValidator,
    ContentMetrics,
    CheckpointManager,
    QualityRetryLoop,
)
from apps.worker.helpers.schemas import QualityResult, ParseResult

class Step3AQueryAnalysis(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator(
            required_fields=["step0.analysis"],
            recommended_fields=["step1.competitors"],
        )

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 入力検証
        validation = self.input_validator.validate({
            "step0": step0_data,
            "step1": step1_data,
        })

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # 入力キャッシュ
        input_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "inputs_loaded"
        )

        if not input_checkpoint:
            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "inputs_loaded",
                {"step0_data": step0_data, "step1_data": step1_data}
            )

        # 品質リトライループ
        retry_loop = QualityRetryLoop(
            validator=self._validate_output_quality,
            max_retries=1,
        )

        result = await retry_loop.execute(
            generate_fn=self._generate,
            enhance_prompt_fn=self._enhance_prompt,
        )

        # 出力パース
        parse_result = self.parser.parse_json(result.content)
        ...

    def _validate_output_quality(self, content: str) -> QualityResult:
        """出力品質をチェック"""
        required_elements = {
            "search_intent": ["検索意図", "search intent", "intent"],
            "persona": ["ペルソナ", "persona", "ユーザー像"],
            "pain_points": ["課題", "pain point", "悩み"],
        }

        issues = []
        content_lower = content.lower()

        for element, keywords in required_elements.items():
            if not any(kw in content_lower for kw in keywords):
                issues.append(f"missing_{element}")

        return QualityResult(
            is_acceptable=len(issues) <= 1,
            issues=issues,
        )
```

### 構造化出力スキーマ

```python
# apps/worker/activities/schemas/step3a.py
from pydantic import BaseModel, Field
from typing import Literal

class SearchIntent(BaseModel):
    primary: Literal["informational", "navigational", "transactional", "commercial"]
    secondary: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

class UserPersona(BaseModel):
    name: str
    demographics: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    search_context: str = ""

class Step3aOutput(BaseModel):
    keyword: str
    search_intent: SearchIntent
    personas: list[UserPersona] = Field(default_factory=list)
    content_expectations: list[str] = Field(default_factory=list)
    recommended_tone: str = ""
    raw_analysis: str
```

---

## Step3b: Cooccurrence Extraction（心臓部）

### 対象ファイル

- `apps/worker/activities/step3b.py`

### 特記事項

**ワークフローの心臓部** - 品質基準を厳格に適用

### 統合するヘルパー

```python
from apps.worker.helpers import (
    OutputParser,
    InputValidator,
    QualityValidator,
    ContentMetrics,
    CheckpointManager,
    QualityRetryLoop,
)
from apps.worker.helpers.quality_validator import (
    MinCountValidator,
    KeywordPresenceValidator,
    CompositeValidator,
)

class Step3BCooccurrenceExtraction(BaseActivity):
    # 心臓部としての厳格な品質基準
    MIN_COOCCURRENCE_KEYWORDS = 10
    MIN_LSI_KEYWORDS = 5
    MIN_COMPETITORS_FOR_QUALITY = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()

        self.input_validator = InputValidator(
            required_fields=["step1.competitors"],
            recommended_fields=["step0.analysis"],
        )

        # 厳格な品質検証
        self.output_validator = CompositeValidator([
            MinCountValidator(
                field="cooccurrence_keywords",
                min_count=self.MIN_COOCCURRENCE_KEYWORDS,
                issue_code="too_few_cooccurrence",
            ),
            MinCountValidator(
                field="lsi_keywords",
                min_count=self.MIN_LSI_KEYWORDS,
                issue_code="too_few_lsi",
            ),
        ])

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 競合データの品質チェック
        competitors = step1_data.get("competitors", [])

        if len(competitors) < self.MIN_COMPETITORS_FOR_QUALITY:
            raise ActivityError(
                f"Insufficient competitor data: {len(competitors)} "
                f"(minimum: {self.MIN_COMPETITORS_FOR_QUALITY})",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # 競合サマリーのチェックポイント
        summaries_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "competitor_summaries"
        )

        if summaries_checkpoint:
            competitor_summaries = summaries_checkpoint["summaries"]
        else:
            competitor_summaries = self._prepare_competitor_summaries(competitors)
            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "competitor_summaries",
                {"summaries": competitor_summaries}
            )

        # 品質リトライループ
        retry_loop = QualityRetryLoop(
            validator=self._validate_output_quality,
            max_retries=1,
        )

        result = await retry_loop.execute(
            generate_fn=self._generate,
            enhance_prompt_fn=self._enhance_prompt,
        )

        # 出力パース
        parse_result = self.parser.parse_json(result.content)

        if parse_result.success:
            data = parse_result.data
            # 品質基準の最終チェック
            final_quality = self._enforce_quality_standards(data)
            if final_quality.warnings:
                activity.logger.warning(f"Quality warnings: {final_quality.warnings}")
        else:
            # 自由形式からキーワード抽出
            data = self._extract_keywords_from_freeform(result.content)

        return self._structure_output(data, keyword)

    def _validate_output_quality(self, content: str) -> QualityResult:
        """共起キーワード抽出の品質チェック"""
        issues = []

        # キーワードリストの存在確認
        list_indicators = ["・", "-", "*", "1.", "2."]
        has_list = any(ind in content for ind in list_indicators)
        if not has_list:
            issues.append("no_keyword_list")

        # カテゴリの存在確認
        keyword_patterns = [
            r"関連キーワード|related keyword",
            r"共起|co-occur",
            r"LSI|latent semantic",
        ]
        found_patterns = sum(1 for p in keyword_patterns if re.search(p, content, re.I))
        if found_patterns < 1:
            issues.append("no_keyword_categories")

        return QualityResult(
            is_acceptable=len(issues) <= 1,
            issues=issues,
        )

    def _enforce_quality_standards(self, data: dict) -> QualityResult:
        """心臓部としての品質基準強制"""
        warnings = []

        cooccurrence = data.get("cooccurrence_keywords", [])
        lsi = data.get("lsi_keywords", [])

        if len(cooccurrence) < self.MIN_COOCCURRENCE_KEYWORDS:
            warnings.append(f"cooccurrence_count: {len(cooccurrence)}")

        if len(lsi) < self.MIN_LSI_KEYWORDS:
            warnings.append(f"lsi_count: {len(lsi)}")

        return QualityResult(
            is_acceptable=True,  # 警告のみ、失敗はさせない
            warnings=warnings,
        )
```

### 構造化出力スキーマ

```python
# apps/worker/activities/schemas/step3b.py
from pydantic import BaseModel, Field
from typing import Literal

class KeywordItem(BaseModel):
    keyword: str
    category: Literal["cooccurrence", "lsi", "related", "synonym", "long_tail"] = "cooccurrence"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    frequency: int = 0
    context: str = ""

class KeywordCluster(BaseModel):
    theme: str
    keywords: list[KeywordItem] = Field(default_factory=list)
    relevance_to_main: float = Field(default=0.5, ge=0.0, le=1.0)

class Step3bOutput(BaseModel):
    primary_keyword: str
    cooccurrence_keywords: list[KeywordItem] = Field(default_factory=list, min_length=5)
    lsi_keywords: list[KeywordItem] = Field(default_factory=list)
    long_tail_variations: list[str] = Field(default_factory=list)
    keyword_clusters: list[KeywordCluster] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    raw_analysis: str
```

---

## Step3c: Competitor Analysis

### 対象ファイル

- `apps/worker/activities/step3c.py`

### 統合するヘルパー

```python
from apps.worker.helpers import (
    OutputParser,
    InputValidator,
    QualityValidator,
    ContentMetrics,
    CheckpointManager,
    QualityRetryLoop,
)

class Step3CCompetitorAnalysis(BaseActivity):
    MIN_COMPETITORS = 2
    MIN_CONTENT_PER_COMPETITOR = 200

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)

        self.input_validator = InputValidator(
            required_fields=["step1.competitors"],
        )

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 入力検証
        validation = self.input_validator.validate({"step1": step1_data})

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # 競合データ品質チェック
        competitors = step1_data.get("competitors", [])
        quality_competitors = [
            c for c in competitors
            if len(c.get("content", "")) >= self.MIN_CONTENT_PER_COMPETITOR
        ]

        if len(quality_competitors) < self.MIN_COMPETITORS:
            raise ActivityError(
                f"Insufficient quality competitors: {len(quality_competitors)}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # 分析データのチェックポイント
        analysis_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "analysis_data"
        )

        if analysis_checkpoint:
            competitor_analysis = analysis_checkpoint["competitor_analysis"]
        else:
            competitor_analysis = self._prepare_competitor_analysis(quality_competitors)
            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "analysis_data",
                {"competitor_analysis": competitor_analysis}
            )

        # 品質リトライループ
        retry_loop = QualityRetryLoop(
            validator=self._validate_output_quality,
            max_retries=1,
        )

        result = await retry_loop.execute(
            generate_fn=self._generate,
            enhance_prompt_fn=self._enhance_prompt,
        )

        return self._structure_output(result.content, keyword)

    def _validate_output_quality(self, content: str) -> QualityResult:
        """競合分析の品質チェック"""
        issues = []

        # 差別化に関する言及
        differentiation_keywords = [
            "差別化", "differentiation", "独自", "unique",
            "強み", "strength", "弱み", "weakness",
        ]
        found = sum(1 for kw in differentiation_keywords if kw in content.lower())
        if found < 2:
            issues.append("insufficient_differentiation_analysis")

        # 具体的な提案の存在
        recommendation_indicators = [
            "推奨", "recommend", "すべき", "should",
            "提案", "suggest", "戦略", "strategy",
        ]
        found_rec = sum(1 for kw in recommendation_indicators if kw in content.lower())
        if found_rec < 1:
            issues.append("no_recommendations")

        return QualityResult(
            is_acceptable=len(issues) <= 1,
            issues=issues,
        )
```

### 構造化出力スキーマ

```python
# apps/worker/activities/schemas/step3c.py
from pydantic import BaseModel, Field
from typing import Literal

class CompetitorProfile(BaseModel):
    url: str
    title: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    content_focus: list[str] = Field(default_factory=list)
    unique_value: str = ""
    threat_level: Literal["high", "medium", "low"] = "medium"

class DifferentiationStrategy(BaseModel):
    category: Literal["content", "expertise", "format", "depth", "perspective"]
    description: str
    priority: Literal["must", "should", "nice_to_have"] = "should"
    implementation_hint: str = ""

class GapOpportunity(BaseModel):
    gap_type: str
    description: str
    competitors_missing: list[str] = Field(default_factory=list)
    value_potential: float = Field(default=0.5, ge=0.0, le=1.0)

class Step3cOutput(BaseModel):
    keyword: str
    competitor_profiles: list[CompetitorProfile] = Field(default_factory=list)
    market_overview: str = ""
    differentiation_strategies: list[DifferentiationStrategy] = Field(default_factory=list)
    gap_opportunities: list[GapOpportunity] = Field(default_factory=list)
    content_recommendations: list[str] = Field(default_factory=list)
    raw_analysis: str
```

---

## 完了条件（3ステップ共通）

### Step3a

- [ ] InputValidator 統合
- [ ] OutputParser 統合
- [ ] QualityRetryLoop 統合
- [ ] CheckpointManager 統合
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過

### Step3b（心臓部 - 厳格な検証）

- [ ] InputValidator 統合
- [ ] OutputParser 統合
- [ ] QualityRetryLoop 統合（厳格な基準）
- [ ] CheckpointManager 統合
- [ ] 品質基準の強制（警告ログ）
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過

### Step3c

- [ ] InputValidator 統合
- [ ] OutputParser 統合
- [ ] QualityRetryLoop 統合
- [ ] CheckpointManager 統合
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過
