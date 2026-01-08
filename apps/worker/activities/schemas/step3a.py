"""Step 3A: Query Analysis output schemas.

blog.System Ver8.3 対応版:
- 核心的疑問（CoreQuestion）
- 疑問の階層構造（QuestionHierarchy）
- 行動経済学6原則（BehavioralEconomicsProfile）
- 3フェーズ心理マッピング（ThreePhaseMapping）
- 拡張ペルソナ（DetailedPersona）
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# 既存スキーマ（後方互換性維持）
# =============================================================================


class SearchIntent(BaseModel):
    """Search intent classification."""

    primary: Literal["informational", "navigational", "transactional", "commercial"]
    secondary: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class UserPersona(BaseModel):
    """User persona definition (legacy, for backward compatibility)."""

    name: str
    demographics: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    search_context: str = ""


class Step3aOutput(BaseModel):
    """Step 3A output schema (legacy, for backward compatibility)."""

    keyword: str
    search_intent: SearchIntent
    personas: list[UserPersona] = Field(default_factory=list)
    content_expectations: list[str] = Field(default_factory=list)
    recommended_tone: str = ""
    raw_analysis: str


# =============================================================================
# 新規スキーマ（blog.System Ver8.3 対応）
# =============================================================================


class CoreQuestion(BaseModel):
    """検索者の核心的な疑問."""

    primary: str = Field(..., description="メインQuestion（50字以内推奨）")
    underlying_concern: str = Field(default="", description="根底にある懸念・欲求（100字以内推奨）")
    time_sensitivity: Literal["high", "medium", "low"] = Field(default="medium")
    urgency_reason: str = Field(default="", description="緊急度の理由")
    sub_questions: list[str] = Field(default_factory=list, description="派生質問（3-5個推奨）")


class QuestionHierarchy(BaseModel):
    """疑問の階層構造."""

    level_1_primary: list[str] = Field(default_factory=list, description="一次的疑問（3-5個推奨）")
    level_2_secondary: dict[str, list[str]] = Field(default_factory=dict, description="二次的疑問（一次疑問をキーに、各2-3個）")


# -----------------------------------------------------------------------------
# 行動経済学6原則
# -----------------------------------------------------------------------------


class BehavioralEconomicsPrinciple(BaseModel):
    """行動経済学の個別原則."""

    trigger: str = Field(default="", description="トリガーとなる要素")
    examples: list[str] = Field(default_factory=list, description="具体例（2-5個推奨）")
    content_strategy: str = Field(default="", description="コンテンツでの活用方法")


class BehavioralEconomicsProfile(BaseModel):
    """行動経済学6原則のプロファイル."""

    loss_aversion: BehavioralEconomicsPrinciple = Field(default_factory=BehavioralEconomicsPrinciple, description="損失回避")
    social_proof: BehavioralEconomicsPrinciple = Field(default_factory=BehavioralEconomicsPrinciple, description="社会的証明")
    authority: BehavioralEconomicsPrinciple = Field(default_factory=BehavioralEconomicsPrinciple, description="権威性")
    consistency: BehavioralEconomicsPrinciple = Field(default_factory=BehavioralEconomicsPrinciple, description="一貫性")
    liking: BehavioralEconomicsPrinciple = Field(default_factory=BehavioralEconomicsPrinciple, description="好意")
    scarcity: BehavioralEconomicsPrinciple = Field(default_factory=BehavioralEconomicsPrinciple, description="希少性")


# -----------------------------------------------------------------------------
# 3フェーズ心理マッピング
# -----------------------------------------------------------------------------


class PhaseState(BaseModel):
    """各フェーズの心理状態（基底クラス）."""

    emotions: list[str] = Field(default_factory=list, description="感情（2-5個推奨）")
    brain_trigger: str = Field(default="", description="脳活性化トリガー")
    content_needs: list[str] = Field(default_factory=list, description="コンテンツニーズ")
    content_strategy: str = Field(default="", description="コンテンツ戦略")


class Phase1Anxiety(PhaseState):
    """Phase 1: 不安・課題認識（扁桃体活性）."""

    pass


class Phase2Understanding(PhaseState):
    """Phase 2: 理解・納得（前頭前野活性）."""

    logic_points: list[str] = Field(default_factory=list, description="論理的ポイント")
    comparison_needs: list[str] = Field(default_factory=list, description="比較ニーズ")


class Phase3Action(PhaseState):
    """Phase 3: 行動決定（線条体活性）."""

    action_barriers: list[str] = Field(default_factory=list, description="行動障壁")
    urgency_factors: list[str] = Field(default_factory=list, description="緊急性要因")
    cvr_targets: dict[str, float] = Field(
        default_factory=lambda: {"early_cta": 3.0, "mid_cta": 4.0, "final_cta": 5.0},
        description="CTA別CVR目標（%）",
    )


class ThreePhaseMapping(BaseModel):
    """3フェーズ心理マッピング."""

    phase1_anxiety: Phase1Anxiety = Field(default_factory=Phase1Anxiety, description="Phase 1: 不安・課題認識")
    phase2_understanding: Phase2Understanding = Field(default_factory=Phase2Understanding, description="Phase 2: 理解・納得")
    phase3_action: Phase3Action = Field(default_factory=Phase3Action, description="Phase 3: 行動決定")


# -----------------------------------------------------------------------------
# 拡張ペルソナ
# -----------------------------------------------------------------------------


class SearchScenario(BaseModel):
    """検索シーン."""

    trigger_event: str = Field(default="", description="検索のきっかけとなった出来事")
    search_timing: str = Field(default="", description="検索した時間帯")
    device: str = Field(default="", description="使用デバイス")
    prior_knowledge: str = Field(default="", description="事前知識レベル")
    expected_action: str = Field(default="", description="記事を読んだ後に期待する行動")
    conversion_likelihood: float = Field(default=0.0, ge=0, le=100, description="問い合わせ確率（%）")


class EmotionalState(BaseModel):
    """感情状態."""

    anxiety_level: Literal["high", "medium", "low"] = Field(default="medium")
    anxiety_sources: list[str] = Field(default_factory=list, description="不安の源泉")
    urgency: Literal["high", "medium", "low"] = Field(default="medium")
    urgency_reason: str = Field(default="", description="緊急度の理由")
    motivation_type: Literal["loss_aversion", "gain_seeking", "curiosity"] = Field(default="loss_aversion")
    motivation_detail: str = Field(default="", description="動機の詳細")
    confidence_level: Literal["high", "medium", "low"] = Field(default="medium")
    openness_to_external_help: Literal["high", "medium", "low"] = Field(default="medium")


class DetailedPersona(BaseModel):
    """拡張ペルソナ."""

    # 基本情報
    name: str = Field(default="", description="仮名")
    age: int = Field(default=35, ge=18, le=80, description="年齢")
    job_title: str = Field(default="", description="職種・役職")
    company_size: str = Field(default="", description="企業規模")
    experience_years: int = Field(default=5, ge=0, le=50, description="経験年数")
    department: str = Field(default="", description="所属部署")
    responsibilities: list[str] = Field(default_factory=list, description="職務内容")

    # 課題・目標
    pain_points: list[str] = Field(default_factory=list, description="課題（3-7個推奨、具体的数値含む）")
    goals: list[str] = Field(default_factory=list, description="目標（3-5個推奨、具体的数値含む）")
    constraints: list[str] = Field(default_factory=list, description="制約条件")

    # 検索・感情
    search_scenario: SearchScenario = Field(default_factory=SearchScenario, description="検索シーン")
    emotional_state: EmotionalState = Field(default_factory=EmotionalState, description="感情状態")


# =============================================================================
# 拡張出力スキーマ（blog.System Ver8.3 対応）
# =============================================================================


class Step3aOutputV2(BaseModel):
    """Step 3A 拡張出力スキーマ（blog.System Ver8.3 対応）.

    既存フィールドを維持しつつ、新規フィールドを追加。
    新規フィールドはすべてオプショナルで後方互換性を確保。
    """

    # 既存フィールド（後方互換）
    keyword: str
    search_intent: SearchIntent
    personas: list[UserPersona] = Field(default_factory=list, description="簡易版ペルソナ（後方互換）")
    content_expectations: list[str] = Field(default_factory=list)
    recommended_tone: str = ""
    raw_analysis: str = ""

    # 新規フィールド（blog.System Ver8.3 対応）
    core_question: CoreQuestion | None = Field(default=None, description="核心的疑問")
    question_hierarchy: QuestionHierarchy | None = Field(default=None, description="疑問の階層構造")
    detailed_persona: DetailedPersona | None = Field(default=None, description="拡張ペルソナ")
    behavioral_economics_profile: BehavioralEconomicsProfile | None = Field(default=None, description="行動経済学6原則")
    three_phase_mapping: ThreePhaseMapping | None = Field(default=None, description="3フェーズ心理マッピング")
