# Worktree: helpers-validation 要件定義書

> **ブランチ名**: `feat/helpers-validation`
> **担当**: InputValidator + QualityValidator
> **優先度**: 最高/高（入力・出力品質保証の基盤）

---

## 目的

入力データと出力コンテンツの品質を統一的に検証するヘルパーを実装する。
全ステップで使用される品質ゲートの基盤となる。

---

## 成果物

### ファイル構成

```
apps/worker/helpers/
├── input_validator.py    # InputValidator クラス
├── quality_validator.py  # QualityValidator + 派生クラス
tests/unit/helpers/
├── test_input_validator.py
├── test_quality_validator.py
```

---

## 前提条件

**`helpers-parsing` worktree で以下が実装済みであること:**
- `schemas.py` の `QualityResult`, `InputValidationResult`

```python
# インポート例
from apps.worker.helpers.schemas import QualityResult, InputValidationResult
```

---

## 1. InputValidator (`input_validator.py`)

### 1.1 クラス定義

```python
from typing import Any
from apps.worker.helpers.schemas import InputValidationResult


class InputValidator:
    """入力データの検証"""

    def validate(
        self,
        data: dict[str, Any],
        required: list[str] | None = None,
        recommended: list[str] | None = None,
        min_lengths: dict[str, int] | None = None,
        min_counts: dict[str, int] | None = None,
    ) -> InputValidationResult:
        """
        入力データを検証

        Args:
            data: 検証対象のデータ（ネスト可）
            required: 必須フィールド（dot notation対応、例: "step3a.query_analysis"）
            recommended: 推奨フィールド（欠落は警告のみ）
            min_lengths: 最低文字数の制約（フィールド名 -> 最低文字数）
            min_counts: 最低件数の制約（フィールド名 -> 最低件数）

        Returns:
            InputValidationResult: 検証結果
        """

    def check_required(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> list[str]:
        """
        必須フィールドをチェック

        Returns:
            list[str]: 欠落しているフィールド名のリスト
        """

    def check_recommended(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> list[str]:
        """
        推奨フィールドをチェック

        Returns:
            list[str]: 欠落しているフィールド名のリスト
        """

    def get_nested(self, data: dict[str, Any], path: str) -> Any:
        """
        ネストしたフィールドを取得（dot notation対応）

        Args:
            data: データ辞書
            path: ドット区切りのパス（例: "step3a.query_analysis"）

        Returns:
            Any: 取得した値、存在しなければ None
        """

    def check_min_length(
        self,
        data: dict[str, Any],
        field: str,
        min_len: int,
    ) -> str | None:
        """
        最低文字数をチェック

        Returns:
            str | None: 問題があればエラーメッセージ、なければ None
        """

    def check_min_count(
        self,
        data: dict[str, Any],
        field: str,
        min_count: int,
    ) -> str | None:
        """
        最低件数をチェック

        Returns:
            str | None: 問題があればエラーメッセージ、なければ None
        """
```

### 1.2 使用例

```python
from apps.worker.helpers import InputValidator

validator = InputValidator()

# Step4での使用例
result = validator.validate(
    data={
        "step3a": step3a_data,
        "step3b": step3b_data,
        "step3c": step3c_data,
    },
    required=["step3a.query_analysis", "step3b.cooccurrence_analysis"],
    recommended=["step3c.competitor_analysis"],
    min_lengths={"step3a.query_analysis": 100},
)

if not result.is_valid:
    raise ActivityError(
        f"Required inputs missing: {result.missing_required}",
        category=ErrorCategory.NON_RETRYABLE,
    )

if result.missing_recommended:
    activity.logger.warning(f"Recommended missing: {result.missing_recommended}")

if result.quality_issues:
    activity.logger.warning(f"Quality issues: {result.quality_issues}")
```

---

## 2. QualityValidator (`quality_validator.py`)

### 2.1 プロトコル定義

