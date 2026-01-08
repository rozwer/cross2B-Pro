"""Test Step 9 schemas for blog.System Ver8.3 integration."""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step9 import (
    BehavioralEconomicsCheck,
    FactcheckCorrection,
    FAQPlacement,
    FourPillarsFinalVerification,
    KGICheck,
    LLMOCheck,
    NeuroscienceCheck,
    QualityScores,
    RedundancyCheck,
    RewriteChange,
    RewriteMetrics,
    SEOFinalAdjustments,
    Step9Output,
    WordCountFinal,
)

# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestRewriteChangeBackwardCompatibility:
    """Test RewriteChange backward compatibility."""

    def test_rewrite_change_minimal(self):
        """Minimal RewriteChange."""
        change = RewriteChange()
        assert change.change_type == ""
        assert change.section == ""
        assert change.description == ""

    def test_rewrite_change_full(self):
        """Full RewriteChange with new fields."""
        change = RewriteChange(
            change_type="factcheck_correction",
            section="導入部",
            description="データ修正",
            original="50%",
            corrected="52.3%",
        )
        assert change.change_type == "factcheck_correction"
        assert change.original == "50%"
        assert change.corrected == "52.3%"


class TestRewriteMetricsBackwardCompatibility:
    """Test RewriteMetrics backward compatibility."""

    def test_rewrite_metrics_defaults(self):
        """Default values."""
        metrics = RewriteMetrics()
        assert metrics.original_word_count == 0
        assert metrics.final_word_count == 0
        assert metrics.faq_integrated is False

    def test_rewrite_metrics_full(self):
        """Full RewriteMetrics."""
        metrics = RewriteMetrics(
            original_word_count=5000,
            final_word_count=5200,
            word_diff=200,
            sections_count=8,
            faq_integrated=True,
            factcheck_corrections_applied=3,
        )
        assert metrics.word_diff == 200
        assert metrics.factcheck_corrections_applied == 3


# =============================================================================
# New Schema Tests: FactcheckCorrection
# =============================================================================


class TestFactcheckCorrection:
    """Test FactcheckCorrection schema."""

    def test_factcheck_correction_minimal(self):
        """Minimal."""
        fc = FactcheckCorrection()
        assert fc.claim_id == ""
        assert fc.source == ""

    def test_factcheck_correction_full(self):
        """Full factcheck correction."""
        fc = FactcheckCorrection(
            claim_id="claim_001",
            original="離職率は50%です",
            corrected="離職率は52.3%です（厚生労働省2023年調査）",
            reason="正確なデータに更新",
            source="厚生労働省",
        )
        assert fc.claim_id == "claim_001"
        assert "52.3%" in fc.corrected
        assert fc.source == "厚生労働省"


# =============================================================================
# New Schema Tests: FAQPlacement
# =============================================================================


class TestFAQPlacement:
    """Test FAQPlacement schema."""

    def test_faq_placement_defaults(self):
        """Defaults."""
        faq = FAQPlacement()
        assert faq.position == "before_conclusion"
        assert faq.items_count == 0
        assert faq.integrated is False

    def test_faq_placement_positions(self):
        """Different positions."""
        for pos in ["before_conclusion", "after_conclusion", "separate_section"]:
            faq = FAQPlacement(position=pos, items_count=5, integrated=True)
            assert faq.position == pos

    def test_faq_placement_invalid_position(self):
        """Invalid position."""
        with pytest.raises(ValidationError):
            FAQPlacement(position="invalid_position")


# =============================================================================
# New Schema Tests: SEOFinalAdjustments
# =============================================================================


class TestSEOFinalAdjustments:
    """Test SEOFinalAdjustments schema."""

    def test_seo_adjustments_defaults(self):
        """Defaults."""
        seo = SEOFinalAdjustments()
        assert seo.headings_optimized == []
        assert seo.internal_links_added == 0
        assert seo.keyword_density == 0.0
        assert seo.heading_cleanup_done is False

    def test_seo_adjustments_full(self):
        """Full SEO adjustments."""
        seo = SEOFinalAdjustments(
            headings_optimized=["見出し1", "見出し2"],
            internal_links_added=3,
            alt_texts_generated=["ALT1", "ALT2"],
            meta_description_optimized=True,
            keyword_density=1.8,
            heading_cleanup_done=True,
        )
        assert len(seo.headings_optimized) == 2
        assert seo.keyword_density == 1.8
        assert seo.heading_cleanup_done is True

    def test_seo_keyword_density_bounds(self):
        """Keyword density bounds."""
        seo = SEOFinalAdjustments(keyword_density=10.0)
        assert seo.keyword_density == 10.0

        with pytest.raises(ValidationError):
            SEOFinalAdjustments(keyword_density=15.0)  # > 10.0


