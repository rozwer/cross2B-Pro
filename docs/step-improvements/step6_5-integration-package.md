# Step6.5: Integration Package - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step6_5.py` |
| Activity名 | `step6_5_integration_package` |
| 使用LLM | Claude（デフォルト: anthropic） |
| 目的 | 全分析・アウトラインを統合パッケージ化 |
| 特記 | **Step7a へのハンドオフポイント** - コンテンツ生成の直前 |

---

## 現状分析

### リトライ戦略

**現状**:
- 汎用的な `Exception` キャッチで `RETRYABLE` 分類
- JSON パース失敗時も `RETRYABLE`

**問題点**:
1. **入力データの網羅性チェック不十分**: 空データでも続行
2. **統合品質の検証なし**: パッケージの完全性を確認しない
3. **JSON パース失敗の頻発可能性**: 大きな出力で形式崩れやすい

### フォーマット整形機構

**現状**:
- JSON パース後に `integration_package`, `outline_summary`, `section_count`, `total_sources` を抽出
- マークダウンコードブロックの除去処理あり

**問題点**:
1. **統合パッケージの構造が不明確**: 何が含まれているべきか定義なし
2. **入力サマリーが部分的**: `inputs_summary` は存在有無のみ
3. **後続ステップへの引継ぎ情報不足**: Step7a が必要とする情報の明示なし

### 中途開始機構

**現状**:
- ステップ全体の冪等性のみ
- 7ステップ分のデータロード後にチェックポイントなし

**問題点**:
1. **大量データロードのやり直し**: step0, step3a/3b/3c, step4, step5, step6 を毎回ロード
2. **統合処理の中間結果なし**: プロンプト生成後に失敗すると最初から

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 入力データの網羅性チェック

```python
class Step65IntegrationPackage(BaseActivity):
    # 必須入力
    REQUIRED_INPUTS = ["step4", "step6"]  # 戦略アウトライン、拡張アウトライン
    # 推奨入力
    RECOMMENDED_INPUTS = ["step0", "step3a", "step3b", "step3c", "step5"]

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # データロード
        all_data = await self._load_all_step_data(ctx)

        # 必須入力チェック
        missing_required = [
            step for step in self.REQUIRED_INPUTS
            if not all_data.get(step)
        ]
        if missing_required:
            raise ActivityError(
                f"Required inputs missing: {missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": missing_required},
            )

        # 推奨入力チェック
        missing_recommended = [
            step for step in self.RECOMMENDED_INPUTS
            if not all_data.get(step)
        ]
        if missing_recommended:
            activity.logger.warning(
                f"Recommended inputs missing: {missing_recommended}"
            )

        # ... 統合処理 ...

    async def _load_all_step_data(
        self,
        ctx: ExecutionContext,
    ) -> dict[str, dict]:
        """全ステップのデータをロード"""
        steps = ["step0", "step3a", "step3b", "step3c", "step4", "step5", "step6"]
        data = {}

        for step in steps:
            step_data = await load_step_data(
                self.store, ctx.tenant_id, ctx.run_id, step
            )
            data[step] = step_data or {}

        return data
```

#### 1.2 統合品質チェック

```python
def _validate_integration_quality(
    self,
    package: dict,
    all_data: dict,
) -> QualityResult:
    """統合パッケージの品質検証"""
    issues = []

    # integration_package の存在
    if not package.get("integration_package"):
        issues.append("empty_integration_package")

    # outline_summary の存在
    if not package.get("outline_summary"):
        issues.append("no_outline_summary")

    # セクション数の妥当性
    section_count = package.get("section_count", 0)
    if section_count < 3:
        issues.append(f"too_few_sections: {section_count}")

    # ソース数の反映
    step5_sources = len(all_data.get("step5", {}).get("sources", []))
    total_sources = package.get("total_sources", 0)
    if step5_sources > 0 and total_sources == 0:
        issues.append("sources_not_integrated")

    return QualityResult(
        is_acceptable=len(issues) <= 1,
        issues=issues,
    )
```

#### 1.3 JSON パース改善

```python
def _parse_json_response(self, content: str) -> dict:
    """堅牢なJSONパース"""
    content = content.strip()

    # コードブロック除去
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        if end > start:
            content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        if end > start:
            content = content[start:end].strip()

    if not content:
        raise ActivityError(
            "Empty JSON content after extraction",
            category=ErrorCategory.RETRYABLE,
        )

    # JSONパース試行
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # 修復を試みる（末尾カンマ除去等）
        fixed_content = self._attempt_json_fix(content)
        if fixed_content:
            try:
                return json.loads(fixed_content)
            except json.JSONDecodeError:
                pass

        raise ActivityError(
            f"JSON parse failed: {e}",
            category=ErrorCategory.RETRYABLE,
            details={
                "error_position": e.pos,
                "content_preview": content[:200],
            },
        ) from e

def _attempt_json_fix(self, content: str) -> str | None:
    """JSON修復を試みる（決定的修正のみ）"""
    # 末尾カンマ除去
    fixed = re.sub(r',\s*}', '}', content)
    fixed = re.sub(r',\s*]', ']', fixed)

    if fixed != content:
        activity.logger.info("Applied JSON fix: trailing comma removal")
        return fixed

    return None
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field

class InputSummary(BaseModel):
    """入力データサマリー"""
    step_id: str
    available: bool
    key_points: list[str] = Field(default_factory=list)
    data_quality: str = "unknown"  # "high", "medium", "low", "unknown"

class SectionBlueprint(BaseModel):
    """セクション設計図"""
    level: int
    title: str
    target_words: int
    key_points: list[str]
    sources_to_cite: list[str]
    keywords_to_include: list[str]

class IntegrationPackageOutput(BaseModel):
    """Step6.5 の構造化出力"""
    keyword: str
    integration_package: str  # Step7a へ渡す統合テキスト
    article_blueprint: dict[str, Any] = Field(
        default_factory=dict,
        description="記事の設計図"
    )
    section_blueprints: list[SectionBlueprint] = Field(default_factory=list)
    outline_summary: str
    section_count: int
    total_sources: int
    input_summaries: list[InputSummary]
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    handoff_notes: list[str] = Field(
        default_factory=list,
        description="Step7aへの申し送り事項"
    )
```

