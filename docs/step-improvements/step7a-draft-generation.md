# Step7a: Draft Generation - 改善案

## 概要

| 項目       | 内容                                            |
| ---------- | ----------------------------------------------- |
| ファイル   | `apps/worker/activities/step7a.py`              |
| Activity名 | `step7a_draft_generation`                       |
| 使用LLM    | Claude（デフォルト: anthropic）                 |
| 目的       | 統合パッケージに基づく記事ドラフト生成          |
| 特記       | **最長ステップ**（600秒タイムアウト）、長文生成 |

---

## 現状分析

### リトライ戦略

**現状**:

- 汎用的な `Exception` キャッチで `RETRYABLE` 分類
- JSON パース失敗時も `RETRYABLE`
- 600秒のタイムアウト設定

**問題点**:

1. **長文生成の途中切れ対応なし**: max_tokens 到達で切れる可能性
2. **JSON パース失敗の頻発**: 長文でコードブロック形式が崩れやすい
3. **ドラフト品質の検証なし**: 生成内容の品質を確認しない
4. **integration_package 欠落時の対応不十分**

### フォーマット整形機構

**現状**:

- JSON パース後に `draft`, `word_count`, `section_count`, `cta_positions` を抽出
- マークダウンコードブロックの除去処理あり
- 実際の word_count と LLM 報告値を両方記録

**問題点**:

1. **ドラフト構造の検証なし**: アウトラインに沿っているか確認しない
2. **キーワード密度チェックなし**: SEO 観点の検証がない
3. **セクション完全性チェックなし**: 予定セクションがすべて含まれているか不明

### 中途開始機構

**現状**:

- ステップ全体の冪等性のみ
- 長文生成の途中保存なし

**問題点**:

1. **600秒かけた生成が失敗すると全ロスト**: 最も時間がかかるステップ
2. **部分生成の活用なし**: 途中まで生成されていても再利用できない

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 長文生成の完全性チェック

```python
class Step7ADraftGeneration(BaseActivity):
    # 最小要件
    MIN_WORD_COUNT = 1000
    MIN_SECTION_COUNT = 3

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... LLM呼び出し ...

        # 完全性チェック
        completeness = self._check_draft_completeness(parsed, integration_package)

        if not completeness.is_complete:
            if completeness.is_truncated:
                # 切れている場合は続きを生成（分割生成戦略）
                parsed = await self._continue_generation(
                    llm, parsed, integration_package, completeness
                )
            else:
                raise ActivityError(
                    f"Draft incomplete: {completeness.issues}",
                    category=ErrorCategory.RETRYABLE,
                    details={"issues": completeness.issues},
                )

        return self._structure_output(parsed)

    def _check_draft_completeness(
        self,
        parsed: dict,
        integration_package: str,
    ) -> CompletenessResult:
        """ドラフトの完全性チェック"""
        issues = []
        is_truncated = False

        draft = parsed.get("draft", "")
        word_count = len(draft.split())

        # 最小文字数チェック
        if word_count < self.MIN_WORD_COUNT:
            issues.append(f"word_count_low: {word_count}")

            # 切れているかの判定
            if draft.endswith(("...", "…", "。", "、")) == False:
                is_truncated = True

        # セクション数チェック
        section_count = parsed.get("section_count", 0)
        if section_count < self.MIN_SECTION_COUNT:
            issues.append(f"section_count_low: {section_count}")

        # 結論セクションの存在
        conclusion_indicators = ["まとめ", "結論", "おわり", "conclusion"]
        has_conclusion = any(ind in draft.lower() for ind in conclusion_indicators)
        if not has_conclusion:
            issues.append("no_conclusion")
            is_truncated = True

        return CompletenessResult(
            is_complete=len(issues) == 0,
            is_truncated=is_truncated,
            issues=issues,
        )
```

#### 1.2 分割生成戦略（途中から続き）

