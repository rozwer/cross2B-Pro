"""Tests for Step6, Step6.5, Step7a schemas."""

import pytest

from apps.worker.activities.schemas.step6 import (
    EnhancedOutlineMetrics,
    EnhancedOutlineQuality,
    EnhancedSection,
    EnhancementSummary,
    Step6Output,
)
from apps.worker.activities.schemas.step6_5 import (
    InputSummary,
    PackageQuality,
    SectionBlueprint,
    Step6_5Output,
)
from apps.worker.activities.schemas.step7a import (
    DraftQuality,
    DraftQualityMetrics,
    DraftSection,
    GenerationStats,
    Step7aOutput,
)


class TestStep6Schemas:
    """Step6 スキーマのテスト."""

    def test_enhanced_section_creation(self) -> None:
        """EnhancedSection の作成."""
        section = EnhancedSection(
            level=2,
            title="テストセクション",
            enhanced_content="拡張コンテンツ",
            enhancement_type="detail",
        )
        assert section.level == 2
        assert section.title == "テストセクション"
        assert section.enhancement_type == "detail"

    def test_enhancement_summary_defaults(self) -> None:
        """EnhancementSummary のデフォルト値."""
        summary = EnhancementSummary()
        assert summary.sections_enhanced == 0
        assert summary.sections_added == 0
        assert summary.sources_integrated == 0
        assert summary.total_word_increase == 0

    def test_enhanced_outline_metrics(self) -> None:
        """EnhancedOutlineMetrics の値設定."""
        metrics = EnhancedOutlineMetrics(
            word_count=1000,
            char_count=5000,
            h2_count=5,
            h3_count=10,
            original_word_count=500,
            word_increase=500,
        )
        assert metrics.word_count == 1000
        assert metrics.word_increase == 500

    def test_step6_output_creation(self) -> None:
        """Step6Output の作成."""
        output = Step6Output(
            keyword="テストキーワード",
            enhanced_outline="# 拡張アウトライン",
            sources_used=5,
        )
        assert output.step == "step6"
        assert output.keyword == "テストキーワード"
        assert output.sources_used == 5


class TestStep6_5Schemas:
    """Step6.5 スキーマのテスト."""

    def test_input_summary_creation(self) -> None:
        """InputSummary の作成."""
        summary = InputSummary(
            step_id="step3a",
            available=True,
            data_quality="good",
        )
        assert summary.step_id == "step3a"
        assert summary.available is True
        assert summary.data_quality == "good"

    def test_section_blueprint_creation(self) -> None:
        """SectionBlueprint の作成."""
        blueprint = SectionBlueprint(
            level=2,
            title="セクション1",
            target_words=500,
            key_points=["ポイント1", "ポイント2"],
        )
        assert blueprint.level == 2
        assert blueprint.target_words == 500
        assert len(blueprint.key_points) == 2

    def test_package_quality_defaults(self) -> None:
        """PackageQuality のデフォルト値."""
        quality = PackageQuality()
        assert quality.is_acceptable is True
        assert quality.issues == []

    def test_step6_5_output_creation(self) -> None:
        """Step6_5Output の作成."""
        output = Step6_5Output(
            keyword="テストキーワード",
            integration_package="統合パッケージ内容",
            section_count=5,
            total_sources=10,
        )
        assert output.step == "step6_5"
        assert output.section_count == 5
        assert output.total_sources == 10


class TestStep7aSchemas:
    """Step7a スキーマのテスト."""

    def test_draft_section_creation(self) -> None:
        """DraftSection の作成."""
        section = DraftSection(
            level=2,
            title="セクション",
            content="コンテンツ",
            word_count=100,
        )
        assert section.level == 2
        assert section.word_count == 100

    def test_draft_quality_metrics(self) -> None:
        """DraftQualityMetrics の値設定."""
        metrics = DraftQualityMetrics(
            word_count=3000,
            char_count=15000,
            section_count=7,
            avg_section_length=428,
            keyword_density=1.5,
            has_introduction=True,
            has_conclusion=True,
        )
        assert metrics.word_count == 3000
        assert metrics.has_introduction is True
        assert metrics.has_conclusion is True

    def test_generation_stats_defaults(self) -> None:
        """GenerationStats のデフォルト値."""
        stats = GenerationStats()
        assert stats.continuation_used is False
        assert stats.checkpoint_resumed is False

    def test_step7a_output_creation(self) -> None:
        """Step7aOutput の作成."""
        output = Step7aOutput(
            keyword="テストキーワード",
            draft="# ドラフト\n## セクション1\nコンテンツ",
            section_count=3,
            continued=False,
        )
        assert output.step == "step7a"
        assert output.section_count == 3
        assert output.continued is False

    def test_step7a_output_with_continuation(self) -> None:
        """継続生成を使用した Step7aOutput."""
        stats = GenerationStats(
            word_count=5000,
            char_count=25000,
            continuation_used=True,
            checkpoint_resumed=True,
        )
        output = Step7aOutput(
            keyword="テストキーワード",
            draft="長いドラフト",
            stats=stats,
            continued=True,
        )
        assert output.continued is True
        assert output.stats.continuation_used is True
        assert output.stats.checkpoint_resumed is True
