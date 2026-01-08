"""Step10 Final Output schema.

工程10は最終記事出力を担当し、4つのバリエーション記事を生成する:
- メイン記事: 最も包括的で詳細な記事
- 初心者向け: 基礎から丁寧に説明
- 実践編: 具体的なアクションにフォーカス
- まとめ・比較: 要点を簡潔にまとめた記事

blog.System Ver8.3 対応:
- 構造化データ（JSON-LD: Article/FAQPage schema）
- 詳細公開チェックリスト（SEO/4本柱/技術）
- 文字数レポート（目標vs実績、セクション別内訳）
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArticleVariationType(str, Enum):
    """記事バリエーションタイプ."""

    MAIN = "メイン記事"
    BEGINNER = "初心者向け"
    PRACTICAL = "実践編"
    SUMMARY = "まとめ・比較"


# 各バリエーションの目標文字数
ARTICLE_WORD_COUNT_TARGETS: dict[ArticleVariationType, tuple[int, int]] = {
    ArticleVariationType.MAIN: (5000, 8000),
    ArticleVariationType.BEGINNER: (3000, 5000),
    ArticleVariationType.PRACTICAL: (4000, 6000),
    ArticleVariationType.SUMMARY: (2000, 3000),
}


class HTMLValidationResult(BaseModel):
    """HTML検証結果."""

    is_valid: bool
    has_required_tags: bool = False
    has_meta_tags: bool = False
    has_proper_heading_hierarchy: bool = False
    issues: list[str] = Field(default_factory=list)


class ArticleStats(BaseModel):
    """記事統計."""

    word_count: int
    char_count: int
    paragraph_count: int = 0
    sentence_count: int = 0
    heading_count: int = 0
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    list_count: int = 0
    link_count: int = 0
    image_count: int = 0


class PublicationReadiness(BaseModel):
    """出版準備状態."""

    is_ready: bool
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ArticleVariation(BaseModel):
    """個別の記事バリエーション."""

    article_number: int = Field(..., ge=1, le=4, description="記事番号（1-4）")
    variation_type: ArticleVariationType = Field(..., description="バリエーションタイプ")
    title: str = Field(..., description="記事タイトル")
    content: str = Field(..., description="記事本文（Markdown）")
    html_content: str = Field(default="", description="HTML変換後のコンテンツ")
    word_count: int = Field(default=0, description="文字数")
    target_audience: str = Field(default="", description="ターゲット読者層")
    sections: list[str] = Field(default_factory=list, description="セクション見出しリスト")
    stats: ArticleStats | None = Field(default=None, description="記事統計")
    html_validation: HTMLValidationResult | None = Field(default=None, description="HTML検証結果")
    meta_description: str = Field(default="", description="メタディスクリプション")
    output_path: str = Field(default="", description="個別記事の保存パス")
    output_digest: str = Field(default="", description="個別記事のダイジェスト")

    # === blog.System Ver8.3: 記事別拡張フィールド ===
    structured_data: StructuredData | None = Field(
        default=None,
        description="構造化データ（JSON-LD: Article/FAQPage schema）",
    )
    publication_checklist_detailed: PublicationChecklistDetailed | None = Field(
        default=None,
        description="詳細公開チェックリスト（SEO/4本柱/技術）",
    )
    word_count_report: WordCountReport | None = Field(
        default=None,
        description="文字数レポート（目標vs実績、セクション別内訳）",
    )


class Step10Metadata(BaseModel):
    """Step10のメタデータ."""

    generated_at: datetime | None = Field(default=None, description="生成日時（Activity側で設定）")
    model: str = Field(default="", description="使用したLLMモデル")
    total_word_count: int = Field(default=0, description="全記事の合計文字数")
    generation_order: list[int] = Field(
        default_factory=lambda: [1, 2, 3, 4],
        description="生成順序",
    )


# =============================================================================
# blog.System Ver8.3 対応スキーマ
# =============================================================================


class StructuredData(BaseModel):
    """構造化データ（JSON-LD）.

    Google検索結果でのリッチスニペット表示に対応。
    """

    json_ld: dict[str, Any] = Field(
        default_factory=dict,
        description="Article schema（JSON-LD形式）",
    )
    faq_schema: dict[str, Any] | None = Field(
        default=None,
        description="FAQPage schema（FAQがある場合）",
    )


class SEOChecklist(BaseModel):
    """SEOチェックリスト."""

    title_optimized: bool = Field(default=False, description="タイトルが最適化されているか")
    meta_description_present: bool = Field(default=False, description="メタディスクリプションが存在するか")
    headings_hierarchy_valid: bool = Field(default=False, description="見出し階層が正しいか")
    internal_links_present: bool = Field(default=False, description="内部リンクが存在するか")
    keyword_density_appropriate: bool = Field(default=False, description="キーワード密度が適切か")


class FourPillarsChecklist(BaseModel):
    """4本柱チェックリスト.

    blog.System Ver8.3 の4本柱（神経科学/行動経済学/LLMO/KGI）が
    適切に適用されているかを確認。
    """

    neuroscience_applied: bool = Field(default=False, description="神経科学原則が適用されているか")
    behavioral_economics_applied: bool = Field(default=False, description="行動経済学原則が適用されているか")
    llmo_optimized: bool = Field(default=False, description="LLMO最適化されているか")
    kgi_cta_placed: bool = Field(default=False, description="KGI達成のためのCTAが配置されているか")


class TechnicalChecklist(BaseModel):
    """技術チェックリスト."""

    html_valid: bool = Field(default=False, description="HTMLが有効か")
    images_have_alt: bool = Field(default=False, description="画像にalt属性があるか")
    links_valid: bool = Field(default=False, description="リンクが有効か")


class PublicationChecklistDetailed(BaseModel):
    """詳細公開チェックリスト.

    blog.System Ver8.3 対応の詳細チェックリスト。
    SEO、4本柱、技術の3観点でチェック。
    """

    seo_checklist: SEOChecklist = Field(
        default_factory=SEOChecklist,
        description="SEOチェックリスト",
    )
    four_pillars_checklist: FourPillarsChecklist = Field(
        default_factory=FourPillarsChecklist,
        description="4本柱チェックリスト",
    )
    technical_checklist: TechnicalChecklist = Field(
        default_factory=TechnicalChecklist,
        description="技術チェックリスト",
    )

    def all_passed(self) -> bool:
        """全てのチェックが通過したか."""
        seo = self.seo_checklist
        fp = self.four_pillars_checklist
        tech = self.technical_checklist

        return all(
            [
                seo.title_optimized,
                seo.meta_description_present,
                seo.headings_hierarchy_valid,
                fp.neuroscience_applied,
                fp.behavioral_economics_applied,
                fp.llmo_optimized,
                fp.kgi_cta_placed,
                tech.html_valid,
            ]
        )

    def get_failed_items(self) -> list[str]:
        """失敗したチェック項目を取得."""
        failed = []

        seo = self.seo_checklist
        if not seo.title_optimized:
            failed.append("SEO: タイトル最適化")
        if not seo.meta_description_present:
            failed.append("SEO: メタディスクリプション")
        if not seo.headings_hierarchy_valid:
            failed.append("SEO: 見出し階層")
        if not seo.internal_links_present:
            failed.append("SEO: 内部リンク")
        if not seo.keyword_density_appropriate:
            failed.append("SEO: キーワード密度")

        fp = self.four_pillars_checklist
        if not fp.neuroscience_applied:
            failed.append("4本柱: 神経科学")
        if not fp.behavioral_economics_applied:
            failed.append("4本柱: 行動経済学")
        if not fp.llmo_optimized:
            failed.append("4本柱: LLMO")
        if not fp.kgi_cta_placed:
            failed.append("4本柱: KGI/CTA")

        tech = self.technical_checklist
        if not tech.html_valid:
            failed.append("技術: HTML検証")
        if not tech.images_have_alt:
            failed.append("技術: 画像alt属性")
        if not tech.links_valid:
            failed.append("技術: リンク検証")

        return failed


class SectionWordCount(BaseModel):
    """セクション別文字数."""

    section_title: str = Field(..., description="セクションタイトル")
    target: int = Field(default=0, ge=0, description="目標文字数")
    achieved: int = Field(default=0, ge=0, description="実績文字数")
    variance: int = Field(default=0, description="差分（実績-目標）")
    status: str = Field(default="unknown", description="状態（on_target/over/under）")


class WordCountReport(BaseModel):
    """文字数レポート.

    blog.System Ver8.3 対応の文字数達成状況レポート。
    """

    target: int = Field(default=0, ge=0, description="目標文字数")
    achieved: int = Field(default=0, ge=0, description="実績文字数")
    variance: int = Field(default=0, description="差分（実績-目標）")
    status: str = Field(
        default="unknown",
        description="状態（on_target: ±5%, over: +5%超, under: -5%超）",
    )
    section_breakdown: list[SectionWordCount] = Field(
        default_factory=list,
        description="セクション別内訳",
    )

    def calculate_status(self) -> str:
        """状態を計算."""
        if self.target == 0:
            return "unknown"

        variance_percent = (self.variance / self.target) * 100

        if -5 <= variance_percent <= 5:
            return "on_target"
        elif variance_percent > 5:
            return "over"
        else:
            return "under"


class Step10Output(BaseModel):
    """Step10 の構造化出力.

    4記事対応版。後方互換性のため、単一記事フィールドも保持。
    """

    step: str = "step10"
    keyword: str

    # === 新規: 4記事出力 ===
    articles: list[ArticleVariation] = Field(
        default_factory=list,
        description="4つのバリエーション記事",
    )
    metadata: Step10Metadata = Field(
        default_factory=Step10Metadata,
        description="生成メタデータ",
    )

    # === 後方互換性: 単一記事フィールド（メイン記事を参照） ===
    article_title: str = ""
    markdown_content: str = ""
    html_content: str = ""
    meta_description: str = ""
    publication_checklist: str = ""
    html_validation: HTMLValidationResult | None = None
    stats: ArticleStats | None = None
    publication_readiness: PublicationReadiness | None = None

    # === 共通フィールド ===
    model: str = ""
    usage: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    output_path: str = Field(default="", description="統合出力ファイルのパス")
    output_digest: str = Field(default="", description="統合出力のダイジェスト")

    # === blog.System Ver8.3: 全体サマリー ===
    total_word_count_report: WordCountReport | None = Field(
        default=None,
        description="全記事の合計文字数レポート",
    )
    overall_publication_checklist: PublicationChecklistDetailed | None = Field(
        default=None,
        description="全体の公開準備チェックリスト（全記事の統合）",
    )

    def get_main_article(self) -> ArticleVariation | None:
        """メイン記事を取得."""
        for article in self.articles:
            if article.variation_type == ArticleVariationType.MAIN:
                return article
        return self.articles[0] if self.articles else None

    def get_article_by_number(self, number: int) -> ArticleVariation | None:
        """記事番号で記事を取得."""
        for article in self.articles:
            if article.article_number == number:
                return article
        return None

    def populate_legacy_fields(self) -> None:
        """後方互換性のため、メイン記事から単一記事フィールドを埋める."""
        main_article = self.get_main_article()
        if main_article:
            self.article_title = main_article.title
            self.markdown_content = main_article.content
            self.html_content = main_article.html_content
            self.meta_description = main_article.meta_description
            self.stats = main_article.stats
            self.html_validation = main_article.html_validation
