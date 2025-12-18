# Step6: Enhanced Outline - 改善案

## 概要

| 項目       | 内容                                         |
| ---------- | -------------------------------------------- |
| ファイル   | `apps/worker/activities/step6.py`            |
| Activity名 | `step6_enhanced_outline`                     |
| 使用LLM    | Claude（デフォルト: anthropic）              |
| 目的       | 一次資料を統合してアウトラインを拡張・詳細化 |

---

## 現状分析

### リトライ戦略

**現状**:

- 汎用的な `Exception` キャッチで `RETRYABLE` 分類
- ソース数のチェックなし（0件でも続行）

**問題点**:

1. **ソース不在時の品質低下**: step5 で資料が取れなくても続行
2. **アウトライン拡張の品質検証なし**: 単に LLM 出力を保存
3. **step4 との整合性チェックなし**: 元のアウトライン構造が維持されているか不明

### フォーマット整形機構

**現状**:

- `enhanced_outline` として自由形式テキスト保存
- `sources_used` で使用ソース数を記録

**問題点**:

1. **拡張内容の構造化なし**: 何がどう拡張されたか不明
2. **ソース引用の追跡なし**: どのセクションにどのソースが使われたか不明
3. **step4 との差分が不明**: 拡張前後の比較ができない

### 中途開始機構

**現状**:

- ステップ全体の冪等性のみ
- ソースサマリー生成後のチェックポイントなし

**問題点**:

1. **ソース処理のやり直し**: 毎回サマリー生成
2. **LLM 呼び出し前の状態保存なし**

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 ソース品質チェック

```python
MIN_SOURCES_FOR_ENHANCEMENT = 1  # 最低1件は欲しい

async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    sources = step5_data.get("sources", [])

    if len(sources) < MIN_SOURCES_FOR_ENHANCEMENT:
        activity.logger.warning(
            f"Low source count ({len(sources)}), "
            f"outline enhancement may be limited"
        )
        # 警告のみ、続行（ソースなしでも基本的な拡張は可能）

    # ... 処理続行 ...
```

#### 1.2 拡張品質チェック

```python
def _validate_enhancement_quality(
    self,
    original_outline: str,
    enhanced_outline: str,
) -> QualityResult:
    """拡張品質の検証"""
    issues = []

    # 長さチェック（拡張後は元より長くなるべき）
    if len(enhanced_outline) < len(original_outline):
        issues.append("enhancement_shorter_than_original")

    # 見出し構造の保持
    original_h2 = set(re.findall(r'^##\s+(.+)$', original_outline, re.M))
    enhanced_h2 = set(re.findall(r'^##\s+(.+)$', enhanced_outline, re.M))

    missing_sections = original_h2 - enhanced_h2
    if missing_sections:
        issues.append(f"missing_sections: {missing_sections}")

    # 詳細度の向上（H3の増加）
    original_h3_count = len(re.findall(r'^###\s', original_outline, re.M))
    enhanced_h3_count = len(re.findall(r'^###\s', enhanced_outline, re.M))

    if enhanced_h3_count <= original_h3_count:
        issues.append("no_additional_subsections")

    return QualityResult(
        is_acceptable=len(issues) <= 1,
        issues=issues,
    )
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class EnhancedSection(BaseModel):
    """拡張されたセクション"""
    level: int
    title: str
    original_content: str = ""
    enhanced_content: str
    sources_referenced: list[str] = Field(
        default_factory=list,
        description="参照したソースURL"
    )
    enhancement_type: str = Field(
        default="detail",
        description="elaboration|detail|evidence|example"
    )

class EnhancementSummary(BaseModel):
    """拡張サマリー"""
    sections_enhanced: int
    sections_added: int
    sources_integrated: int
    total_word_increase: int

class Step6Output(BaseModel):
    """Step6 の構造化出力"""
    keyword: str
    enhanced_outline: str
    sections: list[EnhancedSection]
    enhancement_summary: EnhancementSummary
    source_citations: dict[str, list[str]]  # section -> [source_urls]
    original_outline_hash: str  # 元アウトラインのハッシュ（トレーサビリティ）
```

#### 2.2 ソース引用の追跡

```python
def _prepare_source_summaries(
    self,
    sources: list[dict],
    max_sources: int = 10,
) -> tuple[list[dict], dict[str, str]]:
    """ソースサマリーと引用マッピングを準備"""
    summaries = []
    url_to_id = {}

    for i, source in enumerate(sources[:max_sources]):
        source_id = f"[{i+1}]"
        url = source.get("url", "")
        url_to_id[url] = source_id

        summaries.append({
            "id": source_id,
            "url": url,
            "title": source.get("title", ""),
            "excerpt": source.get("excerpt", "")[:200],
        })

    return summaries, url_to_id
```

#### 2.3 プロンプトでの引用指示

````python
STEP6_OUTPUT_FORMAT = """
アウトラインを拡張してください。拡張時は以下のルールに従ってください：

1. 元のアウトライン構造（H2セクション）を維持する
2. 各セクションに適切なH3サブセクションを追加する
3. 一次資料からの情報を統合する際は、引用元を[1], [2]のように明記する
4. 具体的なデータや統計を追加する

出力形式：
```json
{
  "enhanced_outline": "マークダウン形式の拡張アウトライン",
  "source_citations": {
    "セクションタイトル": ["引用したソースID"]
  },
  "enhancement_summary": {
    "sections_enhanced": 拡張したセクション数,
    "sections_added": 追加したセクション数,
    "sources_integrated": 統合したソース数
  }
}
````

"""

````

### 3. 中途開始機構の実装

#### 3.1 ソースサマリーのキャッシュ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # ソースサマリーのチェックポイント
    summary_checkpoint = await self._load_checkpoint(ctx, "source_summaries")

    if summary_checkpoint:
        source_summaries = summary_checkpoint["summaries"]
        url_to_id = summary_checkpoint["url_to_id"]
    else:
        step5_data = await load_step_data(...) or {}
        sources = step5_data.get("sources", [])

        source_summaries, url_to_id = self._prepare_source_summaries(sources)

        await self._save_checkpoint(ctx, "source_summaries", {
            "summaries": source_summaries,
            "url_to_id": url_to_id,
        })

    # ... LLM呼び出し ...
````

---

## 優先度と実装順序

| 優先度 | 改善項目                 | 工数見積 | 理由               |
| ------ | ------------------------ | -------- | ------------------ |
| **高** | 拡張品質チェック         | 2h       | アウトライン整合性 |
| **高** | ソース引用追跡           | 2h       | トレーサビリティ   |
| **中** | 構造化出力スキーマ       | 2h       | 可視化改善         |
| **低** | ソースサマリーキャッシュ | 1h       | 効率化             |

---

## テスト観点

1. **正常系**: アウトラインが適切に拡張される
2. **構造保持**: 元のH2セクションが維持される
3. **引用追跡**: ソース参照が記録される
4. **ソースなし**: 0件でも基本拡張が動作
5. **品質チェック**: 拡張後が元より短い場合に警告
