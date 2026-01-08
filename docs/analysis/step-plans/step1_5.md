# 工程1.5: 関連KW競合取得

## 概要

関連キーワードに対する競合記事を取得し、step2以降の分析に活用するデータを収集する。

---

## 入力スキーマ

```json
{
  "related_keywords": "string[] - configから、またはstep0のrecommended_anglesから派生",
  "recommended_angles": "string[] | dict[] - step0から（related_keywords未指定時の派生元）"
}
```

**入力元**:
- `config.related_keywords` - 優先
- `step0.recommended_angles` - フォールバック派生

---

## 出力スキーマ（既存）

```python
class RelatedCompetitorArticle(BaseModel):
    related_keyword: str              # 関連キーワード
    url: str                          # 競合記事URL
    title: str = ""                   # 記事タイトル
    content_summary: str = ""         # コンテンツ要約（最大2000文字）
    word_count: int = 0               # 単語数
    headings: list[str] = []          # 見出しリスト
    fetched_at: str = ""              # 取得日時 (ISO format)

class RelatedKeywordData(BaseModel):
    keyword: str                      # 関連キーワード
    search_results_count: int = 0     # 検索結果数
    competitors: list[RelatedCompetitorArticle] = []
    fetch_success_count: int = 0
    fetch_failed_count: int = 0

class FetchMetadata(BaseModel):
    fetched_at: str = ""
    source: str = "serp_fetch"
    total_keywords_processed: int = 0
    total_articles_fetched: int = 0

class Step1_5Output(BaseModel):
    step: str = "step1_5"
    related_keywords_analyzed: int
    related_competitor_data: list[RelatedKeywordData]
    metadata: FetchMetadata
    skipped: bool = False
    skip_reason: str | None = None
    output_path: str | None = None
    output_digest: str | None = None
```

---

## blog.System との差分

| 観点 | 既存実装 | blog.System | 対応方針 |
|------|----------|-------------|----------|
| 対象KW | related_keywords | サジェストKW含む | **Phase 2** |
| step1重複除外 | なし | 明示的に除外 | **Phase 1** |
| step2への統合 | ロードのみ | 検証に含める | **Phase 1** |
| 出力形式 | JSON | CSV + MD | JSON維持（互換不要） |

---

## 実装フェーズ

### Phase 1: 工程間連携の強化 `cc:TODO`

step1との重複除外とstep2への統合を実装。

#### 1.1 step1重複URL除外

**ファイル**: `apps/worker/activities/step1_5.py`

**変更内容**:
```python
# execute() 冒頭で step1 結果をロード
step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1")
existing_urls = set()
if step1_data:
    for comp in step1_data.get("competitors", []):
        existing_urls.add(comp.get("url", ""))

# _process_related_keyword() 内でフィルタ
filtered_urls = [u for u in urls if u not in existing_urls]
```

**テスト**:
- [ ] step1に重複URLがある場合、step1_5で除外されること
- [ ] step1が空/未実行の場合、正常動作すること

#### 1.2 step2での検証統合

**ファイル**: `apps/worker/activities/step2.py`

**変更内容**:
```python
# step1_5 の競合を step1 競合に統合して検証
competitors = step1_data.get("competitors", [])
if step1_5_data and not step1_5_data.get("skipped"):
    for kw_data in step1_5_data.get("related_competitor_data", []):
        for comp in kw_data.get("competitors", []):
            competitors.append({
                "url": comp.get("url"),
                "title": comp.get("title"),
                "word_count": comp.get("word_count"),
                "source": "step1_5",  # 識別用
            })
```

**テスト**:
- [ ] step1_5結果がstep2検証に含まれること
- [ ] step1_5スキップ時、step1結果のみで検証されること

---

### Phase 2: サジェストKW対応（オプション） `cc:TODO`

blog.Systemではサジェストキーワードも対象。必要に応じて追加。

#### 2.1 スキーマ拡張

**ファイル**: `apps/worker/activities/schemas/step1_5.py`

