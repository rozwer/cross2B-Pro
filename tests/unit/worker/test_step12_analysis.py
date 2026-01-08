"""Unit tests for Step12 blog.System integration features."""

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.worker.activities.schemas.step12 import (
    StructuredDataBlocks,
    WordPressArticle,
    YoastSeoMetadata,
)
from apps.worker.activities.step12 import Step12WordPressHtmlGeneration


class TestYoastSeoMetadata:
    """Tests for YoastSeoMetadata schema."""

    def test_valid_metadata(self):
        """Test valid Yoast SEO metadata creation."""
        metadata = YoastSeoMetadata(
            focus_keyword="テストキーワード",
            seo_title="SEOタイトル",
            meta_description="メタディスクリプション",
            readability_score="good",
            seo_score="good",
        )
        assert metadata.focus_keyword == "テストキーワード"
        assert metadata.seo_title == "SEOタイトル"
        assert metadata.readability_score == "good"
        assert metadata.seo_score == "good"

    def test_default_values(self):
        """Test default values."""
        metadata = YoastSeoMetadata()
        assert metadata.focus_keyword == ""
        assert metadata.seo_title == ""
        assert metadata.readability_score == "ok"
        assert metadata.seo_score == "ok"


class TestStructuredDataBlocks:
    """Tests for StructuredDataBlocks schema."""

    def test_valid_blocks(self):
        """Test valid structured data blocks creation."""
        blocks = StructuredDataBlocks(
            article_schema='{"@type": "Article"}',
            faq_schema='{"@type": "FAQPage"}',
        )
        assert blocks.article_schema == '{"@type": "Article"}'
        assert blocks.faq_schema == '{"@type": "FAQPage"}'

    def test_default_values(self):
        """Test default values."""
        blocks = StructuredDataBlocks()
        assert blocks.article_schema == ""
        assert blocks.faq_schema is None


class TestWordPressArticleWithBlogSystem:
    """Tests for WordPressArticle with blog.System fields."""

    def test_article_with_blog_system_fields(self):
        """Test WordPressArticle with all blog.System fields."""
        article = WordPressArticle(
            article_number=1,
            filename="article_1.html",
            html_content="<p>Test</p>",
            yoast_seo_metadata=YoastSeoMetadata(
                focus_keyword="テスト",
                seo_score="good",
            ),
            gutenberg_block_types_used=["paragraph", "heading"],
            structured_data_blocks=StructuredDataBlocks(
                article_schema='{"@type": "Article"}',
            ),
        )
        assert article.yoast_seo_metadata is not None
        assert article.yoast_seo_metadata.focus_keyword == "テスト"
        assert article.gutenberg_block_types_used == ["paragraph", "heading"]
        assert article.structured_data_blocks is not None

    def test_article_without_blog_system_fields(self):
        """Test WordPressArticle without blog.System fields (backward compatibility)."""
        article = WordPressArticle(article_number=1)
        assert article.yoast_seo_metadata is None
        assert article.gutenberg_block_types_used == []
        assert article.structured_data_blocks is None


class TestGenerateYoastMetadata:
    """Tests for _generate_yoast_metadata method."""

    @pytest.fixture
    def activity(self):
        """Create Step12WordPressHtmlGeneration instance with mocked dependencies."""
        with patch("apps.worker.activities.step12.BaseActivity.__init__", return_value=None):
            step = Step12WordPressHtmlGeneration()
            step.store = MagicMock()
            return step

    def test_basic_metadata_generation(self, activity):
        """Test basic Yoast metadata generation."""
        result = activity._generate_yoast_metadata(
            title="テスト記事タイトル - SEO最適化のポイント",
            meta_description="この記事ではSEO最適化の重要なポイントについて詳しく解説します。初心者でもわかりやすい内容です。",
            keyword="SEO最適化",
            content="SEO最適化は重要です。" * 50,
        )

        assert result.focus_keyword == "SEO最適化"
        assert result.seo_title == "テスト記事タイトル - SEO最適化のポイント"
        assert len(result.meta_description) <= 155

    def test_long_title_truncation(self, activity):
        """Test SEO title truncation for long titles."""
        long_title = "A" * 100
        result = activity._generate_yoast_metadata(
            title=long_title,
            meta_description="Description",
            keyword="keyword",
            content="Content",
        )
        assert len(result.seo_title) == 60

    def test_long_description_truncation(self, activity):
        """Test meta description truncation."""
        long_description = "A" * 200
        result = activity._generate_yoast_metadata(
            title="Title",
            meta_description=long_description,
            keyword="keyword",
            content="Content",
        )
        assert len(result.meta_description) == 155
        assert result.meta_description.endswith("...")


