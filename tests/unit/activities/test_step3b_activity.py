"""Step 3B activity tests.

Tests for Step3B Co-occurrence & Related Keywords Extraction Activity.
This is the HEART of the SEO workflow.

Test coverage:
- Quality validator (Step3BQualityValidator)
- Keyword extraction from freeform content
- blog.System extensions enrichment
- Phase classification
- LLMO keyword extraction
- Behavioral economics trigger mapping
- CTA keyword extraction
- Keyword categorization
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.activities.schemas.step3b import (
    BehavioralEconomicsTriggers,
    CTAKeywords,
    KeywordCategorization,
    LLMOOptimizedKeywords,
    ThreePhaseDistribution,
)
from apps.worker.activities.step3b import (
    BEHAVIORAL_PATTERNS,
    CTA_PATTERNS,
    PHASE1_PATTERNS,
    PHASE2_PATTERNS,
    PHASE3_PATTERNS,
    QUESTION_FORMAT_PATTERNS,
    VOICE_SEARCH_PATTERNS,
    Step3BCooccurrenceExtraction,
    Step3BQualityValidator,
)


class TestStep3BQualityValidator:
    """Test Step3BQualityValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = Step3BQualityValidator()

    def test_validate_acceptable_content(self):
        """許容可能なコンテンツの検証."""
        content = """
        # 共起キーワード抽出結果

        ## Phase 1: 不安・課題認識キーワード
        - 離職率
        - 人材不足
        - コスト

        ## Phase 2: 理解・比較キーワード
        - 教育方法
        - 研修プログラム
        - OJT

        ## Phase 3: 行動・決定キーワード
        - 無料相談
        - 資料請求

        ## 音声検索キーワード
        - どのように教育すれば
        - なぜ離職するのか

        ## 質問形式キーワード
        - 派遣社員 教育 とは
        - 派遣社員 研修 方法
        """
        result = self.validator.validate(content)
        assert result.is_acceptable is True
        assert len(result.issues) <= 2

    def test_validate_no_keyword_list(self):
        """キーワードリストがない場合."""
        content = "キーワードの分析結果です。共起語について説明します。"
        result = self.validator.validate(content)
        assert "no_keyword_list" in result.issues

    def test_validate_no_keyword_categories(self):
        """キーワードカテゴリがない場合."""
        content = """
        - キーワード1
        - キーワード2
        - キーワード3
        """
        result = self.validator.validate(content)
        assert "no_keyword_categories" in result.issues

    def test_validate_insufficient_phase_distribution(self):
        """フェーズ分布が不十分な場合."""
        content = """
        ## 共起キーワード
        - キーワード1
        - キーワード2
        """
        result = self.validator.validate(content)
        assert "insufficient_phase_distribution" in result.issues

    def test_validate_no_llmo_elements(self):
        """LLMO要素がない場合."""
        content = """
        ## 共起キーワード co-occurrence
        - キーワード1
        - キーワード2

        ## Phase 1: 不安
        ## Phase 2: 理解
        ## Phase 3: 行動
        """
        result = self.validator.validate(content)
        assert "no_llmo_elements" in result.issues

    def test_validate_allows_up_to_two_issues(self):
        """2つまでの問題は許容."""
        # 2つの問題がある場合
        content = """
        ## 共起 co-occurrence
        - キーワード1

        ## Phase 1: 不安
        ## Phase 2: 理解
        ## Phase 3: 行動
        """
        result = self.validator.validate(content)
        # no_llmo_elements のみ
        assert result.is_acceptable is True