# =============================================================================
# New Schema Tests: FourPillarsFinalVerification
# =============================================================================


class TestNeuroscienceCheck:
    """Test NeuroscienceCheck schema."""

    def test_neuroscience_defaults(self):
        """Defaults."""
        ns = NeuroscienceCheck()
        assert ns.shocking_data_verified is False
        assert ns.concepts_within_limit is False
        assert ns.issues == []

    def test_neuroscience_full(self):
        """Full neuroscience check."""
        ns = NeuroscienceCheck(
            shocking_data_verified=True,
            concepts_within_limit=True,
            sentence_length_ok=True,
            three_phase_maintained=True,
            issues=[],
        )
        assert ns.shocking_data_verified is True


class TestBehavioralEconomicsCheck:
    """Test BehavioralEconomicsCheck schema."""

    def test_behavioral_economics_defaults(self):
        """Defaults."""
        be = BehavioralEconomicsCheck()
        assert be.social_proof_verified is False
        assert be.six_principles_placed is False

    def test_behavioral_economics_full(self):
        """Full check."""
        be = BehavioralEconomicsCheck(
            social_proof_verified=True,
            six_principles_placed=True,
            specific_numbers_maintained=True,
            issues=[],
        )
        assert be.six_principles_placed is True


class TestLLMOCheck:
    """Test LLMOCheck schema."""

    def test_llmo_defaults(self):
        """Defaults."""
        llmo = LLMOCheck()
        assert llmo.citation_format_correct is False
        assert llmo.section_independence is False

    def test_llmo_full(self):
        """Full LLMO check."""
        llmo = LLMOCheck(
            citation_format_correct=True,
            token_count_in_range=True,
            bullet_points_maintained=True,
            section_independence=True,
            issues=[],
        )
        assert llmo.section_independence is True


class TestKGICheck:
    """Test KGICheck schema."""

    def test_kgi_defaults(self):
        """Defaults."""
        kgi = KGICheck()
        assert kgi.cta_data_verified is False
        assert kgi.cta_text_matches_step0 is False

    def test_kgi_full(self):
        """Full KGI check."""
        kgi = KGICheck(
            cta_data_verified=True,
            three_stage_cta=True,
            internal_links_maintained=True,
            cta_text_matches_step0=True,
            issues=[],
        )
        assert kgi.cta_text_matches_step0 is True


class TestFourPillarsFinalVerification:
    """Test FourPillarsFinalVerification schema."""

    def test_four_pillars_defaults(self):
        """Defaults."""
        fp = FourPillarsFinalVerification()
        assert fp.all_compliant is False
        assert fp.issues_remaining == []
        assert fp.manual_review_needed is False

    def test_four_pillars_all_compliant(self):
        """All compliant."""
        fp = FourPillarsFinalVerification(
            all_compliant=True,
            issues_remaining=[],
            manual_review_needed=False,
            neuroscience=NeuroscienceCheck(
                shocking_data_verified=True,
                concepts_within_limit=True,
                sentence_length_ok=True,
                three_phase_maintained=True,
            ),
            behavioral_economics=BehavioralEconomicsCheck(
                social_proof_verified=True,
                six_principles_placed=True,
                specific_numbers_maintained=True,
            ),
            llmo=LLMOCheck(
                citation_format_correct=True,
                token_count_in_range=True,
                bullet_points_maintained=True,
                section_independence=True,
            ),
            kgi=KGICheck(
                cta_data_verified=True,
                three_stage_cta=True,
                internal_links_maintained=True,
                cta_text_matches_step0=True,
            ),
        )
        assert fp.all_compliant is True
        assert fp.neuroscience.shocking_data_verified is True


# =============================================================================
# New Schema Tests: WordCountFinal
# =============================================================================


