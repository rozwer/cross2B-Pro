"""Step 0 (Keyword Selection) input/output schemas.

blog.System Ver8.3 対応の拡張スキーマ。
4本柱評価、記事戦略、CTA設計などの新機能をサポート。
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# 入力スキーマ（blog.System 拡張）
# =============================================================================


class BusinessContext(BaseModel):
    """事業情報コンテキスト（工程-1相当）."""

    business_description: str = Field(default="", description="事業内容の説明")
    conversion_goal: str = Field(default="", description="目標CV（問い合わせ/資料DL等）")
    target_persona: str = Field(default="", description="ターゲット読者像")
    company_strengths: str = Field(default="", description="自社の強み・差別化ポイント")


class WordCountTolerance(BaseModel):
    """文字数の許容範囲."""

    min_tolerance: int = Field(default=-300, description="最小許容差（基本-300、緩和-500）")
    max_tolerance: int = Field(default=300, description="最大許容差")


class WordCountConfig(BaseModel):
    """文字数設定."""

    mode: Literal["manual", "ai_seo_optimized", "ai_readability", "ai_balanced"] = Field(
        default="ai_balanced", description="文字数決定モード"
    )
    manual_word_count: int | None = Field(default=None, description="手動指定時の文字数（mode=manual時のみ使用）")
    tolerance: WordCountTolerance = Field(default_factory=WordCountTolerance, description="文字数の許容範囲")


class CTAPlacement(BaseModel):
    """CTA配置位置."""

    position: int | str = Field(..., description="配置位置（文字数または 'target_word_count - 500' などの式）")
    url: str = Field(default="", description="CTA URL")
    text: str = Field(default="", description="CTAテキスト")


class CTASpecification(BaseModel):
    """CTA設計仕様."""

    design_type: Literal["single", "staged"] = Field(default="staged", description="CTA設計タイプ（single: 単一、staged: 3段階）")
    placements: dict[str, CTAPlacement] = Field(
        default_factory=lambda: {
            "early": CTAPlacement(position=650, url="", text=""),
            "mid": CTAPlacement(position=2800, url="", text=""),
            "final": CTAPlacement(position="target_word_count - 500", url="", text=""),
        },
        description="CTA配置位置（early/mid/final）",
    )


class Step0Input(BaseModel):
    """Step 0 入力スキーマ（blog.System 拡張）."""

    # 必須フィールド
    keyword: str = Field(..., description="メインキーワード（必須）")
    pack_id: str = Field(..., description="プロンプトパックID（必須）")

    # 事業コンテキスト（オプション）
    business_context: BusinessContext = Field(default_factory=BusinessContext, description="事業情報コンテキスト")

    # キーワード関連（オプション）
    search_volume: int | None = Field(default=None, description="月間検索ボリューム")
    competition: Literal["high", "medium", "low"] | None = Field(default=None, description="競合性")
    related_keywords: list[str] = Field(default_factory=list, description="関連キーワード")

    # 記事戦略（オプション）
    strategy: Literal["standard", "topic_cluster"] = Field(default="standard", description="記事戦略")
    cluster_topics: list[str] = Field(default_factory=list, description="子記事トピック（topic_cluster時）")

    # 文字数・CTA設定（オプション）
    word_count_config: WordCountConfig = Field(default_factory=WordCountConfig, description="文字数設定")
    cta_specification: CTASpecification = Field(default_factory=CTASpecification, description="CTA設計仕様")


# =============================================================================
# 出力スキーマ（4本柱評価）
# =============================================================================


class NeuroscienceEvaluation(BaseModel):
    """神経科学評価."""

    phase: Literal[1, 2, 3] = Field(default=1, description="フェーズ（1: 不安喚起、2: 理解促進、3: 行動喚起）")
    brain_activation: str = Field(default="", description="活性化する脳領域（扁桃体/前頭前野/線条体）")
    score: int = Field(default=50, ge=0, le=100, description="神経科学スコア (0-100)")


class BehavioralEconomicsEvaluation(BaseModel):
    """行動経済学評価."""

    applicable_principles: list[str] = Field(
        default_factory=list, description="適用可能な原則（損失回避/社会的証明/権威性/一貫性/好意/希少性）"
    )
    score: int = Field(default=50, ge=0, le=100, description="行動経済学スコア (0-100)")


class LLMOEvaluation(BaseModel):
    """LLMO（LLM最適化）評価."""

    citation_potential: Literal["high", "medium", "low"] = Field(default="medium", description="引用可能性")
    score: int = Field(default=50, ge=0, le=100, description="LLMOスコア (0-100)")


class KGIEvaluation(BaseModel):
    """KGI（重要目標指標）評価."""

    expected_cvr: float = Field(default=0.0, ge=0.0, le=100.0, description="期待CVR (%)")
    score: int = Field(default=50, ge=0, le=100, description="KGIスコア (0-100)")


class FourPillarsEvaluation(BaseModel):
    """4本柱評価."""

    neuroscience: NeuroscienceEvaluation = Field(default_factory=NeuroscienceEvaluation, description="神経科学評価")
    behavioral_economics: BehavioralEconomicsEvaluation = Field(default_factory=BehavioralEconomicsEvaluation, description="行動経済学評価")
    llmo: LLMOEvaluation = Field(default_factory=LLMOEvaluation, description="LLMO評価")
    kgi: KGIEvaluation = Field(default_factory=KGIEvaluation, description="KGI評価")


# =============================================================================
# 出力スキーマ（記事戦略）
# =============================================================================


class ArticleBackground(BaseModel):
    """記事の背景情報."""

    why_now: str = Field(default="", description="なぜ今この記事が必要か")
    target_pain: str = Field(default="", description="ターゲットの課題・痛み")
    key_message: str = Field(default="", description="伝えたい核心メッセージ")
    urgency: Literal["high", "medium", "low"] = Field(default="medium", description="緊急度")


class ArticleStrategy(BaseModel):
    """記事戦略."""

    type: Literal["comprehensive_guide", "deep_dive", "case_study", "comparison", "news_analysis", "how_to"] = Field(
        default="comprehensive_guide", description="記事タイプ（6種類）"
    )
    strategy: Literal["standard", "topic_cluster"] = Field(default="standard", description="戦略（単独/トピッククラスター）")
    background: ArticleBackground = Field(default_factory=ArticleBackground, description="背景情報")


# =============================================================================
# Step0Output（既存 + blog.System 拡張）
# =============================================================================


class Step0Output(BaseModel):
    """Step 0 structured output.

    キーワード選択・分析の結果を表す構造化出力。
    LLMの分析結果をパースして構造化データとして保存する。

    blog.System Ver8.3 対応:
    - 4本柱評価（four_pillars_evaluation）
    - 記事戦略（article_strategy）
    - 文字数設定（word_count_config）
    - CTA設計（cta_specification）
    """

    step: str = "step0"
    keyword: str = Field(..., description="分析対象のキーワード")
    analysis: str = Field(..., description="LLMによる分析結果（生テキスト）")

    # =========================================================================
    # 既存フィールド（後方互換性のため維持）
    # =========================================================================

    # Parsed fields (optional - may not always be present)
    search_intent: str = Field(default="", description="検索意図の分析")
    difficulty_score: int = Field(
        default=5,
        ge=1,
        le=10,
        description="難易度スコア (1-10) [DEPRECATED: four_pillars_evaluation を使用推奨]",
    )
    recommended_angles: list[str] = Field(default_factory=list, description="推奨アプローチ角度のリスト")
    target_audience: str = Field(default="", description="ターゲットオーディエンス")
    content_type_suggestion: str = Field(
        default="",
        description="推奨コンテンツタイプ [DEPRECATED: article_strategy.type を使用推奨]",
    )

    # Model info
    model: str = Field(default="", description="使用したLLMモデル")
    usage: dict[str, int] = Field(default_factory=dict, description="トークン使用量")

    # Metrics
    metrics: dict[str, int] = Field(default_factory=dict, description="テキストメトリクス (char_count, word_count)")

    # Quality info
    quality: dict[str, list[str] | int] = Field(default_factory=dict, description="品質チェック結果 (issues, attempts)")

    # Parse result
    parse_result: dict[str, bool | str | list[str]] = Field(
        default_factory=dict,
        description="JSONパース結果 (success, format_detected, fixes_applied)",
    )

    # =========================================================================
    # blog.System 拡張フィールド（全て Optional）
    # =========================================================================

    # 4本柱評価
    four_pillars_evaluation: FourPillarsEvaluation | None = Field(
        default=None,
        description="4本柱評価（神経科学/行動経済学/LLMO/KGI）",
    )

    # 記事戦略
    article_strategy: ArticleStrategy | None = Field(
        default=None,
        description="記事戦略（タイプ/戦略/背景）",
    )

    # 文字数設定（入力から引き継ぎ、または step3c で確定）
    word_count_config: WordCountConfig | None = Field(
        default=None,
        description="文字数設定（モード/目標文字数/許容範囲）",
    )

    # CTA設計（入力から引き継ぎ）
    cta_specification: CTASpecification | None = Field(
        default=None,
        description="CTA設計仕様（タイプ/配置位置）",
    )

    # キーワード関連（入力から引き継ぎ）
    search_volume: int | None = Field(
        default=None,
        description="月間検索ボリューム",
    )
    competition: Literal["high", "medium", "low"] | None = Field(
        default=None,
        description="競合性",
    )
