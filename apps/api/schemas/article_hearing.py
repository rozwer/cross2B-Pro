"""Article hearing input schemas for workflow initialization.

This module defines the comprehensive input structure for the article generation workflow,
replacing the simple RunInput with a detailed 6-section hearing form.

Also includes HearingTemplate schemas for template save/reuse functionality.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

# =============================================================================
# Enums
# =============================================================================


class TargetCV(str, Enum):
    """Target conversion types."""

    INQUIRY = "inquiry"  # 問い合わせ獲得
    DOCUMENT_REQUEST = "document_request"  # 資料請求
    FREE_CONSULTATION = "free_consultation"  # 無料相談申込
    OTHER = "other"  # その他


class KeywordStatus(str, Enum):
    """Keyword selection status."""

    DECIDED = "decided"  # 既に決まっている
    UNDECIDED = "undecided"  # まだ決まっていない


class CompetitionLevel(str, Enum):
    """Keyword competition level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ArticleStyle(str, Enum):
    """Article style types."""

    STANDALONE = "standalone"  # 標準記事（スタンドアロン型）
    TOPIC_CLUSTER = "topic_cluster"  # トピッククラスター戦略（親記事+子記事）


class WordCountMode(str, Enum):
    """Word count determination mode."""

    MANUAL = "manual"  # ユーザー指定
    AI_SEO_OPTIMIZED = "ai_seo_optimized"  # 競合平均 × 1.2
    AI_READABILITY = "ai_readability"  # 競合平均 × 0.9
    AI_BALANCED = "ai_balanced"  # 競合平均 × 1.0 ±5%


class CTAType(str, Enum):
    """CTA design type."""

    SINGLE = "single"  # 単一CTA
    STAGED = "staged"  # 段階的CTA


class CTAPositionMode(str, Enum):
    """CTA position determination mode."""

    FIXED = "fixed"  # 固定位置（Early: 650字, Mid: 2800字, Final: 末尾）
    RATIO = "ratio"  # 文字数比率で動的計算
    AI = "ai"  # AIにお任せ


# =============================================================================
# Section 1: Business & Target
# =============================================================================


class BusinessInput(BaseModel):
    """Section 1: Business information and target audience."""

    description: str = Field(
        ...,
        min_length=10,
        description="事業内容の詳細説明",
        json_schema_extra={"example": "派遣社員向けeラーニングサービス"},
    )
    target_cv: TargetCV = Field(
        ...,
        description="目標CV（コンバージョン）",
    )
    target_cv_other: str | None = Field(
        None,
        description="target_cv='other'の場合のカスタム値",
    )
    target_audience: str = Field(
        ...,
        min_length=10,
        description="ターゲット読者像",
        json_schema_extra={"example": "派遣会社の教育担当者、人事部長、30〜40代、派遣社員の離職率に悩んでいる"},
    )
    company_strengths: str = Field(
        ...,
        min_length=10,
        description="競合と比較した自社の強み",
        json_schema_extra={"example": "中小企業特化、低予算での教育プラン提供、導入実績300社以上"},
    )

    @model_validator(mode="after")
    def validate_target_cv_other(self) -> "BusinessInput":
        """Validate that target_cv_other is provided when target_cv is 'other'."""
        if self.target_cv == TargetCV.OTHER and not self.target_cv_other:
            raise ValueError("target_cv='other'の場合、target_cv_otherは必須です")
        return self


# =============================================================================
# Section 2: Keyword Selection
# =============================================================================


class RelatedKeyword(BaseModel):
    """Related keyword with search volume."""

    keyword: str = Field(..., description="関連キーワード")
    volume: str | None = Field(None, description="月間検索ボリューム（例: '50-100'）")


class SelectedKeyword(BaseModel):
    """Keyword selected from LLM suggestions."""

    keyword: str = Field(..., description="選択されたキーワード")
    estimated_volume: str = Field(..., description="推定検索ボリューム")
    estimated_competition: CompetitionLevel = Field(..., description="推定競合性")
    relevance_score: float = Field(..., ge=0, le=1, description="関連性スコア")


