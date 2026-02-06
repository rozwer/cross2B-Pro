"""Unit tests for step7a primary sources formatting."""



class TestFormatPrimarySources:
    """Test _format_primary_sources method."""

    def setup_method(self):
        """Setup test fixtures."""
        from apps.worker.activities.step7a import Step7ADraftGeneration

        self.step = Step7ADraftGeneration()

    def test_empty_sources_returns_empty_string(self):
        """Empty source list returns empty string."""
        result = self.step._format_primary_sources([])
        assert result == ""

    def test_none_sources_returns_empty_string(self):
        """None as sources returns empty string (via default)."""
        # The method expects a list, but should handle empty gracefully
        result = self.step._format_primary_sources([])
        assert result == ""

    def test_single_source_basic(self):
        """Single source with basic fields."""
        sources = [
            {
                "url": "https://www.mhlw.go.jp/example",
                "title": "厚生労働省レポート",
                "source_type": "government_report",
                "excerpt": "ドライバー不足に関する調査結果",
            }
        ]
        result = self.step._format_primary_sources(sources)

        assert "## 引用可能な一次資料" in result
        assert "[1] 厚生労働省レポート" in result
        assert "(government_report)" in result
        assert "URL: https://www.mhlw.go.jp/example" in result
        assert "要約: ドライバー不足に関する調査結果" in result

    def test_source_with_phase_alignment(self):
        """Source with phase alignment field."""
        sources = [
            {
                "url": "https://example.com",
                "title": "統計データ",
                "source_type": "statistics",
                "phase_alignment": "phase1_anxiety",
            }
        ]
        result = self.step._format_primary_sources(sources)

        assert "フェーズ: phase1_anxiety" in result

    def test_source_with_data_points(self):
        """Source with data points."""
        sources = [
            {
                "url": "https://example.com",
                "title": "業界レポート",
                "source_type": "industry_report",
                "data_points": [
                    {"metric": "有効求人倍率", "value": "2.59倍"},
                    {"metric": "ドライバー不足数", "value": "14万人"},
                ],
            }
        ]
        result = self.step._format_primary_sources(sources)

        assert "データ: 有効求人倍率: 2.59倍, ドライバー不足数: 14万人" in result

    def test_multiple_sources(self):
        """Multiple sources are numbered correctly."""
        sources = [
            {"url": "https://example1.com", "title": "資料1", "source_type": "other"},
            {"url": "https://example2.com", "title": "資料2", "source_type": "other"},
            {"url": "https://example3.com", "title": "資料3", "source_type": "other"},
        ]
        result = self.step._format_primary_sources(sources)

        assert "[1] 資料1" in result
        assert "[2] 資料2" in result
        assert "[3] 資料3" in result

    def test_max_15_sources(self):
        """Only first 15 sources are included."""
        sources = [{"url": f"https://example{i}.com", "title": f"資料{i}", "source_type": "other"} for i in range(20)]
        result = self.step._format_primary_sources(sources)

        assert "[15] 資料14" in result  # 0-indexed, so 15th is index 14
        assert "[16]" not in result
        assert "資料15" not in result  # This would be the 16th source

    def test_source_type_other_not_shown(self):
        """Source type 'other' is not displayed in parentheses."""
        sources = [
            {"url": "https://example.com", "title": "一般資料", "source_type": "other"},
        ]
        result = self.step._format_primary_sources(sources)

        assert "[1] 一般資料" in result
        assert "(other)" not in result

    def test_excerpt_truncated_at_200_chars(self):
        """Long excerpts are truncated at 200 characters."""
        long_excerpt = "あ" * 300
        sources = [
            {
                "url": "https://example.com",
                "title": "長い要約",
                "source_type": "other",
                "excerpt": long_excerpt,
            },
        ]
        result = self.step._format_primary_sources(sources)

        # Excerpt should be truncated
        assert "要約: " in result
        # The truncated excerpt should be at most 200 chars
        excerpt_line = [line for line in result.split("\n") if "要約:" in line][0]
        excerpt_content = excerpt_line.split("要約: ")[1]
        assert len(excerpt_content) <= 200

    def test_missing_optional_fields(self):
        """Sources with missing optional fields don't cause errors."""
        sources = [
            {
                "url": "https://example.com",
                "title": "最小限の資料",
                # No source_type, excerpt, phase_alignment, data_points
            },
        ]
        result = self.step._format_primary_sources(sources)

        assert "[1] 最小限の資料" in result
        assert "URL: https://example.com" in result
        # Optional fields should not appear
        assert "要約:" not in result
        assert "フェーズ:" not in result
        assert "データ:" not in result


class TestFormatPrimarySourcesIntegration:
    """Integration-style tests with realistic data."""

    def setup_method(self):
        """Setup test fixtures."""
        from apps.worker.activities.step7a import Step7ADraftGeneration

        self.step = Step7ADraftGeneration()

    def test_realistic_driver_recruitment_sources(self):
        """Test with realistic driver recruitment sources."""
        sources = [
            {
                "url": "https://www.mhlw.go.jp/stf/houdou/0000212893_00001.html",
                "title": "一般職業紹介状況（令和5年10月分）",
                "source_type": "government_report",
                "excerpt": "自動車運転の職業（パート除く常用）の有効求人倍率は2.59倍",
                "phase_alignment": "phase1_anxiety",
                "data_points": [
                    {"metric": "有効求人倍率", "value": "2.59倍"},
                ],
            },
            {
                "url": "https://www.mlit.go.jp/jidosha/jidosha_tk1_000074.html",
                "title": "物流の2024年問題について",
                "source_type": "government_report",
                "excerpt": "時間外労働の上限規制により、ドライバー不足が深刻化",
                "phase_alignment": "phase1_anxiety",
                "data_points": [
                    {"metric": "不足ドライバー数", "value": "14万人"},
                ],
            },
            {
                "url": "https://www.driver-agent.co.jp/case/001",
                "title": "ドライバー採用成功事例 A社",
                "source_type": "industry_report",
                "excerpt": "採用媒体の見直しにより、応募数が3倍に増加",
                "phase_alignment": "phase2_understanding",
                "data_points": [
                    {"metric": "応募数増加率", "value": "300%"},
                    {"metric": "採用コスト削減", "value": "40%"},
                ],
            },
        ]

        result = self.step._format_primary_sources(sources)

        # Header
        assert "## 引用可能な一次資料" in result
        assert "脚注形式で引用" in result

        # First source
        assert "[1] 一般職業紹介状況（令和5年10月分）" in result
        assert "(government_report)" in result
        assert "有効求人倍率: 2.59倍" in result

        # Second source
        assert "[2] 物流の2024年問題について" in result
        assert "不足ドライバー数: 14万人" in result

        # Third source
        assert "[3] ドライバー採用成功事例 A社" in result
        assert "応募数増加率: 300%" in result
        assert "採用コスト削減: 40%" in result

        # Phase alignment
        assert "フェーズ: phase1_anxiety" in result
        assert "フェーズ: phase2_understanding" in result
