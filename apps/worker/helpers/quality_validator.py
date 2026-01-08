"""Quality validation helpers for content verification."""

import re
from typing import Protocol

from apps.worker.helpers.schemas import QualityResult


class QualityValidator(Protocol):
    """品質検証のプロトコル."""

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """
        コンテンツを検証.

        Args:
            content: 検証対象のテキスト
            **kwargs: バリデータ固有のオプション

        Returns:
            QualityResult: 検証結果
        """
        ...


class RequiredElementsValidator:
    """必須要素の存在チェック."""

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

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """
        必須要素の存在をチェック.

        ロジック:
        1. content を小文字化
        2. 各要素について、パターンのいずれかが含まれるかチェック
        3. 欠落数が max_missing 以下なら acceptable

        Returns:
            QualityResult:
                - is_acceptable: 欠落数 <= max_missing
                - issues: ["missing_{要素名}", ...]
        """
        content_lower = content.lower()
        issues: list[str] = []

        for element_name, patterns in self.required_patterns.items():
            found = False
            for pattern in patterns:
                if pattern.lower() in content_lower:
                    found = True
                    break
            if not found:
                issues.append(f"missing_{element_name}")

        return QualityResult(
            is_acceptable=len(issues) <= self.max_missing,
            issues=issues,
        )


class StructureValidator:
    """構造的な品質チェック."""

    def __init__(
        self,
        min_h2_sections: int = 3,
        require_h3: bool = False,
        min_word_count: int = 0,
        max_word_count: int = 0,
    ):
        """
        Args:
            min_h2_sections: 最低H2セクション数
            require_h3: H3サブセクションを必須とするか
            min_word_count: 最低単語数
            max_word_count: 最大単語数（0で無制限）
        """
        self.min_h2_sections = min_h2_sections
        self.require_h3 = require_h3
        self.min_word_count = min_word_count
        self.max_word_count = max_word_count

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """
        構造をチェック.

        チェック項目:
        1. H2セクション数 (^##\\s)
        2. H3サブセクションの存在 (^###\\s)
        3. 単語数

        Returns:
            QualityResult:
                - is_acceptable: 全チェック通過
                - issues: ["h2_count_low: X < Y", ...]
                - warnings: ["no_h3_subsections", ...]
                - scores: {"h2_count": X, "word_count": Y}
        """
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        h2_pattern = re.compile(r"^##\s", re.MULTILINE)
        h2_count = len(h2_pattern.findall(content))
        scores["h2_count"] = float(h2_count)

        if h2_count < self.min_h2_sections:
            issues.append(f"h2_count_low: {h2_count} < {self.min_h2_sections}")

        h3_pattern = re.compile(r"^###\s", re.MULTILINE)
        h3_count = len(h3_pattern.findall(content))
        scores["h3_count"] = float(h3_count)

        if self.require_h3 and h3_count == 0:
            warnings.append("no_h3_subsections")

        words = content.split()
        word_count = len(words)
        scores["word_count"] = float(word_count)

        if self.min_word_count > 0 and word_count < self.min_word_count:
            issues.append(f"word_count_low: {word_count} < {self.min_word_count}")

        if self.max_word_count > 0 and word_count > self.max_word_count:
            issues.append(f"word_count_high: {word_count} > {self.max_word_count}")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )


class CompletenessValidator:
    """完全性チェック（切れていないか）."""

    DEFAULT_CONCLUSION_PATTERNS = ["まとめ", "結論", "おわり", "conclusion"]

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
        self.conclusion_patterns = conclusion_patterns if conclusion_patterns is not None else self.DEFAULT_CONCLUSION_PATTERNS
        self.check_truncation = check_truncation

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """
        完全性をチェック.

        チェック項目:
        1. 結論セクションの存在
        2. 切れの兆候（末尾が "...", "…", "、" で終わる）

        Returns:
            QualityResult:
                - is_acceptable: 両方のチェック通過
                - issues: ["no_conclusion_section", "appears_truncated"]
        """
        issues: list[str] = []
        content_lower = content.lower()

        has_conclusion = False
        for pattern in self.conclusion_patterns:
            if pattern.lower() in content_lower:
                has_conclusion = True
                break

        if not has_conclusion:
            issues.append("no_conclusion_section")

        if self.check_truncation:
            stripped = content.rstrip()
            truncation_indicators = ["...", "…", "、"]
            for indicator in truncation_indicators:
                if stripped.endswith(indicator):
                    issues.append("appears_truncated")
                    break

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
        )


