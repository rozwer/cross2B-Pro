# 工程1: 競合記事本文取得

## 入力スキーマ

```json
{
  "keyword": "string (必須) - step0から",
  "num_results": "number (任意) - 取得件数上限（デフォルト10）"
}
```

## 出力スキーマ（既存）

```python
class CompetitorPage(BaseModel):
    """競合ページの情報."""
    url: str
    title: str = ""
    content: str  # max_length=15000
    word_count: int = 0
    headings: list[str] = []
    fetched_at: str = ""

class FetchStats(BaseModel):
    """取得統計."""
    total_urls: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0

class FailedUrl(BaseModel):
    """取得失敗URL."""
    url: str
    error: str = ""

class Step1Output(BaseModel):
    step: str = "step1"
    keyword: str
    serp_query: str = ""
    competitors: list[CompetitorPage]
    failed_urls: list[FailedUrl]
    fetch_stats: FetchStats
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 取得件数 | 任意（デフォルト10） | 上位10サイト固定 |
| 出力形式 | JSON | CSV + JSON |
| 追加情報 | なし | メタディスクリプション、構造化データ、公開日 |

---

## 追加スキーマ（詳細）

### CompetitorPage 拡張フィールド

```python
class CompetitorPage(BaseModel):
    """競合ページの情報 - blog.System対応."""
    # 既存フィールド
    url: str = Field(..., description="ページURL")
    title: str = Field(default="", description="ページタイトル")
    content: str = Field(..., max_length=15000, description="ページコンテンツ")
    word_count: int = Field(default=0, ge=0, description="単語数")
    headings: list[str] = Field(default_factory=list, description="見出しリスト")
    fetched_at: str = Field(default="", description="取得日時 (ISO format)")

    # 新規フィールド（オプショナル - 後方互換性維持）
    meta_description: str | None = Field(
        default=None,
        description="ページのメタディスクリプション（SEO分析用）"
    )
    structured_data: dict | None = Field(
        default=None,
        description="JSON-LD等の構造化データ"
    )
    publish_date: str | None = Field(
        default=None,
        description="公開日（ISO format、取得可能な場合）"
    )
```

---

## 実装タスク

### 1.1 スキーマ拡張（schemas/step1.py）`cc:TODO`

- [ ] `CompetitorPage` に `meta_description` 追加（`str | None`、default=None）
- [ ] `CompetitorPage` に `structured_data` 追加（`dict | None`、default=None）
- [ ] `CompetitorPage` に `publish_date` 追加（`str | None`、default=None）
- [ ] 各フィールドに Field description を追加

**ファイル**: `apps/worker/activities/schemas/step1.py`

**変更例**:
```python
# L6-14 の CompetitorPage クラスに以下を追加
    meta_description: str | None = Field(
        default=None,
        description="メタディスクリプション（SEO分析用）"
    )
    structured_data: dict | None = Field(
        default=None,
        description="JSON-LD等の構造化データ"
    )
    publish_date: str | None = Field(
        default=None,
        description="公開日（ISO format、取得可能な場合）"
    )
```

### 1.2 Activity修正（step1.py）`cc:TODO`

- [ ] `_extract_page_data()` メソッド（L307-342）に新フィールド抽出ロジック追加
- [ ] `page_fetch_tool` の戻り値から `meta_description`, `structured_data`, `publish_date` を取得
- [ ] 取得失敗時は None のまま（エラーにしない）

**ファイル**: `apps/worker/activities/step1.py`

**修正箇所**: `_extract_page_data()` メソッド（L335-342 の return 文）

```python
# 既存
return {
    "url": url,
    "title": fetch_data.get("title", ""),
    "content": content,
    "word_count": text_metrics.word_count,
    "headings": headings,
    "fetched_at": datetime.utcnow().isoformat(),
}

