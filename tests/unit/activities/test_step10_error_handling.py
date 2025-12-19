"""Step10 Error Handling Tests.

Tests for the enhanced error handling in Step10FinalOutput.
Verifies:
- Step9 data missing detection
- Step9 data corruption detection
- Field validation (final_content, meta_description, article_title)
- Error categorization and recovery suggestions
"""

import pytest

from apps.worker.activities.step10 import Step10FinalOutput


class TestStep10DataIntegrityValidation:
    """Test _validate_step9_data_integrity method."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.step10 = Step10FinalOutput()

    # === Happy Path Tests ===

    def test_valid_step9_data_passes(self) -> None:
        """Valid step9 data should pass validation."""
        valid_data = {
            "final_content": "# Test Article\n\n## Section 1\n\n" + "This is valid content. " * 100,
            "meta_description": "A valid meta description for SEO.",
            "article_title": "Test Article Title",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            valid_data
        )

        assert is_valid is True
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_valid_data_with_minimum_content_passes(self) -> None:
        """Content at exactly minimum length should pass."""
        # Create content just over minimum length with proper headings
        content = "# Heading 1\n\n## Heading 2\n\n" + "x" * 1000

        valid_data = {
            "final_content": content,
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            valid_data
        )

        assert is_valid is True
        assert len(errors) == 0

    # === Missing Data Tests ===

    def test_missing_final_content_fails(self) -> None:
        """Missing final_content should fail validation."""
        invalid_data = {
            "meta_description": "Some description",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            invalid_data
        )

        assert is_valid is False
        assert len(errors) == 1
        assert "final_content is missing" in errors[0]

    def test_none_final_content_fails(self) -> None:
        """None final_content should fail validation."""
        invalid_data = {
            "final_content": None,
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            invalid_data
        )

        assert is_valid is False
        assert "final_content is missing" in errors[0]

    def test_empty_final_content_fails(self) -> None:
        """Empty string final_content should fail validation."""
        invalid_data = {
            "final_content": "",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            invalid_data
        )

        assert is_valid is False
        assert "empty" in errors[0].lower()

    # === Type Error Tests ===

    def test_wrong_type_final_content_fails(self) -> None:
        """Non-string final_content should fail validation."""
        invalid_data = {
            "final_content": 12345,  # Wrong type
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            invalid_data
        )

        assert is_valid is False
        assert "invalid type" in errors[0]
        assert "int" in errors[0]

    def test_list_final_content_fails(self) -> None:
        """List final_content should fail validation."""
        invalid_data = {
            "final_content": ["line1", "line2"],  # Wrong type
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            invalid_data
        )

        assert is_valid is False
        assert "invalid type" in errors[0]
        assert "list" in errors[0]

    # === Content Length Tests ===

    def test_too_short_content_fails(self) -> None:
        """Content below minimum length should fail."""
        invalid_data = {
            "final_content": "Short content",  # Too short
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            invalid_data
        )

        assert is_valid is False
        assert "too short" in errors[0]

    def test_unusually_long_content_warns(self) -> None:
        """Unusually long content should generate warning."""
        # Create content over max length
        long_content = "# Test\n\n" + "x" * 150000

        valid_data = {
            "final_content": long_content,
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            valid_data
        )

        assert is_valid is True  # Should still pass
        assert len(errors) == 0
        assert any("unusually long" in w for w in warnings)

    # === Corruption Pattern Tests ===

    def test_json_content_detected_as_corruption(self) -> None:
        """Content starting with JSON should be flagged as corruption."""
        corrupted_data = {
            "final_content": '{"key": "value", "nested": {"data": true}}',
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            corrupted_data
        )

        assert is_valid is False
        assert any("corrupted" in e.lower() for e in errors)
        assert any("json" in e.lower() for e in errors)

    def test_xml_content_detected_as_corruption(self) -> None:
        """Content starting with XML declaration should be flagged."""
        corrupted_data = {
            "final_content": '<?xml version="1.0"?><root>data</root>',
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            corrupted_data
        )

        assert is_valid is False
        assert any("corrupted" in e.lower() for e in errors)

    def test_null_string_detected_as_corruption(self) -> None:
        """Literal 'null' string should be flagged as corruption."""
        corrupted_data = {
            "final_content": "null",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            corrupted_data
        )

        assert is_valid is False
        assert any("corrupted" in e.lower() for e in errors)

    def test_undefined_string_detected_as_corruption(self) -> None:
        """Literal 'undefined' string should be flagged as corruption."""
        corrupted_data = {
            "final_content": "  undefined  ",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            corrupted_data
        )

        assert is_valid is False
        assert any("corrupted" in e.lower() for e in errors)

    def test_object_object_detected_as_corruption(self) -> None:
        """'[object Object]' should be flagged as serialization error."""
        corrupted_data = {
            "final_content": "[object Object]",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            corrupted_data
        )

        assert is_valid is False
        assert any("serialization" in e.lower() for e in errors)

    # === Heading Structure Tests ===

    def test_no_headings_warns(self) -> None:
        """Content without headings should generate warning."""
        no_heading_data = {
            "final_content": "This is just plain text content without any headings. " * 100,
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            no_heading_data
        )

        assert is_valid is True  # Should still pass
        assert any("insufficient headings" in w for w in warnings)

    # === Meta Description Tests ===

    def test_invalid_type_meta_description_warns(self) -> None:
        """Non-string meta_description should generate warning."""
        data = {
            "final_content": "# Test\n\n## Section\n\n" + "content " * 200,
            "meta_description": 12345,  # Wrong type
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(data)

        assert is_valid is True  # meta_description is recommended, not required
        assert any("meta_description" in w and "invalid type" in w for w in warnings)

    def test_too_long_meta_description_warns(self) -> None:
        """Overly long meta_description should generate warning."""
        data = {
            "final_content": "# Test\n\n## Section\n\n" + "content " * 200,
            "meta_description": "x" * 350,  # Too long
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(data)

        assert is_valid is True
        assert any("meta_description" in w and "too long" in w for w in warnings)

    # === Article Title Tests ===

    def test_invalid_type_article_title_warns(self) -> None:
        """Non-string article_title should generate warning."""
        data = {
            "final_content": "# Test\n\n## Section\n\n" + "content " * 200,
            "article_title": ["Title", "Array"],  # Wrong type
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(data)

        assert is_valid is True
        assert any("article_title" in w and "invalid type" in w for w in warnings)

    def test_unusually_long_article_title_warns(self) -> None:
        """Overly long article_title should generate warning."""
        data = {
            "final_content": "# Test\n\n## Section\n\n" + "content " * 200,
            "article_title": "x" * 250,  # Too long
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(data)

        assert is_valid is True
        assert any("article_title" in w and "unusually long" in w for w in warnings)


class TestStep10ErrorDetails:
    """Test _build_error_details method."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.step10 = Step10FinalOutput()

    def test_error_details_contains_recovery_suggestions(self) -> None:
        """Error details should include recovery suggestions."""
        errors = ["step9.final_content is missing"]
        warnings = []
        step9_data = {}

        details = self.step10._build_error_details(errors, warnings, step9_data)

        assert "recovery_suggestions" in details
        assert len(details["recovery_suggestions"]) > 0

    def test_error_details_includes_data_summary(self) -> None:
        """Error details should include data summary for debugging."""
        errors = ["some error"]
        warnings = []
        step9_data = {
            "final_content": "test",
            "meta_description": "desc",
        }

        details = self.step10._build_error_details(errors, warnings, step9_data)

        assert "data_summary" in details
        assert details["data_summary"]["has_final_content"] is True
        assert details["data_summary"]["has_meta_description"] is True
        assert "available_keys" in details["data_summary"]

    def test_recovery_suggestion_for_missing_data(self) -> None:
        """Missing data should suggest re-running step9."""
        errors = ["step9.final_content is missing"]
        warnings = []
        step9_data = {}

        details = self.step10._build_error_details(errors, warnings, step9_data)

        assert any(
            "re-run step9" in s.lower() for s in details["recovery_suggestions"]
        )

    def test_recovery_suggestion_for_short_content(self) -> None:
        """Short content should suggest checking output quality."""
        errors = ["content is too short"]
        warnings = []
        step9_data = {"final_content": "short"}

        details = self.step10._build_error_details(errors, warnings, step9_data)

        assert any(
            "output quality" in s.lower() for s in details["recovery_suggestions"]
        )

    def test_recovery_suggestion_for_corrupted_data(self) -> None:
        """Corrupted data should suggest investigating serialization."""
        errors = ["content appears corrupted"]
        warnings = []
        step9_data = {"final_content": "{}"}

        details = self.step10._build_error_details(errors, warnings, step9_data)

        assert any(
            "serialization" in s.lower() for s in details["recovery_suggestions"]
        )


