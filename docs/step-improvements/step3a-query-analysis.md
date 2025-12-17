# Step3a: Query Analysis - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step3a.py` |
| Activity名 | `step3a_query_analysis` |
| 使用LLM | Gemini（デフォルト） |
| 目的 | 検索クエリ意図分析・ペルソナ構築 |
| 特記 | Step3b/3c と並列実行 |

---

## 現状分析

### リトライ戦略

**現状**:
- Temporal の `RetryPolicy` に依存（最大3回）
- 並列実行時は `parallel.py` の `STEP_RETRY_POLICY` を使用
- LLM エラーを `RETRYABLE` / `NON_RETRYABLE` に分類

**問題点**:
1. **並列ステップ間の依存関係考慮なし**: 3a が失敗しても 3b/3c は続行
2. **部分成功の判定なし**: LLM 出力の品質チェックがない
3. **リトライラウンド制限**: 3ラウンドで全ステップ成功必須は厳しい場合あり

### フォーマット整形機構

**現状**:
- LLM レスポンスを `query_analysis` としてそのまま保存
- 自由形式テキスト（構造化なし）

**問題点**:
1. **出力形式が不定**: ペルソナや検索意図の形式が毎回異なる
2. **後続ステップでの利用困難**: Step4 が `query_analysis` を参照するが形式不明
3. **必須項目の保証なし**: 検索意図、ペルソナ等の必須要素が欠落する可能性

### 中途開始機構

**現状**:
- 並列実行の成功分はスキップ（`parallel.py` の `completed` dict）
- 個別ステップ内のチェックポイントなし

**問題点**:
1. **入力データのキャッシュなし**: step0/step1 データを毎回ロード
2. **LLM 呼び出し前後の状態保存なし**: プロンプト生成後に失敗しても最初から

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 出力品質チェック付きリトライ

```python
class Step3AQueryAnalysis(BaseActivity):
    MAX_QUALITY_RETRIES = 1  # 品質不足時の追加リトライ

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... プロンプト準備 ...

        response = await self._call_llm_with_quality_check(
            llm, prompt, llm_config, metadata
        )

        return self._structure_output(response)

    async def _call_llm_with_quality_check(
        self,
        llm,
        prompt: str,
        config: LLMRequestConfig,
        metadata: LLMCallMetadata,
    ) -> LLMResponse:
        """品質チェック付きLLM呼び出し"""
        for attempt in range(self.MAX_QUALITY_RETRIES + 1):
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a search query analysis expert.",
                config=config,
                metadata=metadata,
            )

            quality_result = self._check_output_quality(response.content)
            if quality_result.is_acceptable:
                return response

            if attempt < self.MAX_QUALITY_RETRIES:
                # 不足要素を指定してリトライ
                prompt = self._add_quality_guidance(prompt, quality_result.missing)
                activity.logger.warning(
                    f"Quality retry {attempt + 1}: missing {quality_result.missing}"
                )

        # 最終試行の結果を返す（不完全でも続行）
        activity.logger.warning(
            f"Output quality not optimal, proceeding with available data"
        )
        return response

    def _check_output_quality(self, content: str) -> QualityResult:
        """出力品質をチェック"""
        required_elements = {
            "search_intent": ["検索意図", "search intent", "intent"],
            "persona": ["ペルソナ", "persona", "ユーザー像"],
            "pain_points": ["課題", "pain point", "悩み"],
        }

        missing = []
        content_lower = content.lower()

        for element, keywords in required_elements.items():
            if not any(kw in content_lower for kw in keywords):
                missing.append(element)

        return QualityResult(
            is_acceptable=len(missing) <= 1,  # 1項目まで許容
            missing=missing,
        )
```

#### 1.2 並列ステップの相互補完

```python
# parallel.py での改善案
async def run_parallel_steps(...) -> dict[str, Any]:
    # ... 既存の並列実行 ...

    # 全ステップ成功後、相互参照による補完を検討
    if all(s in completed for s in parallel_steps):
        # 出力品質の相互検証（オプション）
        cross_validation = await _cross_validate_outputs(completed)
        if cross_validation.warnings:
            workflow_logger.warning(f"Cross-validation warnings: {cross_validation.warnings}")

    return completed
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field
from typing import Literal

class SearchIntent(BaseModel):
    """検索意図の構造化"""
    primary: Literal["informational", "navigational", "transactional", "commercial"]
    secondary: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)

class UserPersona(BaseModel):
    """ユーザーペルソナ"""
    name: str
    demographics: str
    goals: list[str]
    pain_points: list[str]
    search_context: str

class QueryAnalysisOutput(BaseModel):
    """Step3a の構造化出力"""
    keyword: str
    search_intent: SearchIntent
    personas: list[UserPersona] = Field(..., min_length=1, max_length=3)
    content_expectations: list[str]
    recommended_tone: str
    raw_analysis: str
```

