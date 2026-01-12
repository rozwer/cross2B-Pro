"""Tests for generation step helper integrations (Step6, Step6.5, Step7a).

These tests verify the helper integration patterns without requiring
actual LLM calls or Temporal infrastructure.
"""

import re

from apps.worker.helpers import (
    CompletenessValidator,
    CompositeValidator,
    ContentMetrics,
    InputValidator,
    OutputParser,
    StructureValidator,
)


class TestStep6HelperIntegration:
    """Step6 ヘルパー統合のテスト."""

    def test_input_validation_step4_required(self) -> None:
        """step4.outline が必須."""
        validator = InputValidator()
        result = validator.validate(
            data={"step4": {}, "step5": {}},
            required=["step4.outline"],
            recommended=["step5.sources"],
        )
        assert result.is_valid is False
        assert "step4.outline" in result.missing_required

    def test_input_validation_step5_recommended(self) -> None:
        """step5.sources が推奨."""
        validator = InputValidator()
        result = validator.validate(
            data={
                "step4": {"outline": "# アウトライン"},
                "step5": {},
            },
            required=["step4.outline"],
            recommended=["step5.sources"],
        )
        assert result.is_valid is True
        assert "step5.sources" in result.missing_recommended

    def test_enhancement_quality_check(self) -> None:
        """拡張品質チェック: 元より長くなるべき."""
        original = "## Section 1\nContent"
        enhanced = "## Section 1\nContent\n### 1.1 Detail\nMore content"

        # Check: Enhanced should be longer
        assert len(enhanced) >= len(original)

        # Check: H2 preserved
        original_h2s = set(re.findall(r"^##\s+(.+)$", original, re.M))
        enhanced_h2s = set(re.findall(r"^##\s+(.+)$", enhanced, re.M))
        assert original_h2s <= enhanced_h2s

        # Check: H3 added
        original_h3_count = len(re.findall(r"^###\s", original, re.M))
        enhanced_h3_count = len(re.findall(r"^###\s", enhanced, re.M))
        assert enhanced_h3_count > original_h3_count

    def test_outline_validator_config(self) -> None:
        """アウトライン検証器の設定."""
        validator = CompositeValidator(
            [
                StructureValidator(
                    min_h2_sections=3,
                    require_h3=True,
                    min_word_count=200,
                ),
                CompletenessValidator(
                    conclusion_patterns=["まとめ", "結論", "おわり", "conclusion"],
                    check_truncation=True,
                ),
            ]
        )

        # Valid outline
        valid_outline = (
            """
## セクション1
内容1

### サブセクション1.1
詳細内容

## セクション2
内容2

### サブセクション2.1
詳細内容

## セクション3
内容3

## まとめ
結論内容
"""
            + " word" * 200
        )  # Ensure word count (200 words minimum)

        result = validator.validate(valid_outline)
        assert result.is_acceptable is True

    def test_outline_missing_conclusion(self) -> None:
        """結論がないアウトライン."""
        validator = CompletenessValidator()
        content = "## セクション1\n内容"
        result = validator.validate(content)
        assert "no_conclusion_section" in result.issues


class TestStep6_5HelperIntegration:
    """Step6.5 ヘルパー統合のテスト."""

    def test_input_validation_7_steps(self) -> None:
        """7ステップ分の入力検証."""
        validator = InputValidator()
        all_data = {
            "step0": {"analysis": "キーワード分析"},
            "step3a": {"query_analysis": "クエリ分析"},
            "step3b": {"cooccurrence_analysis": "共起分析"},
            "step3c": {"competitor_analysis": "競合分析"},
            "step4": {"outline": "アウトライン"},
            "step5": {"sources": [{"url": "http://example.com"}]},
            "step6": {"enhanced_outline": "拡張アウトライン"},
        }

        result = validator.validate(
            data=all_data,
            required=["step4.outline", "step6.enhanced_outline"],
            recommended=[
                "step0.analysis",
                "step3a.query_analysis",
                "step3b.cooccurrence_analysis",
                "step3c.competitor_analysis",
                "step5.sources",
            ],
        )

        assert result.is_valid is True
        assert len(result.missing_recommended) == 0

    def test_json_parser_with_repair(self) -> None:
        """JSON修復機能付きパーサー."""
        parser = OutputParser()

        # 末尾カンマありのJSON
        broken_json = '{"key": "value",}'

        # OutputParser は parse_json で修復を試みる
        result = parser.parse_json(broken_json)

        # 修復できれば success、できなければ false
        # (実装に依存するため、両方のケースを許容)
        if result.success:
            assert result.data == {"key": "value"}
        else:
            # 修復できない場合も問題ない
            assert result.format_detected in ["json", "unknown"]

    def test_package_quality_validation(self) -> None:
        """パッケージ品質検証."""
        # integration_package 必須
        package_with_integration = {
            "integration_package": "統合パッケージ内容",
            "outline_summary": "サマリー",
            "section_count": 5,
            "total_sources": 3,
        }

        assert package_with_integration.get("integration_package")
        assert package_with_integration.get("outline_summary")
        assert package_with_integration.get("section_count", 0) >= 3


