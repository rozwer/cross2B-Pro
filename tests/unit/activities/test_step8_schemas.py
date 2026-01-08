"""Unit tests for Step 8 schemas.

Tests for blog.System Ver8.3 enhanced schemas:
- Verification categories (numeric, source, timeline, logical)
- FAQ LLMO optimization
- Four pillars FAQ integration
- Enhanced rejection analysis with severity levels
"""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step8 import (
    Claim,
    FAQFourPillars,
    FAQItem,
    FAQLLMOOptimization,
    FAQSummary,
    RejectionAnalysis,
    Step8Output,
    VerificationCategories,
    VerificationCategoryResult,
    VerificationResult,
    VerificationSummary,
)


class TestClaim:
    """Test cases for Claim schema."""

    def test_claim_minimal(self):
        """Test claim with minimal fields."""
        claim = Claim()
        assert claim.claim_id == ""
        assert claim.text == ""
        assert claim.source_section == ""
        assert claim.claim_type == "fact"
        assert claim.verification_category is None
        assert claim.data_anchor_id is None

    def test_claim_full(self):
        """Test claim with all fields."""
        claim = Claim(
            claim_id="C1",
            text="離職率が30%上昇した",
            source_section="導入部",
            claim_type="statistic",
            verification_category="numeric_data",
            data_anchor_id="[PS-01]",
        )
        assert claim.claim_id == "C1"
        assert claim.claim_type == "statistic"
        assert claim.verification_category == "numeric_data"
        assert claim.data_anchor_id == "[PS-01]"

    def test_claim_type_literal(self):
        """Test claim type validation."""
        for claim_type in ["statistic", "fact", "opinion", "definition"]:
            claim = Claim(claim_type=claim_type)
            assert claim.claim_type == claim_type

    def test_claim_verification_category_literal(self):
        """Test verification category validation."""
        categories = [
            "numeric_data",
            "source_accuracy",
            "timeline_consistency",
            "logical_consistency",
        ]
        for cat in categories:
            claim = Claim(verification_category=cat)
            assert claim.verification_category == cat


class TestVerificationResult:
    """Test cases for VerificationResult schema."""

    def test_verification_result_minimal(self):
        """Test verification result with minimal fields."""
        result = VerificationResult()
        assert result.claim_id == ""
        assert result.status == "unverified"
        assert result.confidence == 0.5
        assert result.evidence == ""
        assert result.verification_method == ""
        assert result.url_checked is False
        assert result.url_valid is None

    def test_verification_result_full(self):
        """Test verification result with all fields."""
        result = VerificationResult(
            claim_id="C1",
            status="verified",
            confidence=0.95,
            evidence="厚生労働省の統計で確認",
            source="厚生労働省",
            recommendation="変更不要",
            verification_method="web_search",
            url_checked=True,
            url_valid=True,
        )
        assert result.status == "verified"
        assert result.confidence == 0.95
        assert result.url_checked is True
        assert result.url_valid is True

    def test_verification_status_literal(self):
        """Test verification status validation."""
        for status in ["verified", "unverified", "contradicted", "partially_verified"]:
            result = VerificationResult(status=status)
            assert result.status == status

    def test_confidence_bounds(self):
        """Test confidence value bounds."""
        result = VerificationResult(confidence=0.0)
        assert result.confidence == 0.0

        result = VerificationResult(confidence=1.0)
        assert result.confidence == 1.0

        with pytest.raises(ValidationError):
            VerificationResult(confidence=-0.1)

        with pytest.raises(ValidationError):
            VerificationResult(confidence=1.1)


class TestVerificationCategoryResult:
    """Test cases for VerificationCategoryResult schema."""

    def test_category_result_defaults(self):
        """Test category result with defaults."""
        result = VerificationCategoryResult()
        assert result.claims_checked == 0
        assert result.verified == 0
        assert result.issues == []

    def test_category_result_with_issues(self):
        """Test category result with issues."""
        result = VerificationCategoryResult(
            claims_checked=5,
            verified=3,
            issues=["[C1] データ不一致", "[C4] 未検証"],
        )
        assert result.claims_checked == 5
        assert result.verified == 3
        assert len(result.issues) == 2