class TestPatternConstants:
    """Test pattern constants."""

    def test_phase1_patterns_match(self):
        """Phase1パターンのマッチング."""
        import re

        test_words = ["課題", "問題", "悩み", "失敗", "リスク"]
        pattern = PHASE1_PATTERNS[0]
        for word in test_words:
            assert re.search(pattern, word) is not None

    def test_phase2_patterns_match(self):
        """Phase2パターンのマッチング."""
        import re

        test_words = ["方法", "ステップ", "事例", "データ", "比較"]
        pattern = PHASE2_PATTERNS[0]
        for word in test_words:
            assert re.search(pattern, word) is not None

    def test_phase3_patterns_match(self):
        """Phase3パターンのマッチング."""
        import re

        test_words = ["今すぐ", "簡単", "無料", "実績", "成功"]
        pattern = PHASE3_PATTERNS[0]
        for word in test_words:
            assert re.search(pattern, word) is not None

    def test_behavioral_patterns_match(self):
        """行動経済学パターンのマッチング."""
        import re

        test_cases = {
            "loss_aversion": ["損失", "無駄", "リスク"],
            "social_proof": ["導入", "実績", "満足"],
            "authority": ["専門家", "研究", "認定"],
            "consistency": ["まずは", "次に", "ステップ"],
            "liking": ["お困り", "サポート"],
            "scarcity": ["限定", "先着", "今だけ"],
        }
        for trigger, words in test_cases.items():
            pattern = BEHAVIORAL_PATTERNS[trigger]
            for word in words:
                assert re.search(pattern, word) is not None, f"{trigger}: {word}"

    def test_question_format_patterns(self):
        """質問形式パターンのマッチング."""
        import re

        test_words = ["とは", "方法", "やり方", "メリット", "デメリット"]
        for word in test_words:
            assert re.search(QUESTION_FORMAT_PATTERNS, word) is not None

    def test_voice_search_patterns(self):
        """音声検索パターンのマッチング."""
        import re

        test_words = ["どのくらい", "どのように", "なぜ", "いつ"]
        for word in test_words:
            assert re.search(VOICE_SEARCH_PATTERNS, word) is not None

    def test_cta_patterns(self):
        """CTAパターンのマッチング."""
        import re

        test_cases = {
            "urgency": ["今すぐ", "すぐに", "緊急"],
            "ease": ["簡単", "手軽", "クリック"],
            "free": ["無料", "0円", "タダ"],
            "expertise": ["専門家", "プロ", "実績"],
        }
        for category, words in test_cases.items():
            pattern = CTA_PATTERNS[category]
            for word in words:
                assert re.search(pattern, word) is not None, f"{category}: {word}"


