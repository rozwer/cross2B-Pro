# Step0: Keyword Selection - 改善案

## 概要

| 項目       | 内容                                 |
| ---------- | ------------------------------------ |
| ファイル   | `apps/worker/activities/step0.py`    |
| Activity名 | `step0_keyword_selection`            |
| 使用LLM    | Gemini（デフォルト）                 |
| 目的       | 入力キーワードの分析・最適化戦略決定 |

---

## 現状分析

### リトライ戦略

**現状**:

- Temporal の `RetryPolicy` に依存（最大3回、指数バックオフ）
- LLM エラーを `RETRYABLE` / `NON_RETRYABLE` に分類

**問題点**:

1. **LLM出力の品質チェックなし**: レスポンスが返ってきたら成功扱い
2. **Rate Limit対応が単純**: 429エラー時の待機時間が固定的
3. **部分的失敗の考慮なし**: LLMが不完全な回答を返した場合の対応がない

### フォーマット整形機構

**現状**:

- LLMレスポンスを `response.content` としてそのまま保存
- JSON構造化なし（自由形式テキスト）

**問題点**:

1. **出力形式が不定**: LLMの気分次第で形式が変わる
2. **後続ステップでのパースが困難**: step3a等が `analysis` を参照するが形式保証なし
3. **バリデーションなし**: 必須項目の欠落を検出できない

### 中途開始機構

**現状**:

- `BaseActivity._check_existing_output()` で冪等性チェック可能（だが無効化中）
- `input_digest` による同一入力検出の仕組みはある

**問題点**:

1. **冪等性キャッシュが無効**: Line 337 で `return None` 固定
2. **部分結果の保存なし**: LLM呼び出し前後で中間状態がない
3. **再開ポイントがない**: 失敗したら最初からやり直し

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 出力品質チェック付きリトライ

```python
class Step0KeywordSelection(BaseActivity):
    MAX_QUALITY_RETRIES = 2  # 品質不足時の追加リトライ

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... 既存のプロンプト準備 ...

        for quality_attempt in range(self.MAX_QUALITY_RETRIES + 1):
            response = await self._call_llm_with_retry(llm, prompt, llm_config, metadata)

            # 出力品質チェック
            quality_result = self._validate_output_quality(response.content)
            if quality_result.is_acceptable:
                break

            if quality_attempt < self.MAX_QUALITY_RETRIES:
                # 品質向上のためのリトライ（プロンプト補強）
                prompt = self._enhance_prompt_for_retry(prompt, quality_result.issues)
                activity.logger.warning(f"Quality retry {quality_attempt + 1}: {quality_result.issues}")
            else:
                raise ActivityError(
                    f"Output quality insufficient after {self.MAX_QUALITY_RETRIES} retries",
                    category=ErrorCategory.RETRYABLE,
                    details={"quality_issues": quality_result.issues},
                )

        return self._structure_output(response)
```

#### 1.2 Rate Limit 対応の改善

```python
async def _call_llm_with_retry(self, llm, prompt, config, metadata) -> LLMResponse:
    """Rate limit を考慮したLLM呼び出し"""
    try:
        return await llm.generate(...)
    except LLMRateLimitError as e:
        # Retry-After ヘッダーがあれば尊重
        retry_after = getattr(e, 'retry_after', None)
        if retry_after and retry_after < 60:  # 60秒以内なら待機
            activity.logger.info(f"Rate limited, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            return await llm.generate(...)  # 1回だけ即時リトライ
        raise  # Temporal のリトライに任せる
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマの定義

```python
from pydantic import BaseModel, Field

class KeywordAnalysisOutput(BaseModel):
    """Step0の構造化出力スキーマ"""
    primary_keyword: str = Field(..., description="メインキーワード")
    search_intent: str = Field(..., description="検索意図の分類")
    difficulty_score: int = Field(..., ge=1, le=10, description="難易度スコア")
    recommended_angles: list[str] = Field(..., min_length=1, description="推奨切り口")
    target_audience: str = Field(..., description="想定読者層")
    content_type_suggestion: str = Field(..., description="推奨コンテンツ形式")
    raw_analysis: str = Field(..., description="詳細分析テキスト")
