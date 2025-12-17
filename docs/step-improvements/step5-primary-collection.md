# Step5: Primary Collection - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step5.py` |
| Activity名 | `step5_primary_collection` |
| 使用ツール | `primary_collector`, `url_verify` |
| 使用LLM | Gemini（クエリ生成用） |
| 目的 | 一次資料（論文、統計、公式データ）の収集 |

---

## 現状分析

### リトライ戦略

**現状**:
- 個別クエリの失敗は `failed_queries` に記録して続行
- ツール未登録時は警告のみで続行
- **フォールバック発見**: Line 92-98 でパース失敗時に基本クエリへフォールバック

**問題点**:
1. **フォールバック禁止違反**: LLM パース失敗時に固定クエリへフォールバックしている
2. **ツール未登録時の挙動が曖昧**: primary_collector がない場合の処理が不明確
3. **URL 検証失敗時のリトライなし**: 1回失敗したらそのソースは除外

### フォーマット整形機構

**現状**:
- `sources` リストとして保存
- 各ソースは `url`, `title`, `excerpt`, `verified` フィールド
- URL 検証でステータス200のみを verified とする

**問題点**:
1. **ソース品質の評価なし**: 学術論文と一般記事の区別がない
2. **信頼性スコアなし**: ソースの信頼度が不明
3. **重複検出なし**: 同じソースが複数回収集される可能性

### 中途開始機構

**現状**:
- ステップ全体の冪等性のみ
- クエリ生成後のチェックポイントなし

**問題点**:
1. **クエリ生成のやり直し**: 毎回 LLM でクエリ生成
2. **部分収集結果の保存なし**: 3/5クエリ完了後に失敗すると全ロスト
3. **URL 検証の中間保存なし**: 検証済みと未検証の区別が保存されない

---

## 改善案

### 1. フォールバック禁止違反の修正

#### 1.1 パース失敗時はエラーとして扱う

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # ... 準備処理 ...

    # Step 5.1: クエリ生成
    try:
        query_response = await llm.generate(...)
        search_queries = self._parse_queries(query_response.content)

        if not search_queries:
            raise ActivityError(
                "Failed to generate search queries: empty result",
                category=ErrorCategory.RETRYABLE,
                details={"raw_response": query_response.content[:500]},
            )
    except ActivityError:
        raise  # そのまま上位へ
    except Exception as e:
        # フォールバックせず、明示的にエラーとする
        raise ActivityError(
            f"Query generation failed: {e}",
            category=ErrorCategory.RETRYABLE,
            details={"error": str(e)},
        ) from e

    # ... 収集処理 ...
```

#### 1.2 ツール未登録時の明示的エラー

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    registry = ToolRegistry()

    # primary_collector は必須ツール
    try:
        primary_collector = registry.get("primary_collector")
    except Exception as e:
        raise ActivityError(
            f"primary_collector tool not available: {e}",
            category=ErrorCategory.NON_RETRYABLE,
            details={"tool": "primary_collector"},
        ) from e

    if not primary_collector:
        raise ActivityError(
            "primary_collector tool not registered",
            category=ErrorCategory.NON_RETRYABLE,
        )

    # url_verify は推奨だが必須ではない
    url_verify = registry.get("url_verify", default=None)
    if not url_verify:
        activity.logger.warning("url_verify tool not available, skipping verification")

    # ... 収集処理 ...
```

### 2. リトライ戦略の強化

#### 2.1 個別クエリのリトライ

```python
MAX_QUERY_RETRIES = 2

async def _execute_query_with_retry(
    self,
    primary_collector,
    query: str,
) -> tuple[list[dict], str | None]:
    """個別クエリをリトライ付きで実行"""
    last_error = None

    for attempt in range(MAX_QUERY_RETRIES):
        try:
            result = await primary_collector.execute(query=query)

            if result.success and result.data:
                sources = result.data.get("sources", [])
                return sources, None

            last_error = result.error_message or "Unknown error"

        except Exception as e:
            last_error = str(e)

        if attempt < MAX_QUERY_RETRIES - 1:
            await asyncio.sleep(1 * (attempt + 1))

    return [], last_error
```

#### 2.2 URL 検証のリトライ