class KeywordValidator:
    """キーワード関連のチェック."""

    def __init__(
        self,
        min_density: float = 0.0,
        max_density: float = 5.0,
    ):
        """
        Args:
            min_density: 最低キーワード密度（%）
            max_density: 最大キーワード密度（%）
        """
        self.min_density = min_density
        self.max_density = max_density

    def validate(self, content: str, keyword: str = "", **kwargs: str) -> QualityResult:
        """
        キーワード関連をチェック.

        チェック項目:
        1. キーワードの存在
        2. キーワード密度が適正範囲内

        Returns:
            QualityResult:
                - is_acceptable: キーワードが存在し密度が適正
                - issues: ["keyword_missing", "keyword_density_high: X%"]
                - scores: {"keyword_density": X}
        """
        issues: list[str] = []
        scores: dict[str, float] = {}

        if not keyword:
            return QualityResult(is_acceptable=True, issues=[], scores={})

        content_lower = content.lower()
        keyword_lower = keyword.lower()

        if keyword_lower not in content_lower:
            issues.append("keyword_missing")
            scores["keyword_density"] = 0.0
            return QualityResult(
                is_acceptable=False,
                issues=issues,
                scores=scores,
            )

        words = content.split()
        total_words = len(words)
        if total_words == 0:
            scores["keyword_density"] = 0.0
            return QualityResult(is_acceptable=True, issues=[], scores=scores)

        keyword_count = content_lower.count(keyword_lower)
        density = (keyword_count / total_words) * 100
        scores["keyword_density"] = density

        if density < self.min_density:
            issues.append(f"keyword_density_low: {density:.2f}%")

        if density > self.max_density:
            issues.append(f"keyword_density_high: {density:.2f}%")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            scores=scores,
        )


class CompositeValidator:
    """複数のバリデータを組み合わせる."""

    def __init__(self, validators: list[QualityValidator]):
        """
        Args:
            validators: 組み合わせるバリデータのリスト
        """
        self.validators = validators

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """
        全バリデータを実行して統合.

        ロジック:
        1. 各バリデータの validate を順に呼び出す
        2. issues, warnings, scores を統合
        3. issues が1つでもあれば is_acceptable = False

        Returns:
            QualityResult: 統合された結果
        """
        all_issues: list[str] = []
        all_warnings: list[str] = []
        all_scores: dict[str, float] = {}

        for validator in self.validators:
            result = validator.validate(content, **kwargs)
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
            all_scores.update(result.scores)

        return QualityResult(
            is_acceptable=len(all_issues) == 0,
            issues=all_issues,
            warnings=all_warnings,
            scores=all_scores,
        )


# =============================================================================
# blog.System Ver8.3 対応バリデータ
# =============================================================================


