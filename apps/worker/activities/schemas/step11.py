"""Step11 Image Generation schema.

Step11は記事への画像挿入を扱う工程で、以下のサブステップから構成される:
- 11A: 画像生成を行うか確認
- 11B: 画像設定入力（枚数、挿入位置リクエスト）
- 11C: 挿入候補分析＆提案
- 11D: ユーザー確認・修正
- 11E: 各画像の生成指示入力
- 11F: 画像生成＆確認
- 11G: HTML/Markdownへ画像挿入
- 11H: プレビュー表示

blog.System Ver8.3 対応:
- PositionAnalysisEnhanced: 拡張位置分析（コンテンツギャップ、視覚的ブレーク、データ可視化）
- ImagePurposeClassification: 画像目的分類（hero/illustration/data_viz/break/cta_support）
- Step11OutputV2: 拡張出力スキーマ
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Step11SubStep(str, Enum):
    """Step11のサブステップ."""

    CONFIRM_IMAGE_GEN = "11A"  # 画像生成を行うか確認
    INPUT_SETTINGS = "11B"  # 画像設定入力
    ANALYZE_POSITIONS = "11C"  # 挿入候補分析
    USER_REVIEW_POSITIONS = "11D"  # ユーザー確認・修正
    INPUT_IMAGE_INSTRUCTIONS = "11E"  # 各画像の生成指示入力
    GENERATE_AND_REVIEW = "11F"  # 画像生成＆確認
    INSERT_IMAGES = "11G"  # 画像挿入
    PREVIEW = "11H"  # プレビュー表示


class ImageInsertionPosition(BaseModel):
    """画像挿入位置."""

    article_number: int | None = Field(
        default=None,
        description="対象記事番号（1-4）。None の場合は全記事共通",
    )
    section_title: str = Field(..., description="挿入先のセクションタイトル")
    section_index: int = Field(..., description="セクションのインデックス（0始まり）")
    position: str = Field(
        default="after",
        pattern="^(before|after)$",
        description="セクションの前後どちらに挿入するか",
    )
    source_text: str = Field(
        default="",
        description="画像の元となるテキスト（該当セクションの要約）",
    )
    description: str = Field(
        default="",
        description="なぜこの位置に画像が必要かの説明",
    )


class ImageGenerationRequest(BaseModel):
    """画像生成リクエスト."""

    position: ImageInsertionPosition
    user_instruction: str = Field(
        default="",
        description="ユーザーからの画像生成指示",
    )
    generated_prompt: str = Field(
        default="",
        description="LLMが生成した画像生成プロンプト（英語）",
    )
    alt_text: str = Field(
        default="",
        description="画像のalt属性用テキスト（日本語）",
    )


class GeneratedImage(BaseModel):
    """生成された画像."""

    request: ImageGenerationRequest
    image_path: str = Field(default="", description="storage上の画像パス")
    image_digest: str = Field(default="", description="画像のsha256ダイジェスト")
    image_base64: str = Field(default="", description="Base64エンコード済み画像")
    mime_type: str = Field(default="image/png")
    width: int = Field(default=0)
    height: int = Field(default=0)
    file_size: int = Field(default=0, description="ファイルサイズ（バイト）")
    retry_count: int = Field(default=0, description="リトライ回数")
    accepted: bool = Field(default=False, description="ユーザーが承認したか")
    article_number: int | None = Field(default=None, description="所属する記事番号（1-4）、None=全記事共通")


class Step11Config(BaseModel):
    """Step11の設定."""

    enabled: bool = Field(default=True, description="画像生成を有効にするか")
    image_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="生成する画像数",
    )
    position_request: str = Field(
        default="",
        description="挿入位置に関するユーザーリクエスト",
    )
    max_retries_per_image: int = Field(
        default=3,
        ge=1,
        le=5,
        description="画像あたりの最大リトライ回数",
    )


class PositionAnalysisResult(BaseModel):
    """挿入位置分析結果."""

    analysis_summary: str = Field(
        default="",
        description="記事全体の分析サマリー",
    )
    positions: list[ImageInsertionPosition] = Field(
        default_factory=list,
        description="推奨挿入位置リスト",
    )
    model: str = Field(default="", description="分析に使用したモデル")
    token_usage: dict[str, int] = Field(default_factory=dict)


class Step11State(BaseModel):
    """Step11の状態.

    Human-in-the-loopのため、複数のサブステップを持つ。
    """

    current_substep: Step11SubStep = Field(
        default=Step11SubStep.CONFIRM_IMAGE_GEN,
        description="現在のサブステップ",
    )
    config: Step11Config = Field(
        default_factory=Step11Config,
        description="画像生成設定",
    )
    position_analysis: PositionAnalysisResult | None = Field(
        default=None,
        description="挿入位置分析結果",
    )
    confirmed_positions: list[ImageInsertionPosition] = Field(
        default_factory=list,
        description="ユーザーが確定した挿入位置",
    )
    image_requests: list[ImageGenerationRequest] = Field(
        default_factory=list,
        description="画像生成リクエストリスト",
    )
    generated_images: list[GeneratedImage] = Field(
        default_factory=list,
        description="生成済み画像リスト",
    )
    current_image_index: int = Field(
        default=0,
        description="現在処理中の画像インデックス",
    )
    # 最終出力
    final_markdown: str = Field(
        default="",
        description="画像挿入後のMarkdown",
    )
    final_html: str = Field(
        default="",
        description="画像挿入後のHTML",
    )


class Step11Output(BaseModel):
    """Step11の出力."""

    step: str = "step11"
    enabled: bool = Field(..., description="画像生成を行ったか")
    image_count: int = Field(default=0, description="生成した画像数")
    images: list[GeneratedImage] = Field(
        default_factory=list,
        description="生成した画像リスト",
    )
    markdown_with_images: str = Field(
        default="",
        description="画像挿入後のMarkdownコンテンツ",
    )
    html_with_images: str = Field(
        default="",
        description="画像挿入後のHTMLコンテンツ",
    )
    model: str = Field(default="", description="使用したモデル")
    token_usage: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


# Human-in-the-loop用のシグナルペイロード
class Step11ConfirmImageGenPayload(BaseModel):
    """11A: 画像生成確認のペイロード."""

    generate_images: bool = Field(..., description="画像を生成するか")


class Step11SettingsPayload(BaseModel):
    """11B: 画像設定入力のペイロード."""

    image_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="生成する画像数",
    )
    position_request: str = Field(
        default="",
        description="挿入位置に関するリクエスト",
    )


class Step11PositionReviewPayload(BaseModel):
    """11D: 挿入位置確認のペイロード."""

    approved: bool = Field(..., description="位置を承認するか")
    modified_positions: list[ImageInsertionPosition] | None = Field(
        default=None,
        description="修正した位置リスト（Noneの場合は分析結果をそのまま使用）",
    )
    reanalyze: bool = Field(
        default=False,
        description="再分析を要求するか",
    )
    reanalyze_request: str = Field(
        default="",
        description="再分析時の追加リクエスト",
    )


class Step11ImageInstructionPayload(BaseModel):
    """11E: 画像生成指示のペイロード."""

    image_index: int = Field(..., description="画像インデックス")
    instruction: str = Field(..., description="画像生成指示")


class Step11ImageReviewPayload(BaseModel):
    """11F: 画像確認のペイロード."""

    image_index: int = Field(..., description="画像インデックス")
    accepted: bool = Field(..., description="画像を承認するか")
    retry: bool = Field(default=False, description="リトライするか")
    retry_instruction: str = Field(
        default="",
        description="リトライ時の追加指示",
    )


# =============================================================================
# 新規スキーマ（blog.System Ver8.3 対応）
# =============================================================================


class ImagePurpose(str, Enum):
    """画像の目的分類."""

    HERO = "hero"  # 記事冒頭のアイキャッチ
    ILLUSTRATION = "illustration"  # 概念・コンセプトの図解
    DATA_VIZ = "data_viz"  # データ可視化（グラフ、チャート）
    BREAK = "break"  # 視覚的な休憩ポイント
    CTA_SUPPORT = "cta_support"  # CTA支援（行動促進）
    PROCESS = "process"  # プロセス・手順の図解
    COMPARISON = "comparison"  # 比較・対比


class EnhancedImageInsertionPosition(BaseModel):
    """拡張画像挿入位置（blog.System Ver8.3）.

    通常のImageInsertionPositionに加え、分類カテゴリと推奨理由を含む。
    """

    article_number: int | None = Field(
        default=None,
        description="対象記事番号（1-4）。None の場合は全記事共通",
    )
    section_title: str = Field(..., description="挿入先のセクションタイトル")
    section_index: int = Field(..., description="セクションのインデックス（0始まり）")
    position: str = Field(
        default="after",
        pattern="^(before|after)$",
        description="セクションの前後どちらに挿入するか",
    )
    source_text: str = Field(
        default="",
        description="画像の元となるテキスト（該当セクションの要約）",
    )
    description: str = Field(
        default="",
        description="なぜこの位置に画像が必要かの説明",
    )
    # V2追加フィールド
    category: Literal["content_gap", "visual_break", "data_visualization"] = Field(
        default="content_gap",
        description="挿入位置のカテゴリ",
    )
    priority: int = Field(
        default=1,
        ge=1,
        le=5,
        description="優先度（1が最高）",
    )
    recommendation_reason: str = Field(
        default="",
        description="この位置を推奨する理由",
    )


class ImagePurposeClassification(BaseModel):
    """画像目的分類（blog.System Ver8.3）.

    各画像の目的と配置コンテキストを記録。
    """

    image_index: int = Field(..., description="画像インデックス")
    purpose: ImagePurpose = Field(
        default=ImagePurpose.ILLUSTRATION,
        description="画像の目的",
    )
    section_context: str = Field(
        default="",
        description="配置されるセクションのコンテキスト",
    )
    target_emotion: str = Field(
        default="",
        description="ターゲットとする読者の感情（Phase1-3対応）",
    )
    four_pillar_relevance: list[str] = Field(
        default_factory=list,
        description="関連する4本柱（neuroscience/behavioral_economics/llmo/kgi）",
    )


class PositionAnalysisEnhanced(BaseModel):
    """拡張位置分析結果（blog.System Ver8.3）.

    コンテンツギャップ、視覚的ブレーク、データ可視化の3カテゴリで分析。
    """

    content_gap_positions: list[EnhancedImageInsertionPosition] = Field(
        default_factory=list,
        description="コンテンツギャップ分析で特定された位置",
    )
    visual_break_positions: list[EnhancedImageInsertionPosition] = Field(
        default_factory=list,
        description="視覚的ブレーク推奨位置",
    )
    data_visualization_positions: list[EnhancedImageInsertionPosition] = Field(
        default_factory=list,
        description="データ可視化推奨位置",
    )
    total_recommended: int = Field(
        default=0,
        description="推奨位置の総数",
    )
    analysis_summary: str = Field(
        default="",
        description="分析サマリー",
    )


class Step11OutputV2(BaseModel):
    """Step11 拡張出力スキーマ（blog.System Ver8.3 対応）.

    既存フィールドを維持しつつ、新規フィールドを追加。
    新規フィールドはすべてオプショナルで後方互換性を確保。
    """

    # 既存フィールド（後方互換）
    step: str = "step11"
    enabled: bool = Field(..., description="画像生成を行ったか")
    image_count: int = Field(default=0, description="生成した画像数")
    images: list[GeneratedImage] = Field(
        default_factory=list,
        description="生成した画像リスト",
    )
    markdown_with_images: str = Field(
        default="",
        description="画像挿入後のMarkdownコンテンツ",
    )
    html_with_images: str = Field(
        default="",
        description="画像挿入後のHTMLコンテンツ",
    )
    model: str = Field(default="", description="使用したモデル")
    token_usage: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    # 新規フィールド（blog.System Ver8.3 対応）
    position_analysis_enhanced: PositionAnalysisEnhanced | None = Field(
        default=None,
        description="拡張位置分析結果",
    )
    image_purpose_classification: list[ImagePurposeClassification] | None = Field(
        default=None,
        description="画像目的分類リスト",
    )
