"""Step10 Final Output schema.

工程10は最終記事出力を担当し、4つのバリエーション記事を生成する:
- メイン記事: 最も包括的で詳細な記事
- 初心者向け: 基礎から丁寧に説明
- 実践編: 具体的なアクションにフォーカス
- まとめ・比較: 要点を簡潔にまとめた記事
"""

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


class Step10Metadata(BaseModel):
    """Step10のメタデータ."""

    generated_at: datetime | None = Field(default=None, description="生成日時（Activity側で設定）")
    model: str = Field(default="", description="使用したLLMモデル")
    total_word_count: int = Field(default=0, description="全記事の合計文字数")
    generation_order: list[int] = Field(
        default_factory=lambda: [1, 2, 3, 4],
        description="生成順序",
    )


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
