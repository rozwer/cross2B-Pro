"""Step 9 output schemas.

Final rewrite step schemas:
- RewriteChange: Individual rewrite change tracking
- RewriteMetrics: Final rewrite comparison metrics
- Step9Output: Final step output

blog.System Ver8.3 Integration:
- FactcheckCorrection: Detailed factcheck correction record
- FAQPlacement: FAQ placement configuration
- SEOFinalAdjustments: SEO final optimization results
- FourPillarsFinalVerification: 4-pillar final check
- WordCountFinal: Final word count verification
- QualityScores: 8-item quality scoring
"""

from typing import Literal

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase

# =============================================================================
# 既存スキーマ（後方互換性維持）
# =============================================================================


class RewriteChange(BaseModel):
    """Individual rewrite change."""

    change_type: str = Field(
        default="",
        description="Type: factcheck_correction, faq_addition, style, structure, redundancy_removal",
    )
    section: str = Field(default="")
    description: str = Field(default="")
    original: str = Field(default="", description="修正前のテキスト")
    corrected: str = Field(default="", description="修正後のテキスト")


class RewriteMetrics(BaseModel):
    """Final rewrite comparison metrics."""

    original_word_count: int = 0
    final_word_count: int = 0
    word_diff: int = 0
    sections_count: int = 0
    faq_integrated: bool = False
    factcheck_corrections_applied: int = 0


# =============================================================================
# 新規スキーマ: FactcheckCorrection（ファクトチェック修正記録）
# =============================================================================


class FactcheckCorrection(BaseModel):
    """Detailed factcheck correction record."""

    claim_id: str = Field(default="", description="修正対象のクレームID")
    original: str = Field(default="", description="修正前のテキスト")
    corrected: str = Field(default="", description="修正後のテキスト")
    reason: str = Field(default="", description="修正理由")
    source: str = Field(default="", description="正しい情報の出典")


# =============================================================================
# 新規スキーマ: FAQPlacement（FAQ配置設定）
# =============================================================================


class FAQPlacement(BaseModel):
    """FAQ placement configuration."""

    position: Literal["before_conclusion", "after_conclusion", "separate_section"] = Field(
        default="before_conclusion", description="FAQ配置位置"
    )
    items_count: int = Field(default=0, description="統合されたFAQ数")
    integrated: bool = Field(default=False, description="FAQ統合完了フラグ")


# =============================================================================
# 新規スキーマ: SEOFinalAdjustments（SEO最終調整）
# =============================================================================


class SEOFinalAdjustments(BaseModel):
    """SEO final optimization results."""

    headings_optimized: list[str] = Field(default_factory=list, description="最適化された見出しリスト")
    internal_links_added: int = Field(default=0, description="追加された内部リンク数")
    alt_texts_generated: list[str] = Field(default_factory=list, description="生成されたALTテキスト")
    meta_description_optimized: bool = Field(default=False, description="メタディスクリプション最適化完了")
    keyword_density: float = Field(default=0.0, ge=0.0, le=10.0, description="キーワード密度（%）")
    heading_cleanup_done: bool = Field(default=False, description="見出しクリーンアップ完了（H2-1等削除）")


# =============================================================================
# 新規スキーマ: FourPillarsFinalVerification（4本柱最終確認）
# =============================================================================


class NeuroscienceCheck(BaseModel):
    """神経科学チェック結果."""

    shocking_data_verified: bool = Field(default=False, description="衝撃的データの正確性確認")
    concepts_within_limit: bool = Field(default=False, description="3概念以内")
    sentence_length_ok: bool = Field(default=False, description="文の長さ20-35文字")
    three_phase_maintained: bool = Field(default=False, description="3フェーズ配分維持")
    issues: list[str] = Field(default_factory=list)


class BehavioralEconomicsCheck(BaseModel):
    """行動経済学チェック結果."""

    social_proof_verified: bool = Field(default=False, description="社会的証明データ検証")
    six_principles_placed: bool = Field(default=False, description="6原則配置確認")
    specific_numbers_maintained: bool = Field(default=False, description="具体的数値維持")
    issues: list[str] = Field(default_factory=list)


class LLMOCheck(BaseModel):
    """LLMOチェック結果."""

    citation_format_correct: bool = Field(default=False, description="引用形式確認")
    token_count_in_range: bool = Field(default=False, description="トークン数400-600維持")
    bullet_points_maintained: bool = Field(default=False, description="箇条書き維持")
    section_independence: bool = Field(default=False, description="セクション独立性維持")
    issues: list[str] = Field(default_factory=list)