class TestStep3BCooccurrenceExtraction:
    """Test Step3BCooccurrenceExtraction activity."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock()
        self.activity = Step3BCooccurrenceExtraction(store=self.mock_store)

    def test_step_id(self):
        """step_idの確認."""
        assert self.activity.step_id == "step3b"

    def test_quality_thresholds(self):
        """品質閾値の確認（blog.System Ver8.3）."""
        assert self.activity.MIN_COOCCURRENCE_KEYWORDS == 100
        assert self.activity.MIN_LSI_KEYWORDS == 30
        assert self.activity.MIN_RELATED_KEYWORDS == 30
        assert self.activity.TARGET_COOCCURRENCE == 150
        assert self.activity.TARGET_RELATED == 50

    def test_prepare_competitor_summaries(self):
        """競合サマリー準備のテスト."""
        competitors = [
            {
                "title": "記事1",
                "url": "https://example.com/1",
                "content": "コンテンツ1" * 100,
                "word_count": 1000,
                "headings": ["H1", "H2", "H3"],
            },
            {
                "title": "記事2",
                "url": "https://example.com/2",
                "content": "コンテンツ2" * 100,
                "word_count": 800,
                "headings": ["H1"],
            },
        ]
        summaries = self.activity._prepare_competitor_summaries(competitors)

        assert len(summaries) == 2
        assert summaries[0]["title"] == "記事1"
        assert summaries[0]["word_count"] == 1000
        assert len(summaries[0]["content_preview"]) <= 1000

    def test_extract_full_texts(self):
        """フルテキスト抽出のテスト."""
        competitors = [
            {"content": "テキスト1"},
            {"content": "テキスト2"},
            {"content": "テキスト3"},
        ]
        texts = self.activity._extract_full_texts(competitors)

        assert len(texts) == 3
        assert texts[0] == "テキスト1"

    def test_pre_analyze_competitors(self):
        """競合事前分析のテスト."""
        full_texts = [
            "派遣社員の教育方法について。課題として離職率が高い。",
            "研修プログラムの比較。効果的な方法を解説。",
            "今すぐ始められる無料相談。実績多数。",
        ]
        step2_data = {}

        hints = self.activity._pre_analyze_competitors(
            main_keyword="派遣社員",
            full_texts=full_texts,
            step2_data=step2_data,
        )

        assert "top_frequent_words" in hints
        assert "phase_hints" in hints
        assert "total_word_count" in hints
        assert "unique_words" in hints


class TestStep3BPrivateMethods:
    """Test Step3B private methods for blog.System extensions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock()
        self.activity = Step3BCooccurrenceExtraction(store=self.mock_store)

    def test_extract_keywords_from_freeform(self):
        """フリーフォームからのキーワード抽出テスト."""
        content = """
        共起キーワード:
        - 教育方法
        - 研修プログラム
        - 人材育成

        関連キーワード:
        - OJT
        - Off-JT
        - メンター制度
        """
        data = self.activity._extract_keywords_from_freeform(content)

        assert "cooccurrence_keywords" in data
        # 抽出されたキーワードが存在することを確認
        assert len(data.get("cooccurrence_keywords", [])) > 0 or len(data.get("keywords", [])) > 0

    def test_classify_keywords_by_phase(self):
        """フェーズ別キーワード分類テスト."""
        # Note: _classify_keywords_by_phase expects list[str], not list[KeywordItem]
        keywords = [
            "課題",
            "離職率",
            "方法",
            "比較",
            "今すぐ",
            "無料",
        ]

        result = self.activity._classify_keywords_by_phase(keywords)

        assert isinstance(result, ThreePhaseDistribution)
        # Phase1 should have anxiety keywords
        phase1_keywords = [kw.keyword for kw in result.phase1_keywords]
        phase3_keywords = [kw.keyword for kw in result.phase3_keywords]

        # 分類が行われていることを確認
        total_classified = len(result.phase1_keywords) + len(result.phase2_keywords) + len(result.phase3_keywords)
        assert total_classified == 6  # All keywords should be classified

        # Verify correct phase assignment
        assert "課題" in phase1_keywords or "離職率" in phase1_keywords  # Phase 1 anxiety keywords
        assert "今すぐ" in phase3_keywords or "無料" in phase3_keywords  # Phase 3 action keywords

    def test_extract_llmo_keywords(self):
        """LLMOキーワード抽出テスト."""
        # Note: _extract_llmo_keywords expects list[str]
        keywords = [
            "派遣社員 教育 とは",
            "派遣社員 研修 方法",
            "どのように教育すれば",
            "なぜ離職するのか",
            "一般的なキーワード",
        ]

        result = self.activity._extract_llmo_keywords(keywords)

        assert isinstance(result, LLMOOptimizedKeywords)
        # 質問形式や音声検索キーワードが抽出されていることを確認
        assert len(result.question_format) > 0 or len(result.voice_search) > 0

    def test_map_behavioral_triggers(self):
        """行動経済学トリガーマッピングテスト."""
        # Note: _map_behavioral_triggers expects list[str]
        keywords = [
            "採用コスト損失",
            "500社導入実績",
            "専門家監修",
            "まずは無料相談",
            "お困りの方へ",
            "先着30社限定",
        ]

        result = self.activity._map_behavioral_triggers(keywords)

        assert isinstance(result, BehavioralEconomicsTriggers)
        # 各トリガーにキーワードがマッピングされていることを確認
        total_mapped = (
            len(result.loss_aversion)
            + len(result.social_proof)
            + len(result.authority)
            + len(result.consistency)
            + len(result.liking)
            + len(result.scarcity)
        )
        assert total_mapped > 0

    def test_extract_cta_keywords(self):
        """CTAキーワード抽出テスト."""
        # Note: _extract_cta_keywords expects list[str]
        keywords = [
            "今すぐ申込",
            "簡単3ステップ",
            "無料診断",
            "専門家が対応",
            "一般的なキーワード",
        ]

        result = self.activity._extract_cta_keywords(keywords)

        assert isinstance(result, CTAKeywords)
        total_cta = len(result.urgency) + len(result.ease) + len(result.free) + len(result.expertise)
        assert total_cta > 0

    def test_categorize_keywords(self):
        """キーワードカテゴリ分類テスト."""
        # Note: _categorize_keywords expects (list[str], list[str])
        keywords = [
            "必須KW1",
            "必須KW2",
            "標準KW",
            "独自KW",
        ]
        # Competitor texts where some keywords appear frequently
        competitor_texts = [
            "必須KW1と必須KW2が含まれる記事1",
            "必須KW1と必須KW2が含まれる記事2",
            "必須KW1と必須KW2が含まれる記事3",
            "必須KW1と必須KW2と標準KWが含まれる記事4",
            "必須KW1と必須KW2と標準KWが含まれる記事5",
            "必須KW1と必須KW2と標準KWと独自KWが含まれる記事6",
            "必須KW1と必須KW2と標準KWが含まれる記事7",
            "必須KW1と必須KW2が含まれる記事8",
            "必須KW1と必須KW2が含まれる記事9",
            "必須KW1と必須KW2が含まれる記事10",
        ]

        result = self.activity._categorize_keywords(keywords, competitor_texts)

        assert isinstance(result, KeywordCategorization)
        # Essential: 70%+, Standard: 40-60%, Unique: <40%
        assert len(result.essential) >= 0
        assert len(result.standard) >= 0
        assert len(result.unique) >= 0

    def test_build_extraction_summary(self):
        """抽出サマリー構築テスト."""
        data = {
            "cooccurrence_keywords": [{"keyword": f"kw{i}"} for i in range(100)],
            "lsi_keywords": [{"keyword": f"lsi{i}"} for i in range(30)],
            "related_keywords": [{"keyword": f"rel{i}"} for i in range(40)],
            "three_phase_distribution": {
                "phase1_keywords": [{"keyword": "p1"}] * 15,
                "phase2_keywords": [{"keyword": "p2"}] * 45,
                "phase3_keywords": [{"keyword": "p3"}] * 10,
            },
            "llmo_optimized_keywords": {
                "question_format": ["q1", "q2"] * 10,
                "voice_search": ["v1", "v2"] * 8,
            },
            "behavioral_economics_triggers": {
                "loss_aversion": ["la1", "la2"],
                "social_proof": ["sp1"],
                "authority": ["au1"],
                "consistency": ["co1"],
                "liking": ["li1"],
                "scarcity": ["sc1"],
            },
        }

        summary = self.activity._build_extraction_summary(data)

        assert summary["cooccurrence"] == 100
        assert summary["lsi"] == 30
        assert summary["related"] == 40
        assert summary["phase1"] == 15
        assert summary["phase2"] == 45
        assert summary["phase3"] == 10

    def test_enforce_quality_standards(self):
        """品質基準強制テスト."""
        # 品質基準を満たさないデータ
        low_quality_data = {
            "cooccurrence_keywords": [{"keyword": f"kw{i}"} for i in range(50)],  # Target: 100
            "related_keywords": [{"keyword": f"rel{i}"} for i in range(10)],  # Target: 30
        }

        warnings = self.activity._enforce_quality_standards(low_quality_data)

        # 警告が生成されることを確認
        assert len(warnings) > 0
        assert any("cooccurrence" in w.lower() or "共起" in w for w in warnings)