```python
from typing import Protocol
from apps.worker.helpers.schemas import QualityResult


class QualityValidator(Protocol):
    """品質検証のプロトコル"""

    def validate(self, content: str, **kwargs) -> QualityResult:
        """
        コンテンツを検証

        Args:
            content: 検証対象のテキスト
            **kwargs: バリデータ固有のオプション

        Returns:
            QualityResult: 検証結果
        """
        ...
```

### 2.2 RequiredElementsValidator

```python
class RequiredElementsValidator:
    """必須要素の存在チェック"""

    def __init__(
        self,
        required_patterns: dict[str, list[str]],
        max_missing: int = 0,
    ):
        """
        Args:
            required_patterns: {要素名: [検出パターンのリスト]}
                例: {"search_intent": ["検索意図", "search intent", "intent"]}
            max_missing: 許容する欠落数（デフォルト0 = 全必須）
        """
        self.required_patterns = required_patterns
        self.max_missing = max_missing

    def validate(self, content: str, **kwargs) -> QualityResult:
        """
        必須要素の存在をチェック

        ロジック:
        1. content を小文字化
        2. 各要素について、パターンのいずれかが含まれるかチェック
        3. 欠落数が max_missing 以下なら acceptable

        Returns:
            QualityResult:
                - is_acceptable: 欠落数 <= max_missing
                - issues: ["missing_{要素名}", ...]
        """
```

### 2.3 StructureValidator

```python
class StructureValidator:
    """構造的な品質チェック"""

    def __init__(
        self,
        min_h2_sections: int = 3,
        require_h3: bool = False,
        min_word_count: int = 0,
        max_word_count: int = 0,  # 0 = 制限なし
    ):
        """
        Args:
            min_h2_sections: 最低H2セクション数
            require_h3: H3サブセクションを必須とするか
            min_word_count: 最低単語数
            max_word_count: 最大単語数（0で無制限）
        """

    def validate(self, content: str, **kwargs) -> QualityResult:
        """
        構造をチェック

        チェック項目:
        1. H2セクション数 (^##\s)
        2. H3サブセクションの存在 (^###\s)
        3. 単語数

        Returns:
            QualityResult:
                - is_acceptable: 全チェック通過
                - issues: ["h2_count_low: X < Y", ...]
                - warnings: ["no_h3_subsections", ...]
                - scores: {"h2_count": X, "word_count": Y}
        """
```

### 2.4 CompletenessValidator

```python
class CompletenessValidator:
    """完全性チェック（切れていないか）"""

    def __init__(
        self,
        conclusion_patterns: list[str] | None = None,
        check_truncation: bool = True,
    ):
        """
        Args:
            conclusion_patterns: 結論を示すパターン
                デフォルト: ["まとめ", "結論", "おわり", "conclusion"]
            check_truncation: 切れの兆候をチェックするか
        """

    def validate(self, content: str, **kwargs) -> QualityResult:
        """
        完全性をチェック

        チェック項目:
        1. 結論セクションの存在
        2. 切れの兆候（末尾が "...", "…", "、" で終わる）

        Returns:
            QualityResult:
                - is_acceptable: 両方のチェック通過
                - issues: ["no_conclusion_section", "appears_truncated"]
        """
```

### 2.5 KeywordValidator

```python
class KeywordValidator:
    """キーワード関連のチェック"""

    def __init__(
        self,
        min_density: float = 0.0,
        max_density: float = 5.0,  # 5% 以上はキーワード詰め込み
    ):
        """
        Args:
            min_density: 最低キーワード密度（%）
            max_density: 最大キーワード密度（%）
        """

    def validate(self, content: str, keyword: str = "", **kwargs) -> QualityResult:
        """
        キーワード関連をチェック

        チェック項目:
        1. キーワードの存在
        2. キーワード密度が適正範囲内

        Returns:
            QualityResult:
                - is_acceptable: キーワードが存在し密度が適正
                - issues: ["keyword_missing", "keyword_density_high: X%"]
                - scores: {"keyword_density": X}
        """
```