```python
async def _continue_generation(
    self,
    llm,
    current_draft: dict,
    integration_package: str,
    completeness: CompletenessResult,
) -> dict:
    """ドラフトの続きを生成"""
    continuation_prompt = f"""
以下は記事ドラフトの途中です。この続きから完成させてください。

## 現在のドラフト（最後の500文字）
{current_draft.get("draft", "")[-500:]}

## 統合パッケージ（参照用）
{integration_package[:2000]}

## 指示
- 既存の内容と自然につながるように続きを書いてください
- 必ず「まとめ」または「結論」セクションで締めくくってください
- JSON形式ではなく、マークダウン形式で出力してください
"""

    llm_config = LLMRequestConfig(max_tokens=4000, temperature=0.7)
    response = await llm.generate(
        messages=[{"role": "user", "content": continuation_prompt}],
        system_prompt="Continue the article draft.",
        config=llm_config,
    )

    # 既存ドラフトと結合
    combined_draft = current_draft.get("draft", "") + "\n\n" + response.content

    return {
        "draft": combined_draft,
        "word_count": len(combined_draft.split()),
        "section_count": current_draft.get("section_count", 0),
        "cta_positions": current_draft.get("cta_positions", []),
        "continued": True,
    }
```

#### 1.3 JSON パース改善

```python
def _parse_draft_response(self, content: str) -> dict:
    """ドラフトレスポンスの堅牢なパース"""
    content = content.strip()

    # コードブロック除去を試みる
    json_content = self._extract_json_block(content)

    if json_content:
        try:
            return json.loads(json_content)
        except json.JSONDecodeError:
            pass

    # JSON パースに失敗した場合、マークダウンとして扱う
    # （長文生成ではJSONが崩れやすい）
    if self._looks_like_markdown(content):
        activity.logger.info("Treating response as markdown (JSON parse failed)")
        return {
            "draft": content,
            "word_count": len(content.split()),
            "section_count": len(re.findall(r'^##\s', content, re.M)),
            "cta_positions": [],
            "format": "markdown_fallback",
        }

    raise ActivityError(
        "Failed to parse draft response",
        category=ErrorCategory.RETRYABLE,
        details={"content_preview": content[:500]},
    )

def _looks_like_markdown(self, content: str) -> bool:
    """マークダウン形式かどうか判定"""
    md_indicators = [
        r'^#\s',      # 見出し
        r'^##\s',     # H2
        r'^\*\s',     # リスト
        r'^\d+\.\s',  # 番号付きリスト
    ]
    return any(re.search(p, content, re.M) for p in md_indicators)
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class DraftSection(BaseModel):
    """ドラフトセクション"""
    level: int
    title: str
    content: str
    word_count: int
    has_subheadings: bool = False

class DraftQualityMetrics(BaseModel):
    """ドラフト品質メトリクス"""
    word_count: int
    char_count: int
    section_count: int
    avg_section_length: int
    keyword_density: float = 0.0
    readability_score: float = 0.0
    has_introduction: bool = False
    has_conclusion: bool = False

class Step7aOutput(BaseModel):
    """Step7a の構造化出力"""
    keyword: str
    draft: str
    sections: list[DraftSection] = Field(default_factory=list)
    cta_positions: list[str] = Field(default_factory=list)
    quality_metrics: DraftQualityMetrics
    generation_stats: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
```

#### 2.2 ドラフト品質メトリクス

```python
def _calculate_quality_metrics(
    self,
    draft: str,
    keyword: str,
) -> DraftQualityMetrics:
    """ドラフトの品質メトリクスを計算"""
    words = draft.split()
    word_count = len(words)

    # セクション分析
    sections = re.split(r'^##\s', draft, flags=re.M)
    section_count = len(sections) - 1  # 最初は見出し前

    # キーワード密度
    keyword_count = draft.lower().count(keyword.lower())
    keyword_density = keyword_count / max(word_count, 1) * 100

    # 構造チェック
    intro_indicators = ["はじめに", "導入", "introduction"]
    has_intro = any(ind in draft.lower() for ind in intro_indicators)

    conclusion_indicators = ["まとめ", "結論", "おわり", "conclusion"]
    has_conclusion = any(ind in draft.lower() for ind in conclusion_indicators)

    return DraftQualityMetrics(
        word_count=word_count,
        char_count=len(draft),
        section_count=section_count,
        avg_section_length=word_count // max(section_count, 1),
        keyword_density=keyword_density,
        has_introduction=has_intro,
        has_conclusion=has_conclusion,
    )
```