class TestStep10RealScenarios:
    """Integration-style tests with realistic data scenarios."""

    def setup_method(self) -> None:
        """Set up test instance."""
        self.step10 = Step10FinalOutput()

    def test_realistic_valid_article(self) -> None:
        """Test with realistic valid article content."""
        # Create content that exceeds MIN_CONTENT_LENGTH (1000 chars)
        # Using padding to ensure it's over 1000 characters
        base_content = """# SEO対策の基本ガイド

## はじめに

SEO対策は、Webサイトの検索順位を向上させるための重要な施策です。
検索エンジンからの流入を増やすことで、ビジネスの成長に大きく貢献します。
本記事では、SEO対策の基本から応用まで、初心者にもわかりやすく解説します。

## 基本的な対策

### キーワード選定

適切なキーワードを選ぶことが成功の鍵です。
ユーザーが実際に検索する言葉を調査し、競合の少ないロングテールキーワードを狙いましょう。
キーワードプランナーやサジェストツールを活用して、検索ボリュームと競合度を確認することが重要です。

### コンテンツ作成

質の高いコンテンツを作成することが重要です。
読者の悩みを解決し、価値を提供するコンテンツを心がけましょう。
オリジナリティのある情報を提供し、専門性・権威性・信頼性（E-E-A-T）を高めることが求められます。

### 内部リンクの最適化

サイト内のページ同士を適切にリンクすることで、ユーザーの回遊性を高めます。
関連コンテンツへの誘導を行い、サイト全体の構造を整理することで、クローラビリティも向上します。

### 外部リンクの獲得

信頼性の高いサイトからのリンクを獲得することで、ドメインの権威性が向上します。
質の高いコンテンツを作成し、自然なリンクを獲得することが最も効果的な方法です。

## テクニカルSEO

### ページ速度の最適化

ページの読み込み速度は、ユーザー体験とSEOの両方に影響します。
画像の最適化、キャッシュの活用、不要なスクリプトの削除などを行いましょう。
Core Web Vitalsのスコアを定期的にチェックし、改善を続けることが大切です。

### モバイル対応

Googleはモバイルファーストインデックスを採用しています。
レスポンシブデザインを採用し、モバイルでの表示を最適化しましょう。
タップターゲットのサイズやフォントの可読性にも注意が必要です。

## まとめ

SEO対策は継続的な取り組みが必要です。
定期的にデータを分析し、改善を繰り返すことで、長期的な成果を得ることができます。
最新のアルゴリズム変更にも対応しながら、ユーザーファーストの姿勢を忘れずに取り組みましょう。
焦らず着実に一歩ずつ前進していくことが、最終的な成功への近道となります。
"""
        realistic_data = {
            "final_content": base_content,
            "meta_description": "SEO対策の基本を解説。キーワード選定からコンテンツ作成まで。",
            "article_title": "SEO対策の基本ガイド",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            realistic_data
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_truncated_json_response(self) -> None:
        """Test detection of truncated JSON response from LLM."""
        truncated_data = {
            "final_content": '{"step": "step9", "final_content": "# Article',
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            truncated_data
        )

        assert is_valid is False
        assert any("json" in e.lower() for e in errors)

    def test_accidental_serialization_of_object(self) -> None:
        """Test detection of serialized object instead of content."""
        serialized_data = {
            "final_content": "[object Object]",
        }

        is_valid, errors, warnings = self.step10._validate_step9_data_integrity(
            serialized_data
        )

        assert is_valid is False
        assert any("serialization" in e.lower() for e in errors)