class TestWordCountFinal:
    """Test WordCountFinal schema."""

    def test_word_count_defaults(self):
        """Defaults."""
        wc = WordCountFinal()
        assert wc.target == 0
        assert wc.status == "achieved"

    def test_word_count_achieved(self):
        """Achieved status."""
        wc = WordCountFinal(
            target=6000,
            actual=5850,
            variance=-150,
            variance_percent=-2.5,
            status="achieved",
            compression_applied=False,
        )
        assert wc.status == "achieved"
        assert wc.variance == -150

    def test_word_count_statuses(self):
        """Different statuses."""
        for status in ["achieved", "補筆推奨", "補筆必須", "要約必須"]:
            wc = WordCountFinal(status=status)
            assert wc.status == status

    def test_word_count_invalid_status(self):
        """Invalid status."""
        with pytest.raises(ValidationError):
            WordCountFinal(status="invalid")


# =============================================================================
# New Schema Tests: QualityScores
# =============================================================================


class TestQualityScores:
    """Test QualityScores schema."""

    def test_quality_scores_defaults(self):
        """Defaults."""
        qs = QualityScores()
        assert qs.accuracy == 0.0
        assert qs.total_score == 0.0
        assert qs.publication_ready is False

    def test_quality_scores_high(self):
        """High quality scores."""
        qs = QualityScores(
            accuracy=0.95,
            readability=0.90,
            persuasiveness=0.88,
            comprehensiveness=0.92,
            differentiation=0.85,
            practicality=0.90,
            seo_optimization=0.88,
            cta_effectiveness=0.85,
            total_score=0.89,
            publication_ready=False,
        )
        assert qs.total_score == 0.89
        assert qs.publication_ready is False

    def test_quality_scores_publication_ready(self):
        """Publication ready (0.90+)."""
        qs = QualityScores(
            accuracy=0.95,
            readability=0.92,
            persuasiveness=0.90,
            comprehensiveness=0.93,
            differentiation=0.88,
            practicality=0.91,
            seo_optimization=0.90,
            cta_effectiveness=0.88,
            total_score=0.91,
            publication_ready=True,
        )
        assert qs.publication_ready is True

    def test_quality_scores_bounds(self):
        """Score bounds validation."""
        # Valid bounds
        qs = QualityScores(accuracy=0.0, readability=1.0)
        assert qs.accuracy == 0.0
        assert qs.readability == 1.0

        # Invalid bounds
        with pytest.raises(ValidationError):
            QualityScores(accuracy=1.5)  # > 1.0


# =============================================================================
# New Schema Tests: RedundancyCheck
# =============================================================================


class TestRedundancyCheck:
    """Test RedundancyCheck schema."""

    def test_redundancy_defaults(self):
        """Defaults."""
        rc = RedundancyCheck()
        assert rc.redundant_expressions_removed == 0
        assert rc.duplicate_content_merged == 0
        assert rc.long_sentences_split == 0

    def test_redundancy_full(self):
        """Full redundancy check."""
        rc = RedundancyCheck(
            redundant_expressions_removed=5,
            duplicate_content_merged=2,
            long_sentences_split=3,
        )
        assert rc.redundant_expressions_removed == 5


# =============================================================================
# Step9Output Integration Tests
# =============================================================================