#### 2.3 プロンプトでの形式指定

````python
STEP7A_OUTPUT_FORMAT = """
統合パッケージに基づいて記事ドラフトを生成してください。

出力形式：
```json
{
  "draft": "マークダウン形式の記事本文",
  "word_count": 推定文字数,
  "section_count": セクション数,
  "cta_positions": ["CTA挿入推奨位置の説明"]
}
````

重要な制約：

- 最低3000文字以上
- 必ず「導入」と「まとめ」セクションを含める
- 各セクションは300文字以上
- キーワードを自然に含める（キーワード詰め込み禁止）
- H2, H3 の見出し階層を適切に使用

注意：JSONが大きくなりすぎる場合は、draftフィールドにマークダウンをそのまま入れてください。
"""

````

### 3. 中途開始機構の実装

#### 3.1 セクション単位の生成と保存

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 部分生成チェックポイント
    draft_checkpoint = await self._load_checkpoint(ctx, "draft_progress")

    if draft_checkpoint:
        current_draft = draft_checkpoint["draft"]
        completed_sections = draft_checkpoint["completed_sections"]
        activity.logger.info(
            f"Resuming from checkpoint: {len(completed_sections)} sections done"
        )
    else:
        current_draft = ""
        completed_sections = []

    # セクション単位で生成（大きなドラフトを分割）
    if not completed_sections:
        # 最初の生成
        response = await self._generate_full_draft(llm, integration_package)
        current_draft = response.get("draft", "")

        # 完全性チェック
        completeness = self._check_draft_completeness(response, integration_package)

        if completeness.is_truncated:
            # チェックポイント保存
            await self._save_checkpoint(ctx, "draft_progress", {
                "draft": current_draft,
                "completed_sections": self._extract_section_titles(current_draft),
                "needs_continuation": True,
            })

            # 続きを生成
            current_draft = await self._continue_generation(...)

    # 最終チェックポイント保存
    await self._save_checkpoint(ctx, "draft_progress", {
        "draft": current_draft,
        "completed_sections": self._extract_section_titles(current_draft),
        "needs_continuation": False,
    })

    return self._structure_output(current_draft)
````

---

## 長文生成特有の考慮事項

### タイムアウト対策

```python
# Temporal Activity の設定
STEP7A_TIMEOUT = timedelta(seconds=600)  # 10分
STEP7A_HEARTBEAT_TIMEOUT = timedelta(seconds=120)  # 2分ごとにheartbeat

async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # Heartbeat で進捗を報告
    activity.heartbeat("Starting draft generation...")

    # LLM呼び出し中も定期的に heartbeat
    # （LLMクライアント側でストリーミング対応が必要）
```

### max_tokens の考慮

```python
# 日本語は1文字≈2-3トークン
# 3000文字 ≈ 6000-9000トークン
# 安全マージンを含めて max_tokens=8000 設定

llm_config = LLMRequestConfig(
    max_tokens=8000,
    temperature=0.7,
)
```

---

## 優先度と実装順序

| 優先度   | 改善項目         | 工数見積 | 理由                   |
| -------- | ---------------- | -------- | ---------------------- |
| **最高** | 完全性チェック   | 2h       | ドラフト品質保証       |
| **最高** | JSONパース改善   | 2h       | 長文でのパース失敗対策 |
| **高**   | 分割生成戦略     | 3h       | 切れた場合のリカバリ   |
| **高**   | 品質メトリクス   | 2h       | 品質可視化             |
| **中**   | チェックポイント | 2h       | 再実行効率化           |
| **低**   | Heartbeat        | 1h       | タイムアウト対策       |

---

## テスト観点

1. **正常系**: 完全なドラフトが生成される
2. **切れ検出**: max_tokens到達で切れた場合に検出
3. **続き生成**: 切れた場合に続きが生成される
4. **JSONパース失敗**: マークダウンとして処理される
5. **チェックポイント**: 途中から再開できる
6. **品質メトリクス**: 正しく計算される
7. **最小要件**: 1000文字未満でリトライ