class TestCalculateReadabilityScore:
    """Tests for _calculate_readability_score method."""

    @pytest.fixture
    def activity(self):
        """Create Step12WordPressHtmlGeneration instance with mocked dependencies."""
        with patch("apps.worker.activities.step12.BaseActivity.__init__", return_value=None):
            step = Step12WordPressHtmlGeneration()
            step.store = MagicMock()
            return step

    def test_good_readability(self, activity):
        """Test good readability score."""
        # 適度な長さの文章 + 見出し
        content = (
            """
<h2>はじめに</h2>
これは適度な長さの文章です。読みやすさを意識して書いています。
短すぎず長すぎない文章が理想的です。

<h2>詳細</h2>
さらに詳しい内容をここで説明します。見出しを使って構造化しています。
読者が理解しやすいように工夫しています。
"""
            * 10
        )  # 約2000文字

        result = activity._calculate_readability_score(content)
        # 見出しがあり、文が適度な長さなら良いスコア
        assert result in ["good", "ok"]

    def test_empty_content(self, activity):
        """Test empty content returns needs_improvement."""
        result = activity._calculate_readability_score("")
        assert result == "needs_improvement"

    def test_no_sentences(self, activity):
        """Test content without sentence breaks."""
        content = "これは句点のない文章です"
        result = activity._calculate_readability_score(content)
        assert result == "needs_improvement"


class TestCalculateSeoScore:
    """Tests for _calculate_seo_score method."""

    @pytest.fixture
    def activity(self):
        """Create Step12WordPressHtmlGeneration instance with mocked dependencies."""
        with patch("apps.worker.activities.step12.BaseActivity.__init__", return_value=None):
            step = Step12WordPressHtmlGeneration()
            step.store = MagicMock()
            return step

    def test_good_seo_score(self, activity):
        """Test good SEO score with all criteria met."""
        # キーワード密度0.5-2.5%を満たすコンテンツを作成
        # 500文字中にキーワード(5文字)が2回 → 10/500*100 = 2.0%
        base_content = "これは記事の本文です。ウェブサイトの改善は重要です。多くの企業が取り組んでいます。" * 10  # 約400文字
        content_with_keyword = f"SEO最適化について解説します。{base_content}さらにSEO最適化のポイントも重要です。"

        # タイトル: 30-70文字が理想（39文字）
        title = "SEO最適化の完全ガイド - 初心者でもわかりやすく解説します【2025年版】"
        # メタディスクリプション: 80-160文字が理想
        meta_description = (
            "SEO最適化について詳しく解説します。初心者でもわかりやすい内容で、"
            "実践的なテクニックを紹介しています。今日から始められる方法を詳しくお伝えしています。"
            "ぜひご覧ください。"
        )

        result = activity._calculate_seo_score(
            title=title,
            meta_description=meta_description,
            keyword="SEO最適化",
            content=content_with_keyword,
        )
        assert result == "good"

    def test_no_keyword(self, activity):
        """Test score with no keyword."""
        result = activity._calculate_seo_score(
            title="タイトル",
            meta_description="説明",
            keyword="",
            content="本文",
        )
        assert result == "needs_improvement"

    def test_keyword_not_in_title(self, activity):
        """Test score when keyword is not in title."""
        result = activity._calculate_seo_score(
            title="まったく関係ないタイトル",
            meta_description="SEO最適化の説明です。詳しく解説しています。初心者でもわかりやすいように書いています。",
            keyword="SEO最適化",
            content="SEO最適化の本文です。" * 50,
        )
        # キーワードがタイトルにない分スコアが下がる
        assert result in ["ok", "needs_improvement"]