```python
MAX_VERIFY_RETRIES = 2

async def _verify_url_with_retry(
    self,
    url_verify,
    url: str,
) -> tuple[bool, dict | None]:
    """URL検証をリトライ付きで実行"""
    for attempt in range(MAX_VERIFY_RETRIES):
        try:
            result = await url_verify.execute(url=url)
            data = result.data or {}

            if result.success:
                return data.get("status") == 200, data

        except Exception:
            pass

        if attempt < MAX_VERIFY_RETRIES - 1:
            await asyncio.sleep(0.5)

    return False, None
```

#### 2.3 最低収集件数の保証

```python
MIN_SOURCES_REQUIRED = 2
MIN_VERIFIED_SOURCES = 1

async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # ... 収集・検証処理 ...

    # 最低件数チェック
    if len(collected_sources) < MIN_SOURCES_REQUIRED:
        raise ActivityError(
            f"Insufficient sources collected: {len(collected_sources)} "
            f"(minimum: {MIN_SOURCES_REQUIRED})",
            category=ErrorCategory.RETRYABLE,
            details={
                "collected": len(collected_sources),
                "failed_queries": failed_queries,
            },
        )

    if len(verified_sources) < MIN_VERIFIED_SOURCES:
        activity.logger.warning(
            f"Low verified source count: {len(verified_sources)}"
        )
        # 検証済みが少なくても続行（警告のみ）

    return {...}
```

### 3. フォーマット整形機構の導入

#### 3.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal, Optional
from datetime import datetime

class PrimarySource(BaseModel):
    """一次資料"""
    url: HttpUrl
    title: str
    source_type: Literal[
        "academic_paper",
        "government_report",
        "statistics",
        "official_document",
        "industry_report",
        "news_article",
        "other"
    ]
    excerpt: str = Field(..., max_length=500)
    publication_date: Optional[datetime] = None
    author_organization: Optional[str] = None
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    verified: bool = False
    verification_status: Optional[int] = None  # HTTP status
    relevance_to_outline: list[str] = Field(
        default_factory=list,
        description="関連するアウトラインセクション"
    )

class Step5Output(BaseModel):
    """Step5 の構造化出力"""
    keyword: str
    search_queries: list[str]
    sources: list[PrimarySource]
    invalid_sources: list[dict]
    failed_queries: list[dict]
    collection_stats: dict[str, int]
    source_type_distribution: dict[str, int]
```

#### 3.2 ソース品質評価

```python
def _evaluate_source_quality(self, source: dict, url: str) -> PrimarySource:
    """ソースの品質を評価"""
    # ソースタイプの推定
    source_type = self._classify_source_type(url, source)

    # 信頼性スコアの計算
    credibility = self._calculate_credibility(source_type, url, source)

    return PrimarySource(
        url=url,
        title=source.get("title", ""),
        source_type=source_type,
        excerpt=source.get("excerpt", "")[:500],
        credibility_score=credibility,
        verified=False,  # 後で検証
    )

def _classify_source_type(self, url: str, source: dict) -> str:
    """URLと内容からソースタイプを分類"""
    url_lower = url.lower()

    # 学術論文
    if any(d in url_lower for d in [".edu", "scholar.google", "researchgate", "pubmed"]):
        return "academic_paper"

    # 政府機関
    if any(d in url_lower for d in [".gov", ".go.jp", "mhlw.go.jp", "stat.go.jp"]):
        return "government_report"

    # 統計データ
    if any(kw in url_lower for kw in ["statistics", "stats", "data", "survey"]):
        return "statistics"

    # 業界レポート
    if any(d in url_lower for d in ["mckinsey", "bcg", "deloitte", "pwc"]):
        return "industry_report"

    # ニュース
    if any(d in url_lower for d in ["news", "reuters", "bloomberg", "nikkei"]):
        return "news_article"

    return "other"

def _calculate_credibility(
    self,
    source_type: str,
    url: str,
    source: dict,
) -> float:
    """信頼性スコアを計算"""
    base_scores = {
        "academic_paper": 0.9,
        "government_report": 0.85,
        "statistics": 0.8,
        "official_document": 0.8,
        "industry_report": 0.7,
        "news_article": 0.5,
        "other": 0.3,
    }

    score = base_scores.get(source_type, 0.3)

    # HTTPS ボーナス
    if url.startswith("https://"):
        score = min(score + 0.05, 1.0)

    # 著者/組織情報があればボーナス
    if source.get("author") or source.get("organization"):
        score = min(score + 0.05, 1.0)

    return score
