"""Input data validation helper."""

from typing import Any

from apps.worker.helpers.schemas import InputValidationResult


class InputValidator:
    """入力データの検証."""

    def validate(
        self,
        data: dict[str, Any],
        required: list[str] | None = None,
        recommended: list[str] | None = None,
        min_lengths: dict[str, int] | None = None,
        min_counts: dict[str, int] | None = None,
    ) -> InputValidationResult:
        """
        入力データを検証.

        Args:
            data: 検証対象のデータ（ネスト可）
            required: 必須フィールド（dot notation対応、例: "step3a.query_analysis"）
            recommended: 推奨フィールド（欠落は警告のみ）
            min_lengths: 最低文字数の制約（フィールド名 -> 最低文字数）
            min_counts: 最低件数の制約（フィールド名 -> 最低件数）

        Returns:
            InputValidationResult: 検証結果
        """
        required = required or []
        recommended = recommended or []
        min_lengths = min_lengths or {}
        min_counts = min_counts or {}

        missing_required = self.check_required(data, required)
        missing_recommended = self.check_recommended(data, recommended)
        quality_issues: list[str] = []

        for field_name, min_len in min_lengths.items():
            issue = self.check_min_length(data, field_name, min_len)
            if issue:
                quality_issues.append(issue)

        for field_name, min_count in min_counts.items():
            issue = self.check_min_count(data, field_name, min_count)
            if issue:
                quality_issues.append(issue)

        return InputValidationResult(
            is_valid=len(missing_required) == 0,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            quality_issues=quality_issues,
        )

    def check_required(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> list[str]:
        """
        必須フィールドをチェック.

        Returns:
            list[str]: 欠落しているフィールド名のリスト
        """
        missing = []
        for field_name in fields:
            value = self.get_nested(data, field_name)
            if not self._is_present(value):
                missing.append(field_name)
        return missing

    def check_recommended(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> list[str]:
        """
        推奨フィールドをチェック.

        Returns:
            list[str]: 欠落しているフィールド名のリスト
        """
        missing = []
        for field_name in fields:
            value = self.get_nested(data, field_name)
            if not self._is_present(value):
                missing.append(field_name)
        return missing

    def get_nested(self, data: dict[str, Any], path: str) -> Any:
        """
        ネストしたフィールドを取得（dot notation対応）.

        Args:
            data: データ辞書
            path: ドット区切りのパス（例: "step3a.query_analysis"）

        Returns:
            Any: 取得した値、存在しなければ None
        """
        keys = path.split(".")
        current: Any = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    def check_min_length(
        self,
        data: dict[str, Any],
        field: str,
        min_len: int,
    ) -> str | None:
        """
        最低文字数をチェック.

        Returns:
            str | None: 問題があればエラーメッセージ、なければ None
        """
        value = self.get_nested(data, field)
        if value is None:
            return None
        if isinstance(value, str):
            actual_len = len(value)
            if actual_len < min_len:
                return f"{field}_too_short: {actual_len} < {min_len}"
        return None

    def check_min_count(
        self,
        data: dict[str, Any],
        field: str,
        min_count: int,
    ) -> str | None:
        """
        最低件数をチェック.

        Returns:
            str | None: 問題があればエラーメッセージ、なければ None
        """
        value = self.get_nested(data, field)
        if value is None:
            return None
        if isinstance(value, list):
            actual_count = len(value)
            if actual_count < min_count:
                return f"{field}_count_low: {actual_count} < {min_count}"
        return None

    def _is_present(self, value: Any) -> bool:
        """空文字列、None、空リストは「欠落」として扱う."""
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        return True