### 2.6 CompositeValidator

```python
class CompositeValidator:
    """複数のバリデータを組み合わせる"""

    def __init__(self, validators: list[QualityValidator]):
        """
        Args:
            validators: 組み合わせるバリデータのリスト
        """
        self.validators = validators

    def validate(self, content: str, **kwargs) -> QualityResult:
        """
        全バリデータを実行して統合

        ロジック:
        1. 各バリデータの validate を順に呼び出す
        2. issues, warnings, scores を統合
        3. issues が1つでもあれば is_acceptable = False

        Returns:
            QualityResult: 統合された結果
        """
```

### 2.7 使用例

```python
from apps.worker.helpers import (
    RequiredElementsValidator,
    StructureValidator,
    CompletenessValidator,
    KeywordValidator,
    CompositeValidator,
)

# Step4（戦略的アウトライン）用のバリデータ
step4_validator = CompositeValidator([
    KeywordValidator(),  # キーワードが含まれているか
    StructureValidator(
        min_h2_sections=3,
        require_h3=True,
    ),
])

result = step4_validator.validate(outline_content, keyword=keyword)

if not result.is_acceptable:
    activity.logger.warning(f"Quality issues: {result.issues}")
    # リトライ or エラー

# Step7a（ドラフト生成）用のバリデータ
step7a_validator = CompositeValidator([
    StructureValidator(min_word_count=1000),
    CompletenessValidator(),
])
```

---

## テスト要件

### test_input_validator.py

```python
import pytest
from apps.worker.helpers import InputValidator


class TestValidate:
    """validate メソッドのテスト"""

    def test_all_required_present(self):
        """全ての必須フィールドが存在"""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": "value1", "field2": "value2"},
            required=["field1", "field2"],
        )

        assert result.is_valid is True
        assert result.missing_required == []

    def test_missing_required(self):
        """必須フィールドが欠落"""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": "value1"},
            required=["field1", "field2"],
        )

        assert result.is_valid is False
        assert "field2" in result.missing_required

    def test_missing_recommended(self):
        """推奨フィールドが欠落（is_valid は True）"""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": "value1"},
            required=["field1"],
            recommended=["field2"],
        )

        assert result.is_valid is True
        assert "field2" in result.missing_recommended

    def test_nested_field_required(self):
        """ネストしたフィールドの必須チェック"""
        validator = InputValidator()
        result = validator.validate(
            data={"step3a": {"query_analysis": "content"}},
            required=["step3a.query_analysis"],
        )

        assert result.is_valid is True

    def test_nested_field_missing(self):
        """ネストしたフィールドの欠落"""
        validator = InputValidator()
        result = validator.validate(
            data={"step3a": {}},
            required=["step3a.query_analysis"],
        )

        assert result.is_valid is False
        assert "step3a.query_analysis" in result.missing_required

    def test_min_length_check(self):
        """最低文字数チェック"""
        validator = InputValidator()
        result = validator.validate(
            data={"content": "short"},
            min_lengths={"content": 100},
        )

        assert any("too_short" in issue for issue in result.quality_issues)

    def test_min_count_check(self):
        """最低件数チェック"""
        validator = InputValidator()
        result = validator.validate(
            data={"items": [1, 2]},
            min_counts={"items": 5},
        )

        assert any("count_low" in issue for issue in result.quality_issues)

    def test_empty_data(self):
        """空データの場合"""
        validator = InputValidator()
        result = validator.validate(
            data={},
            required=["field1"],
        )

        assert result.is_valid is False

    def test_none_value_treated_as_missing(self):
        """None値は欠落扱い"""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": None},
            required=["field1"],
        )

        assert result.is_valid is False

    def test_empty_string_treated_as_missing(self):
        """空文字列は欠落扱い"""
        validator = InputValidator()
        result = validator.validate(
            data={"field1": ""},
            required=["field1"],
        )

        assert result.is_valid is False

    def test_empty_list_treated_as_missing(self):
        """空リストは欠落扱い"""
        validator = InputValidator()
        result = validator.validate(
            data={"items": []},
            required=["items"],
        )

        assert result.is_valid is False


class TestGetNested:
    """get_nested メソッドのテスト"""

    def test_single_level(self):
        """単一階層"""
        validator = InputValidator()
        data = {"key": "value"}

        assert validator.get_nested(data, "key") == "value"

    def test_two_levels(self):
        """2階層"""
        validator = InputValidator()
        data = {"outer": {"inner": "value"}}

        assert validator.get_nested(data, "outer.inner") == "value"

    def test_three_levels(self):
        """3階層"""
        validator = InputValidator()
        data = {"a": {"b": {"c": "value"}}}

        assert validator.get_nested(data, "a.b.c") == "value"

    def test_missing_returns_none(self):
        """存在しないパスは None"""
        validator = InputValidator()
        data = {"key": "value"}

        assert validator.get_nested(data, "missing") is None
        assert validator.get_nested(data, "key.missing") is None
```