```

#### 3.3 重複検出

```python
def _deduplicate_sources(
    self,
    sources: list[PrimarySource],
) -> list[PrimarySource]:
    """重複ソースを除去"""
    seen_urls = set()
    seen_titles = set()
    unique_sources = []

    for source in sources:
        # URL正規化
        normalized_url = self._normalize_url(str(source.url))

        if normalized_url in seen_urls:
            continue

        # タイトルの類似度チェック（完全一致のみ）
        normalized_title = source.title.lower().strip()
        if normalized_title in seen_titles:
            continue

        seen_urls.add(normalized_url)
        seen_titles.add(normalized_title)
        unique_sources.append(source)

    return unique_sources
```

### 4. 中途開始機構の実装

#### 4.1 クエリ生成後のチェックポイント

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # クエリチェックポイント
    query_checkpoint = await self._load_checkpoint(ctx, "queries_generated")

    if query_checkpoint:
        search_queries = query_checkpoint["queries"]
    else:
        # クエリ生成
        search_queries = await self._generate_queries(llm, keyword, outline)

        # チェックポイント保存
        await self._save_checkpoint(ctx, "queries_generated", {
            "queries": search_queries,
        })

    # ... 収集処理 ...
```

#### 4.2 部分収集結果の保存

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # ... クエリ生成 ...

    # 収集チェックポイント
    collection_checkpoint = await self._load_checkpoint(ctx, "collection_progress")

    if collection_checkpoint:
        completed_queries = set(collection_checkpoint["completed_queries"])
        collected_sources = collection_checkpoint["collected_sources"]
        failed_queries = collection_checkpoint["failed_queries"]
    else:
        completed_queries = set()
        collected_sources = []
        failed_queries = []

    # 未完了クエリのみ実行
    for query in search_queries:
        if query in completed_queries:
            continue

        sources, error = await self._execute_query_with_retry(primary_collector, query)

        if sources:
            collected_sources.extend(sources)
        if error:
            failed_queries.append({"query": query, "error": error})

        completed_queries.add(query)

        # 各クエリ完了後にチェックポイント保存
        await self._save_checkpoint(ctx, "collection_progress", {
            "completed_queries": list(completed_queries),
            "collected_sources": collected_sources,
            "failed_queries": failed_queries,
        })

    # ... 検証処理 ...
```

---

## 重要な修正点

### フォールバック禁止の遵守

現在のコード（Line 92-98）には以下のフォールバックがあります：

```python
except Exception:
    # Fall back to basic queries if parsing fails  ← 禁止違反
    search_queries = [
        f"{keyword} research statistics",
        f"{keyword} official data",
        f"{keyword} academic study",
    ]
```

これは **フォールバック禁止ルール** に違反しています。修正後：

```python
except Exception as e:
    raise ActivityError(
        f"Query generation failed: {e}",
        category=ErrorCategory.RETRYABLE,
    ) from e
```

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **最高** | フォールバック削除 | 30m | ルール違反の修正 |
| **高** | ツール必須化 | 1h | 曖昧な挙動の解消 |
| **高** | 構造化出力スキーマ | 2h | ソース品質の可視化 |
| **中** | ソース品質評価 | 2h | 信頼性の明確化 |
| **中** | 部分収集チェックポイント | 2h | 再実行効率化 |
| **低** | 重複検出 | 1h | データ品質向上 |
| **低** | URL検証リトライ | 1h | 検証成功率向上 |

---

## テスト観点

1. **正常系**: 一次資料が収集・検証される
2. **フォールバック禁止**: パース失敗でエラーが発生する
3. **ツール未登録**: primary_collector 未登録でエラー
4. **最低件数**: 収集件数不足でリトライ可能エラー
5. **チェックポイント**: 途中から再開できる
6. **重複除去**: 同一URLが重複しない
7. **品質評価**: source_type と credibility_score が正しく設定される