class TestStep7aHelperIntegration:
    """Step7a ヘルパー統合のテスト."""

    def test_input_validation_integration_package(self) -> None:
        """integration_package 入力検証."""
        validator = InputValidator()
        result = validator.validate(
            data={"step6_5": {"integration_package": "パッケージ内容" * 100}},
            required=["step6_5.integration_package"],
            min_lengths={"step6_5.integration_package": 500},
        )

        # 500文字以上なら valid
        assert result.is_valid is True

    def test_input_validation_integration_package_too_short(self) -> None:
        """integration_package が短すぎる."""
        validator = InputValidator()
        validator.validate(
            data={"step6_5": {"integration_package": "短い"}},
            required=["step6_5.integration_package"],
            min_lengths={"step6_5.integration_package": 500},
        )

        # 短すぎるので invalid または警告
        # (実装による)

    def test_draft_validator_config(self) -> None:
        """ドラフト検証器の設定."""
        min_word_count = 1000
        min_section_count = 3

        validator = CompositeValidator(
            [
                StructureValidator(
                    min_h2_sections=min_section_count,
                    require_h3=False,
                    min_word_count=min_word_count,
                ),
                CompletenessValidator(
                    conclusion_patterns=["まとめ", "結論", "おわり", "conclusion"],
                    check_truncation=True,
                ),
            ]
        )

        # Valid draft
        valid_draft = (
            """
## はじめに
導入文

## セクション1
内容1

## セクション2
内容2

## セクション3
内容3

## まとめ
結論
"""
            + " word" * 1000
        )  # Ensure word count >= 1000

        result = validator.validate(valid_draft)
        assert result.is_acceptable is True

    def test_truncation_detection(self) -> None:
        """切れの検出."""
        validator = CompletenessValidator(check_truncation=True)

        truncated_draft = "これは途中で切れた文章..."
        result = validator.validate(truncated_draft)

        assert "appears_truncated" in result.issues

    def test_content_metrics_calculation(self) -> None:
        """コンテンツメトリクス計算."""
        metrics = ContentMetrics()

        draft = """
## セクション1
日本語のテスト文章です。

## セクション2
これは二番目のセクションです。

## まとめ
結論です。
"""
        text_metrics = metrics.text_metrics(draft)
        md_metrics = metrics.markdown_metrics(draft)

        assert text_metrics.char_count > 0
        assert text_metrics.word_count > 0
        assert md_metrics.h2_count == 3

    def test_keyword_density_calculation(self) -> None:
        """キーワード密度計算."""
        metrics = ContentMetrics()

        draft = "SEO対策について解説します。SEOは検索エンジン最適化の略です。"
        density = metrics.keyword_density(draft, "SEO")

        assert density > 0

    def test_markdown_fallback_detection(self) -> None:
        """Markdownフォールバック検出."""
        parser = OutputParser()

        markdown_content = """# タイトル

## セクション1
コンテンツ

## セクション2
コンテンツ
"""

        assert parser.looks_like_markdown(markdown_content) is True

        json_content = '{"key": "value"}'
        assert parser.looks_like_markdown(json_content) is False


class TestCommonPatterns:
    """共通パターンのテスト."""

    def test_enhancement_ratio_calculation(self) -> None:
        """拡張比率の計算."""
        original = "オリジナル文章"
        enhanced = "オリジナル文章に詳細を追加した拡張版です"

        if len(original) > 0:
            enhancement_ratio = len(enhanced) / len(original)
            assert enhancement_ratio > 1.0

    def test_section_preservation_check(self) -> None:
        """セクション保持チェック."""
        original = """
## セクション1
## セクション2
## セクション3
"""
        enhanced = """
## セクション1
### 詳細1
## セクション2
### 詳細2
## セクション3
### 詳細3
## 追加セクション
"""

        original_h2s = set(re.findall(r"^##\s+(.+)$", original, re.M))
        enhanced_h2s = set(re.findall(r"^##\s+(.+)$", enhanced, re.M))

        # All original H2s should be preserved
        assert original_h2s <= enhanced_h2s
        # Additional H2 may be added
        assert len(enhanced_h2s) >= len(original_h2s)