**追加フィールド**:
```python
class Step1_5Output(BaseModel):
    # ... 既存フィールド ...
    suggest_keywords: list[str] = []  # 追加: サジェストKWリスト
    search_volume_estimates: dict[str, int] = {}  # 追加: 推定検索ボリューム
```

#### 2.2 サジェストKW取得ロジック

**ファイル**: `apps/worker/activities/step1_5.py`

**変更内容**:
- configに `include_suggest_keywords: bool` フラグ追加
- True時、Google Suggest APIまたはSERP関連キーワードから取得

**テスト**:
- [ ] サジェストKW取得の動作確認
- [ ] フラグOFF時、既存動作に影響なし

---

### Phase 3: スキップ条件の明確化 `cc:TODO`

#### 3.1 ドキュメント化

**スキップ条件**（現状）:
1. `config.related_keywords` が空 AND `step0.recommended_angles` が空
2. `config.enable_step1_5` が `false`

**追加検討**:
- step0の `four_pillars_score` が低い場合のスキップ
- 主キーワードのみで十分な場合のスキップ

#### 3.2 プロンプト更新

**ファイル**: `apps/api/prompts/packs/default.json` (step1_5セクション)

現状プロンプトが簡素な場合、blog.Systemの詳細指示を反映:
- 重複除外の明示
- 出力フォーマットの統一

---

## テスト計画

### 単体テスト

| テスト項目 | ファイル | 状態 |
|-----------|---------|------|
| step_id プロパティ | test_step1_5.py | ✅ 既存 |
| スキップロジック（empty related_keywords） | test_step1_5.py | ✅ 既存 |
| スキップロジック（missing key） | test_step1_5.py | ✅ 既存 |
| 正常系実行 | test_step1_5.py | ✅ 既存 |
| MAX_RELATED_KEYWORDS 制限 | test_step1_5.py | ✅ 既存 |
| **step1重複除外** | test_step1_5.py | ❌ 追加必要 |
| **チェックポイント復帰** | test_step1_5.py | ❌ 追加必要 |

### 統合テスト

| テスト項目 | 状態 |
|-----------|------|
| step0 → step1_5 連携（recommended_angles派生） | ❌ 追加必要 |
| step1 → step1_5 連携（重複除外） | ❌ 追加必要 |
| step1_5 → step2 連携（検証統合） | ❌ 追加必要 |

---

## 実装ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `apps/worker/activities/step1_5.py` | 修正（Phase 1.1） |
| `apps/worker/activities/step2.py` | 修正（Phase 1.2） |
| `apps/worker/activities/schemas/step1_5.py` | 修正（Phase 2.1） |
| `tests/unit/activities/test_step1_5.py` | 追加 |
| `tests/integration/test_step1_5_integration.py` | 新規 |

---

## フロー変更の必要性

**なし** - 既存Activity枠で対応可能

---

## 定数・設定

```python
# apps/worker/activities/step1_5.py
MAX_RELATED_KEYWORDS = 5              # 処理する関連KWの上限
MAX_COMPETITORS_PER_KEYWORD = 3       # 関連KWあたりの競合記事数
PAGE_FETCH_MAX_RETRIES = 2            # ページ取得リトライ回数
PAGE_FETCH_TIMEOUT = 30               # フェッチタイムアウト (秒)
MAX_CONTENT_CHARS = 15000             # コンテンツ最大文字数
```

---

## 優先度

| Phase | 重要度 | 理由 |
|-------|--------|------|
| Phase 1 | **高** | 工程間連携の整合性確保 |
| Phase 2 | 中 | blog.System完全互換に必要だが、MVP外 |
| Phase 3 | 低 | ドキュメント・品質向上 |

---

## 次のアクション

1. `/work` で Phase 1 を実装開始
2. `apps/worker/activities/step1_5.py` の重複除外ロジック追加
3. `apps/worker/activities/step2.py` の検証統合
4. テスト追加・実行
