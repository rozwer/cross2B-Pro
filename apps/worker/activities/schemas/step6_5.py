"""Step6.5 Integration Package output schema.

blog.System Ver8.3 対応:
- ReferenceData: パート2参照データ集
- ComprehensiveBlueprint: 包括的構成案（パート1/2構成）
- SectionExecutionInstruction: セクション別詳細執筆指示
- VisualElementInstruction: 視覚要素配置指示
- FourPillarsFinalCheck: 4本柱最終適合チェック
"""

from typing import Any

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class InputSummary(BaseModel):
    """入力データサマリー."""

    step_id: str
    available: bool
    key_points: list[str] = Field(default_factory=list)
    data_quality: str = "unknown"  # good|fair|poor|unknown


# =============================================================================
# blog.System Ver8.3 対応モデル
# =============================================================================


class ReferenceData(BaseModel):
    """パート2: 参照データ集.

    構成案で使用するキーワード、ソース、人間味要素、CTA配置を集約。
    """

    keywords: list[str] = Field(default_factory=list, description="使用するキーワード")
    sources: list[str] = Field(default_factory=list, description="引用するソース")
    human_touch_elements: list[str] = Field(default_factory=list, description="人間味要素")
    cta_placements: list[str] = Field(default_factory=list, description="CTA配置")


class ComprehensiveBlueprint(BaseModel):
    """包括的な構成案（パート1/2構成）.

    パート1: 構成案概要（テキスト）
    パート2: 参照データ集（ReferenceData）
    """

    part1_outline: str = Field(default="", description="構成案概要")
    part2_reference_data: ReferenceData = Field(default_factory=ReferenceData, description="参照データ集")


class SectionExecutionInstruction(BaseModel):
    """セクション別の詳細執筆指示.

    工程7Aでの本文生成時に各セクションの執筆指示として使用。
    PREP法ベースの論理展開、必須ポイント、引用ソース、キーワード、
    人間味要素、目標文字数を詳細に指定。
    """

    section_title: str = Field(..., description="セクションタイトル")
    logic_flow: str = Field(default="", description="論理展開の詳細（PREP法ベース）")
    key_points: list[str] = Field(default_factory=list, description="必須含むポイント")
    sources_to_cite: list[str] = Field(default_factory=list, description="引用するソース")
    keywords_to_include: list[str] = Field(default_factory=list, description="含めるキーワード")
    human_touch_to_apply: list[str] = Field(default_factory=list, description="適用する人間味要素")
    word_count_target: int = Field(default=0, ge=0, description="目標文字数")


class VisualElementInstruction(BaseModel):
    """視覚要素の配置指示.

    工程7Bでの視覚要素追加時に使用。
    表、グラフ、図解、画像の配置位置と内容・目的を指定。
    """

    element_type: str = Field(..., description="要素タイプ（table/chart/diagram/image）")
    placement_section: str = Field(..., description="配置するセクション")
    content_description: str = Field(default="", description="内容の説明")
    purpose: str = Field(default="", description="目的・効果")


class FourPillarsFinalCheck(BaseModel):
    """4本柱の最終適合チェック.

    工程4で設計した4本柱（神経科学・行動経済学・LLMO・KGI）が
    全セクションに適切に実装されているかを最終確認。
    """

    all_sections_compliant: bool = Field(default=False, description="全セクション適合")
    neuroscience_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="神経科学カバー率")
    behavioral_economics_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="行動経済学カバー率")
    llmo_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="LLMOカバー率")
    kgi_coverage: float = Field(default=0.0, ge=0.0, le=1.0, description="KGIカバー率")
    issues: list[str] = Field(default_factory=list, description="不適合の問題点")
    recommendations: list[str] = Field(default_factory=list, description="改善推奨事項")


class SectionBlueprint(BaseModel):
    """セクション設計図."""

    level: int = Field(default=2, ge=1, le=4)
    title: str = ""
    target_words: int = 0
    key_points: list[str] = Field(default_factory=list)
    sources_to_cite: list[str] = Field(default_factory=list)
    keywords_to_include: list[str] = Field(default_factory=list)


class PackageQuality(BaseModel):
    """パッケージ品質."""

    is_acceptable: bool = True
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class Step6_5Output(StepOutputBase):
    """Step6.5 の構造化出力.

    blog.System Ver8.3 対応:
    - comprehensive_blueprint: 包括的構成案（パート1/2構成）
    - section_execution_instructions: セクション別詳細執筆指示
    - visual_element_instructions: 視覚要素配置指示
    - four_pillars_final_check: 4本柱最終適合チェック
    """

    step: str = "step6_5"
    integration_package: str = ""
    article_blueprint: dict[str, Any] = Field(default_factory=dict)
    section_blueprints: list[SectionBlueprint] = Field(default_factory=list)
    outline_summary: str = ""
    section_count: int = 0
    total_sources: int = 0
    input_summaries: list[InputSummary] = Field(default_factory=list)
    inputs_summary: dict[str, bool] = Field(default_factory=dict)
    quality: PackageQuality = Field(default_factory=PackageQuality)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    handoff_notes: list[str] = Field(default_factory=list)
    model: str = ""
    model_config_data: dict[str, str] = Field(default_factory=dict, description="モデル設定（platform, model）")
    token_usage: dict[str, int] = Field(default_factory=dict)

    # blog.System Ver8.3 対応フィールド（後方互換性のため Optional）
    comprehensive_blueprint: ComprehensiveBlueprint | None = Field(default=None, description="包括的構成案（パート1/2構成）")
    section_execution_instructions: list[SectionExecutionInstruction] = Field(default_factory=list, description="セクション別詳細執筆指示")
    visual_element_instructions: list[VisualElementInstruction] = Field(default_factory=list, description="視覚要素配置指示")
    four_pillars_final_check: FourPillarsFinalCheck | None = Field(default=None, description="4本柱最終適合チェック")
