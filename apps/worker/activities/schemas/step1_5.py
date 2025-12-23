"""Step 1.5 (Related Keyword Competitor Extraction) output schema.

関連キーワードの上位サイト競合本文を抽出するオプション工程。
step0のrecommended_anglesを参照して関連KW選定を最適化する。
"""

from pydantic import BaseModel, Field


class RelatedCompetitorArticle(BaseModel):
    """関連キーワードに対する競合記事情報."""

    related_keyword: str = Field(..., description="関連キーワード")
    url: str = Field(..., description="競合記事URL")
    title: str = Field(default="", description="記事タイトル")
    content_summary: str = Field(default="", max_length=2000, description="コンテンツ要約")
    word_count: int = Field(default=0, ge=0, description="単語数")
    headings: list[str] = Field(default_factory=list, description="見出しリスト")
    fetched_at: str = Field(default="", description="取得日時 (ISO format)")


class RelatedKeywordData(BaseModel):
    """関連キーワードごとの競合データ."""

    keyword: str = Field(..., description="関連キーワード")
    search_results_count: int = Field(default=0, ge=0, description="検索結果数")
    competitors: list[RelatedCompetitorArticle] = Field(
        default_factory=list,
        description="競合記事リスト",
    )
    fetch_success_count: int = Field(default=0, ge=0, description="取得成功数")
    fetch_failed_count: int = Field(default=0, ge=0, description="取得失敗数")


class FetchMetadata(BaseModel):
    """取得メタデータ."""

    fetched_at: str = Field(default="", description="取得完了日時 (ISO format)")
    source: str = Field(default="serp_fetch", description="データソース")
    total_keywords_processed: int = Field(default=0, ge=0, description="処理した関連KW数")
    total_articles_fetched: int = Field(default=0, ge=0, description="取得した競合記事総数")


class Step1_5Output(BaseModel):
    """Step 1.5 structured output.

    関連キーワードの競合記事取得結果を表す構造化出力。
    step0のrecommended_anglesを活用して関連KW選定を最適化。
    """

    step: str = "step1_5"
    related_keywords_analyzed: int = Field(
        default=0,
        ge=0,
        description="分析した関連キーワード数",
    )
    related_competitor_data: list[RelatedKeywordData] = Field(
        default_factory=list,
        description="関連KW毎の競合データ",
    )
    metadata: FetchMetadata = Field(
        default_factory=FetchMetadata,
        description="取得メタデータ",
    )
    skipped: bool = Field(default=False, description="スキップされたかどうか")
    skip_reason: str | None = Field(default=None, description="スキップ理由")