class KeywordInput(BaseModel):
    """Section 2: Keyword selection."""

    status: KeywordStatus = Field(
        ...,
        description="キーワードの状態（決定済み/未定）",
    )
    # Fields for status='decided'
    main_keyword: str | None = Field(
        None,
        description="メインキーワード（status='decided'の場合必須）",
        json_schema_extra={"example": "派遣社員 教育方法"},
    )
    monthly_search_volume: str | None = Field(
        None,
        description="月間検索ボリューム",
        json_schema_extra={"example": "100-200"},
    )
    competition_level: CompetitionLevel | None = Field(
        None,
        description="競合性（high/medium/low）",
    )
    # Fields for status='undecided'
    theme_topics: str | None = Field(
        None,
        description="書きたいテーマ・トピック（status='undecided'の場合必須）",
        json_schema_extra={"example": "派遣社員の教育方法について知りたい\n派遣社員の定着率を高める方法"},
    )
    selected_keyword: SelectedKeyword | None = Field(
        None,
        description="LLM候補から選択したキーワード",
    )
    # Optional
    related_keywords: list[RelatedKeyword] | None = Field(
        None,
        description="関連キーワード一覧（任意）",
    )

    @model_validator(mode="after")
    def validate_conditional_fields(self) -> "KeywordInput":
        """Validate fields based on keyword status."""
        if self.status == KeywordStatus.DECIDED:
            if not self.main_keyword:
                raise ValueError("status='decided'の場合、main_keywordは必須です")
        else:  # UNDECIDED
            if not self.theme_topics and not self.selected_keyword:
                raise ValueError("status='undecided'の場合、theme_topicsまたはselected_keywordが必要です")
        return self


# =============================================================================
# Section 3: Article Strategy
# =============================================================================


class StrategyInput(BaseModel):
    """Section 3: Article strategy."""

    article_style: ArticleStyle = Field(
        ...,
        description="記事のスタイル",
    )
    child_topics: list[str] | None = Field(
        None,
        description="子記事のトピック（article_style='topic_cluster'の場合）",
        json_schema_extra={
            "example": [
                "派遣社員向けOJTの具体的手法",
                "派遣社員向けeラーニングツール比較",
                "派遣社員の定着率を高めるフォローアップ方法",
            ]
        },
    )


# =============================================================================
# Section 4: Word Count Settings
# =============================================================================


class WordCountInput(BaseModel):
    """Section 4: Word count settings."""

    mode: WordCountMode = Field(
        ...,
        description="文字数設定モード",
    )
    target: int | None = Field(
        None,
        ge=1000,
        le=50000,
        description="ターゲット文字数（mode='manual'の場合必須）",
        json_schema_extra={"example": 12000},
    )

    @model_validator(mode="after")
    def validate_manual_target(self) -> "WordCountInput":
        """Validate that target is provided when mode is manual."""
        if self.mode == WordCountMode.MANUAL and self.target is None:
            raise ValueError("mode='manual'の場合、targetは必須です")
        return self


# =============================================================================
# Section 5: CTA Settings
# =============================================================================


class SingleCTA(BaseModel):
    """Single CTA configuration."""

    url: HttpUrl = Field(
        ...,
        description="CTA誘導先URL",
        json_schema_extra={"example": "https://cross-learning.jp/"},
    )
    text: str = Field(
        ...,
        min_length=1,
        description="CTAテキスト",
        json_schema_extra={"example": "クロスラーニングの詳細を見る"},
    )
    description: str = Field(
        "",
        description="誘導先の説明",
        json_schema_extra={"example": "クロスラーニング広報サイトのTOPページ"},
    )


