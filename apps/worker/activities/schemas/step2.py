"""Step 2 (CSV Validation) output schema."""

from typing import Any

from pydantic import BaseModel, Field


class ValidatedCompetitor(BaseModel):
    """検証済み競合データ."""

    url: str = Field(..., description="正規化されたURL")
    title: str = Field(default="", description="ページタイトル")
    content: str = Field(..., description="正規化されたコンテンツ")
    content_hash: str = Field(default="", description="コンテンツのSHA256ハッシュ")
    word_count: int = Field(default=0, ge=0, description="単語数")
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0, description="品質スコア")
    headings: list[str] = Field(default_factory=list, description="見出しリスト")
    auto_fixes_applied: list[str] = Field(default_factory=list, description="適用された自動修復")


class ValidationIssue(BaseModel):
    """バリデーション問題."""

    field: str = Field(..., description="問題のあるフィールド")
    issue: str = Field(..., description="問題の種類")
    severity: str = Field(..., description="深刻度 (ERROR, WARNING)")
    value: int | str | None = Field(default=None, description="問題の値")


class RejectedRecord(BaseModel):
    """却下されたレコード."""

    url: str = Field(default="unknown", description="URL")
    issues: list[ValidationIssue] = Field(default_factory=list, description="バリデーション問題リスト")


class ValidationSummary(BaseModel):
    """バリデーションサマリー."""

    total_records: int = Field(default=0, ge=0, description="総レコード数")
    valid_records: int = Field(default=0, ge=0, description="有効レコード数")
    rejected_records: int = Field(default=0, ge=0, description="却下レコード数")
    auto_fixed_count: int = Field(default=0, ge=0, description="自動修復されたレコード数")
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="エラー率")


class WordCountAnalysis(BaseModel):
    """競合記事の文字数分析."""

    min: int = Field(..., ge=0, description="最小文字数")
    max: int = Field(..., ge=0, description="最大文字数")
    average: float = Field(..., ge=0, description="平均文字数")
    median: float = Field(..., ge=0, description="中央値文字数")


class StructureAnalysis(BaseModel):
    """競合記事の構造分析."""

    avg_h2_count: float = Field(default=0.0, ge=0, description="平均H2見出し数")
    avg_h3_count: float = Field(default=0.0, ge=0, description="平均H3見出し数")
    common_patterns: list[str] = Field(default_factory=list, description="共通パターン（例: FAQ, まとめ, 比較表）")


class Step2Output(BaseModel):
    """Step 2 structured output.

    CSV検証の結果を表す構造化出力。
    バリデーション、自動修復、品質スコアリングの結果を含む。
    """

    step: str = "step2"
    is_valid: bool = Field(..., description="全体の検証結果")

    validation_summary: ValidationSummary = Field(default_factory=ValidationSummary, description="バリデーションサマリー")
    validated_data: list[ValidatedCompetitor] = Field(default_factory=list, description="検証済みデータリスト")
    rejected_data: list[RejectedRecord] = Field(default_factory=list, description="却下されたデータリスト")
    validation_issues: list[dict[str, Any]] = Field(default_factory=list, description="全バリデーション問題リスト")

    # blog.System 統合用フィールド（オプショナル）
    word_count_analysis: WordCountAnalysis | None = Field(default=None, description="競合記事の文字数分析")
    structure_analysis: StructureAnalysis | None = Field(default=None, description="競合記事の構造分析")
