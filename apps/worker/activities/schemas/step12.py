"""Step12 WordPress HTML Generation schema.

Step12は最終記事と画像提案を元にWordPress用HTMLを生成する工程。
4記事分のHTMLを生成し、Gutenbergブロック形式で出力する。

入力:
- step0_output: キーワード情報
- step6_5_output: 構成案
- step10_output: 最終記事4本
- step11_output: 画像提案

出力:
- wordpress_html: 4記事分のWordPress用HTML
- output_path: storage上のパス
- output_digest: sha256ダイジェスト
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class YoastSeoMetadata(BaseModel):
    """Yoast SEO メタデータ."""

    focus_keyword: str = Field(default="", description="フォーカスキーワード")
    seo_title: str = Field(default="", description="SEOタイトル")
    meta_description: str = Field(default="", description="メタディスクリプション")
    readability_score: str = Field(
        default="ok",
        description="可読性スコア（good/ok/needs_improvement）",
    )
    seo_score: str = Field(
        default="ok",
        description="SEOスコア（good/ok/needs_improvement）",
    )


class StructuredDataBlocks(BaseModel):
    """構造化データブロック."""

    article_schema: str = Field(default="", description="Article JSON-LDブロック")
    faq_schema: str | None = Field(default=None, description="FAQ JSON-LDブロック")


class ArticleImage(BaseModel):
    """記事内の画像情報."""

    position: str = Field(default="", description="画像の挿入位置（セクション名）")
    alt_text: str = Field(default="", description="画像のalt属性")
    suggested_filename: str = Field(default="", description="推奨ファイル名")
    image_path: str = Field(default="", description="Storage上のパス")
    image_base64: str = Field(default="", description="Base64エンコード済み画像")


class ArticleMetadata(BaseModel):
    """記事のメタデータ."""

    title: str = Field(default="", description="記事タイトル")
    meta_description: str = Field(default="", description="メタディスクリプション")
    focus_keyword: str = Field(default="", description="フォーカスキーワード")
    word_count: int = Field(default=0, description="文字数")
    slug: str = Field(default="", description="URLスラッグ")
    categories: list[str] = Field(default_factory=list, description="カテゴリ")
    tags: list[str] = Field(default_factory=list, description="タグ")


class WordPressArticle(BaseModel):
    """WordPress用記事."""

    article_number: int = Field(..., ge=1, le=4, description="記事番号（1-4）")
    filename: str = Field(default="", description="ファイル名（article_1.html など）")
    html_content: str = Field(default="", description="HTML本文")
    gutenberg_blocks: str = Field(default="", description="Gutenbergブロック形式HTML")
    metadata: ArticleMetadata = Field(
        default_factory=ArticleMetadata,
        description="記事メタデータ",
    )
    images: list[ArticleImage] = Field(
        default_factory=list,
        description="記事内の画像リスト",
    )
    # blog.System 統合用フィールド（オプショナル）
    yoast_seo_metadata: YoastSeoMetadata | None = Field(
        default=None,
        description="Yoast SEO メタデータ",
    )
    gutenberg_block_types_used: list[str] = Field(
        default_factory=list,
        description="使用されたGutenbergブロックタイプ一覧",
    )
    structured_data_blocks: StructuredDataBlocks | None = Field(
        default=None,
        description="構造化データブロック",
    )


class CommonAssets(BaseModel):
    """共通アセット情報."""

    css_classes: list[str] = Field(
        default_factory=lambda: [
            "wp-block-paragraph",
            "wp-block-heading",
            "wp-block-image",
            "wp-block-list",
            "wp-block-quote",
        ],
        description="使用されているCSSクラス",
    )
    recommended_plugins: list[str] = Field(
        default_factory=lambda: [
            "Yoast SEO",
            "WP Super Cache",
        ],
        description="推奨プラグイン",
    )


class GenerationMetadata(BaseModel):
    """生成メタデータ."""

    generated_at: datetime | None = Field(
        default=None,
        description="生成日時（冪等性のため実行時に明示的に設定）",
    )
    model: str = Field(default="", description="使用したLLMモデル")
    wordpress_version_target: str = Field(
        default="6.0+",
        description="対象WordPressバージョン",
    )
    total_articles: int = Field(default=4, description="生成記事数")
    total_images: int = Field(default=0, description="総画像数")


class Step12Input(BaseModel):
    """Step12の入力."""

    step0_output: dict[str, Any] = Field(
        default_factory=dict,
        description="キーワード情報",
    )
    step6_5_output: dict[str, Any] = Field(
        default_factory=dict,
        description="構成案",
    )
    step10_output: dict[str, Any] = Field(
        default_factory=dict,
        description="最終記事4本",
    )
    step11_output: dict[str, Any] = Field(
        default_factory=dict,
        description="画像提案",
    )
    tenant_id: str = Field(..., description="テナントID")
    run_id: str = Field(..., description="実行ID")


class Step12Output(BaseModel):
    """Step12の出力."""

    step: str = "step12"
    articles: list[WordPressArticle] = Field(
        default_factory=list,
        description="4記事分のWordPress HTML",
    )
    common_assets: CommonAssets = Field(
        default_factory=CommonAssets,
        description="共通アセット情報",
    )
    generation_metadata: GenerationMetadata = Field(
        default_factory=GenerationMetadata,
        description="生成メタデータ",
    )
    output_path: str = Field(default="", description="Storage上のパス")
    output_digest: str = Field(default="", description="sha256ダイジェスト")
    warnings: list[str] = Field(default_factory=list, description="警告メッセージ")
    model: str = Field(default="", description="使用したモデル")
    usage: dict[str, Any] = Field(default_factory=dict, description="トークン使用量")