class FourPillarsValidator:
    """4本柱評価のバリデーション.

    blog.System Ver8.3 で導入された4本柱評価の検証を行う。
    - 神経科学（Neuroscience）: phase 1-3, score 0-100
    - 行動経済学（Behavioral Economics）: score 0-100
    - LLMO: citation_potential high/medium/low, score 0-100
    - KGI: expected_cvr 0-100%, score 0-100
    """

    VALID_PHASES = {1, 2, 3}
    VALID_CITATION_POTENTIALS = {"high", "medium", "low"}

    def __init__(self, strict: bool = False):
        """
        Args:
            strict: True の場合、全フィールドが必須。
                    False の場合、存在するフィールドのみ検証。
        """
        self.strict = strict

    def validate_dict(self, data: dict[str, object] | None) -> QualityResult:
        """
        4本柱評価データを検証.

        Args:
            data: FourPillarsEvaluation の dict 表現

        Returns:
            QualityResult: 検証結果
        """
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        if data is None:
            if self.strict:
                issues.append("four_pillars_missing")
            return QualityResult(
                is_acceptable=len(issues) == 0,
                issues=issues,
                warnings=warnings,
                scores=scores,
            )

        # 神経科学
        neuroscience = data.get("neuroscience", {})
        if neuroscience:
            phase = neuroscience.get("phase")
            if phase is not None and phase not in self.VALID_PHASES:
                issues.append(f"neuroscience_phase_invalid: {phase} not in 1-3")

            ns_score = neuroscience.get("score")
            if ns_score is not None:
                if not (0 <= ns_score <= 100):
                    issues.append(f"neuroscience_score_invalid: {ns_score} not in 0-100")
                else:
                    scores["neuroscience_score"] = float(ns_score)

        # 行動経済学
        behavioral = data.get("behavioral_economics", {})
        if behavioral:
            be_score = behavioral.get("score")
            if be_score is not None:
                if not (0 <= be_score <= 100):
                    issues.append(f"behavioral_economics_score_invalid: {be_score} not in 0-100")
                else:
                    scores["behavioral_economics_score"] = float(be_score)

        # LLMO
        llmo = data.get("llmo", {})
        if llmo:
            citation = llmo.get("citation_potential")
            if citation is not None and citation not in self.VALID_CITATION_POTENTIALS:
                issues.append(f"llmo_citation_potential_invalid: {citation}")

            llmo_score = llmo.get("score")
            if llmo_score is not None:
                if not (0 <= llmo_score <= 100):
                    issues.append(f"llmo_score_invalid: {llmo_score} not in 0-100")
                else:
                    scores["llmo_score"] = float(llmo_score)

        # KGI
        kgi = data.get("kgi", {})
        if kgi:
            cvr = kgi.get("expected_cvr")
            if cvr is not None:
                if not (0.0 <= cvr <= 100.0):
                    issues.append(f"kgi_expected_cvr_invalid: {cvr} not in 0-100%")
                else:
                    scores["kgi_expected_cvr"] = float(cvr)

            kgi_score = kgi.get("score")
            if kgi_score is not None:
                if not (0 <= kgi_score <= 100):
                    issues.append(f"kgi_score_invalid: {kgi_score} not in 0-100")
                else:
                    scores["kgi_score"] = float(kgi_score)

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """
        コンテンツから4本柱評価を検証（Protocol 互換）.

        Note:
            このメソッドは QualityValidator Protocol に準拠するためのもの。
            実際の検証には validate_dict() を使用することを推奨。
        """
        # content から JSON を抽出して検証する場合に使用
        # 通常は validate_dict() を直接使用
        return QualityResult(is_acceptable=True, issues=[])


class ArticleStrategyValidator:
    """記事戦略のバリデーション.

    blog.System Ver8.3 で導入された記事戦略の検証を行う。
    - type: 6種類（comprehensive_guide, deep_dive, case_study, comparison, news_analysis, how_to）
    - strategy: standard / topic_cluster
    - urgency: high / medium / low
    """

    VALID_ARTICLE_TYPES = {
        "comprehensive_guide",
        "deep_dive",
        "case_study",
        "comparison",
        "news_analysis",
        "how_to",
    }
    VALID_STRATEGIES = {"standard", "topic_cluster"}
    VALID_URGENCIES = {"high", "medium", "low"}

    def __init__(self, strict: bool = False):
        """
        Args:
            strict: True の場合、全フィールドが必須。
        """
        self.strict = strict

    def validate_dict(self, data: dict[str, object] | None) -> QualityResult:
        """
        記事戦略データを検証.

        Args:
            data: ArticleStrategy の dict 表現

        Returns:
            QualityResult: 検証結果
        """
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        if data is None:
            if self.strict:
                issues.append("article_strategy_missing")
            return QualityResult(
                is_acceptable=len(issues) == 0,
                issues=issues,
                warnings=warnings,
                scores=scores,
            )

        # 記事タイプ
        article_type = data.get("type")
        if article_type is not None and article_type not in self.VALID_ARTICLE_TYPES:
            issues.append(f"article_type_invalid: {article_type}")

        # 戦略
        strategy = data.get("strategy")
        if strategy is not None and strategy not in self.VALID_STRATEGIES:
            issues.append(f"strategy_invalid: {strategy}")

        # 背景情報
        background_raw = data.get("background", {})
        background: dict[str, object] = background_raw if isinstance(background_raw, dict) else {}
        if background:
            urgency = background.get("urgency")
            if urgency is not None and urgency not in self.VALID_URGENCIES:
                issues.append(f"urgency_invalid: {urgency}")

            # 背景情報の充実度をスコア化
            filled_fields = sum(1 for field in ["why_now", "target_pain", "key_message"] if background.get(field))
            scores["background_completeness"] = (filled_fields / 3) * 100

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """
        コンテンツから記事戦略を検証（Protocol 互換）.

        Note:
            実際の検証には validate_dict() を使用することを推奨。
        """
        return QualityResult(is_acceptable=True, issues=[])