### test_quality_validator.py

```python
import pytest
from apps.worker.helpers import (
    RequiredElementsValidator,
    StructureValidator,
    CompletenessValidator,
    KeywordValidator,
    CompositeValidator,
)


class TestRequiredElementsValidator:
    """RequiredElementsValidator のテスト"""

    def test_all_elements_present(self):
        """全要素が存在"""
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

    def test_element_missing(self):
        """要素が欠落"""
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

    def test_max_missing_allows_some(self):
        """max_missing で欠落を許容"""
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

    def test_case_insensitive(self):
        """大文字小文字を区別しない"""
        validator = RequiredElementsValidator(
            required_patterns={"intent": ["INTENT"]},
        )
        content = "The search intent is informational."
        result = validator.validate(content)

        assert result.is_acceptable is True


class TestStructureValidator:
    """StructureValidator のテスト"""

    def test_sufficient_h2_sections(self):
        """十分なH2セクション"""
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

    def test_insufficient_h2_sections(self):
        """H2セクション不足"""
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

    def test_require_h3(self):
        """H3が必要な場合"""
        validator = StructureValidator(require_h3=True)
        content = """
## Section 1
Content

### Subsection
More content
"""
        result = validator.validate(content)

        assert result.is_acceptable is True

    def test_require_h3_missing(self):
        """H3が必要だが存在しない"""
        validator = StructureValidator(require_h3=True)
        content = """
## Section 1
Content
"""
        result = validator.validate(content)

        # H3欠落は warning
        assert "no_h3_subsections" in result.warnings

    def test_min_word_count(self):
        """最低単語数チェック"""
        validator = StructureValidator(min_word_count=10)
        content = "Short text"
        result = validator.validate(content)

        assert result.is_acceptable is False
        assert any("word_count_low" in issue for issue in result.issues)


class TestCompletenessValidator:
    """CompletenessValidator のテスト"""

    def test_has_conclusion(self):
        """結論セクションあり"""
        validator = CompletenessValidator()
        content = """
## 本文
内容です。

## まとめ
これがまとめです。
"""
        result = validator.validate(content)

        assert result.is_acceptable is True

    def test_no_conclusion(self):
        """結論セクションなし"""
        validator = CompletenessValidator()
        content = """
## 本文
内容です。
"""
        result = validator.validate(content)

        assert result.is_acceptable is False
        assert "no_conclusion_section" in result.issues

    def test_truncation_detected(self):
        """切れの兆候を検出"""
        validator = CompletenessValidator()
        content = "本文の内容は..."
        result = validator.validate(content)

        assert "appears_truncated" in result.issues

    def test_custom_conclusion_patterns(self):
        """カスタム結論パターン"""
        validator = CompletenessValidator(
            conclusion_patterns=["終わり", "END"]
        )
        content = """
## 本文
## 終わり
おしまい
"""
        result = validator.validate(content)

        assert result.is_acceptable is True


class TestKeywordValidator:
    """KeywordValidator のテスト"""

    def test_keyword_present(self):
        """キーワードが存在"""
        validator = KeywordValidator()
        result = validator.validate("SEO対策について解説します", keyword="SEO")

        assert result.is_acceptable is True

    def test_keyword_missing(self):
        """キーワードが存在しない"""
        validator = KeywordValidator()
        result = validator.validate("検索エンジン最適化について", keyword="SEO")

        assert result.is_acceptable is False
        assert "keyword_missing" in result.issues

    def test_keyword_density_high(self):
        """キーワード密度が高すぎる"""
        validator = KeywordValidator(max_density=2.0)
        # 10単語中3回 = 30%
        content = "SEO SEO SEO word word word word word word word"
        result = validator.validate(content, keyword="SEO")

        assert result.is_acceptable is False
        assert any("density_high" in issue for issue in result.issues)


class TestCompositeValidator:
    """CompositeValidator のテスト"""

    def test_all_validators_pass(self):
        """全バリデータが通過"""
        composite = CompositeValidator([
            RequiredElementsValidator({"keyword": ["SEO"]}),
            StructureValidator(min_h2_sections=1),
        ])
        content = """
## SEO対策
SEOについて解説します。
"""
        result = composite.validate(content)

        assert result.is_acceptable is True

    def test_one_validator_fails(self):
        """1つのバリデータが失敗"""
        composite = CompositeValidator([
            RequiredElementsValidator({"keyword": ["SEO"]}),
            StructureValidator(min_h2_sections=3),
        ])
        content = """
## SEO対策
SEOについて解説します。
"""
        result = composite.validate(content)

        assert result.is_acceptable is False

    def test_results_merged(self):
        """結果が統合される"""
        composite = CompositeValidator([
            StructureValidator(min_h2_sections=3),
            CompletenessValidator(),
        ])
        content = "短いコンテンツ"
        result = composite.validate(content)

        # 両方の issues が含まれる
        assert len(result.issues) >= 2
```