class KGICheck(BaseModel):
    """KGIチェック結果."""

    cta_data_verified: bool = Field(default=False, description="CTA周辺データ検証")
    three_stage_cta: bool = Field(default=False, description="3段階CTA配置確認")
    internal_links_maintained: bool = Field(default=False, description="内部リンク維持")
    cta_text_matches_step0: bool = Field(default=False, description="CTA文言が工程0指定と一致")
    issues: list[str] = Field(default_factory=list)


class FourPillarsFinalVerification(BaseModel):
    """4本柱最終確認結果."""

    all_compliant: bool = Field(default=False, description="全項目適合")
    issues_remaining: list[str] = Field(default_factory=list, description="残存問題リスト")
    manual_review_needed: bool = Field(default=False, description="手動レビュー必要フラグ")

    neuroscience: NeuroscienceCheck = Field(default_factory=NeuroscienceCheck)
    behavioral_economics: BehavioralEconomicsCheck = Field(default_factory=BehavioralEconomicsCheck)
    llmo: LLMOCheck = Field(default_factory=LLMOCheck)
    kgi: KGICheck = Field(default_factory=KGICheck)


# =============================================================================
# 新規スキーマ: WordCountFinal（最終文字数確認）
# =============================================================================


class WordCountFinal(BaseModel):
    """Final word count verification."""

    target: int = Field(default=0, description="目標文字数")
    actual: int = Field(default=0, description="実際の文字数")
    variance: int = Field(default=0, description="差分（actual - target）")
    variance_percent: float = Field(default=0.0, description="差分率（%）")
    status: Literal["achieved", "補筆推奨", "補筆必須", "要約必須"] = Field(default="achieved", description="達成状況")
    compression_applied: bool = Field(default=False, description="圧縮処理実施済み")


# =============================================================================
# 新規スキーマ: QualityScores（8項目品質スコア）
# =============================================================================


class QualityScores(BaseModel):
    """8-item quality scoring (each 0.0-1.0)."""

    accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="正確性")
    readability: float = Field(default=0.0, ge=0.0, le=1.0, description="読みやすさ")
    persuasiveness: float = Field(default=0.0, ge=0.0, le=1.0, description="説得力")
    comprehensiveness: float = Field(default=0.0, ge=0.0, le=1.0, description="網羅性")
    differentiation: float = Field(default=0.0, ge=0.0, le=1.0, description="差別化")
    practicality: float = Field(default=0.0, ge=0.0, le=1.0, description="実用性")
    seo_optimization: float = Field(default=0.0, ge=0.0, le=1.0, description="SEO最適化")
    cta_effectiveness: float = Field(default=0.0, ge=0.0, le=1.0, description="CTA効果")

    total_score: float = Field(default=0.0, ge=0.0, le=1.0, description="総合品質スコア（平均）")
    publication_ready: bool = Field(default=False, description="公開準備完了（0.90以上）")


# =============================================================================
# 新規スキーマ: RedundancyCheck（冗長性チェック）
# =============================================================================


class RedundancyCheck(BaseModel):
    """Redundancy and duplication check results."""

    redundant_expressions_removed: int = Field(default=0, description="削除した冗長表現数")
    duplicate_content_merged: int = Field(default=0, description="統合した重複コンテンツ数")
    long_sentences_split: int = Field(default=0, description="分割した長文数（60文字以上）")


# =============================================================================
# 拡張版 Step9Output
# =============================================================================


class Step9Output(StepOutputBase):
    """Step 9 output schema."""

    # 既存フィールド（後方互換性維持）
    final_content: str = Field(default="", description="Final rewritten content")
    meta_description: str = Field(
        default="",
        max_length=160,
        description="Meta description for SEO",
    )
    changes_summary: list[RewriteChange] = Field(
        default_factory=list,
        description="List of changes made",
    )
    rewrite_metrics: RewriteMetrics = Field(default_factory=RewriteMetrics)
    internal_link_suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested internal links",
    )
    quality_warnings: list[str] = Field(default_factory=list)
    model: str = Field(default="")
    model_config_data: dict[str, str] = Field(default_factory=dict, description="モデル設定（platform, model）")

    # 新規フィールド（blog.System統合）
    factcheck_corrections: list[FactcheckCorrection] = Field(default_factory=list, description="ファクトチェック修正記録")
    faq_placement: FAQPlacement | None = Field(default=None, description="FAQ配置設定")
    seo_final_adjustments: SEOFinalAdjustments | None = Field(default=None, description="SEO最終調整")
    four_pillars_final_verification: FourPillarsFinalVerification | None = Field(default=None, description="4本柱最終確認")
    word_count_final: WordCountFinal | None = Field(default=None, description="最終文字数確認")
    quality_scores: QualityScores | None = Field(default=None, description="8項目品質スコア")
    redundancy_check: RedundancyCheck | None = Field(default=None, description="冗長性チェック結果")
