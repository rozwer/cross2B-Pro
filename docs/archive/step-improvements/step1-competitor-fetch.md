# Step1: Competitor Fetch - 改善案

## 概要

| 項目       | 内容                                |
| ---------- | ----------------------------------- |
| ファイル   | `apps/worker/activities/step1.py`   |
| Activity名 | `step1_competitor_fetch`            |
| 使用ツール | `serp_fetch`, `page_fetch`          |
| 目的       | 競合サイトのURL取得とコンテンツ収集 |

---

## 現状分析

### リトライ戦略

**現状**:

- SERP取得失敗 → `RETRYABLE` でTemporal任せ
- 個別ページ取得失敗 → `failed_urls` に記録して続行
- 0件結果 → `NON_RETRYABLE` で即座に失敗

**問題点**:

1. **個別ページのリトライなし**: 1回失敗したらそのURLは諦める
2. **部分成功の閾値なし**: 1件でも取れれば成功扱い
3. **SERP プロバイダー固定**: SERPツールが失敗したら終了（代替なし＝正しい）
4. **タイムアウト制御なし**: 遅いサイトで全体が詰まる可能性

### フォーマット整形機構

**現状**:

- 競合データを `competitors` リストとして保存
- `content` は10,000文字で切り詰め
- `title`, `url`, `content`, `fetched_at` の4フィールド

**問題点**:

1. **コンテンツ品質チェックなし**: 403ページやエラーページも保存される
2. **メタデータ不足**: word count, language, 主要見出し等がない
3. **重複URL検出なし**: リダイレクト先が同じ場合に重複する
4. **エンコーディング問題**: 文字化けの検出・修正なし

### 中途開始機構

**現状**:

- ステップ全体の冪等性のみ（BaseActivity経由）
- SERP取得後の中間保存なし

**問題点**:

1. **SERP結果の再利用不可**: ページ取得中に失敗したら最初から
2. **部分結果の保存なし**: 5/10件取得後に失敗すると全ロスト
3. **再開ポイントがない**: failed_urlsだけでは再開できない

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 個別ページ取得のリトライ

```python
class Step1CompetitorFetch(BaseActivity):
    PAGE_FETCH_MAX_RETRIES = 2
    PAGE_FETCH_TIMEOUT = 30  # seconds

    async def _fetch_page_with_retry(
        self,
        page_fetch_tool,
        url: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """個別ページを最大2回リトライで取得"""
        last_error = None

        for attempt in range(self.PAGE_FETCH_MAX_RETRIES):
            try:
                fetch_result = await asyncio.wait_for(
                    page_fetch_tool.execute(url=url),
                    timeout=self.PAGE_FETCH_TIMEOUT,
                )

                if fetch_result.success and fetch_result.data:
                    content = fetch_result.data.get("body_text", "")

                    # コンテンツ品質チェック
                    if self._is_valid_content(content):
                        return self._extract_page_data(fetch_result.data, url), None

                    last_error = "invalid_content"
                else:
                    last_error = fetch_result.error_message

            except asyncio.TimeoutError:
                last_error = f"timeout_{self.PAGE_FETCH_TIMEOUT}s"
            except Exception as e:
                last_error = str(e)

            # リトライ前に少し待機
            if attempt < self.PAGE_FETCH_MAX_RETRIES - 1:
                await asyncio.sleep(1 * (attempt + 1))

        return None, last_error

    def _is_valid_content(self, content: str) -> bool:
        """コンテンツが有効かチェック"""
        if not content or len(content) < 100:
            return False

        # エラーページの検出
        error_indicators = [
            "404", "403", "access denied", "not found",
            "cloudflare", "captcha", "robot check",
        ]
        content_lower = content.lower()
        for indicator in error_indicators:
            if indicator in content_lower and len(content) < 500:
                return False

        return True
```

#### 1.2 部分成功の閾値設定

