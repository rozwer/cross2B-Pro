"""Tests for QualityValidator and related classes."""

import pytest

from apps.worker.helpers import (
    CompletenessValidator,
    CompositeValidator,
    KeywordValidator,
    RequiredElementsValidator,
    StructureValidator,
)


class TestRequiredElementsValidator:
    """RequiredElementsValidator のテスト."""

    def test_all_elements_present(self) -> None:
        """全要素が存在."""
        validator = RequiredElementsValidator(
            required_patterns={
                "intent": ["検索意図", "intent"],
                "persona": ["ペルソナ", "persona"],
            }
        )
        content = "検索意図は情報収集です。ペルソナは30代男性。"
        result = validator.validate(content)

        assert result.is_acceptable is True
        assert result.issues == []

    def test_element_missing(self) -> None:
        """要素が欠落."""
        validator = RequiredElementsValidator(
            required_patterns={
                "intent": ["検索意図"],
                "persona": ["ペルソナ"],
            }
        )
        content = "検索意図は情報収集です。"
        result = validator.validate(content)

        assert result.is_acceptable is False
        assert "missing_persona" in result.issues

    def test_max_missing_allows_some(self) -> None:
        """max_missing で欠落を許容."""
        validator = RequiredElementsValidator(
            required_patterns={
                "intent": ["検索意図"],
                "persona": ["ペルソナ"],
            },
            max_missing=1,
        )
        content = "検索意図は情報収集です。"
        result = validator.validate(content)

        assert result.is_acceptable is True

    def test_case_insensitive(self) -> None:
        """大文字小文字を区別しない."""
        validator = RequiredElementsValidator(
            required_patterns={"intent": ["INTENT"]},
        )
        content = "The search intent is informational."
        result = validator.validate(content)

        assert result.is_acceptable is True


class TestStructureValidator:
    """StructureValidator のテスト."""

    def test_sufficient_h2_sections(self) -> None:
        """十分なH2セクション."""
        validator = StructureValidator(min_h2_sections=3)
        content = """
## Section 1
Content

## Section 2
Content

## Section 3
Content
"""
        result = validator.validate(content)

        assert result.is_acceptable is True
        assert result.scores["h2_count"] == 3

    def test_insufficient_h2_sections(self) -> None:
        """H2セクション不足."""
        validator = StructureValidator(min_h2_sections=3)
        content = """
## Section 1
Content

## Section 2
Content
"""
        result = validator.validate(content)

        assert result.is_acceptable is False
        assert any("h2_count_low" in issue for issue in result.issues)

    def test_require_h3(self) -> None:
        """H3が必要な場合."""
        validator = StructureValidator(min_h2_sections=1, require_h3=True)
        content = """
## Section 1
Content

### Subsection
More content
"""
        result = validator.validate(content)

        assert result.is_acceptable is True

    def test_require_h3_missing(self) -> None:
        """H3が必要だが存在しない."""
        validator = StructureValidator(require_h3=True)
        content = """
## Section 1
Content
"""
        result = validator.validate(content)

        assert "no_h3_subsections" in result.warnings

    def test_min_word_count(self) -> None:
        """最低単語数チェック."""
        validator = StructureValidator(min_word_count=10)
        content = "Short text"
        result = validator.validate(content)

        assert result.is_acceptable is False
        assert any("word_count_low" in issue for issue in result.issues)


class TestCompletenessValidator:
    """CompletenessValidator のテスト."""

    def test_has_conclusion(self) -> None:
        """結論セクションあり."""
        validator = CompletenessValidator()
        content = """
## 本文
内容です。

## まとめ
これがまとめです。
"""
        result = validator.validate(content)

        assert result.is_acceptable is True

    def test_no_conclusion(self) -> None:
        """結論セクションなし."""
        validator = CompletenessValidator()
        content = """
## 本文
内容です。
"""
        result = validator.validate(content)

        assert result.is_acceptable is False
        assert "no_conclusion_section" in result.issues

    def test_truncation_detected(self) -> None:
        """切れの兆候を検出."""
        validator = CompletenessValidator()
        content = "本文の内容は..."
        result = validator.validate(content)

        assert "appears_truncated" in result.issues

    def test_custom_conclusion_patterns(self) -> None:
        """カスタム結論パターン."""
        validator = CompletenessValidator(conclusion_patterns=["終わり", "END"])
        content = """
## 本文
## 終わり
おしまい
"""
        result = validator.validate(content)

        assert result.is_acceptable is True


class TestKeywordValidator:
    """KeywordValidator のテスト."""

    def test_keyword_present(self) -> None:
        """キーワードが存在."""
        validator = KeywordValidator()
        # 50 words total, 1 keyword occurrence = 2% density
        content = (
            "This is a comprehensive article about search engine optimization. "
            "We will explore various marketing strategies and techniques that "
            "help improve website rankings. The key to success in SEO is "
            "understanding how search engines work. Content quality and "
            "backlinks are essential factors for better visibility."
        )
        result = validator.validate(content, keyword="SEO")

        assert result.is_acceptable is True

    def test_keyword_missing(self) -> None:
        """キーワードが存在しない."""
        validator = KeywordValidator()
        result = validator.validate("検索エンジン最適化について", keyword="SEO")

        assert result.is_acceptable is False
        assert "keyword_missing" in result.issues

    def test_keyword_density_high(self) -> None:
        """キーワード密度が高すぎる."""
        validator = KeywordValidator(max_density=2.0)
        content = "SEO SEO SEO word word word word word word word"
        result = validator.validate(content, keyword="SEO")

        assert result.is_acceptable is False
        assert any("density_high" in issue for issue in result.issues)


class TestCompositeValidator:
    """CompositeValidator のテスト."""

    def test_all_validators_pass(self) -> None:
        """全バリデータが通過."""
        composite = CompositeValidator(
            [
                RequiredElementsValidator({"keyword": ["SEO"]}),
                StructureValidator(min_h2_sections=1),
            ]
        )
        content = """
## SEO対策
SEOについて解説します。
"""
        result = composite.validate(content)

        assert result.is_acceptable is True

    def test_one_validator_fails(self) -> None:
        """1つのバリデータが失敗."""
        composite = CompositeValidator(
            [
                RequiredElementsValidator({"keyword": ["SEO"]}),
                StructureValidator(min_h2_sections=3),
            ]
        )
        content = """
## SEO対策
SEOについて解説します。
"""
        result = composite.validate(content)

        assert result.is_acceptable is False

    def test_results_merged(self) -> None:
        """結果が統合される."""
        composite = CompositeValidator(
            [
                StructureValidator(min_h2_sections=3),
                CompletenessValidator(),
            ]
        )
        content = "短いコンテンツ"
        result = composite.validate(content)

        assert len(result.issues) >= 2
