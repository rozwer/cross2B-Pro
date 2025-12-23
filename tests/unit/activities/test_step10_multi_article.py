"""Step10 Multi-Article Output Tests.

Tests for the 4-article variation output in Step10.
Verifies:
- ArticleVariation schema validation
- Step10Output with articles array
- Backward compatibility (legacy fields)
- Article differentiation (no excessive duplication)
- Word count targets per variation type
"""

import pytest

from apps.worker.activities.schemas.step10 import (
    ARTICLE_WORD_COUNT_TARGETS,
    ArticleStats,
    ArticleVariation,
    ArticleVariationType,
    HTMLValidationResult,
    Step10Metadata,
    Step10Output,
)


class TestArticleVariationType:
    """Test ArticleVariationType enum."""

    def test_variation_types_exist(self) -> None:
        """All 4 variation types should exist."""
        assert ArticleVariationType.MAIN.value == "メイン記事"
        assert ArticleVariationType.BEGINNER.value == "初心者向け"
        assert ArticleVariationType.PRACTICAL.value == "実践編"
        assert ArticleVariationType.SUMMARY.value == "まとめ・比較"

    def test_word_count_targets_defined(self) -> None:
        """Word count targets should be defined for all types."""
        assert len(ARTICLE_WORD_COUNT_TARGETS) == 4
        assert ArticleVariationType.MAIN in ARTICLE_WORD_COUNT_TARGETS
        assert ArticleVariationType.BEGINNER in ARTICLE_WORD_COUNT_TARGETS
        assert ArticleVariationType.PRACTICAL in ARTICLE_WORD_COUNT_TARGETS
        assert ArticleVariationType.SUMMARY in ARTICLE_WORD_COUNT_TARGETS

    def test_word_count_ranges_valid(self) -> None:
        """Word count ranges should be valid (min < max)."""
        for variation_type, (min_count, max_count) in ARTICLE_WORD_COUNT_TARGETS.items():
            assert min_count < max_count, f"{variation_type}: min should be < max"
            assert min_count > 0, f"{variation_type}: min should be > 0"


class TestArticleVariation:
    """Test ArticleVariation model."""

    def test_create_valid_article(self) -> None:
        """Valid article creation should work."""
        article = ArticleVariation(
            article_number=1,
            variation_type=ArticleVariationType.MAIN,
            title="SEO対策の完全ガイド",
            content="# SEO対策の完全ガイド\n\n## はじめに\n\nSEOとは...",
            word_count=5000,
        )

        assert article.article_number == 1
        assert article.variation_type == ArticleVariationType.MAIN
        assert article.title == "SEO対策の完全ガイド"
        assert article.word_count == 5000

    def test_article_number_validation(self) -> None:
        """Article number should be 1-4."""
        # Valid numbers
        for num in [1, 2, 3, 4]:
            article = ArticleVariation(
                article_number=num,
                variation_type=ArticleVariationType.MAIN,
                title="Test",
                content="Test content",
            )
            assert article.article_number == num

        # Invalid: 0
        with pytest.raises(ValueError):
            ArticleVariation(
                article_number=0,
                variation_type=ArticleVariationType.MAIN,
                title="Test",
                content="Test content",
            )

        # Invalid: 5
        with pytest.raises(ValueError):
            ArticleVariation(
                article_number=5,
                variation_type=ArticleVariationType.MAIN,
                title="Test",
                content="Test content",
            )

    def test_article_with_stats(self) -> None:
        """Article with stats should work."""
        stats = ArticleStats(
            word_count=5000,
            char_count=15000,
            paragraph_count=20,
            sentence_count=100,
            heading_count=10,
            h1_count=1,
            h2_count=5,
            h3_count=4,
        )

        article = ArticleVariation(
            article_number=1,
            variation_type=ArticleVariationType.MAIN,
            title="Test Article",
            content="# Test\n\nContent here.",
            word_count=5000,
            stats=stats,
        )

        assert article.stats is not None
        assert article.stats.word_count == 5000
        assert article.stats.h2_count == 5

    def test_article_with_html_validation(self) -> None:
        """Article with HTML validation should work."""
        html_validation = HTMLValidationResult(
            is_valid=True,
            has_required_tags=True,
            has_meta_tags=True,
            has_proper_heading_hierarchy=True,
        )

        article = ArticleVariation(
            article_number=1,
            variation_type=ArticleVariationType.MAIN,
            title="Test",
            content="Content",
            html_content="<html>...</html>",
            html_validation=html_validation,
        )

        assert article.html_validation is not None
        assert article.html_validation.is_valid is True


