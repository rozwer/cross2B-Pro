"""Step 1 schema tests.

Tests for CompetitorPage backward compatibility and new fields.
"""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step1 import (
    CompetitorPage,
    FailedUrl,
    FetchStats,
    Step1Output,
)


class TestCompetitorPageBackwardCompatibility:
    """Test that existing data format still works."""

    def test_competitor_page_with_existing_fields_only(self):
        """既存データ形式でも動作することを確認."""
        old_data = {
            "url": "https://example.com",
            "title": "Example Title",
            "content": "Sample content for testing...",
            "word_count": 1000,
            "headings": ["Introduction", "Main Content", "Conclusion"],
            "fetched_at": "2025-01-01T00:00:00",
        }
        page = CompetitorPage(**old_data)

        assert page.url == "https://example.com"
        assert page.title == "Example Title"
        assert page.content == "Sample content for testing..."
        assert page.word_count == 1000
        assert page.headings == ["Introduction", "Main Content", "Conclusion"]
        assert page.fetched_at == "2025-01-01T00:00:00"
        # 新フィールドは None
        assert page.meta_description is None
        assert page.structured_data is None
        assert page.publish_date is None

    def test_competitor_page_minimal_fields(self):
        """最小限のフィールドで動作確認."""
        minimal_data = {
            "url": "https://example.com",
            "content": "Minimal content",
        }
        page = CompetitorPage(**minimal_data)

        assert page.url == "https://example.com"
        assert page.content == "Minimal content"
        assert page.title == ""  # default
        assert page.word_count == 0  # default
        assert page.headings == []  # default
        assert page.fetched_at == ""  # default


class TestCompetitorPageNewFields:
    """Test new blog.System fields."""

    def test_competitor_page_with_new_fields(self):
        """新フィールド付きデータの動作確認."""
        new_data = {
            "url": "https://example.com",
            "title": "Example Title",
            "content": "Sample content...",
            "word_count": 1000,
            "headings": ["H1"],
            "fetched_at": "2025-01-01T00:00:00",
            "meta_description": "This is a meta description for SEO",
            "structured_data": {
                "@type": "Article",
                "headline": "Example Title",
                "author": {"@type": "Person", "name": "Author"},
            },
            "publish_date": "2024-12-01",
        }
        page = CompetitorPage(**new_data)

        assert page.meta_description == "This is a meta description for SEO"
        assert page.structured_data["@type"] == "Article"
        assert page.structured_data["headline"] == "Example Title"
        assert page.publish_date == "2024-12-01"

    def test_competitor_page_partial_new_fields(self):
        """一部の新フィールドのみ設定."""
        partial_data = {
            "url": "https://example.com",
            "content": "Content...",
            "meta_description": "Has description",
            # structured_data と publish_date は None
        }
        page = CompetitorPage(**partial_data)

        assert page.meta_description == "Has description"
        assert page.structured_data is None
        assert page.publish_date is None

    def test_competitor_page_empty_structured_data(self):
        """空の structured_data."""
        data = {
            "url": "https://example.com",
            "content": "Content...",
            "structured_data": {},
        }
        page = CompetitorPage(**data)

        assert page.structured_data == {}

    def test_competitor_page_complex_structured_data(self):
        """複雑な JSON-LD structured_data."""
        data = {
            "url": "https://example.com",
            "content": "Content...",
            "structured_data": {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": "Test Article",
                "datePublished": "2024-12-01",
                "author": [
                    {"@type": "Person", "name": "Author 1"},
                    {"@type": "Person", "name": "Author 2"},
                ],
                "publisher": {
                    "@type": "Organization",
                    "name": "Publisher Inc",
                },
            },
        }
        page = CompetitorPage(**data)

        assert page.structured_data["@type"] == "Article"
        assert len(page.structured_data["author"]) == 2


class TestCompetitorPageSerialization:
    """Test serialization/deserialization."""

    def test_model_dump_includes_new_fields(self):
        """model_dump() に新フィールドが含まれる."""
        page = CompetitorPage(
            url="https://example.com",
            content="Content...",
            meta_description="Description",
        )
        dumped = page.model_dump()

        assert "meta_description" in dumped
        assert "structured_data" in dumped
        assert "publish_date" in dumped
        assert dumped["meta_description"] == "Description"
        assert dumped["structured_data"] is None

    def test_model_dump_excludes_none(self):
        """exclude_none=True で None フィールドを除外."""
        page = CompetitorPage(
            url="https://example.com",
            content="Content...",
        )
        dumped = page.model_dump(exclude_none=True)

        # None のフィールドは除外される
        assert "meta_description" not in dumped
        assert "structured_data" not in dumped
        assert "publish_date" not in dumped


class TestStep1Output:
    """Test Step1Output with new CompetitorPage fields."""

    def test_step1_output_with_new_fields(self):
        """Step1Output が新フィールド付き CompetitorPage を含む."""
        output = Step1Output(
            keyword="test keyword",
            competitors=[
                CompetitorPage(
                    url="https://example1.com",
                    content="Content 1",
                    meta_description="Desc 1",
                ),
                CompetitorPage(
                    url="https://example2.com",
                    content="Content 2",
                    structured_data={"@type": "Article"},
                ),
            ],
            fetch_stats=FetchStats(
                total_urls=2,
                successful=2,
                failed=0,
                success_rate=1.0,
            ),
        )

        assert len(output.competitors) == 2
        assert output.competitors[0].meta_description == "Desc 1"
        assert output.competitors[1].structured_data == {"@type": "Article"}

    def test_step1_output_backward_compatible(self):
        """既存形式の Step1Output が動作."""
        output = Step1Output(
            keyword="test",
            competitors=[CompetitorPage(url="https://example.com", content="Content")],
        )

        assert output.step == "step1"
        assert output.keyword == "test"
        assert len(output.competitors) == 1
        assert output.competitors[0].meta_description is None


class TestFetchStats:
    """FetchStats tests (unchanged from original)."""

    def test_fetch_stats_defaults(self):
        """デフォルト値の確認."""
        stats = FetchStats()
        assert stats.total_urls == 0
        assert stats.successful == 0
        assert stats.failed == 0
        assert stats.success_rate == 0.0

    def test_fetch_stats_success_rate_range(self):
        """success_rate の範囲チェック."""
        stats = FetchStats(success_rate=0.5)
        assert stats.success_rate == 0.5

        with pytest.raises(ValidationError):
            FetchStats(success_rate=1.5)  # > 1.0 is invalid

        with pytest.raises(ValidationError):
            FetchStats(success_rate=-0.1)  # < 0.0 is invalid


class TestFailedUrl:
    """FailedUrl tests (unchanged from original)."""

    def test_failed_url_creation(self):
        """FailedUrl の作成."""
        failed = FailedUrl(url="https://failed.com", error="timeout")
        assert failed.url == "https://failed.com"
        assert failed.error == "timeout"

    def test_failed_url_empty_error(self):
        """エラーメッセージなしの FailedUrl."""
        failed = FailedUrl(url="https://failed.com")
        assert failed.error == ""