class TestVerificationCategories:
    """Test cases for VerificationCategories schema."""

    def test_categories_defaults(self):
        """Test categories with defaults."""
        cats = VerificationCategories()
        assert cats.numeric_data.claims_checked == 0
        assert cats.source_accuracy.claims_checked == 0
        assert cats.timeline_consistency.claims_checked == 0
        assert cats.logical_consistency.claims_checked == 0

    def test_categories_with_data(self):
        """Test categories with data."""
        cats = VerificationCategories(
            numeric_data=VerificationCategoryResult(claims_checked=10, verified=8),
            source_accuracy=VerificationCategoryResult(claims_checked=5, verified=5),
        )
        assert cats.numeric_data.claims_checked == 10
        assert cats.numeric_data.verified == 8
        assert cats.source_accuracy.verified == 5


class TestFAQFourPillars:
    """Test cases for FAQFourPillars schema."""

    def test_four_pillars_defaults(self):
        """Test four pillars with defaults."""
        pillars = FAQFourPillars()
        assert pillars.neuroscience_applied is False
        assert pillars.behavioral_economics_applied is False
        assert pillars.llmo_optimized is False
        assert pillars.kgi_integrated is False

    def test_four_pillars_full_compliance(self):
        """Test four pillars with full compliance."""
        pillars = FAQFourPillars(
            neuroscience_applied=True,
            neuroscience_details="結論先行、Aha moment適用",
            behavioral_economics_applied=True,
            behavioral_economics_details="社会的証明で統計データ使用",
            llmo_optimized=True,
            llmo_details="音声検索対応、回答独立",
            kgi_integrated=True,
            kgi_details="CTA統合、内部リンク設置",
        )
        assert pillars.neuroscience_applied is True
        assert pillars.behavioral_economics_applied is True
        assert pillars.llmo_optimized is True
        assert pillars.kgi_integrated is True

    def test_four_pillars_is_compliant(self):
        """Test checking if all four pillars are compliant."""
        # All true
        pillars = FAQFourPillars(
            neuroscience_applied=True,
            behavioral_economics_applied=True,
            llmo_optimized=True,
            kgi_integrated=True,
        )
        all_compliant = (
            pillars.neuroscience_applied and pillars.behavioral_economics_applied and pillars.llmo_optimized and pillars.kgi_integrated
        )
        assert all_compliant is True

        # Missing one
        pillars_partial = FAQFourPillars(
            neuroscience_applied=True,
            behavioral_economics_applied=True,
            llmo_optimized=True,
            kgi_integrated=False,
        )
        partial_compliant = (
            pillars_partial.neuroscience_applied
            and pillars_partial.behavioral_economics_applied
            and pillars_partial.llmo_optimized
            and pillars_partial.kgi_integrated
        )
        assert partial_compliant is False


class TestFAQItem:
    """Test cases for FAQItem schema."""

    def test_faq_item_minimal(self):
        """Test FAQ item with minimal fields."""
        faq = FAQItem()
        assert faq.question == ""
        assert faq.answer == ""
        assert faq.related_claims == []
        assert faq.voice_search_optimized is False
        assert faq.question_word_used is None
        assert faq.answer_length == 0
        assert faq.four_pillars is None

    def test_faq_item_full(self):
        """Test FAQ item with all fields."""
        faq = FAQItem(
            question="派遣社員の教育にどのくらいの費用が必要ですか？",
            answer="派遣社員1人あたりの教育費用は平均で年間約15万円です。研修内容や期間により5万円から30万円の幅があります。",
            related_claims=["C1", "C2"],
            voice_search_optimized=True,
            question_word_used="どのくらい",
            answer_length=75,
            has_data_anchor=True,
            has_cta=True,
            has_internal_link=True,
            four_pillars=FAQFourPillars(
                neuroscience_applied=True,
                behavioral_economics_applied=True,
                llmo_optimized=True,
                kgi_integrated=True,
            ),
        )
        assert faq.voice_search_optimized is True
        assert faq.question_word_used == "どのくらい"
        assert faq.has_cta is True
        assert faq.four_pillars is not None
        assert faq.four_pillars.kgi_integrated is True


