"""Tests for InputValidator."""

import pytest

from apps.worker.helpers import InputValidator


class TestValidate:
    """validate メソッドのテスト."""

    def test_all_required_present(self) -> None:
        """全ての必須フィールドが存在."""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": "value1", "field2": "value2"},
            required=["field1", "field2"],
        )

        assert result.is_valid is True
        assert result.missing_required == []

    def test_missing_required(self) -> None:
        """必須フィールドが欠落."""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": "value1"},
            required=["field1", "field2"],
        )

        assert result.is_valid is False
        assert "field2" in result.missing_required

    def test_missing_recommended(self) -> None:
        """推奨フィールドが欠落（is_valid は True）."""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": "value1"},
            required=["field1"],
            recommended=["field2"],
        )

        assert result.is_valid is True
        assert "field2" in result.missing_recommended

    def test_nested_field_required(self) -> None:
        """ネストしたフィールドの必須チェック."""
        validator = InputValidator()
        result = validator.validate(
            data={"step3a": {"query_analysis": "content"}},
            required=["step3a.query_analysis"],
        )

        assert result.is_valid is True

    def test_nested_field_missing(self) -> None:
        """ネストしたフィールドの欠落."""
        validator = InputValidator()
        result = validator.validate(
            data={"step3a": {}},
            required=["step3a.query_analysis"],
        )

        assert result.is_valid is False
        assert "step3a.query_analysis" in result.missing_required

    def test_min_length_check(self) -> None:
        """最低文字数チェック."""
        validator = InputValidator()
        result = validator.validate(
            data={"content": "short"},
            min_lengths={"content": 100},
        )

        assert any("too_short" in issue for issue in result.quality_issues)

    def test_min_count_check(self) -> None:
        """最低件数チェック."""
        validator = InputValidator()
        result = validator.validate(
            data={"items": [1, 2]},
            min_counts={"items": 5},
        )

        assert any("count_low" in issue for issue in result.quality_issues)

    def test_empty_data(self) -> None:
        """空データの場合."""
        validator = InputValidator()
        result = validator.validate(
            data={},
            required=["field1"],
        )

        assert result.is_valid is False

    def test_none_value_treated_as_missing(self) -> None:
        """None値は欠落扱い."""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": None},
            required=["field1"],
        )

        assert result.is_valid is False

    def test_empty_string_treated_as_missing(self) -> None:
        """空文字列は欠落扱い."""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": ""},
            required=["field1"],
        )

        assert result.is_valid is False

    def test_empty_list_treated_as_missing(self) -> None:
        """空リストは欠落扱い."""
        validator = InputValidator()
        result = validator.validate(
            data={"items": []},
            required=["items"],
        )

        assert result.is_valid is False


class TestGetNested:
    """get_nested メソッドのテスト."""

    def test_single_level(self) -> None:
        """単一階層."""
        validator = InputValidator()
        data = {"key": "value"}

        assert validator.get_nested(data, "key") == "value"

    def test_two_levels(self) -> None:
        """2階層."""
        validator = InputValidator()
        data = {"outer": {"inner": "value"}}

        assert validator.get_nested(data, "outer.inner") == "value"

    def test_three_levels(self) -> None:
        """3階層."""
        validator = InputValidator()
        data = {"a": {"b": {"c": "value"}}}

        assert validator.get_nested(data, "a.b.c") == "value"

    def test_missing_returns_none(self) -> None:
        """存在しないパスは None."""
        validator = InputValidator()
        data = {"key": "value"}

        assert validator.get_nested(data, "missing") is None
        assert validator.get_nested(data, "key.missing") is None
