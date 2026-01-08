"""Step 7B schema tests.

Tests for blog.System Ver8.3 extended schemas:
- AdjustmentDetails
- WordCountComparison
- FourPillarsPreservation
- ReadabilityImprovements
- Step7bOutputV2
"""

from apps.worker.activities.schemas.step7b import (
    AdjustmentDetails,
    FourPillarsPreservation,
    PolishChange,
    PolishMetrics,
    ReadabilityImprovements,
    Step7bOutput,
    Step7bOutputV2,
    WordCountComparison,
)


class TestPolishChangeBackwardCompatibility:
    """Test PolishChange backward compatibility."""

    def test_polish_change_defaults(self):
        """デフォルト値で作成可能."""
        change = PolishChange()
        assert change.change_type == ""
        assert change.original_snippet == ""
        assert change.polished_snippet == ""
        assert change.section == ""

    def test_polish_change_with_values(self):
        """値を指定して作成可能."""
        change = PolishChange(
            change_type="wording",
            original_snippet="元の文",
            polished_snippet="修正後の文",
            section="導入部",
        )
        assert change.change_type == "wording"
        assert change.original_snippet == "元の文"
        assert change.polished_snippet == "修正後の文"
        assert change.section == "導入部"


class TestPolishMetricsBackwardCompatibility:
    """Test PolishMetrics backward compatibility."""

    def test_polish_metrics_defaults(self):
        """デフォルト値で作成可能."""
        metrics = PolishMetrics()
        assert metrics.original_word_count == 0
        assert metrics.polished_word_count == 0
        assert metrics.word_diff == 0
        assert metrics.word_diff_percent == 0.0
        assert metrics.sections_preserved == 0
        assert metrics.sections_modified == 0

    def test_polish_metrics_with_values(self):
        """値を指定して作成可能."""
        metrics = PolishMetrics(
            original_word_count=1000,
            polished_word_count=1050,
            word_diff=50,
            word_diff_percent=5.0,
            sections_preserved=5,
            sections_modified=2,
        )
        assert metrics.original_word_count == 1000
        assert metrics.polished_word_count == 1050
        assert metrics.word_diff == 50
        assert metrics.word_diff_percent == 5.0


class TestStep7bOutputBackwardCompatibility:
    """Test Step7bOutput backward compatibility."""

    def test_step7b_output_defaults(self):
        """デフォルト値で作成可能."""
        output = Step7bOutput(step="step7b", keyword="test")
        assert output.step == "step7b"
        assert output.keyword == "test"
        assert output.polished == ""
        assert output.changes_summary == ""
        assert output.change_count == 0
        assert output.quality_warnings == []
        assert output.model == ""

    def test_step7b_output_full(self):
        """全フィールド指定で作成可能."""
        output = Step7bOutput(
            step="step7b",
            keyword="SEOキーワード",
            polished="# ブラッシュアップ済み記事\n\n本文...",
            changes_summary="語尾の統一、接続詞の改善",
            change_count=15,
            polish_metrics=PolishMetrics(
                original_word_count=1000,
                polished_word_count=1020,
            ),
            quality_warnings=["minor_issue"],
            model="gemini-1.5-pro",
        )
        assert output.polished.startswith("# ブラッシュアップ済み記事")
        assert output.change_count == 15
        assert output.polish_metrics.original_word_count == 1000


# =============================================================================
# 新規スキーマテスト（blog.System Ver8.3 対応）
# =============================================================================


class TestAdjustmentDetails:
    """Test AdjustmentDetails schema."""

    def test_adjustment_details_defaults(self):
        """デフォルト値で作成可能."""
        details = AdjustmentDetails()
        assert details.sentence_length_fixes == 0
        assert details.connector_improvements == 0
        assert details.tone_unifications == 0
        assert details.technical_term_explanations_added == 0
        assert details.passive_to_active_conversions == 0
        assert details.redundancy_removals == 0

    def test_adjustment_details_with_values(self):
        """値を指定して作成可能."""
        details = AdjustmentDetails(
            sentence_length_fixes=5,
            connector_improvements=3,
            tone_unifications=10,
            technical_term_explanations_added=2,
            passive_to_active_conversions=4,
            redundancy_removals=7,
        )
        assert details.sentence_length_fixes == 5
        assert details.connector_improvements == 3
        assert details.tone_unifications == 10
        assert details.technical_term_explanations_added == 2
        assert details.passive_to_active_conversions == 4
        assert details.redundancy_removals == 7

    def test_adjustment_details_serialization(self):
        """シリアライズ可能."""
        details = AdjustmentDetails(
            sentence_length_fixes=5,
            tone_unifications=10,
        )
        dumped = details.model_dump()
        assert dumped["sentence_length_fixes"] == 5
        assert dumped["tone_unifications"] == 10
        assert "connector_improvements" in dumped