class TestFAQLLMOOptimization:
    """Test cases for FAQLLMOOptimization schema."""

    def test_llmo_optimization_defaults(self):
        """Test LLMO optimization with defaults."""
        opt = FAQLLMOOptimization()
        assert opt.question_format_count == 0
        assert opt.voice_search_friendly is False
        assert opt.structured_data_ready is False
        assert opt.natural_language_score == 0.0
        assert opt.average_answer_length == 0

    def test_llmo_optimization_full(self):
        """Test LLMO optimization with full data."""
        opt = FAQLLMOOptimization(
            question_format_count=12,
            voice_search_friendly=True,
            structured_data_ready=True,
            natural_language_score=0.85,
            average_answer_length=150,
        )
        assert opt.question_format_count == 12
        assert opt.voice_search_friendly is True
        assert opt.natural_language_score == 0.85

    def test_natural_language_score_bounds(self):
        """Test natural language score bounds."""
        with pytest.raises(ValidationError):
            FAQLLMOOptimization(natural_language_score=-0.1)

        with pytest.raises(ValidationError):
            FAQLLMOOptimization(natural_language_score=1.1)


class TestFAQSummary:
    """Test cases for FAQSummary schema."""

    def test_faq_summary_defaults(self):
        """Test FAQ summary with defaults."""
        summary = FAQSummary()
        assert summary.faq_count == 0
        assert summary.voice_search_optimized_count == 0
        assert summary.four_pillars_compliance_rate == 0.0
        assert summary.cta_integrated_count == 0
        assert summary.internal_link_count == 0

    def test_faq_summary_full(self):
        """Test FAQ summary with full data."""
        summary = FAQSummary(
            faq_count=15,
            voice_search_optimized_count=12,
            four_pillars_compliance_rate=0.8,
            cta_integrated_count=3,
            internal_link_count=10,
        )
        assert summary.faq_count == 15
        assert summary.four_pillars_compliance_rate == 0.8


class TestRejectionAnalysis:
    """Test cases for RejectionAnalysis schema."""

    def test_rejection_analysis_defaults(self):
        """Test rejection analysis with defaults."""
        analysis = RejectionAnalysis()
        assert analysis.should_reject is False
        assert analysis.severity == "none"
        assert analysis.reasons == []
        assert analysis.human_review_required is True
        assert analysis.auto_correction_prohibited is True  # Always true per blog.System
        assert analysis.suggested_actions == []

    def test_rejection_analysis_critical(self):
        """Test rejection analysis with critical severity."""
        analysis = RejectionAnalysis(
            should_reject=True,
            severity="critical",
            reasons=["2 high-confidence contradictions detected"],
            human_review_required=True,
            auto_correction_prohibited=True,
            suggested_actions=["人間レビューで事実確認を行ってください"],
        )
        assert analysis.should_reject is True
        assert analysis.severity == "critical"
        assert len(analysis.reasons) == 1

    def test_rejection_severity_literal(self):
        """Test rejection severity validation."""
        for severity in ["critical", "major", "minor", "none"]:
            analysis = RejectionAnalysis(severity=severity)
            assert analysis.severity == severity

    def test_auto_correction_always_prohibited(self):
        """Test that auto-correction is always prohibited (blog.System rule)."""
        # Even if we try to set it to False, it should be True by design intent
        # Note: Pydantic doesn't prevent this, but the default is True
        analysis = RejectionAnalysis()
        assert analysis.auto_correction_prohibited is True


class TestVerificationSummary:
    """Test cases for VerificationSummary schema."""

    def test_summary_defaults(self):
        """Test verification summary with defaults."""
        summary = VerificationSummary()
        assert summary.verified_count == 0
        assert summary.unverified_count == 0
        assert summary.contradicted_count == 0
        assert summary.partially_verified_count == 0
        assert summary.total_claims == 0
        assert summary.verification_rate == 0.0
        assert summary.data_anchors_verified == 0
        assert summary.urls_checked == 0
        assert summary.urls_valid == 0

    def test_summary_full(self):
        """Test verification summary with full data."""
        summary = VerificationSummary(
            verified_count=8,
            unverified_count=2,
            contradicted_count=1,
            partially_verified_count=1,
            total_claims=12,
            verification_rate=0.67,
            data_anchors_verified=5,
            urls_checked=10,
            urls_valid=9,
        )
        assert summary.verified_count == 8
        assert summary.total_claims == 12
        assert summary.verification_rate == 0.67


