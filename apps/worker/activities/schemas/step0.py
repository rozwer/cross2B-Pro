"""Step 0 (Keyword Selection) output schema."""

from pydantic import BaseModel, Field


class Step0Output(BaseModel):
    """Step 0 structured output.

    キーワード選択・分析の結果を表す構造化出力。
    LLMの分析結果をパースして構造化データとして保存する。
    """

    step: str = "step0"
    keyword: str = Field(..., description="分析対象のキーワード")
    analysis: str = Field(..., description="LLMによる分析結果（生テキスト）")

    # Parsed fields (optional - may not always be present)
    search_intent: str = Field(default="", description="検索意図の分析")
    difficulty_score: int = Field(
        default=5, ge=1, le=10, description="難易度スコア (1-10)"
    )
    recommended_angles: list[str] = Field(
        default_factory=list, description="推奨アプローチ角度のリスト"
    )
    target_audience: str = Field(default="", description="ターゲットオーディエンス")
    content_type_suggestion: str = Field(
        default="", description="推奨コンテンツタイプ"
    )

    # Model info
    model: str = Field(default="", description="使用したLLMモデル")
    usage: dict[str, int] = Field(
        default_factory=dict, description="トークン使用量"
    )

    # Metrics
    metrics: dict[str, int] = Field(
        default_factory=dict, description="テキストメトリクス (char_count, word_count)"
    )

    # Quality info
    quality: dict[str, list[str] | int] = Field(
        default_factory=dict, description="品質チェック結果 (issues, attempts)"
    )

    # Parse result
    parse_result: dict[str, bool | str | list[str]] = Field(
        default_factory=dict,
        description="JSONパース結果 (success, format_detected, fixes_applied)",
    )