```

#### 2.2 出力パーサーの実装

````python
class Step0OutputParser:
    """Step0出力のパース・バリデーション"""

    def parse(self, raw_content: str) -> KeywordAnalysisOutput:
        """LLM出力をパースして構造化"""
        # 1. JSON形式の場合
        if self._looks_like_json(raw_content):
            return self._parse_json(raw_content)

        # 2. Markdown形式の場合
        if self._looks_like_markdown(raw_content):
            return self._parse_markdown(raw_content)

        # 3. 自由形式の場合（フォールバックではなく、構造抽出）
        return self._extract_structure(raw_content)

    def _parse_json(self, content: str) -> KeywordAnalysisOutput:
        """JSON形式をパース"""
        # コードブロック除去
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]

        try:
            data = json.loads(content)
            return KeywordAnalysisOutput(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise OutputParseError(f"JSON parse failed: {e}", raw=content)

    def _extract_structure(self, content: str) -> KeywordAnalysisOutput:
        """自由形式テキストから構造を抽出"""
        # 正規表現やキーワードマッチングで必須項目を抽出
        # 抽出できない場合は明示的にエラー
        extracted = {}

        # 検索意図の抽出
        intent_patterns = [
            r"検索意図[：:]\s*(.+)",
            r"intent[：:]\s*(.+)",
            r"ユーザーの目的[：:]\s*(.+)",
        ]
        for pattern in intent_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted["search_intent"] = match.group(1).strip()
                break

        if "search_intent" not in extracted:
            raise OutputParseError("search_intent not found in output", raw=content)

        # ... 他の必須項目も同様に抽出 ...

        return KeywordAnalysisOutput(**extracted)
````

#### 2.3 プロンプトでの形式指定

````python
STEP0_OUTPUT_FORMAT = """
出力は以下のJSON形式で返してください：
```json
{
  "primary_keyword": "分析対象のキーワード",
  "search_intent": "informational|navigational|transactional|commercial",
  "difficulty_score": 1-10の整数,
  "recommended_angles": ["切り口1", "切り口2", "切り口3"],
  "target_audience": "想定読者層の説明",
  "content_type_suggestion": "記事|比較表|ガイド|FAQ等",
  "raw_analysis": "詳細な分析内容"
}
````

"""

````

### 3. 中途開始機構の実装

#### 3.1 冪等性キャッシュの有効化

```python
async def _check_existing_output(self, path: str, input_digest: str) -> ArtifactRef | None:
    """冪等性チェック - 同一入力なら既存結果を返す"""
    try:
        meta_path = path.replace("/output.json", "/metadata.json")
        meta_bytes = await self.store.get_raw(meta_path)

        if not meta_bytes:
            return None

        metadata = json.loads(meta_bytes.decode("utf-8"))

        # input_digest が一致するか確認
        if metadata.get("input_digest") != input_digest:
            activity.logger.info("Input changed, re-executing step")
            return None

        # 出力が存在するか確認
        output_bytes = await self.store.get_raw(path)
        if not output_bytes:
            return None

        # 出力の整合性チェック（digest検証）
        output_digest = hashlib.sha256(output_bytes).hexdigest()

        return ArtifactRef(
            path=path,
            digest=output_digest,
            size_bytes=len(output_bytes),
            content_type="application/json",
        )
    except Exception as e:
        activity.logger.warning(f"Idempotency check failed: {e}")
        return None
````

#### 3.2 チェックポイントの概念（将来拡張）

```python
# Step0は単純なので中間チェックポイントは不要
# ただし、将来の拡張に備えてインターフェースを定義

class StepCheckpoint(BaseModel):
    """ステップ内チェックポイント"""
    step_id: str
    phase: str  # "pre_llm", "post_llm", "post_validation"
    data: dict[str, Any]
    created_at: datetime
```

---

## 優先度と実装順序

| 優先度 | 改善項目                 | 工数見積 | 理由                       |
| ------ | ------------------------ | -------- | -------------------------- |
| **高** | 構造化出力スキーマ       | 2h       | 後続ステップの安定性に直結 |
| **高** | 出力パーサー             | 3h       | フォーマット整形の基盤     |
| **中** | 品質チェック付きリトライ | 2h       | 出力品質向上               |
| **中** | 冪等性キャッシュ有効化   | 1h       | 再実行時の効率化           |
| **低** | Rate Limit対応改善       | 1h       | 現状でも動作する           |

---

## テスト観点

1. **正常系**: 構造化出力が正しくパースされる
2. **パースエラー**: 不正なJSON/Markdownでエラーが発生する
3. **品質リトライ**: 必須項目欠落時にリトライが発動する
4. **冪等性**: 同一入力で2回目は既存結果を返す
5. **入力変更**: 入力が変わったら再実行される