class StagedCTAItem(BaseModel):
    """Individual staged CTA item."""

    url: HttpUrl = Field(..., description="CTA誘導先URL")
    text: str = Field(..., min_length=1, description="CTAテキスト")
    description: str = Field("", description="誘導先の説明")
    position: int | None = Field(
        None,
        description="挿入位置（文字数）。position_mode='fixed'の場合に使用",
    )


class StagedCTA(BaseModel):
    """Staged CTA configuration."""

    early: StagedCTAItem = Field(..., description="Early CTA（記事前半）")
    mid: StagedCTAItem = Field(..., description="Mid CTA（記事中盤）")
    final: StagedCTAItem = Field(..., description="Final CTA（記事末尾）")


class CTAInput(BaseModel):
    """Section 5: CTA settings."""

    type: CTAType = Field(
        ...,
        description="CTAタイプ（単一/段階的）",
    )
    position_mode: CTAPositionMode = Field(
        ...,
        description="CTA挿入位置モード（固定/比率/AI任せ）",
    )
    single: SingleCTA | None = Field(
        None,
        description="単一CTA設定（type='single'の場合）",
    )
    staged: StagedCTA | None = Field(
        None,
        description="段階的CTA設定（type='staged'の場合）",
    )

    @model_validator(mode="after")
    def validate_cta_type(self) -> "CTAInput":
        """Validate CTA configuration based on type."""
        if self.type == CTAType.SINGLE:
            if not self.single:
                raise ValueError("type='single'の場合、single設定は必須です")
        else:  # STAGED
            if not self.staged:
                raise ValueError("type='staged'の場合、staged設定は必須です")
        return self


# =============================================================================
# Complete Article Hearing Input
# =============================================================================


class ArticleHearingInput(BaseModel):
    """Complete article hearing input - replaces legacy RunInput.

    This is the comprehensive input structure for starting a new workflow run,
    organized into 6 sections matching the hearing form design.

    VULN-016: 明確な型識別のためformat_typeフィールドを追加
    """

    format_type: Literal["article_hearing_v1"] = "article_hearing_v1"
    business: BusinessInput = Field(..., description="セクション1: 事業内容とターゲット")
    keyword: KeywordInput = Field(..., description="セクション2: キーワード選定")
    strategy: StrategyInput = Field(..., description="セクション3: 記事戦略")
    word_count: WordCountInput = Field(..., description="セクション4: 文字数設定")
    cta: CTAInput = Field(..., description="セクション5: CTA設定")
    confirmed: bool = Field(..., description="セクション6: 最終確認")

    @field_validator("confirmed")
    @classmethod
    def validate_confirmed(cls, v: bool) -> bool:
        """Ensure the form is confirmed before submission."""
        if not v:
            raise ValueError("フォームの確認が必要です")
        return v

    def get_effective_keyword(self) -> str:
        """Get the effective main keyword for the workflow."""
        if self.keyword.status == KeywordStatus.DECIDED:
            if not self.keyword.main_keyword:
                raise ValueError("キーワードが決定済みの場合、main_keywordは必須です")
            return self.keyword.main_keyword
        else:
            if not self.keyword.selected_keyword:
                raise ValueError("キーワードが未定の場合、selected_keywordが必要です")
            return self.keyword.selected_keyword.keyword

    def get_target_word_count(self) -> int | None:
        """Get the target word count (None if AI-determined)."""
        if self.word_count.mode == WordCountMode.MANUAL:
            return self.word_count.target
        return None  # Will be determined by AI in step 3C

    def to_legacy_format(self) -> dict[str, Any]:
        """Convert to legacy RunInput format for backward compatibility."""
        return {
            "keyword": self.get_effective_keyword(),
            "target_audience": self.business.target_audience,
            "competitor_urls": None,  # Now auto-fetched
            "additional_requirements": self._build_additional_requirements(),
        }

    def _build_additional_requirements(self) -> str:
        """Build additional requirements string from structured input."""
        parts = []

        # Business context
        parts.append(f"【事業内容】{self.business.description}")
        parts.append(f"【自社の強み】{self.business.company_strengths}")

        # Target CV
        cv_label = {
            TargetCV.INQUIRY: "問い合わせ獲得",
            TargetCV.DOCUMENT_REQUEST: "資料請求",
            TargetCV.FREE_CONSULTATION: "無料相談申込",
            TargetCV.OTHER: self.business.target_cv_other or "その他",
        }
        parts.append(f"【目標CV】{cv_label[self.business.target_cv]}")

        # Article style
        if self.strategy.article_style == ArticleStyle.TOPIC_CLUSTER:
            parts.append("【記事スタイル】トピッククラスター戦略（親記事）")
            if self.strategy.child_topics:
                parts.append(f"【子記事トピック】{', '.join(self.strategy.child_topics)}")
        else:
            parts.append("【記事スタイル】標準記事（スタンドアロン）")

        # Word count
        if self.word_count.mode == WordCountMode.MANUAL and self.word_count.target:
            parts.append(f"【文字数上限】{self.word_count.target}文字")
        else:
            mode_labels = {
                WordCountMode.AI_SEO_OPTIMIZED: "SEO最適化（競合平均×1.2）",
                WordCountMode.AI_READABILITY: "読みやすさ優先（競合平均×0.9）",
                WordCountMode.AI_BALANCED: "バランス型（競合平均±5%）",
            }
            parts.append(f"【文字数モード】{mode_labels.get(self.word_count.mode, '自動')}")

        # CTA
        if self.cta.type == CTAType.SINGLE and self.cta.single:
            parts.append(f"【CTA】{self.cta.single.text} ({self.cta.single.url})")
        elif self.cta.type == CTAType.STAGED and self.cta.staged:
            parts.append("【CTA】段階的CTA")
            parts.append(f"  Early: {self.cta.staged.early.text}")
            parts.append(f"  Mid: {self.cta.staged.mid.text}")
            parts.append(f"  Final: {self.cta.staged.final.text}")

        return "\n".join(parts)