class TestGenerateStructuredData:
    """Tests for _generate_structured_data method."""

    @pytest.fixture
    def activity(self):
        """Create Step12WordPressHtmlGeneration instance with mocked dependencies."""
        with patch("apps.worker.activities.step12.BaseActivity.__init__", return_value=None):
            step = Step12WordPressHtmlGeneration()
            step.store = MagicMock()
            return step

    def test_article_schema_generation(self, activity):
        """Test Article schema JSON-LD generation."""
        result = activity._generate_structured_data(
            title="テスト記事",
            meta_description="テスト説明",
            keyword="テスト",
            content="本文内容です。",
            article_number=1,
        )

        assert result.article_schema != ""
        schema = json.loads(result.article_schema)
        assert schema["@type"] == "Article"
        assert schema["headline"] == "テスト記事"
        assert schema["description"] == "テスト説明"
        assert result.faq_schema is None

    def test_faq_schema_generation(self, activity):
        """Test FAQ schema JSON-LD generation."""
        faq_data = [
            {"question": "質問1とは？", "answer": "回答1です。"},
            {"question": "質問2について", "answer": "回答2です。"},
        ]
        result = activity._generate_structured_data(
            title="テスト記事",
            meta_description="テスト説明",
            keyword="テスト",
            content="本文",
            article_number=1,
            faq_data=faq_data,
        )

        assert result.faq_schema is not None
        faq_schema = json.loads(result.faq_schema)
        assert faq_schema["@type"] == "FAQPage"
        assert len(faq_schema["mainEntity"]) == 2

    def test_empty_faq_data(self, activity):
        """Test with empty FAQ data."""
        result = activity._generate_structured_data(
            title="テスト記事",
            meta_description="テスト説明",
            keyword="テスト",
            content="本文",
            article_number=1,
            faq_data=[],
        )
        assert result.faq_schema is None

    def test_partial_faq_data(self, activity):
        """Test with FAQ data missing question or answer."""
        faq_data = [
            {"question": "有効な質問", "answer": "有効な回答"},
            {"question": "", "answer": "回答のみ"},  # 質問なし
            {"question": "質問のみ", "answer": ""},  # 回答なし
        ]
        result = activity._generate_structured_data(
            title="テスト記事",
            meta_description="テスト説明",
            keyword="テスト",
            content="本文",
            article_number=1,
            faq_data=faq_data,
        )

        assert result.faq_schema is not None
        faq_schema = json.loads(result.faq_schema)
        # 有効なFAQのみ含まれる
        assert len(faq_schema["mainEntity"]) == 1


class TestCollectGutenbergBlockTypes:
    """Tests for _collect_gutenberg_block_types method."""

    @pytest.fixture
    def activity(self):
        """Create Step12WordPressHtmlGeneration instance with mocked dependencies."""
        with patch("apps.worker.activities.step12.BaseActivity.__init__", return_value=None):
            step = Step12WordPressHtmlGeneration()
            step.store = MagicMock()
            return step

    def test_collect_block_types(self, activity):
        """Test collecting various Gutenberg block types."""
        gutenberg_html = """
<!-- wp:heading -->
<h2>見出し</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>段落テキスト</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul><li>リスト項目</li></ul>
<!-- /wp:list -->

<!-- wp:image -->
<figure class="wp-block-image"><img src="test.jpg"/></figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>もう一つの段落</p>
<!-- /wp:paragraph -->
"""
        result = activity._collect_gutenberg_block_types(gutenberg_html)

        assert "heading" in result
        assert "paragraph" in result
        assert "list" in result
        assert "image" in result
        # 重複は除去される
        assert result.count("paragraph") == 1
        # ソートされている
        assert result == sorted(result)

    def test_empty_html(self, activity):
        """Test with empty HTML."""
        result = activity._collect_gutenberg_block_types("")
        assert result == []

    def test_no_gutenberg_blocks(self, activity):
        """Test with plain HTML without Gutenberg blocks."""
        html = "<p>普通のHTML</p><h2>見出し</h2>"
        result = activity._collect_gutenberg_block_types(html)
        assert result == []

    def test_block_with_attributes(self, activity):
        """Test collecting blocks with JSON attributes."""
        gutenberg_html = """
<!-- wp:heading {"level":3} -->
<h3>見出し3</h3>
<!-- /wp:heading -->

<!-- wp:list {"ordered":true} -->
<ol><li>番号付きリスト</li></ol>
<!-- /wp:list -->
"""
        result = activity._collect_gutenberg_block_types(gutenberg_html)
        assert "heading" in result
        assert "list" in result
