"""Step12 WordPress HTML Generation Tests.

Tests for Step12 WordPress HTML generation:
- Schema validation (Step12Input, Step12Output)
- Gutenberg block conversion
- WordPress article generation
- API router functionality
"""

import pytest

from apps.worker.activities.schemas.step12 import (
    ArticleImage,
    ArticleMetadata,
    CommonAssets,
    GenerationMetadata,
    Step12Input,
    Step12Output,
    WordPressArticle,
)


class TestArticleMetadata:
    """Test ArticleMetadata model."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        metadata = ArticleMetadata()
        assert metadata.title == ""
        assert metadata.meta_description == ""
        assert metadata.focus_keyword == ""
        assert metadata.word_count == 0
        assert metadata.slug == ""
        assert metadata.categories == []
        assert metadata.tags == []

    def test_with_values(self) -> None:
        """Should accept valid values."""
        metadata = ArticleMetadata(
            title="SEO対策ガイド",
            meta_description="SEO対策の完全ガイド",
            focus_keyword="SEO対策",
            word_count=5000,
            slug="seo-guide",
            categories=["SEO", "マーケティング"],
            tags=["SEO", "検索エンジン"],
        )
        assert metadata.title == "SEO対策ガイド"
        assert metadata.word_count == 5000
        assert len(metadata.categories) == 2
        assert len(metadata.tags) == 2


class TestArticleImage:
    """Test ArticleImage model."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        image = ArticleImage()
        assert image.position == ""
        assert image.alt_text == ""
        assert image.suggested_filename == ""
        assert image.image_path == ""
        assert image.image_base64 == ""

    def test_with_values(self) -> None:
        """Should accept valid values."""
        image = ArticleImage(
            position="はじめに",
            alt_text="SEO対策のイメージ",
            suggested_filename="seo_intro.png",
            image_path="tenants/t1/runs/r1/step11/images/image_0.png",
        )
        assert image.position == "はじめに"
        assert image.alt_text == "SEO対策のイメージ"


class TestWordPressArticle:
    """Test WordPressArticle model."""

    def test_valid_article_number(self) -> None:
        """Article number should be 1-4."""
        for num in [1, 2, 3, 4]:
            article = WordPressArticle(article_number=num)
            assert article.article_number == num

    def test_invalid_article_number_zero(self) -> None:
        """Article number 0 should be invalid."""
        with pytest.raises(ValueError):
            WordPressArticle(article_number=0)

    def test_invalid_article_number_five(self) -> None:
        """Article number 5 should be invalid."""
        with pytest.raises(ValueError):
            WordPressArticle(article_number=5)

    def test_full_article(self) -> None:
        """Full article with all fields should work."""
        article = WordPressArticle(
            article_number=1,
            filename="article_1.html",
            html_content="<h1>Title</h1><p>Content</p>",
            gutenberg_blocks='<!-- wp:heading {"level":1} -->\n<h1>Title</h1>\n<!-- /wp:heading -->',
            metadata=ArticleMetadata(title="Title", word_count=100),
            images=[ArticleImage(position="intro", alt_text="Image")],
        )
        assert article.article_number == 1
        assert article.filename == "article_1.html"
        assert "wp:heading" in article.gutenberg_blocks
        assert article.metadata.title == "Title"
        assert len(article.images) == 1


class TestCommonAssets:
    """Test CommonAssets model."""

    def test_default_css_classes(self) -> None:
        """Default CSS classes should be defined."""
        assets = CommonAssets()
        assert "wp-block-paragraph" in assets.css_classes
        assert "wp-block-heading" in assets.css_classes
        assert "wp-block-image" in assets.css_classes
        assert "wp-block-list" in assets.css_classes

    def test_default_plugins(self) -> None:
        """Default plugins should be defined."""
        assets = CommonAssets()
        assert "Yoast SEO" in assets.recommended_plugins


class TestGenerationMetadata:
    """Test GenerationMetadata model."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        metadata = GenerationMetadata()
        assert metadata.wordpress_version_target == "6.0+"
        assert metadata.total_articles == 4
        assert metadata.total_images == 0
        assert metadata.model == ""
        assert metadata.generated_at is None  # 冪等性のためNone

    def test_with_values(self) -> None:
        """Should accept valid values."""
        from datetime import datetime

        now = datetime.now()
        metadata = GenerationMetadata(
            generated_at=now,
            model="claude-3-5-sonnet",
            total_articles=4,
            total_images=8,
        )
        assert metadata.generated_at == now
        assert metadata.model == "claude-3-5-sonnet"
        assert metadata.total_articles == 4
        assert metadata.total_images == 8


class TestStep12Input:
    """Test Step12Input model."""

    def test_required_fields(self) -> None:
        """Required fields should be enforced."""
        with pytest.raises(ValueError):
            Step12Input()  # Missing tenant_id and run_id

    def test_valid_input(self) -> None:
        """Valid input should work."""
        input_data = Step12Input(
            tenant_id="tenant-1",
            run_id="run-1",
            step0_output={"keyword": "SEO対策"},
            step10_output={"articles": []},
        )
        assert input_data.tenant_id == "tenant-1"
        assert input_data.run_id == "run-1"


class TestStep12Output:
    """Test Step12Output model."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        output = Step12Output()
        assert output.step == "step12"
        assert output.articles == []
        assert output.output_path == ""
        assert output.output_digest == ""
        assert output.warnings == []

    def test_with_articles(self) -> None:
        """Output with articles should work."""
        output = Step12Output(
            articles=[
                WordPressArticle(
                    article_number=1,
                    filename="article_1.html",
                    gutenberg_blocks="<p>Content</p>",
                ),
                WordPressArticle(
                    article_number=2,
                    filename="article_2.html",
                    gutenberg_blocks="<p>Content 2</p>",
                ),
            ],
            output_path="tenants/t1/runs/r1/step12/output.json",
        )
        assert len(output.articles) == 2
        assert output.output_path.endswith("output.json")


