"""Step 7B output schemas.

Polishing and brush-up step schemas:
- PolishChange: Individual change tracking
- PolishMetrics: Polishing comparison metrics
- Step7bOutput: Final step output

blog.System Ver8.3 対応:
- AdjustmentDetails: 語尾統一、一文長さ、接続詞の調整詳細
- WordCountComparison: 文字数維持確認（±5%以内）
- FourPillarsPreservation: 4本柱維持確認
- ReadabilityImprovements: 可読性改善メトリクス
- Step7bOutputV2: 拡張出力スキーマ
"""

from typing import Literal

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class PolishChange(BaseModel):
    """Individual polishing change."""

    change_type: str = Field(
        default="",
        description="Type: wording, flow, clarity, tone, restructure",
    )
    original_snippet: str = Field(default="")
    polished_snippet: str = Field(default="")
    section: str = Field(default="")


class PolishMetrics(BaseModel):
    """Polishing comparison metrics."""

    original_word_count: int = 0
    polished_word_count: int = 0
    word_diff: int = 0
    word_diff_percent: float = 0.0
    sections_preserved: int = 0
    sections_modified: int = 0


class Step7bOutput(StepOutputBase):
    """Step 7B output schema."""

    polished: str = Field(default="", description="Polished content (Markdown)")
    changes_summary: str = Field(default="", description="Summary of changes made")
    change_count: int = Field(default=0, description="Number of changes made")
    polish_metrics: PolishMetrics = Field(default_factory=PolishMetrics)
    quality_warnings: list[str] = Field(default_factory=list)
    model: str = Field(default="")


# =============================================================================
# 新規スキーマ（blog.System Ver8.3 対応）
# =============================================================================


class AdjustmentDetails(BaseModel):
    """調整詳細（blog.System Ver8.3）.

    語尾統一、一文長さ、接続詞などの詳細な調整記録。
    """

    sentence_length_fixes: int = Field(default=0, description="一文長さ調整回数")
    connector_improvements: int = Field(default=0, description="接続詞改善回数")
    tone_unifications: int = Field(default=0, description="語尾統一回数")
    technical_term_explanations_added: int = Field(default=0, description="専門用語説明追加回数")
    passive_to_active_conversions: int = Field(default=0, description="受動態→能動態変換回数")
    redundancy_removals: int = Field(default=0, description="冗長表現削除回数")


class WordCountComparison(BaseModel):
    """文字数比較（blog.System Ver8.3）.

    ブラッシュアップ前後の文字数比較と±5%維持確認。
    """

    before: int = Field(default=0, description="ブラッシュアップ前の文字数")
    after: int = Field(default=0, description="ブラッシュアップ後の文字数")
    change_percent: float = Field(default=0.0, description="変化率（%）")
    is_within_5_percent: bool = Field(default=True, description="±5%以内かどうか")


class FourPillarsPreservation(BaseModel):
    """4本柱維持確認（blog.System Ver8.3）.

    ブラッシュアップ後も4本柱（神経科学、行動経済学、LLMO、KGI）が維持されているか確認。
    """

    maintained: bool = Field(default=True, description="4本柱が維持されているか")
    changes_affecting_pillars: list[str] = Field(default_factory=list, description="4本柱に影響する変更内容")
    pillar_status: dict[str, Literal["preserved", "modified", "removed"]] = Field(
        default_factory=lambda: {
            "neuroscience": "preserved",
            "behavioral_economics": "preserved",
            "llmo": "preserved",
            "kgi": "preserved",
        },
        description="各柱の状態",
    )


class ReadabilityImprovements(BaseModel):
    """可読性改善メトリクス（blog.System Ver8.3）.

    文章の読みやすさに関する改善指標。目標範囲は20-35文字/文。
    """

    avg_sentence_length_before: float = Field(default=0.0, description="改善前の平均文長")
    avg_sentence_length_after: float = Field(default=0.0, description="改善後の平均文長")
    target_range_min: int = Field(default=20, description="目標文長下限")
    target_range_max: int = Field(default=35, description="目標文長上限")
    is_within_target: bool = Field(default=False, description="目標範囲内かどうか")
    sentences_shortened: int = Field(default=0, description="短縮した文の数")
    sentences_lengthened: int = Field(default=0, description="伸長した文の数")
    complex_sentences_simplified: int = Field(default=0, description="簡略化した複文の数")


class Step7bOutputV2(StepOutputBase):
    """Step 7B 拡張出力スキーマ（blog.System Ver8.3 対応）.

    既存フィールドを維持しつつ、新規フィールドを追加。
    新規フィールドはすべてオプショナルで後方互換性を確保。
    """

    # 既存フィールド（後方互換）
    polished: str = Field(default="", description="Polished content (Markdown)")
    changes_summary: str = Field(default="", description="Summary of changes made")
    change_count: int = Field(default=0, description="Number of changes made")
    polish_metrics: PolishMetrics = Field(default_factory=PolishMetrics)
    quality_warnings: list[str] = Field(default_factory=list)
    model: str = Field(default="")

    # 新規フィールド（blog.System Ver8.3 対応）
    adjustment_details: AdjustmentDetails | None = Field(default=None, description="調整詳細")
    word_count_comparison: WordCountComparison | None = Field(default=None, description="文字数比較")
    four_pillars_preservation: FourPillarsPreservation | None = Field(default=None, description="4本柱維持確認")
    readability_improvements: ReadabilityImprovements | None = Field(default=None, description="可読性改善メトリクス")