#### 2.2 プロンプトでの形式指定

```python
STEP3A_OUTPUT_FORMAT = """
以下のJSON形式で出力してください：
```json
{
  "search_intent": {
    "primary": "informational|navigational|transactional|commercial",
    "secondary": ["関連する検索意図"],
    "confidence": 0.0-1.0
  },
  "personas": [
    {
      "name": "ペルソナ名",
      "demographics": "属性（年齢、職業等）",
      "goals": ["目標1", "目標2"],
      "pain_points": ["課題1", "課題2"],
      "search_context": "検索に至った背景"
    }
  ],
  "content_expectations": ["期待するコンテンツ要素"],
  "recommended_tone": "推奨トーン（専門的/親しみやすい等）",
  "raw_analysis": "詳細分析テキスト"
}
```
"""
```

#### 2.3 出力パーサー

```python
class Step3AOutputParser:
    def parse(self, raw_content: str) -> QueryAnalysisOutput:
        """LLM出力をパースして構造化"""
        # JSON抽出
        if "```json" in raw_content:
            json_str = self._extract_json_block(raw_content)
        elif raw_content.strip().startswith("{"):
            json_str = raw_content.strip()
        else:
            # 自由形式からの抽出を試みる
            return self._extract_from_freeform(raw_content)

        try:
            data = json.loads(json_str)
            return QueryAnalysisOutput(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise OutputParseError(f"Parse failed: {e}", raw=raw_content)

    def _extract_from_freeform(self, content: str) -> QueryAnalysisOutput:
        """自由形式テキストから構造を抽出"""
        # 検索意図の抽出
        intent = self._extract_search_intent(content)

        # ペルソナの抽出
        personas = self._extract_personas(content)

        if not personas:
            raise OutputParseError("No personas found in output", raw=content)

        return QueryAnalysisOutput(
            keyword="",  # 後で補完
            search_intent=intent,
            personas=personas,
            content_expectations=[],
            recommended_tone="",
            raw_analysis=content,
        )
```

### 3. 中途開始機構の実装

#### 3.1 入力データのキャッシュ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 入力データのチェックポイント確認
    input_checkpoint = await self._load_checkpoint(ctx, "inputs_loaded")

    if input_checkpoint:
        step0_data = input_checkpoint["step0_data"]
        step1_data = input_checkpoint["step1_data"]
    else:
        # データロード
        step0_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step0"
        ) or {}
        step1_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step1"
        ) or {}

        # チェックポイント保存
        await self._save_checkpoint(ctx, "inputs_loaded", {
            "step0_data": step0_data,
            "step1_data": step1_data,
        })

    # ... 以降の処理 ...
```

#### 3.2 プロンプト生成後のチェックポイント

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # ... 入力データロード ...

    # プロンプト生成チェックポイント
    prompt_checkpoint = await self._load_checkpoint(ctx, "prompt_ready")

    if prompt_checkpoint:
        prompt = prompt_checkpoint["prompt"]
    else:
        prompt = self._render_prompt(keyword, step0_data, step1_data)
        await self._save_checkpoint(ctx, "prompt_ready", {"prompt": prompt})

    # LLM呼び出し（ここが最もコストが高い）
    response = await llm.generate(...)

    return self._structure_output(response)
```

---

## 並列実行特有の考慮事項

### 1. 3a/3b/3c の役割分担

| ステップ | 主な役割 | 出力の用途 |
|----------|----------|-----------|
| **3a** | 検索意図・ペルソナ | Step4 の戦略立案 |
| **3b** | 共起キーワード | Step4 のSEO最適化 |
| **3c** | 競合差別化 | Step4 の差別化戦略 |

### 2. 出力の相互参照

```python
# Step4 での活用例
def render_step4_prompt(step3a, step3b, step3c):
    return f"""
    ## 検索意図とペルソナ（Step3a）
    {step3a.search_intent}
    {step3a.personas}

    ## 重要キーワード（Step3b）
    {step3b.cooccurrence_keywords}

    ## 差別化ポイント（Step3c）
    {step3c.differentiation_points}

    上記を統合して戦略的アウトラインを作成してください。
    """
```

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **高** | 構造化出力スキーマ | 2h | Step4 の安定性に直結 |
| **高** | 出力パーサー | 2h | フォーマット整形の基盤 |
| **中** | 品質チェック | 2h | 出力品質向上 |
| **中** | プロンプト形式指定 | 1h | パース成功率向上 |
| **低** | 入力キャッシュ | 1h | 再実行効率化 |

---

## テスト観点

1. **正常系**: 構造化出力が正しくパースされる
2. **パース失敗**: 不正形式で適切なエラー
3. **品質チェック**: 必須要素欠落時にリトライ
4. **並列実行**: 他ステップと同時実行で問題なし
5. **部分成功**: 1項目欠落でも警告のみで続行