class TestWordCountComparison:
    """Test WordCountComparison schema."""

    def test_word_count_comparison_defaults(self):
        """デフォルト値で作成可能."""
        comparison = WordCountComparison()
        assert comparison.before == 0
        assert comparison.after == 0
        assert comparison.change_percent == 0.0
        assert comparison.is_within_5_percent is True

    def test_word_count_comparison_within_5_percent(self):
        """5%以内の変動."""
        comparison = WordCountComparison(
            before=10000,
            after=10400,
            change_percent=4.0,
            is_within_5_percent=True,
        )
        assert comparison.is_within_5_percent is True

    def test_word_count_comparison_exceeds_5_percent(self):
        """5%超過の変動."""
        comparison = WordCountComparison(
            before=10000,
            after=10800,
            change_percent=8.0,
            is_within_5_percent=False,
        )
        assert comparison.is_within_5_percent is False

    def test_word_count_comparison_negative_change(self):
        """文字数減少."""
        comparison = WordCountComparison(
            before=10000,
            after=9500,
            change_percent=-5.0,
            is_within_5_percent=True,
        )
        assert comparison.change_percent == -5.0
        assert comparison.is_within_5_percent is True

    def test_word_count_comparison_serialization(self):
        """シリアライズ可能."""
        comparison = WordCountComparison(
            before=10000,
            after=10300,
            change_percent=3.0,
            is_within_5_percent=True,
        )
        dumped = comparison.model_dump()
        assert dumped["before"] == 10000
        assert dumped["after"] == 10300
        assert dumped["change_percent"] == 3.0
        assert dumped["is_within_5_percent"] is True


class TestFourPillarsPreservation:
    """Test FourPillarsPreservation schema."""

    def test_four_pillars_preservation_defaults(self):
        """デフォルト値で作成可能."""
        preservation = FourPillarsPreservation()
        assert preservation.maintained is True
        assert preservation.changes_affecting_pillars == []
        assert preservation.pillar_status["neuroscience"] == "preserved"
        assert preservation.pillar_status["behavioral_economics"] == "preserved"
        assert preservation.pillar_status["llmo"] == "preserved"
        assert preservation.pillar_status["kgi"] == "preserved"

    def test_four_pillars_preservation_maintained(self):
        """全ての柱が維持されている場合."""
        preservation = FourPillarsPreservation(
            maintained=True,
            changes_affecting_pillars=[],
            pillar_status={
                "neuroscience": "preserved",
                "behavioral_economics": "preserved",
                "llmo": "preserved",
                "kgi": "preserved",
            },
        )
        assert preservation.maintained is True
        assert len(preservation.changes_affecting_pillars) == 0

    def test_four_pillars_preservation_not_maintained(self):
        """一部の柱が削除された場合."""
        preservation = FourPillarsPreservation(
            maintained=False,
            changes_affecting_pillars=["neuroscience keywords removed"],
            pillar_status={
                "neuroscience": "removed",
                "behavioral_economics": "preserved",
                "llmo": "preserved",
                "kgi": "preserved",
            },
        )
        assert preservation.maintained is False
        assert "neuroscience keywords removed" in preservation.changes_affecting_pillars
        assert preservation.pillar_status["neuroscience"] == "removed"

    def test_four_pillars_preservation_modified(self):
        """一部の柱が修正された場合."""
        preservation = FourPillarsPreservation(
            maintained=True,  # modified は維持とみなす
            changes_affecting_pillars=["llmo keywords added"],
            pillar_status={
                "neuroscience": "preserved",
                "behavioral_economics": "preserved",
                "llmo": "modified",
                "kgi": "preserved",
            },
        )
        assert preservation.maintained is True
        assert preservation.pillar_status["llmo"] == "modified"

    def test_four_pillars_preservation_serialization(self):
        """シリアライズ可能."""
        preservation = FourPillarsPreservation(
            maintained=True,
            changes_affecting_pillars=["kgi keywords added"],
            pillar_status={
                "neuroscience": "preserved",
                "behavioral_economics": "preserved",
                "llmo": "preserved",
                "kgi": "modified",
            },
        )
        dumped = preservation.model_dump()
        assert dumped["maintained"] is True
        assert dumped["pillar_status"]["kgi"] == "modified"