class TestGutenbergConversion:
    """Test Gutenberg block conversion logic."""

    def test_heading_conversion(self) -> None:
        """Headings should be wrapped in wp:heading blocks."""
        from apps.worker.graphs.post_approval import _convert_to_gutenberg

        html = "<h1>Title</h1>\n<h2>Section</h2>\n<h3>Subsection</h3>"
        result = _convert_to_gutenberg(html)

        assert '<!-- wp:heading {"level":1} -->' in result
        assert "<!-- wp:heading -->" in result  # h2 default
        assert '<!-- wp:heading {"level":3} -->' in result
        assert "<!-- /wp:heading -->" in result

    def test_paragraph_conversion(self) -> None:
        """Paragraphs should be wrapped in wp:paragraph blocks."""
        from apps.worker.graphs.post_approval import _convert_to_gutenberg

        html = "<p>This is a paragraph.</p>"
        result = _convert_to_gutenberg(html)

        assert "<!-- wp:paragraph -->" in result
        assert "<!-- /wp:paragraph -->" in result
        assert "<p>This is a paragraph.</p>" in result

    def test_list_conversion(self) -> None:
        """Lists should be wrapped in wp:list blocks."""
        from apps.worker.graphs.post_approval import _convert_to_gutenberg

        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = _convert_to_gutenberg(html)

        assert "<!-- wp:list -->" in result
        assert "<!-- /wp:list -->" in result

    def test_ordered_list_conversion(self) -> None:
        """Ordered lists should have ordered attribute."""
        from apps.worker.graphs.post_approval import _convert_to_gutenberg

        html = "<ol><li>First</li><li>Second</li></ol>"
        result = _convert_to_gutenberg(html)

        assert '<!-- wp:list {"ordered":true} -->' in result

    def test_image_conversion(self) -> None:
        """Images should be wrapped in wp:image blocks with figure."""
        from apps.worker.graphs.post_approval import _convert_to_gutenberg

        html = '<img src="test.png" alt="Test">'
        result = _convert_to_gutenberg(html)

        assert "<!-- wp:image -->" in result
        assert "<!-- /wp:image -->" in result
        assert 'class="wp-block-image"' in result

    def test_empty_lines_handled(self) -> None:
        """Empty lines should be skipped."""
        from apps.worker.graphs.post_approval import _convert_to_gutenberg

        html = "<p>Line 1</p>\n\n\n<p>Line 2</p>"
        result = _convert_to_gutenberg(html)

        # Count wp:paragraph occurrences - empty lines should not create extra blocks
        para_count = result.count("<!-- wp:paragraph -->")
        assert para_count == 2


class TestStep12APIRouter:
    """Test Step12 API router helper functions."""

    def test_markdown_to_html_headings(self) -> None:
        """Markdown headings should convert to HTML."""
        from apps.api.routers.step12 import _markdown_to_html

        md = "# H1\n## H2\n### H3"
        html = _markdown_to_html(md)

        assert "<h1>H1</h1>" in html
        assert "<h2>H2</h2>" in html
        assert "<h3>H3</h3>" in html

    def test_markdown_to_html_emphasis(self) -> None:
        """Markdown emphasis should convert to HTML."""
        from apps.api.routers.step12 import _markdown_to_html

        md = "**bold** and *italic*"
        html = _markdown_to_html(md)

        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html

    def test_markdown_to_html_links(self) -> None:
        """Markdown links should convert to HTML."""
        from apps.api.routers.step12 import _markdown_to_html

        md = "[Google](https://google.com)"
        html = _markdown_to_html(md)

        assert '<a href="https://google.com">Google</a>' in html

    def test_convert_to_gutenberg_integration(self) -> None:
        """Full conversion pipeline should work."""
        from apps.api.routers.step12 import _convert_to_gutenberg, _markdown_to_html

        md = "# Title\n\nParagraph text.\n\n## Section\n\n- Item 1\n- Item 2"
        html = _markdown_to_html(md)
        gutenberg = _convert_to_gutenberg(html)

        assert "<!-- wp:heading" in gutenberg
        assert "<!-- wp:paragraph" in gutenberg or "<!-- wp:list" in gutenberg