# 変更後
return {
    "url": url,
    "title": fetch_data.get("title", ""),
    "content": content,
    "word_count": text_metrics.word_count,
    "headings": headings,
    "fetched_at": datetime.utcnow().isoformat(),
    # 新規フィールド（取得可能な場合のみ）
    "meta_description": fetch_data.get("meta_description"),
    "structured_data": fetch_data.get("structured_data"),
    "publish_date": fetch_data.get("publish_date"),
}
```

### 1.3 page_fetch ツール確認 `cc:TODO`

- [ ] `page_fetch` ツールが `meta_description` を返すか確認
- [ ] `page_fetch` ツールが `structured_data` を返すか確認
- [ ] `page_fetch` ツールが `publish_date` を返すか確認
- [ ] 必要であれば `page_fetch` ツールを拡張

**確認ファイル**: `apps/api/tools/` 配下の page_fetch 実装

**確認項目**:
1. HTML パース時に `<meta name="description">` を抽出しているか
2. `<script type="application/ld+json">` を抽出しているか
3. `<time>` タグや `datePublished` を抽出しているか

### 1.4 プロンプト更新 `cc:TODO`

- [ ] `v2_blog_system.json` の step1 セクションを確認（存在すれば）
- [ ] 工程1は主にツール実行のため、プロンプト変更は最小限
- [ ] 既存 `default.json` との互換性確認

**注意**: 工程1は LLM プロンプト依存ではなく、ツール（SERP + page_fetch）実行が主体。

---

## テスト計画

### 単体テスト（schemas）`cc:TODO`

**ファイル**: `tests/unit/worker/activities/schemas/test_step1.py`

- [ ] `test_competitor_page_backward_compatible()`: 新フィールドなしで動作確認
- [ ] `test_competitor_page_with_new_fields()`: 新フィールド付きデータの動作確認
- [ ] `test_competitor_page_new_fields_are_optional()`: 新フィールドが Optional であること

```python
def test_competitor_page_backward_compatible():
    """既存データ形式でも動作することを確認."""
    old_data = {
        "url": "https://example.com",
        "title": "Example",
        "content": "Sample content...",
        "word_count": 1000,
        "headings": ["H1"],
        "fetched_at": "2025-01-01T00:00:00"
    }
    page = CompetitorPage(**old_data)
    assert page.meta_description is None
    assert page.structured_data is None
    assert page.publish_date is None

def test_competitor_page_with_new_fields():
    """新フィールド付きデータの動作確認."""
    new_data = {
        "url": "https://example.com",
        "title": "Example",
        "content": "Sample content...",
        "word_count": 1000,
        "headings": ["H1"],
        "fetched_at": "2025-01-01T00:00:00",
        "meta_description": "This is a description",
        "structured_data": {"@type": "Article", "headline": "Example"},
        "publish_date": "2024-12-01"
    }
    page = CompetitorPage(**new_data)
    assert page.meta_description == "This is a description"
    assert page.structured_data["@type"] == "Article"
    assert page.publish_date == "2024-12-01"
```

### 統合テスト（Activity）`cc:TODO`

**ファイル**: `tests/integration/worker/activities/test_step1.py`

- [ ] `test_step1_fetch_10_sites()`: 10サイト取得の動作確認
- [ ] `test_step1_error_handling()`: 失敗時のエラーハンドリング確認（MIN_SUCCESSFUL_FETCHES = 3）
- [ ] `test_step1_new_fields_populated()`: 新フィールドが取得されること（page_fetchツール対応後）
- [ ] `test_step1_checkpoint_resume()`: チェックポイントからの再開動作

### データ整合性テスト `cc:TODO`

**ファイル**: `tests/integration/workflow/test_step1_to_step2.py`

- [ ] `test_step1_output_to_step2()`: step2への引き継ぎデータ整合性
- [ ] `test_new_fields_accessible_in_step2()`: 新フィールドがstep2で参照可能であること

---

## フロー変更の必要性

**なし** - スキーマ拡張のみ。Temporal Workflow 定義の変更は不要。

---

## 依存関係

### 上流
- **step0**: `keyword` を受け取る

### 下流
- **step1.5**: `competitors` を参照（オプション）
- **step2**: `competitors` を検証・分析

### ツール依存
- **serp_fetch**: SERP検索（Google検索結果取得）
- **page_fetch**: ページ取得（HTML取得・パース） ← 拡張が必要な可能性

---

## 参照ファイル

| 種別 | ファイル |
|------|---------|
| スキーマ | `apps/worker/activities/schemas/step1.py` |
| Activity | `apps/worker/activities/step1.py` |
| ツール | `apps/api/tools/` 配下 |
| プロンプト（既存） | `apps/api/prompts/packs/default.json` |
| blog.System参照 | `blog.System_prompts/工程1_競合記事取得/` |

---

## 実装順序

1. **スキーマ拡張**（1.1）- 最初に実施、後方互換性テストを先に書く
2. **ツール確認**（1.3）- page_fetch の現状を確認
3. **Activity修正**（1.2）- ツール対応状況に応じて実装
4. **プロンプト更新**（1.4）- 必要最小限
5. **テスト**（全体）- 各段階で実施

---

## 注意事項

- **後方互換性必須**: 新フィールドは全て Optional とし、既存データで動作すること
- **エラーにしない**: 新フィールドが取得できなくてもエラーにせず None を返す
- **既存ロジック維持**: 以下は変更しない
  - `MIN_SUCCESSFUL_FETCHES = 3`
  - リトライロジック（`PAGE_FETCH_MAX_RETRIES = 2`）
  - チェックポイント機構
  - コンテンツ品質チェック（`_is_valid_content()`）
