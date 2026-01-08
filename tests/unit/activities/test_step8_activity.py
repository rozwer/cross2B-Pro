"""Unit tests for Step 8 activity.

Tests for blog.System Ver8.3 enhanced activity:
- Verification category computation
- FAQ LLMO optimization analysis
- Four pillars compliance checking
- Enhanced rejection analysis
- FAQ markdown generation
"""

from apps.worker.activities.schemas.step8 import (
    Claim,
    FAQFourPillars,
    FAQItem,
    VerificationResult,
)
from apps.worker.activities.step8 import (
    FAQ_ANSWER_MAX_LENGTH,
    FAQ_ANSWER_MIN_LENGTH,
    QUESTION_WORDS,
    _compute_faq_llmo_optimization,
    _compute_faq_summary,
    _compute_rejection_analysis,
    _compute_verification_categories,
    _compute_verification_summary,
    _determine_rejection_recommendation,
    _generate_faq_markdown,
    _parse_claims_from_response,
    _parse_faq_from_response,
    _parse_verification_from_response,
)
from apps.worker.helpers.output_parser import OutputParser


class TestParseClaimsFromResponse:
    """Test cases for _parse_claims_from_response."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = OutputParser()

    def test_parse_claims_empty(self):
        """Test parsing empty response."""
        result = _parse_claims_from_response(self.parser, "")
        assert result == []

    def test_parse_claims_invalid_json(self):
        """Test parsing invalid JSON."""
        result = _parse_claims_from_response(self.parser, "not json")
        assert result == []

    def test_parse_claims_dict_format(self):
        """Test parsing claims from dict format."""
        response = """```json
{
    "claims": [
        {
            "claim_id": "C1",
            "text": "離職率30%上昇",
            "source_section": "導入部",
            "claim_type": "statistic",
            "verification_category": "numeric_data",
            "data_anchor_id": "[PS-01]"
        }
    ]
}
```"""
        result = _parse_claims_from_response(self.parser, response)
        assert len(result) == 1
        assert result[0].claim_id == "C1"
        assert result[0].verification_category == "numeric_data"
        assert result[0].data_anchor_id == "[PS-01]"

    def test_parse_claims_list_format(self):
        """Test parsing claims from list format."""
        response = """```json
[
    {"claim_id": "C1", "text": "テスト主張1"},
    {"claim_id": "C2", "text": "テスト主張2"}
]
```"""
        result = _parse_claims_from_response(self.parser, response)
        assert len(result) == 2
        assert result[0].claim_id == "C1"
        assert result[1].claim_id == "C2"

    def test_parse_claims_auto_id_generation(self):
        """Test auto-generation of claim IDs."""
        response = """```json
{
    "claims": [
        {"text": "主張1"},
        {"text": "主張2"}
    ]
}
```"""
        result = _parse_claims_from_response(self.parser, response)
        assert result[0].claim_id == "C1"
        assert result[1].claim_id == "C2"


class TestParseVerificationFromResponse:
    """Test cases for _parse_verification_from_response."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = OutputParser()

    def test_parse_verification_empty(self):
        """Test parsing empty response."""
        result = _parse_verification_from_response(self.parser, "")
        assert result == []

    def test_parse_verification_full(self):
        """Test parsing full verification response."""
        response = """```json
{
    "verification_results": [
        {
            "claim_id": "C1",
            "status": "verified",
            "confidence": 0.95,
            "evidence": "厚生労働省統計で確認",
            "source": "厚生労働省",
            "recommendation": "変更不要",
            "verification_method": "web_search",
            "url_checked": true,
            "url_valid": true
        }
    ]
}
```"""
        result = _parse_verification_from_response(self.parser, response)
        assert len(result) == 1
        assert result[0].status == "verified"
        assert result[0].confidence == 0.95
        assert result[0].verification_method == "web_search"
        assert result[0].url_checked is True
        assert result[0].url_valid is True

    def test_parse_verification_results_key(self):
        """Test parsing with 'results' key."""
        response = """```json
{
    "results": [
        {"claim_id": "C1", "status": "contradicted", "confidence": 0.8}
    ]
}
```"""
        result = _parse_verification_from_response(self.parser, response)
        assert len(result) == 1
        assert result[0].status == "contradicted"