class TestReadabilityImprovements:
    """Test ReadabilityImprovements schema."""

    def test_readability_improvements_defaults(self):
        """デフォルト値で作成可能."""
        readability = ReadabilityImprovements()
        assert readability.avg_sentence_length_before == 0.0
        assert readability.avg_sentence_length_after == 0.0
        assert readability.target_range_min == 20
        assert readability.target_range_max == 35
        assert readability.is_within_target is False
        assert readability.sentences_shortened == 0
        assert readability.sentences_lengthened == 0
        assert readability.complex_sentences_simplified == 0

    def test_readability_improvements_within_target(self):
        """目標範囲内."""
        readability = ReadabilityImprovements(
            avg_sentence_length_before=45.0,
            avg_sentence_length_after=28.0,
            target_range_min=20,
            target_range_max=35,
            is_within_target=True,
            sentences_shortened=15,
        )
        assert readability.avg_sentence_length_before == 45.0
        assert readability.avg_sentence_length_after == 28.0
        assert readability.is_within_target is True

    def test_readability_improvements_outside_target(self):
        """目標範囲外."""
        readability = ReadabilityImprovements(
            avg_sentence_length_before=45.0,
            avg_sentence_length_after=40.0,
            target_range_min=20,
            target_range_max=35,
            is_within_target=False,
            sentences_shortened=5,
        )
        assert readability.is_within_target is False

    def test_readability_improvements_full_values(self):
        """全フィールド指定."""
        readability = ReadabilityImprovements(
            avg_sentence_length_before=50.0,
            avg_sentence_length_after=30.0,
            target_range_min=20,
            target_range_max=35,
            is_within_target=True,
            sentences_shortened=20,
            sentences_lengthened=5,
            complex_sentences_simplified=10,
        )
        assert readability.sentences_shortened == 20
        assert readability.sentences_lengthened == 5
        assert readability.complex_sentences_simplified == 10

    def test_readability_improvements_serialization(self):
        """シリアライズ可能."""
        readability = ReadabilityImprovements(
            avg_sentence_length_before=45.0,
            avg_sentence_length_after=28.0,
            is_within_target=True,
        )
        dumped = readability.model_dump()
        assert dumped["avg_sentence_length_before"] == 45.0
        assert dumped["avg_sentence_length_after"] == 28.0
        assert dumped["is_within_target"] is True