```python
class Step1CompetitorFetch(BaseActivity):
    MIN_SUCCESSFUL_FETCHES = 3  # 最低3件は必要
    MIN_SUCCESS_RATE = 0.3      # 30%以上は必要

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... SERP取得 ...

        # ページ取得（並列実行）
        results = await self._fetch_pages_parallel(urls, page_fetch_tool)

        # 成功率チェック
        success_count = len([r for r in results if r["success"]])
        success_rate = success_count / len(urls) if urls else 0

        if success_count < self.MIN_SUCCESSFUL_FETCHES:
            raise ActivityError(
                f"Insufficient data: only {success_count} pages fetched "
                f"(minimum: {self.MIN_SUCCESSFUL_FETCHES})",
                category=ErrorCategory.RETRYABLE,
                details={
                    "success_count": success_count,
                    "total_urls": len(urls),
                    "failed_urls": [r["url"] for r in results if not r["success"]],
                },
            )

        if success_rate < self.MIN_SUCCESS_RATE:
            activity.logger.warning(
                f"Low success rate: {success_rate:.1%} ({success_count}/{len(urls)})"
            )

        return {
            "step": self.step_id,
            "competitors": [r["data"] for r in results if r["success"]],
            "failed_urls": [r for r in results if not r["success"]],
            # ...
        }
```

#### 1.3 並列取得の最適化

```python
async def _fetch_pages_parallel(
    self,
    urls: list[str],
    page_fetch_tool,
    max_concurrent: int = 5,
) -> list[dict[str, Any]]:
    """セマフォで並列数を制限した取得"""
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def fetch_with_semaphore(url: str) -> dict[str, Any]:
        async with semaphore:
            data, error = await self._fetch_page_with_retry(page_fetch_tool, url)
            return {
                "url": url,
                "success": data is not None,
                "data": data,
                "error": error,
            }

    tasks = [fetch_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks)

    return results
```

### 2. フォーマット整形機構の導入

#### 2.1 競合データスキーマ

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class CompetitorPage(BaseModel):
    """競合ページの構造化データ"""
    url: HttpUrl
    canonical_url: Optional[HttpUrl] = None
    title: str
    meta_description: Optional[str] = None
    content: str = Field(..., max_length=15000)
    word_count: int
    language: Optional[str] = None
    headings: list[str] = Field(default_factory=list, description="H1-H3見出し")
    fetched_at: datetime
    fetch_duration_ms: int

class Step1Output(BaseModel):
    """Step1の出力スキーマ"""
    step: str = "step1"
    keyword: str
    serp_query: str
    total_found: int
    total_fetched: int
    competitors: list[CompetitorPage]
    failed_urls: list[dict[str, str]]  # {url, error}
    fetch_stats: dict[str, Any]  # 平均時間、成功率等
```

#### 2.2 コンテンツ抽出・正規化

```python
def _extract_page_data(self, raw_data: dict, url: str) -> CompetitorPage:
    """生データから構造化データを抽出"""
    content = raw_data.get("body_text", "")

    # コンテンツ正規化
    content = self._normalize_content(content)

    # 見出し抽出
    headings = self._extract_headings(raw_data.get("html", ""))

    # 言語検出（簡易）
    language = self._detect_language(content)

    return CompetitorPage(
        url=url,
        canonical_url=raw_data.get("canonical_url"),
        title=raw_data.get("title", "")[:200],
        meta_description=raw_data.get("meta_description"),
        content=content[:15000],
        word_count=len(content.split()),
        language=language,
        headings=headings[:20],  # 上位20件
        fetched_at=datetime.now(),
        fetch_duration_ms=raw_data.get("duration_ms", 0),
    )

def _normalize_content(self, content: str) -> str:
    """コンテンツの正規化"""
    # 連続空白の正規化
    content = re.sub(r'\s+', ' ', content)
    # 制御文字の除去
    content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
    # 文字化け検出・警告
    if self._has_encoding_issues(content):
        activity.logger.warning(f"Possible encoding issues in content")
    return content.strip()

def _extract_headings(self, html: str) -> list[str]:
    """HTML から見出しを抽出"""
    headings = []
    for tag in ['h1', 'h2', 'h3']:
        pattern = rf'<{tag}[^>]*>([^<]+)</{tag}>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        headings.extend([m.strip() for m in matches])
    return headings