class TestStep8Output:
    """Test cases for Step8Output schema."""

    def test_output_minimal(self):
        """Test Step8Output with minimal fields."""
        output = Step8Output(step="step8", keyword="テストKW")
        assert output.step == "step8"
        assert output.keyword == "テストKW"
        assert output.claims == []
        assert output.verification_results == []
        assert output.faq_items == []
        assert output.has_contradictions is False
        assert output.recommend_rejection is False
        # blog.System extensions
        assert output.verification_categories is None
        assert output.faq_llmo_optimization is None
        assert output.faq_summary is None
        assert output.rejection_analysis is None
        assert output.faq_section_markdown == ""
        assert output.references_verified is False

    def test_output_full(self):
        """Test Step8Output with all fields."""
        claims = [
            Claim(
                claim_id="C1",
                text="離職率30%",
                verification_category="numeric_data",
            )
        ]
        results = [
            VerificationResult(
                claim_id="C1",
                status="verified",
                confidence=0.9,
            )
        ]
        faqs = [
            FAQItem(
                question="どのくらいのコストがかかりますか？",
                answer="年間約15万円です。",
                voice_search_optimized=True,
            )
        ]

        output = Step8Output(
            step="step8",
            keyword="派遣社員 教育",
            claims=claims,
            verification_results=results,
            faq_items=faqs,
            summary=VerificationSummary(
                verified_count=1,
                total_claims=1,
                verification_rate=1.0,
            ),
            has_contradictions=False,
            critical_issues=[],
            recommend_rejection=False,
            model="gemini-2.0-flash",
            verification_categories=VerificationCategories(numeric_data=VerificationCategoryResult(claims_checked=1, verified=1)),
            faq_llmo_optimization=FAQLLMOOptimization(
                question_format_count=1,
                voice_search_friendly=True,
            ),
            faq_summary=FAQSummary(
                faq_count=1,
                voice_search_optimized_count=1,
            ),
            rejection_analysis=RejectionAnalysis(
                should_reject=False,
                severity="none",
            ),
            faq_section_markdown="## FAQ\n\n### Q1...",
            references_verified=True,
        )

        assert len(output.claims) == 1
        assert len(output.verification_results) == 1
        assert len(output.faq_items) == 1
        assert output.verification_categories is not None
        assert output.faq_llmo_optimization is not None
        assert output.faq_summary is not None
        assert output.rejection_analysis is not None
        assert output.references_verified is True

    def test_output_with_contradictions(self):
        """Test Step8Output with contradictions."""
        results = [
            VerificationResult(
                claim_id="C1",
                status="contradicted",
                confidence=0.85,
            ),
            VerificationResult(
                claim_id="C2",
                status="contradicted",
                confidence=0.9,
            ),
        ]

        output = Step8Output(
            step="step8",
            keyword="test",
            verification_results=results,
            has_contradictions=True,
            critical_issues=["2 contradictions found"],
            recommend_rejection=True,
            rejection_analysis=RejectionAnalysis(
                should_reject=True,
                severity="critical",
                reasons=["2 contradictions found"],
                human_review_required=True,
            ),
        )

        assert output.has_contradictions is True
        assert output.recommend_rejection is True
        assert output.rejection_analysis.severity == "critical"
        assert output.rejection_analysis.human_review_required is True

    def test_output_serialization(self):
        """Test Step8Output serialization."""
        output = Step8Output(
            step="step8",
            keyword="テスト",
            faq_items=[
                FAQItem(
                    question="どうですか？",
                    answer="良いです。",
                    four_pillars=FAQFourPillars(
                        neuroscience_applied=True,
                        behavioral_economics_applied=True,
                        llmo_optimized=True,
                        kgi_integrated=True,
                    ),
                )
            ],
        )

        data = output.model_dump()
        assert data["step"] == "step8"
        assert data["keyword"] == "テスト"
        assert len(data["faq_items"]) == 1
        assert data["faq_items"][0]["four_pillars"]["neuroscience_applied"] is True

        # Deserialize back
        restored = Step8Output(**data)
        assert restored.faq_items[0].four_pillars.neuroscience_applied is True