---

## 実装上の注意

### フォールバック禁止

```python
# ❌ 禁止: 不明なケースでデフォルト値を返す
def validate(self, content: str, **kwargs) -> QualityResult:
    try:
        # 検証ロジック
        pass
    except:
        return QualityResult(is_acceptable=True)  # 禁止！

# ✅ 正しい: エラーは明示的に伝播
def validate(self, content: str, **kwargs) -> QualityResult:
    # 検証ロジック（例外は伝播させる）
    issues = []
    # ... 検証 ...
    return QualityResult(
        is_acceptable=len(issues) == 0,
        issues=issues,
    )
```

### Empty/None の扱い

```python
# 空文字列、None、空リストは「欠落」として扱う
def _is_present(self, value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, list) and len(value) == 0:
        return False
    return True
```

---

## 完了条件

- [ ] `apps/worker/helpers/input_validator.py` 全メソッド実装
- [ ] `apps/worker/helpers/quality_validator.py` 全クラス実装
- [ ] `apps/worker/helpers/__init__.py` にエクスポート追加
- [ ] `tests/unit/helpers/test_input_validator.py` 全テスト通過
- [ ] `tests/unit/helpers/test_quality_validator.py` 全テスト通過
- [ ] `uv run mypy apps/worker/helpers/` 型エラーなし
- [ ] `uv run ruff check apps/worker/helpers/` リントエラーなし

---

## 依存関係

### このworktreeが依存するもの
- `helpers-parsing` の `schemas.py` (QualityResult, InputValidationResult)

### このworktreeに依存するもの
- `helpers-metrics` の `QualityRetryLoop` (QualityValidator を使用)
- 全ステップ (InputValidator, QualityValidator を使用)