```

#### 2.3 重複URL検出

```python
def _deduplicate_urls(self, urls: list[str]) -> list[str]:
    """URLの正規化と重複除去"""
    seen = set()
    unique_urls = []

    for url in urls:
        # URL正規化
        normalized = self._normalize_url(url)
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(url)

    return unique_urls

def _normalize_url(self, url: str) -> str:
    """URLの正規化（クエリパラメータ除去等）"""
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    # トラッキングパラメータ等を除去
    return urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        parsed.path.rstrip('/'),
        '', '', ''
    ))
```

### 3. 中途開始機構の実装

#### 3.1 SERP結果の中間保存

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # SERP取得
    serp_result = await self._fetch_serp(keyword, config)

    # 中間保存: SERP結果
    await self._save_checkpoint(
        ctx, "serp_completed",
        {"urls": serp_result["urls"], "serp_data": serp_result["raw"]}
    )

    # ページ取得
    competitors, failed = await self._fetch_pages(serp_result["urls"])

    # 最終結果
    return {...}

async def _save_checkpoint(
    self,
    ctx: ExecutionContext,
    phase: str,
    data: dict[str, Any],
) -> None:
    """中間チェックポイントを保存"""
    checkpoint_path = self.store.build_path(
        tenant_id=ctx.tenant_id,
        run_id=ctx.run_id,
        step=f"{self.step_id}/checkpoint/{phase}",
    )
    content = json.dumps(data, ensure_ascii=False).encode()
    await self.store.put(content, checkpoint_path, "application/json")
```

#### 3.2 チェックポイントからの再開

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 既存チェックポイントの確認
    checkpoint = await self._load_checkpoint(ctx, "serp_completed")

    if checkpoint:
        activity.logger.info("Resuming from SERP checkpoint")
        urls = checkpoint["urls"]
    else:
        # SERP取得
        serp_result = await self._fetch_serp(keyword, config)
        urls = serp_result["urls"]
        await self._save_checkpoint(ctx, "serp_completed", {...})

    # 既に取得済みのページをスキップ
    fetched_checkpoint = await self._load_checkpoint(ctx, "pages_partial")
    already_fetched = set()
    partial_results = []

    if fetched_checkpoint:
        already_fetched = set(fetched_checkpoint.get("fetched_urls", []))
        partial_results = fetched_checkpoint.get("results", [])

    # 残りを取得
    remaining_urls = [u for u in urls if u not in already_fetched]

    if remaining_urls:
        new_results = await self._fetch_pages_parallel(remaining_urls, page_fetch_tool)
        # 部分結果を更新保存
        all_results = partial_results + new_results
        await self._save_checkpoint(ctx, "pages_partial", {
            "fetched_urls": list(already_fetched) + remaining_urls,
            "results": all_results,
        })
    else:
        all_results = partial_results

    return self._build_output(all_results)
```

---

## 優先度と実装順序

| 優先度 | 改善項目               | 工数見積 | 理由               |
| ------ | ---------------------- | -------- | ------------------ |
| **高** | 個別ページリトライ     | 2h       | 取得成功率向上     |
| **高** | コンテンツ品質チェック | 2h       | 無効データ排除     |
| **高** | 部分成功閾値           | 1h       | 最低品質保証       |
| **中** | 構造化出力スキーマ     | 2h       | データ品質向上     |
| **中** | 中間チェックポイント   | 3h       | 再開効率化         |
| **低** | 重複URL検出            | 1h       | エッジケース対応   |
| **低** | 並列数最適化           | 1h       | パフォーマンス向上 |

---

## テスト観点

1. **正常系**: 10件中8件以上取得できる
2. **リトライ**: 一時的な失敗後にリトライで成功
3. **閾値**: 3件未満でエラーになる
4. **品質フィルタ**: エラーページが除外される
5. **チェックポイント**: 途中から再開できる
6. **タイムアウト**: 遅いサイトで全体が止まらない
