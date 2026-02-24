"""Step5 Primary Collection output schema.

blog.System Ver8.3 拡張:
- 3フェーズ分類 (phase1_anxiety, phase2_understanding, phase3_action)
- 知識ギャップ発見 (step3cとの連携)
- セクション配置マッピング
- 鮮度スコア
"""

from typing import Literal

from pydantic import BaseModel, Field

# === Phase 1: 3フェーズ分類と知識ギャップ ===


class DataPoint(BaseModel):
    """ソースから抽出したデータポイント."""

    metric: str  # 指標名
    value: str  # 値
    previous_year: str = ""  # 前年値
    change: str = ""  # 変化率
    context: str = ""  # 文脈


class PrimarySource(BaseModel):
    """一次資料."""

    url: str
    title: str
    source_type: Literal[
        "academic_paper",
        "government_report",
        "statistics",
        "official_document",
        "industry_report",
        "news_article",
        "other",
    ] = "other"
    excerpt: str = Field(default="", max_length=500)
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    verified: bool = False
    # blog.System Ver8.3 拡張
    phase_alignment: Literal["phase1_anxiety", "phase2_understanding", "phase3_action"] = "phase2_understanding"
    freshness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    data_points: list[DataPoint] = Field(default_factory=list)
    publication_date: str | None = None  # ISO format or year only


class CollectionStats(BaseModel):
    """収集統計."""

    total_collected: int = 0
    total_verified: int = 0
    failed_queries: int = 0
    # blog.System Ver8.3 拡張
    phase1_count: int = 0  # 不安喚起フェーズのソース数
    phase2_count: int = 0  # 理解納得フェーズのソース数
    phase3_count: int = 0  # 行動決定フェーズのソース数


class PhaseData(BaseModel):
    """フェーズ別データ集計."""

    description: str
    source_urls: list[str] = Field(default_factory=list)  # source URLs
    total_count: int = 0
    key_data_summary: list[str] = Field(default_factory=list)
    usage_sections: list[str] = Field(default_factory=list)


class PhaseSpecificData(BaseModel):
    """3フェーズ別のソースデータ."""

    phase1_anxiety: PhaseData = Field(default_factory=lambda: PhaseData(description="不安喚起：問題の深刻さ、リスク、損失"))
    phase2_understanding: PhaseData = Field(default_factory=lambda: PhaseData(description="理解納得：解決策、方法、効果"))
    phase3_action: PhaseData = Field(default_factory=lambda: PhaseData(description="行動決定：成功事例、導入実績、費用対効果"))


class KnowledgeGap(BaseModel):
    """競合がカバーしていない知識ギャップ."""

    gap_id: str  # "KG001"
    gap_description: str
    competitor_coverage: str = ""  # "0/10記事"
    primary_source_url: str | None = None  # 対応するソースURL
    implementation_section: str = ""  # 配置推奨セクション
    differentiation_value: Literal["high", "medium", "low"] = "medium"


# === Phase 2: セクション配置マッピング ===


class SectionSourceMapping(BaseModel):
    """セクションとソースの対応マッピング."""

    section_id: str  # "introduction", "H2-1", etc.
    section_title: str
    assigned_sources: list[str] = Field(default_factory=list)  # source URLs
    source_type_priority: list[str] = Field(default_factory=list)
    enhancement_notes: str = ""


class Step5Output(BaseModel):
    """Step5 の構造化出力."""

    step: str = "step5"
    keyword: str
    search_queries: list[str] = Field(default_factory=list)
    sources: list[PrimarySource] = Field(default_factory=list)
    invalid_sources: list[PrimarySource] = Field(default_factory=list)
    failed_queries: list[dict[str, str]] = Field(default_factory=list)
    collection_stats: CollectionStats = Field(default_factory=CollectionStats)
    model_config_data: dict[str, str] = Field(default_factory=dict, description="モデル設定（platform, model）")
    # blog.System Ver8.3 拡張
    phase_specific_data: PhaseSpecificData | None = None
    knowledge_gaps_filled: list[KnowledgeGap] = Field(default_factory=list)
    section_source_mapping: list[SectionSourceMapping] = Field(default_factory=list)