class TestParseFaqFromResponse:
    """Test cases for _parse_faq_from_response."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = OutputParser()

    def test_parse_faq_empty(self):
        """Test parsing empty response."""
        result = _parse_faq_from_response(self.parser, "")
        assert result == []

    def test_parse_faq_with_question_word(self):
        """Test parsing FAQ with question word detection."""
        response = """```json
{
    "faq_items": [
        {
            "question": "派遣社員の教育にどのくらいの費用が必要ですか？",
            "answer": "年間約15万円が平均です。",
            "related_claims": ["C1"]
        }
    ]
}
```"""
        result = _parse_faq_from_response(self.parser, response)
        assert len(result) == 1
        assert result[0].question_word_used == "どのくらい"
        assert result[0].voice_search_optimized is True

    def test_parse_faq_with_data_anchor_detection(self):
        """Test parsing FAQ with data anchor detection."""
        response = """```json
{
    "faq_items": [
        {
            "question": "効果はどうですか？",
            "answer": "導入企業の離職率が30%低下しました[PS-01]。"
        }
    ]
}
```"""
        result = _parse_faq_from_response(self.parser, response)
        assert result[0].has_data_anchor is True

    def test_parse_faq_with_four_pillars(self):
        """Test parsing FAQ with four pillars."""
        response = """```json
{
    "faq_items": [
        {
            "question": "なぜ効果があるのですか？",
            "answer": "科学的根拠があります。",
            "four_pillars": {
                "neuroscience_applied": true,
                "neuroscience_details": "結論先行で回答",
                "behavioral_economics_applied": true,
                "behavioral_economics_details": "社会的証明使用",
                "llmo_optimized": true,
                "llmo_details": "音声検索対応",
                "kgi_integrated": false,
                "kgi_details": ""
            }
        }
    ]
}
```"""
        result = _parse_faq_from_response(self.parser, response)
        assert result[0].four_pillars is not None
        assert result[0].four_pillars.neuroscience_applied is True
        assert result[0].four_pillars.llmo_optimized is True
        assert result[0].four_pillars.kgi_integrated is False

    def test_parse_faq_answer_length(self):
        """Test answer length calculation."""
        response = """```json
{
    "faq_items": [
        {
            "question": "どうですか？",
            "answer": "これは150文字程度の回答です。具体的なデータを含み、読者の疑問に的確に答えます。詳細は本文をご覧ください。"
        }
    ]
}
```"""
        result = _parse_faq_from_response(self.parser, response)
        assert result[0].answer_length > 0
        assert result[0].answer_length == len(result[0].answer)


class TestDetermineRejectionRecommendation:
    """Test cases for _determine_rejection_recommendation."""

    def test_no_contradictions(self):
        """Test with no contradictions."""
        results = [
            VerificationResult(status="verified", confidence=0.9),
            VerificationResult(status="verified", confidence=0.85),
        ]
        recommend, issues = _determine_rejection_recommendation(results)
        assert recommend is False
        assert issues == []

    def test_multiple_contradictions(self):
        """Test with multiple contradictions."""
        results = [
            VerificationResult(status="contradicted", confidence=0.7),
            VerificationResult(status="contradicted", confidence=0.6),
        ]
        recommend, issues = _determine_rejection_recommendation(results)
        assert recommend is True
        assert "2 contradictions found" in issues[0]

    def test_high_confidence_contradiction(self):
        """Test with high-confidence contradiction."""
        results = [
            VerificationResult(status="contradicted", confidence=0.9),
        ]
        recommend, issues = _determine_rejection_recommendation(results)
        assert recommend is True
        assert "High-confidence contradictions detected" in issues


class TestComputeVerificationSummary:
    """Test cases for _compute_verification_summary."""

    def test_empty_results(self):
        """Test with empty results."""
        summary = _compute_verification_summary([], [])
        assert summary.verified_count == 0
        assert summary.total_claims == 0
        assert summary.verification_rate == 0.0

    def test_all_verified(self):
        """Test with all verified claims."""
        claims = [Claim(claim_id="C1"), Claim(claim_id="C2")]
        results = [
            VerificationResult(claim_id="C1", status="verified"),
            VerificationResult(claim_id="C2", status="verified"),
        ]
        summary = _compute_verification_summary(results, claims)
        assert summary.verified_count == 2
        assert summary.total_claims == 2
        assert summary.verification_rate == 1.0

    def test_with_data_anchors(self):
        """Test with data anchors."""
        claims = [
            Claim(claim_id="C1", data_anchor_id="[PS-01]"),
            Claim(claim_id="C2", data_anchor_id="[PS-02]"),
            Claim(claim_id="C3"),
        ]
        results = []
        summary = _compute_verification_summary(results, claims)
        assert summary.data_anchors_verified == 2

    def test_with_urls(self):
        """Test with URL checking."""
        claims = [Claim(claim_id="C1")]
        results = [
            VerificationResult(claim_id="C1", url_checked=True, url_valid=True),
            VerificationResult(claim_id="C2", url_checked=True, url_valid=False),
            VerificationResult(claim_id="C3", url_checked=False),
        ]
        summary = _compute_verification_summary(results, claims)
        assert summary.urls_checked == 2
        assert summary.urls_valid == 1


class TestComputeVerificationCategories:
    """Test cases for _compute_verification_categories."""

    def test_empty_input(self):
        """Test with empty input."""
        categories = _compute_verification_categories([], [])
        assert categories.numeric_data.claims_checked == 0
        assert categories.source_accuracy.claims_checked == 0

    def test_categorized_claims(self):
        """Test with categorized claims."""
        claims = [
            Claim(claim_id="C1", verification_category="numeric_data"),
            Claim(claim_id="C2", verification_category="numeric_data"),
            Claim(claim_id="C3", verification_category="source_accuracy"),
        ]
        results = [
            VerificationResult(claim_id="C1", status="verified"),
            VerificationResult(claim_id="C2", status="contradicted"),
            VerificationResult(claim_id="C3", status="verified"),
        ]
        categories = _compute_verification_categories(claims, results)
        assert categories.numeric_data.claims_checked == 2
        assert categories.numeric_data.verified == 1
        assert len(categories.numeric_data.issues) == 1
        assert categories.source_accuracy.claims_checked == 1
        assert categories.source_accuracy.verified == 1


class TestComputeFaqLlmoOptimization:
    """Test cases for _compute_faq_llmo_optimization."""

    def test_empty_faqs(self):
        """Test with empty FAQs."""
        opt = _compute_faq_llmo_optimization([])
        assert opt.question_format_count == 0
        assert opt.voice_search_friendly is False

    def test_voice_search_optimized(self):
        """Test voice search optimization calculation."""
        faqs = [
            FAQItem(question="どうですか？", answer="良いです。", question_word_used="どう", voice_search_optimized=True),
            FAQItem(question="なぜですか？", answer="理由です。", question_word_used="なぜ", voice_search_optimized=True),
            FAQItem(question="いつですか？", answer="今です。", question_word_used="いつ", voice_search_optimized=True),
        ]
        opt = _compute_faq_llmo_optimization(faqs)
        assert opt.question_format_count == 3
        assert opt.voice_search_friendly is True  # 100% >= 80%

    def test_natural_language_score(self):
        """Test natural language score calculation."""
        # Good: question word + proper answer length
        answer = "a" * 150  # Within 120-180 range
        faqs = [
            FAQItem(
                question="どうですか？",
                answer=answer,
                question_word_used="どう",
                answer_length=150,
            ),
        ]
        opt = _compute_faq_llmo_optimization(faqs)
        assert opt.natural_language_score == 1.0  # 0.5 (question word) + 0.5 (length)

    def test_average_answer_length(self):
        """Test average answer length calculation."""
        faqs = [
            FAQItem(question="Q1", answer="a" * 100, answer_length=100),
            FAQItem(question="Q2", answer="a" * 200, answer_length=200),
        ]
        opt = _compute_faq_llmo_optimization(faqs)
        assert opt.average_answer_length == 150


class TestComputeFaqSummary:
    """Test cases for _compute_faq_summary."""

    def test_empty_faqs(self):
        """Test with empty FAQs."""
        summary = _compute_faq_summary([])
        assert summary.faq_count == 0
        assert summary.four_pillars_compliance_rate == 0.0

    def test_full_compliance(self):
        """Test with full four pillars compliance."""
        faqs = [
            FAQItem(
                question="Q1",
                answer="A1",
                voice_search_optimized=True,
                has_cta=True,
                has_internal_link=True,
                four_pillars=FAQFourPillars(
                    neuroscience_applied=True,
                    behavioral_economics_applied=True,
                    llmo_optimized=True,
                    kgi_integrated=True,
                ),
            ),
            FAQItem(
                question="Q2",
                answer="A2",
                voice_search_optimized=True,
                has_cta=False,
                has_internal_link=True,
                four_pillars=FAQFourPillars(
                    neuroscience_applied=True,
                    behavioral_economics_applied=True,
                    llmo_optimized=True,
                    kgi_integrated=True,
                ),
            ),
        ]
        summary = _compute_faq_summary(faqs)
        assert summary.faq_count == 2
        assert summary.voice_search_optimized_count == 2
        assert summary.four_pillars_compliance_rate == 1.0
        assert summary.cta_integrated_count == 1
        assert summary.internal_link_count == 2

    def test_partial_compliance(self):
        """Test with partial compliance."""
        faqs = [
            FAQItem(
                question="Q1",
                answer="A1",
                four_pillars=FAQFourPillars(
                    neuroscience_applied=True,
                    behavioral_economics_applied=True,
                    llmo_optimized=True,
                    kgi_integrated=False,  # Missing one
                ),
            ),
        ]
        summary = _compute_faq_summary(faqs)
        assert summary.four_pillars_compliance_rate == 0.0  # Not fully compliant


class TestComputeRejectionAnalysis:
    """Test cases for _compute_rejection_analysis."""

    def test_no_issues(self):
        """Test with no issues."""
        results = [
            VerificationResult(claim_id="C1", status="verified"),
        ]
        claims = [Claim(claim_id="C1")]
        analysis = _compute_rejection_analysis(results, claims)
        assert analysis.should_reject is False
        assert analysis.severity == "none"
        assert analysis.auto_correction_prohibited is True

    def test_critical_high_confidence(self):
        """Test critical severity with high-confidence contradiction."""
        results = [
            VerificationResult(claim_id="C1", status="contradicted", confidence=0.9),
        ]
        claims = [Claim(claim_id="C1")]
        analysis = _compute_rejection_analysis(results, claims)
        assert analysis.should_reject is True
        assert analysis.severity == "critical"
        assert analysis.human_review_required is True

    def test_critical_multiple_contradictions(self):
        """Test critical severity with multiple contradictions."""
        results = [
            VerificationResult(claim_id="C1", status="contradicted", confidence=0.7),
            VerificationResult(claim_id="C2", status="contradicted", confidence=0.6),
        ]
        claims = [Claim(claim_id="C1"), Claim(claim_id="C2")]
        analysis = _compute_rejection_analysis(results, claims)
        assert analysis.severity == "critical"

    def test_major_single_contradiction(self):
        """Test major severity with single contradiction."""
        results = [
            VerificationResult(claim_id="C1", status="contradicted", confidence=0.7),
            VerificationResult(claim_id="C2", status="verified", confidence=0.9),
        ]
        claims = [Claim(claim_id="C1"), Claim(claim_id="C2")]
        analysis = _compute_rejection_analysis(results, claims)
        assert analysis.severity == "major"
        assert analysis.should_reject is True

    def test_major_many_unverified(self):
        """Test major severity with many unverified."""
        results = [
            VerificationResult(claim_id="C1", status="unverified"),
            VerificationResult(claim_id="C2", status="unverified"),
            VerificationResult(claim_id="C3", status="verified"),
        ]
        claims = [Claim(claim_id="C1"), Claim(claim_id="C2"), Claim(claim_id="C3")]
        analysis = _compute_rejection_analysis(results, claims)
        assert analysis.severity == "major"  # 66% unverified > 30%
        assert analysis.should_reject is False  # No contradictions

    def test_minor_few_unverified(self):
        """Test minor severity with few unverified."""
        results = [
            VerificationResult(claim_id="C1", status="unverified"),
            VerificationResult(claim_id="C2", status="verified"),
            VerificationResult(claim_id="C3", status="verified"),
            VerificationResult(claim_id="C4", status="verified"),
            VerificationResult(claim_id="C5", status="verified"),
        ]
        claims = [Claim(claim_id=f"C{i}") for i in range(1, 6)]
        analysis = _compute_rejection_analysis(results, claims)
        assert analysis.severity == "minor"  # 20% unverified < 30%

    def test_suggested_actions(self):
        """Test suggested actions are generated."""
        results = [
            VerificationResult(claim_id="C1", status="contradicted", confidence=0.9),
        ]
        claims = [Claim(claim_id="C1")]
        analysis = _compute_rejection_analysis(results, claims)
        assert len(analysis.suggested_actions) > 0
        assert "人間レビュー" in analysis.suggested_actions[0]


class TestGenerateFaqMarkdown:
    """Test cases for _generate_faq_markdown."""

    def test_empty_faqs(self):
        """Test with empty FAQs."""
        result = _generate_faq_markdown([], "test")
        assert result == ""

    def test_basic_markdown_generation(self):
        """Test basic markdown generation."""
        faqs = [
            FAQItem(question="質問1ですか？", answer="回答1です。"),
            FAQItem(question="質問2ですか？", answer="回答2です。"),
        ]
        result = _generate_faq_markdown(faqs, "テスト")
        assert "## よくある質問（FAQ）" in result
        assert "### Q1. 質問1ですか？" in result
        assert "**A.** 回答1です。" in result
        assert "### Q2. 質問2ですか？" in result

    def test_markdown_structure(self):
        """Test markdown structure."""
        faqs = [FAQItem(question="Q?", answer="A.")]
        result = _generate_faq_markdown(faqs, "kw")
        lines = result.split("\n")
        assert lines[0] == "## よくある質問（FAQ）"
        assert lines[1] == ""
        assert "### Q1." in lines[2]


class TestConstants:
    """Test constants are properly defined."""

    def test_question_words(self):
        """Test question words are defined."""
        assert "どのくらい" in QUESTION_WORDS
        assert "どのように" in QUESTION_WORDS
        assert "なぜ" in QUESTION_WORDS
        assert "いつ" in QUESTION_WORDS

    def test_answer_length_range(self):
        """Test answer length range."""
        assert FAQ_ANSWER_MIN_LENGTH == 120
        assert FAQ_ANSWER_MAX_LENGTH == 180
        assert FAQ_ANSWER_MIN_LENGTH < FAQ_ANSWER_MAX_LENGTH