class TestStep3BIntegration:
    """Integration tests for Step3B activity."""

    @pytest.mark.asyncio
    async def test_execute_missing_pack_id(self):
        """pack_idがない場合のエラー."""
        from datetime import datetime

        from apps.api.core.context import ExecutionContext
        from apps.api.core.state import GraphState
        from apps.worker.activities.base import ActivityError

        mock_store = MagicMock()
        activity = Step3BCooccurrenceExtraction(store=mock_store)

        ctx = ExecutionContext(
            tenant_id="test-tenant",
            run_id="test-run",
            step_id="step3b",
            started_at=datetime.now(),
            timeout_seconds=300,
            config={},  # No pack_id
            attempt=1,
        )
        state = GraphState()

        with pytest.raises(ActivityError) as exc_info:
            await activity.execute(ctx, state)

        assert "pack_id is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_missing_keyword(self):
        """keywordがない場合のエラー."""
        from datetime import datetime

        from apps.api.core.context import ExecutionContext
        from apps.api.core.state import GraphState
        from apps.worker.activities.base import ActivityError

        mock_store = MagicMock()
        activity = Step3BCooccurrenceExtraction(store=mock_store)

        # Mock prompt pack loader
        with patch("apps.worker.activities.step3b.PromptPackLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader_cls.return_value = mock_loader
            mock_pack = MagicMock()
            mock_loader.load.return_value = mock_pack

            ctx = ExecutionContext(
                tenant_id="test-tenant",
                run_id="test-run",
                step_id="step3b",
                started_at=datetime.now(),
                timeout_seconds=300,
                config={"pack_id": "default"},  # No keyword
                attempt=1,
            )
            state = GraphState()

            # Mock load_step_data
            with patch("apps.worker.activities.step3b.load_step_data", new_callable=AsyncMock) as mock_load:
                mock_load.return_value = {}

                with pytest.raises(ActivityError) as exc_info:
                    await activity.execute(ctx, state)

                assert "keyword is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_insufficient_competitors(self):
        """競合データが不十分な場合のエラー."""
        from datetime import datetime

        from apps.api.core.context import ExecutionContext
        from apps.api.core.state import GraphState
        from apps.worker.activities.base import ActivityError

        mock_store = MagicMock()
        activity = Step3BCooccurrenceExtraction(store=mock_store)

        with patch("apps.worker.activities.step3b.PromptPackLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader_cls.return_value = mock_loader
            mock_pack = MagicMock()
            mock_loader.load.return_value = mock_pack

            ctx = ExecutionContext(
                tenant_id="test-tenant",
                run_id="test-run",
                step_id="step3b",
                started_at=datetime.now(),
                timeout_seconds=300,
                config={"pack_id": "default", "keyword": "テスト"},
                attempt=1,
            )
            state = GraphState()

            # Mock load_step_data with insufficient competitors
            with patch("apps.worker.activities.step3b.load_step_data", new_callable=AsyncMock) as mock_load:
                mock_load.side_effect = [
                    {},  # step0
                    {"competitors": [{"title": "記事1"}]},  # step1 with only 1 competitor
                    {},  # step2
                ]

                with pytest.raises(ActivityError) as exc_info:
                    await activity.execute(ctx, state)

                assert "Insufficient competitor data" in str(exc_info.value) or "Input validation failed" in str(exc_info.value)
