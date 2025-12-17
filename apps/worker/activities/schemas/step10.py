"""Step10 Final Output schema."""

from pydantic import BaseModel, Field


class HTMLValidationResult(BaseModel):
    """HTML検証結果."""

    is_valid: bool
    has_required_tags: bool = False
    has_meta_tags: bool = False
    has_proper_heading_hierarchy: bool = False
    issues: list[str] = Field(default_factory=list)


class ArticleStats(BaseModel):
    """記事統計."""

    word_count: int
    char_count: int
    paragraph_count: int = 0
    sentence_count: int = 0
    heading_count: int = 0
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    list_count: int = 0
    link_count: int = 0
    image_count: int = 0


class PublicationReadiness(BaseModel):
    """出版準備状態."""

    is_ready: bool
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Step10Output(BaseModel):
    """Step10 の構造化出力."""

    step: str = "step10"
    keyword: str
    article_title: str = ""
    markdown_content: str
    html_content: str
    meta_description: str = ""
    publication_checklist: str
    html_validation: HTMLValidationResult
    stats: ArticleStats
    publication_readiness: PublicationReadiness
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