class TestStep10Output:
    """Test Step10Output model with 4 articles."""

    def _create_test_article(
        self,
        number: int,
        variation_type: ArticleVariationType,
    ) -> ArticleVariation:
        """Helper to create test articles."""
        return ArticleVariation(
            article_number=number,
            variation_type=variation_type,
            title=f"Test Article {number}",
            content=f"# Article {number}\n\nContent for {variation_type.value}",
            word_count=3000,
            target_audience="Test audience",
        )

    def test_create_output_with_4_articles(self) -> None:
        """Output with 4 articles should work."""
        articles = [
            self._create_test_article(1, ArticleVariationType.MAIN),
            self._create_test_article(2, ArticleVariationType.BEGINNER),
            self._create_test_article(3, ArticleVariationType.PRACTICAL),
            self._create_test_article(4, ArticleVariationType.SUMMARY),
        ]

        output = Step10Output(
            keyword="SEO対策",
            articles=articles,
        )

        assert len(output.articles) == 4
        assert output.keyword == "SEO対策"

    def test_get_main_article(self) -> None:
        """get_main_article should return MAIN type article."""
        articles = [
            self._create_test_article(2, ArticleVariationType.BEGINNER),
            self._create_test_article(1, ArticleVariationType.MAIN),
            self._create_test_article(3, ArticleVariationType.PRACTICAL),
        ]

        output = Step10Output(keyword="test", articles=articles)
        main = output.get_main_article()

        assert main is not None
        assert main.variation_type == ArticleVariationType.MAIN
        assert main.article_number == 1

    def test_get_main_article_fallback(self) -> None:
        """get_main_article should fallback to first article if no MAIN."""
        articles = [
            self._create_test_article(2, ArticleVariationType.BEGINNER),
            self._create_test_article(3, ArticleVariationType.PRACTICAL),
        ]

        output = Step10Output(keyword="test", articles=articles)
        main = output.get_main_article()

        assert main is not None
        assert main.article_number == 2  # First article

    def test_get_main_article_empty(self) -> None:
        """get_main_article should return None for empty articles."""
        output = Step10Output(keyword="test", articles=[])
        assert output.get_main_article() is None

    def test_get_article_by_number(self) -> None:
        """get_article_by_number should work correctly."""
        articles = [
            self._create_test_article(1, ArticleVariationType.MAIN),
            self._create_test_article(2, ArticleVariationType.BEGINNER),
            self._create_test_article(3, ArticleVariationType.PRACTICAL),
            self._create_test_article(4, ArticleVariationType.SUMMARY),
        ]

        output = Step10Output(keyword="test", articles=articles)

        assert output.get_article_by_number(1) is not None
        assert output.get_article_by_number(2) is not None
        assert output.get_article_by_number(3) is not None
        assert output.get_article_by_number(4) is not None
        assert output.get_article_by_number(5) is None  # Not found

    def test_populate_legacy_fields(self) -> None:
        """populate_legacy_fields should fill backward-compatible fields."""
        main_article = ArticleVariation(
            article_number=1,
            variation_type=ArticleVariationType.MAIN,
            title="Main Title",
            content="# Main Content",
            html_content="<html>Main HTML</html>",
            meta_description="Main description",
            word_count=5000,
            stats=ArticleStats(word_count=5000, char_count=15000),
            html_validation=HTMLValidationResult(is_valid=True),
        )

        output = Step10Output(
            keyword="test",
            articles=[main_article],
        )

        # Before populate
        assert output.markdown_content == ""
        assert output.html_content == ""

        # Populate
        output.populate_legacy_fields()

        # After populate
        assert output.article_title == "Main Title"
        assert output.markdown_content == "# Main Content"
        assert output.html_content == "<html>Main HTML</html>"
        assert output.meta_description == "Main description"
        assert output.stats is not None
        assert output.stats.word_count == 5000

    def test_metadata_fields(self) -> None:
        """Metadata fields should work correctly."""
        output = Step10Output(
            keyword="test",
            articles=[
                self._create_test_article(1, ArticleVariationType.MAIN),
            ],
            metadata=Step10Metadata(
                model="anthropic",
                total_word_count=12000,
                generation_order=[1, 2, 3, 4],
            ),
        )

        assert output.metadata.model == "anthropic"
        assert output.metadata.total_word_count == 12000
        assert output.metadata.generation_order == [1, 2, 3, 4]

    def test_output_serialization(self) -> None:
        """Output should serialize to dict correctly."""
        articles = [
            self._create_test_article(1, ArticleVariationType.MAIN),
        ]

        output = Step10Output(
            keyword="SEO",
            articles=articles,
            model="anthropic",
            warnings=["test_warning"],
        )

        data = output.model_dump()

        assert data["keyword"] == "SEO"
        assert len(data["articles"]) == 1
        assert data["articles"][0]["article_number"] == 1
        assert data["articles"][0]["variation_type"] == "メイン記事"
        assert data["model"] == "anthropic"
        assert "test_warning" in data["warnings"]