#### 2.2 プロンプトでの形式指定

```python
STEP6_5_OUTPUT_FORMAT = """
これまでの全分析を統合し、記事生成用のパッケージを作成してください。

出力形式：
```json
{
  "integration_package": "Step7a に渡す統合テキスト（詳細なコンテキスト）",
  "article_blueprint": {
    "title": "記事タイトル",
    "target_audience": "想定読者",
    "main_theme": "記事のメインテーマ",
    "differentiators": ["差別化ポイント"],
    "tone": "記事のトーン"
  },
  "section_blueprints": [
    {
      "level": 2,
      "title": "セクションタイトル",
      "target_words": 500,
      "key_points": ["このセクションで伝えるべきポイント"],
      "sources_to_cite": ["参照すべきソースURL"],
      "keywords_to_include": ["含めるべきキーワード"]
    }
  ],
  "outline_summary": "アウトラインの要約",
  "section_count": セクション数,
  "total_sources": 使用可能なソース数,
  "handoff_notes": [
    "Step7aへの申し送り事項（特に注意すべき点等）"
  ]
}
```

重要：
- integration_package は Step7a が記事を生成するための唯一の入力となります
- 必要な情報はすべて integration_package に含めてください
- section_blueprints は各セクションの詳細な設計図です
"""
```

### 3. 中途開始機構の実装

#### 3.1 全データロードのキャッシュ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 全データロードのチェックポイント
    data_checkpoint = await self._load_checkpoint(ctx, "all_data_loaded")

    if data_checkpoint:
        all_data = data_checkpoint["all_data"]
        integration_input = data_checkpoint["integration_input"]
    else:
        # 全ステップからデータロード
        all_data = await self._load_all_step_data(ctx)

        # 統合入力の準備
        integration_input = self._prepare_integration_input(all_data, keyword)

        # チェックポイント保存
        await self._save_checkpoint(ctx, "all_data_loaded", {
            "all_data": all_data,
            "integration_input": integration_input,
        })

    # ... LLM呼び出し ...
```

#### 3.2 統合入力の準備

```python
def _prepare_integration_input(
    self,
    all_data: dict[str, dict],
    keyword: str,
) -> dict[str, Any]:
    """LLM用の統合入力を準備"""
    return {
        "keyword": keyword,
        "keyword_analysis": all_data.get("step0", {}).get("analysis", ""),
        "query_analysis": all_data.get("step3a", {}).get("query_analysis", ""),
        "cooccurrence_analysis": all_data.get("step3b", {}).get("cooccurrence_analysis", ""),
        "competitor_analysis": all_data.get("step3c", {}).get("competitor_analysis", ""),
        "strategic_outline": all_data.get("step4", {}).get("outline", ""),
        "sources": all_data.get("step5", {}).get("sources", []),
        "enhanced_outline": all_data.get("step6", {}).get("enhanced_outline", ""),
        # メタ情報
        "_input_summary": {
            step: bool(data) for step, data in all_data.items()
        },
    }
```

---

## ハンドオフポイントとしての重要性

### Step7a への引継ぎ

Step6.5 は **コンテンツ生成フェーズへのゲート** です：

```
[分析フェーズ] Step0-3, Step4-6
        ↓
    [Step6.5: 統合パッケージ] ← 全情報をここで集約
        ↓
[生成フェーズ] Step7a-10
```

### 統合パッケージの品質が最終記事品質を決定

- **情報が欠落** → 記事に反映されない
- **構造が不明確** → 記事の構成が崩れる
- **優先度が不明** → 重要でない内容が膨らむ

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **最高** | 入力網羅性チェック | 2h | ハンドオフ品質保証 |
| **最高** | 構造化出力スキーマ | 3h | Step7a への明確な引継ぎ |
| **高** | 統合品質チェック | 2h | パッケージ完全性 |
| **高** | JSONパース改善 | 1h | パース失敗削減 |
| **中** | 全データキャッシュ | 1h | 効率化 |
| **中** | section_blueprints | 2h | 詳細設計図 |

---

## テスト観点

1. **正常系**: 全入力を統合したパッケージが生成される
2. **必須入力欠落**: step4/step6 なしでエラー
3. **推奨入力欠落**: 警告のみで続行
4. **JSONパース**: コードブロック付きでも正しくパース
5. **品質チェック**: セクション数不足で警告
6. **handoff_notes**: Step7aへの申し送りが含まれる