# =============================================================================
# Keyword Suggestion API
# =============================================================================


class KeywordSuggestionRequest(BaseModel):
    """Request for keyword suggestions."""

    theme_topics: str = Field(
        ...,
        min_length=10,
        description="書きたいテーマ・トピック",
    )
    business_description: str = Field(
        ...,
        description="事業内容（コンテキスト用）",
    )
    target_audience: str = Field(
        ...,
        description="ターゲット読者（コンテキスト用）",
    )


class KeywordSuggestion(BaseModel):
    """Single keyword suggestion from LLM."""

    keyword: str = Field(..., description="提案キーワード")
    estimated_volume: str = Field(..., description="推定検索ボリューム")
    estimated_competition: CompetitionLevel = Field(..., description="推定競合性")
    relevance_score: float = Field(..., ge=0, le=1, description="関連性スコア")


class KeywordSuggestionResponse(BaseModel):
    """Response containing keyword suggestions."""

    suggestions: list[KeywordSuggestion] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="キーワード候補リスト",
    )
    model_used: str = Field(..., description="使用したモデル")
    generated_at: str = Field(..., description="生成日時（ISO 8601）")


# =============================================================================
# Hearing Template Schemas
# =============================================================================


class HearingTemplateData(BaseModel):
    """Template data structure (ArticleHearingInput without confirmed field)."""

    business: BusinessInput = Field(..., description="セクション1: 事業内容とターゲット")
    keyword: KeywordInput = Field(..., description="セクション2: キーワード選定")
    strategy: StrategyInput = Field(..., description="セクション3: 記事戦略")
    word_count: WordCountInput = Field(..., description="セクション4: 文字数設定")
    cta: CTAInput = Field(..., description="セクション5: CTA設定")