class TestArticleDifferentiation:
    """Test that articles are properly differentiated."""

    def test_each_variation_has_unique_target_audience(self) -> None:
        """Each variation type should have distinct target audience."""
        from apps.worker.activities.step10 import ARTICLE_VARIATIONS

        audiences = [v["target_audience"] for v in ARTICLE_VARIATIONS]
        # All audiences should be unique
        assert len(audiences) == len(set(audiences))

    def test_each_variation_has_description(self) -> None:
        """Each variation should have a description."""
        from apps.worker.activities.step10 import ARTICLE_VARIATIONS

        for variation in ARTICLE_VARIATIONS:
            assert "description" in variation
            assert len(variation["description"]) > 0

    def test_variation_order_matches_numbering(self) -> None:
        """Variation order should match article numbers."""
        from apps.worker.activities.step10 import ARTICLE_VARIATIONS

        for i, variation in enumerate(ARTICLE_VARIATIONS, start=1):
            assert variation["number"] == i


class TestBackwardCompatibility:
    """Test backward compatibility with single-article format."""

    def test_empty_articles_works(self) -> None:
        """Empty articles array should work (for legacy runs)."""
        output = Step10Output(
            keyword="test",
            articles=[],
            markdown_content="# Legacy Content",
            html_content="<html>Legacy</html>",
        )

        assert output.markdown_content == "# Legacy Content"
        assert output.html_content == "<html>Legacy</html>"

    def test_legacy_fields_accessible(self) -> None:
        """Legacy fields should still be accessible."""
        output = Step10Output(
            keyword="test",
            article_title="Legacy Title",
            markdown_content="# Legacy",
            html_content="<html>...</html>",
            meta_description="Legacy desc",
            publication_checklist="- Item 1",
        )

        assert output.article_title == "Legacy Title"
        assert output.markdown_content == "# Legacy"
        assert output.publication_checklist == "- Item 1"

    def test_mixed_new_and_legacy(self) -> None:
        """Both new articles and legacy fields should coexist."""
        article = ArticleVariation(
            article_number=1,
            variation_type=ArticleVariationType.MAIN,
            title="New Title",
            content="New Content",
        )

        output = Step10Output(
            keyword="test",
            articles=[article],
            # Legacy fields (before populate)
            article_title="Old Title",
            markdown_content="Old Content",
        )

        # Legacy fields are overridden by populate
        output.populate_legacy_fields()

        assert output.article_title == "New Title"
        assert output.markdown_content == "New Content"
