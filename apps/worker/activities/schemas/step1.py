"""Step 1 (Competitor Fetch) output schema."""

from pydantic import BaseModel, Field


class CompetitorPage(BaseModel):
    """競合ページの情報."""

    url: str = Field(..., description="ページURL")
    title: str = Field(default="", description="ページタイトル")
    content: str = Field(..., max_length=15000, description="ページコンテンツ")
    word_count: int = Field(default=0, ge=0, description="単語数")
    headings: list[str] = Field(default_factory=list, description="見出しリスト")
    fetched_at: str = Field(default="", description="取得日時 (ISO format)")


class FetchStats(BaseModel):
    """取得統計."""

    total_urls: int = Field(default=0, ge=0, description="発見したURL総数")
    successful: int = Field(default=0, ge=0, description="取得成功数")
    failed: int = Field(default=0, ge=0, description="取得失敗数")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="成功率")


class FailedUrl(BaseModel):
    """取得失敗URL."""

    url: str = Field(..., description="URL")
    error: str = Field(default="", description="エラーメッセージ")


class Step1Output(BaseModel):
    """Step 1 structured output.

    競合記事取得の結果を表す構造化出力。
    SERP検索とページ取得の結果を含む。
    """

    step: str = "step1"
    keyword: str = Field(..., description="検索キーワード")
    serp_query: str = Field(default="", description="SERP検索クエリ")

    competitors: list[CompetitorPage] = Field(default_factory=list, description="取得した競合ページリスト")
    failed_urls: list[FailedUrl] = Field(default_factory=list, description="取得失敗したURLリスト")
    fetch_stats: FetchStats = Field(default_factory=FetchStats, description="取得統計")