class HearingTemplateBase(BaseModel):
    """Base schema for hearing template."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="テンプレート名",
        json_schema_extra={"example": "派遣社員向けeラーニング記事"},
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="テンプレートの説明",
        json_schema_extra={"example": "派遣社員教育に関する記事のテンプレート"},
    )


class HearingTemplateCreate(HearingTemplateBase):
    """Schema for creating a new hearing template."""

    data: HearingTemplateData = Field(..., description="テンプレートデータ")


class HearingTemplateUpdate(BaseModel):
    """Schema for updating a hearing template."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="テンプレート名",
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="テンプレートの説明",
    )
    data: HearingTemplateData | None = Field(None, description="テンプレートデータ")


class HearingTemplate(HearingTemplateBase):
    """Full hearing template schema with all fields."""

    id: UUID = Field(..., description="テンプレートID")
    tenant_id: str = Field(..., description="テナントID")
    data: HearingTemplateData = Field(..., description="テンプレートデータ")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")

    model_config = {"from_attributes": True}


class HearingTemplateList(BaseModel):
    """Paginated list of hearing templates."""

    items: list[HearingTemplate] = Field(..., description="テンプレート一覧")
    total: int = Field(..., description="総数")
    limit: int = Field(..., description="取得件数上限")
    offset: int = Field(..., description="オフセット")


# =============================================================================
# Content Suggestion API Schemas
# =============================================================================


class TargetAudienceSuggestionRequest(BaseModel):
    """Request for target audience suggestions."""

    business_description: str = Field(
        ...,
        min_length=10,
        description="事業内容",
    )
    target_cv: str = Field(
        ...,
        description="目標CV（inquiry/document_request/free_consultation/other）",
    )


class TargetAudienceSuggestion(BaseModel):
    """Single target audience suggestion."""

    audience: str = Field(..., description="ターゲット読者像")
    rationale: str = Field(..., description="提案理由")


class TargetAudienceSuggestionResponse(BaseModel):
    """Response containing target audience suggestions."""

    suggestions: list[TargetAudienceSuggestion] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="ターゲット読者候補",
    )
    model_used: str = Field(..., description="使用したモデル")
    generated_at: str = Field(..., description="生成日時（ISO 8601）")


class RelatedKeywordSuggestionRequest(BaseModel):
    """Request for related keyword suggestions."""

    main_keyword: str = Field(
        ...,
        min_length=2,
        description="メインキーワード",
    )
    business_description: str = Field(
        ...,
        description="事業内容（コンテキスト用）",
    )


class RelatedKeywordSuggestionItem(BaseModel):
    """Single related keyword suggestion."""

    keyword: str = Field(..., description="関連キーワード")
    volume: str = Field(..., description="推定検索ボリューム")
    relation_type: str = Field(
        ...,
        description="関連タイプ（synonym/long_tail/question/related_topic）",
    )


class RelatedKeywordSuggestionResponse(BaseModel):
    """Response containing related keyword suggestions."""

    suggestions: list[RelatedKeywordSuggestionItem] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="関連キーワード候補",
    )
    model_used: str = Field(..., description="使用したモデル")
    generated_at: str = Field(..., description="生成日時（ISO 8601）")


class ChildTopicSuggestionRequest(BaseModel):
    """Request for child topic suggestions."""

    main_keyword: str = Field(
        ...,
        min_length=2,
        description="メインキーワード",
    )
    business_description: str = Field(
        ...,
        description="事業内容",
    )
    target_audience: str = Field(
        ...,
        description="ターゲット読者",
    )


class ChildTopicSuggestion(BaseModel):
    """Single child topic suggestion."""

    topic: str = Field(..., description="子記事トピック")
    target_keyword: str = Field(..., description="ターゲットキーワード")
    rationale: str = Field(..., description="提案理由")


class ChildTopicSuggestionResponse(BaseModel):
    """Response containing child topic suggestions."""

    suggestions: list[ChildTopicSuggestion] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="子記事トピック候補",
    )
    model_used: str = Field(..., description="使用したモデル")
    generated_at: str = Field(..., description="生成日時（ISO 8601）")