class TestStep7bOutputV2:
    """Test Step7bOutputV2 schema."""

    def test_step7b_output_v2_backward_compatible(self):
        """既存フィールドのみで作成可能（後方互換性）."""
        output = Step7bOutputV2(
            step="step7b",
            keyword="test keyword",
            polished="# ブラッシュアップ済み\n\n本文...",
            polish_metrics=PolishMetrics(
                original_word_count=1000,
                polished_word_count=1020,
            ),
        )
        assert output.step == "step7b"
        assert output.keyword == "test keyword"
        assert output.polished.startswith("# ブラッシュアップ済み")
        # 新規フィールドは None
        assert output.adjustment_details is None
        assert output.word_count_comparison is None
        assert output.four_pillars_preservation is None
        assert output.readability_improvements is None

    def test_step7b_output_v2_with_all_fields(self):
        """全フィールド指定で作成可能."""
        output = Step7bOutputV2(
            step="step7b",
            keyword="SEOキーワード",
            polished="# ブラッシュアップ済み記事\n\n## 導入\n本文...",
            changes_summary="語尾統一、接続詞改善",
            change_count=25,
            polish_metrics=PolishMetrics(
                original_word_count=10000,
                polished_word_count=10200,
                word_diff=200,
                word_diff_percent=2.0,
            ),
            quality_warnings=[],
            model="gemini-1.5-pro",
            adjustment_details=AdjustmentDetails(
                sentence_length_fixes=10,
                connector_improvements=8,
                tone_unifications=15,
            ),
            word_count_comparison=WordCountComparison(
                before=10000,
                after=10200,
                change_percent=2.0,
                is_within_5_percent=True,
            ),
            four_pillars_preservation=FourPillarsPreservation(
                maintained=True,
                pillar_status={
                    "neuroscience": "preserved",
                    "behavioral_economics": "preserved",
                    "llmo": "preserved",
                    "kgi": "preserved",
                },
            ),
            readability_improvements=ReadabilityImprovements(
                avg_sentence_length_before=45.0,
                avg_sentence_length_after=28.0,
                is_within_target=True,
            ),
        )
        assert output.adjustment_details is not None
        assert output.adjustment_details.sentence_length_fixes == 10
        assert output.word_count_comparison is not None
        assert output.word_count_comparison.is_within_5_percent is True
        assert output.four_pillars_preservation is not None
        assert output.four_pillars_preservation.maintained is True
        assert output.readability_improvements is not None
        assert output.readability_improvements.is_within_target is True

    def test_step7b_output_v2_partial_new_fields(self):
        """一部の新規フィールドのみ指定."""
        output = Step7bOutputV2(
            step="step7b",
            keyword="test",
            word_count_comparison=WordCountComparison(
                before=10000,
                after=10400,
                change_percent=4.0,
                is_within_5_percent=True,
            ),
        )
        assert output.word_count_comparison is not None
        assert output.word_count_comparison.before == 10000
        # 他の新規フィールドは None
        assert output.adjustment_details is None
        assert output.four_pillars_preservation is None
        assert output.readability_improvements is None

    def test_step7b_output_v2_serialization(self):
        """シリアライズ可能."""
        output = Step7bOutputV2(
            step="step7b",
            keyword="test",
            adjustment_details=AdjustmentDetails(
                tone_unifications=5,
            ),
            word_count_comparison=WordCountComparison(
                before=10000,
                after=10300,
                change_percent=3.0,
                is_within_5_percent=True,
            ),
        )
        dumped = output.model_dump()
        assert dumped["step"] == "step7b"
        assert dumped["adjustment_details"]["tone_unifications"] == 5
        assert dumped["word_count_comparison"]["before"] == 10000
        # None フィールドも含まれる
        assert dumped["four_pillars_preservation"] is None

    def test_step7b_output_v2_serialization_exclude_none(self):
        """exclude_none=True でシリアライズ."""
        output = Step7bOutputV2(
            step="step7b",
            keyword="test",
            word_count_comparison=WordCountComparison(
                before=10000,
                after=10200,
            ),
        )
        dumped = output.model_dump(exclude_none=True)
        assert "word_count_comparison" in dumped
        assert "adjustment_details" not in dumped
        assert "four_pillars_preservation" not in dumped

    def test_step7b_output_v2_quality_warnings_with_v2_issues(self):
        """V2モードの品質警告."""
        output = Step7bOutputV2(
            step="step7b",
            keyword="test",
            quality_warnings=[
                "word_count_exceeded_5_percent: 8.0%",
                "four_pillars_not_maintained: ['neuroscience keywords removed']",
            ],
            word_count_comparison=WordCountComparison(
                before=10000,
                after=10800,
                change_percent=8.0,
                is_within_5_percent=False,
            ),
            four_pillars_preservation=FourPillarsPreservation(
                maintained=False,
                changes_affecting_pillars=["neuroscience keywords removed"],
                pillar_status={
                    "neuroscience": "removed",
                    "behavioral_economics": "preserved",
                    "llmo": "preserved",
                    "kgi": "preserved",
                },
            ),
        )
        assert len(output.quality_warnings) == 2
        assert "word_count_exceeded_5_percent" in output.quality_warnings[0]
        assert output.word_count_comparison is not None
        assert output.word_count_comparison.is_within_5_percent is False
        assert output.four_pillars_preservation is not None
        assert output.four_pillars_preservation.maintained is False