class TestStep9OutputWithNewFields:
    """Test Step9Output with new fields."""

    def test_step9_output_minimal(self):
        """Minimal output (backward compatible)."""
        output = Step9Output(step="step9", keyword="テストキーワード")
        assert output.step == "step9"
        assert output.keyword == "テストキーワード"
        assert output.final_content == ""
        assert output.factcheck_corrections == []
        assert output.faq_placement is None
        assert output.quality_scores is None

    def test_step9_output_with_factcheck_corrections(self):
        """Output with factcheck corrections."""
        output = Step9Output(
            step="step9",
            keyword="人材育成",
            final_content="# 記事タイトル\n\n本文...",
            factcheck_corrections=[
                FactcheckCorrection(
                    claim_id="fc_001",
                    original="50%",
                    corrected="52.3%",
                    reason="最新データに更新",
                ),
            ],
        )
        assert len(output.factcheck_corrections) == 1
        assert output.factcheck_corrections[0].corrected == "52.3%"

    def test_step9_output_with_faq_placement(self):
        """Output with FAQ placement."""
        output = Step9Output(
            step="step9",
            keyword="人材育成",
            faq_placement=FAQPlacement(
                position="before_conclusion",
                items_count=5,
                integrated=True,
            ),
        )
        assert output.faq_placement is not None
        assert output.faq_placement.items_count == 5

    def test_step9_output_with_four_pillars(self):
        """Output with 4 pillars verification."""
        output = Step9Output(
            step="step9",
            keyword="人材育成",
            four_pillars_final_verification=FourPillarsFinalVerification(
                all_compliant=True,
                issues_remaining=[],
            ),
        )
        assert output.four_pillars_final_verification is not None
        assert output.four_pillars_final_verification.all_compliant is True

    def test_step9_output_with_word_count(self):
        """Output with word count final."""
        output = Step9Output(
            step="step9",
            keyword="人材育成",
            word_count_final=WordCountFinal(
                target=6000,
                actual=5900,
                variance=-100,
                status="achieved",
            ),
        )
        assert output.word_count_final is not None
        assert output.word_count_final.status == "achieved"

    def test_step9_output_with_quality_scores(self):
        """Output with quality scores."""
        output = Step9Output(
            step="step9",
            keyword="人材育成",
            quality_scores=QualityScores(
                accuracy=0.95,
                total_score=0.91,
                publication_ready=True,
            ),
        )
        assert output.quality_scores is not None
        assert output.quality_scores.publication_ready is True

    def test_step9_output_full_integration(self):
        """Full integration test."""
        output = Step9Output(
            step="step9",
            keyword="人材育成",
            final_content="# 人材育成完全ガイド\n\n## 導入\n...\n\n## 参考文献\n...",
            meta_description="人材育成の完全ガイド。採用から定着までの実践的手法を解説。",
            changes_summary=[
                RewriteChange(
                    change_type="factcheck_correction",
                    section="導入",
                    description="データ更新",
                ),
            ],
            rewrite_metrics=RewriteMetrics(
                original_word_count=5800,
                final_word_count=6000,
                word_diff=200,
                sections_count=8,
                faq_integrated=True,
                factcheck_corrections_applied=2,
            ),
            internal_link_suggestions=["採用戦略", "研修制度"],
            quality_warnings=[],
            model="claude-3-5-sonnet",
            factcheck_corrections=[
                FactcheckCorrection(
                    claim_id="fc_001",
                    original="50%",
                    corrected="52.3%",
                    reason="最新データ",
                ),
            ],
            faq_placement=FAQPlacement(
                position="before_conclusion",
                items_count=5,
                integrated=True,
            ),
            seo_final_adjustments=SEOFinalAdjustments(
                headings_optimized=["見出し1", "見出し2"],
                internal_links_added=3,
                keyword_density=1.8,
                heading_cleanup_done=True,
            ),
            four_pillars_final_verification=FourPillarsFinalVerification(
                all_compliant=True,
            ),
            word_count_final=WordCountFinal(
                target=6000,
                actual=6000,
                variance=0,
                status="achieved",
            ),
            quality_scores=QualityScores(
                accuracy=0.95,
                readability=0.92,
                total_score=0.91,
                publication_ready=True,
            ),
            redundancy_check=RedundancyCheck(
                redundant_expressions_removed=5,
                duplicate_content_merged=2,
            ),
        )

        assert output.keyword == "人材育成"
        assert output.rewrite_metrics.faq_integrated is True
        assert len(output.factcheck_corrections) == 1
        assert output.faq_placement.integrated is True
        assert output.seo_final_adjustments.heading_cleanup_done is True
        assert output.four_pillars_final_verification.all_compliant is True
        assert output.word_count_final.status == "achieved"
        assert output.quality_scores.publication_ready is True

    def test_step9_output_serialization(self):
        """Serialization test."""
        output = Step9Output(
            step="step9",
            keyword="テスト",
            final_content="# テスト記事",
            factcheck_corrections=[
                FactcheckCorrection(claim_id="001", original="a", corrected="b"),
            ],
            faq_placement=FAQPlacement(position="before_conclusion", items_count=3),
            quality_scores=QualityScores(total_score=0.90, publication_ready=True),
        )

        # Serialize
        data = output.model_dump()

        # Verify structure
        assert data["keyword"] == "テスト"
        assert len(data["factcheck_corrections"]) == 1
        assert data["faq_placement"]["position"] == "before_conclusion"
        assert data["quality_scores"]["publication_ready"] is True

        # Deserialize
        restored = Step9Output.model_validate(data)
        assert restored.keyword == output.keyword
        assert restored.quality_scores.publication_ready is True
