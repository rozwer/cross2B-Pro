# Step3b: Cooccurrence Extraction - 改善案

## 概要

| 項目       | 内容                                     |
| ---------- | ---------------------------------------- |
| ファイル   | `apps/worker/activities/step3b.py`       |
| Activity名 | `step3b_cooccurrence_extraction`         |
| 使用LLM    | Gemini（グラウンディング対応）           |
| 目的       | 共起キーワード・関連キーワード抽出       |
| 特記       | **ワークフローの心臓部** - SEO分析の核心 |

---

## 現状分析

### リトライ戦略

**現状**:

- Temporal の `RetryPolicy` に依存
- 並列実行時は `parallel.py` で管理
- 汎用的な `Exception` キャッチで `RETRYABLE` 分類

**問題点**:

1. **LLM エラーの詳細分類なし**: 3a と異なり細分化されていない
2. **グラウンディング失敗の考慮なし**: Gemini 固有の grounding エラー対応なし
3. **競合データ不足時の対応なし**: `competitors` が少ない場合の品質低下

### フォーマット整形機構

**現状**:

- `cooccurrence_analysis` として自由形式テキスト保存
- 競合サマリーを上位5件・各500文字に制限

**問題点**:

1. **キーワードリストの構造化なし**: 後続での活用が困難
2. **重要度・頻度の定量化なし**: どのキーワードが重要か不明
3. **カテゴリ分類なし**: LSIキーワード、関連語、同義語の区別なし

### 中途開始機構

**現状**:

- ステップ全体の冪等性のみ
- 競合データ準備後のチェックポイントなし

**問題点**:

1. **競合サマリー生成のやり直し**: step1 データの加工を毎回実行
2. **プロンプト生成後の保存なし**: LLM 呼び出し前に失敗すると最初から

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 LLM エラーの詳細分類

```python
from apps.api.llm.exceptions import (
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMGroundingError,  # Gemini 固有
)

class Step3BCooccurrenceExtraction(BaseActivity):
    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... 準備処理 ...

        try:
            response = await llm.generate(...)
        except LLMGroundingError as e:
            # グラウンディング失敗は RETRYABLE（一時的な問題の可能性）
            raise ActivityError(
                f"Grounding failed: {e}",
                category=ErrorCategory.RETRYABLE,
                details={"grounding_error": str(e)},
            ) from e
        except (LLMRateLimitError, LLMTimeoutError) as e:
            raise ActivityError(
                f"LLM temporary failure: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e
        except (LLMAuthenticationError, LLMInvalidRequestError) as e:
            raise ActivityError(
                f"LLM permanent failure: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e
        except Exception as e:
            raise ActivityError(
                f"Unexpected error: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e
```

#### 1.2 競合データ不足時の対応

```python
MIN_COMPETITORS_FOR_QUALITY = 3  # 最低3件で品質保証
COMPETITOR_WARNING_THRESHOLD = 5  # 5件未満で警告

async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    competitors = step1_data.get("competitors", [])

    if len(competitors) < MIN_COMPETITORS_FOR_QUALITY:
        raise ActivityError(
            f"Insufficient competitor data: {len(competitors)} "
            f"(minimum: {MIN_COMPETITORS_FOR_QUALITY})",
            category=ErrorCategory.NON_RETRYABLE,
            details={"competitor_count": len(competitors)},
        )

    if len(competitors) < COMPETITOR_WARNING_THRESHOLD:
        activity.logger.warning(
            f"Low competitor count ({len(competitors)}), "
            f"analysis quality may be reduced"
        )

    # ... 処理続行 ...
```

#### 1.3 出力品質チェック

```python
def _validate_output_quality(self, content: str, keyword: str) -> QualityResult:
    """共起キーワード抽出の品質チェック"""
    issues = []

    # キーワードが含まれているか
    if keyword.lower() not in content.lower():
        issues.append("primary_keyword_missing")

    # 最低限のキーワード数があるか
    keyword_patterns = [
        r"関連キーワード|related keyword",
        r"共起|co-occur",
        r"LSI|latent semantic",
    ]
    found_patterns = sum(1 for p in keyword_patterns if re.search(p, content, re.I))
    if found_patterns < 1:
        issues.append("no_keyword_categories")

    # 具体的なキーワードがリストされているか
    list_indicators = ["・", "-", "1.", "2.", "*"]
    has_list = any(ind in content for ind in list_indicators)
    if not has_list:
        issues.append("no_keyword_list")

    return QualityResult(
        is_acceptable=len(issues) <= 1,
        issues=issues,
    )
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field
from typing import Literal

class KeywordItem(BaseModel):
    """個別キーワード"""
    keyword: str
    category: Literal["cooccurrence", "lsi", "related", "synonym", "long_tail"]
    importance: float = Field(..., ge=0.0, le=1.0, description="重要度スコア")
    frequency: int = Field(default=0, description="競合での出現頻度")
    context: str = Field(default="", description="使用コンテキスト")

class KeywordCluster(BaseModel):
    """キーワードクラスター"""
    theme: str
    keywords: list[KeywordItem]
    relevance_to_main: float

class CooccurrenceOutput(BaseModel):
    """Step3b の構造化出力"""
    primary_keyword: str
    cooccurrence_keywords: list[KeywordItem] = Field(..., min_length=5)
    lsi_keywords: list[KeywordItem] = Field(default_factory=list)
    long_tail_variations: list[str] = Field(default_factory=list)
    keyword_clusters: list[KeywordCluster] = Field(default_factory=list)
    competitor_coverage: dict[str, list[str]] = Field(
        default_factory=dict,
        description="競合ごとのキーワードカバレッジ"
    )
    recommendations: list[str] = Field(default_factory=list)
    raw_analysis: str
```

#### 2.2 プロンプトでの形式指定

````python
STEP3B_OUTPUT_FORMAT = """
以下のJSON形式で出力してください。これはSEO記事の心臓部となる重要な分析です。

```json
{
  "primary_keyword": "メインキーワード",
  "cooccurrence_keywords": [
    {
      "keyword": "共起キーワード",
      "category": "cooccurrence",
      "importance": 0.0-1.0,
      "frequency": 競合での出現数,
      "context": "よく使われる文脈"
    }
  ],
  "lsi_keywords": [
    {"keyword": "意味的に関連するキーワード", "category": "lsi", ...}
  ],
  "long_tail_variations": [
    "ロングテールキーワード1",
    "ロングテールキーワード2"
  ],
  "keyword_clusters": [
    {
      "theme": "クラスターテーマ",
      "keywords": [...],
      "relevance_to_main": 0.0-1.0
    }
  ],
  "recommendations": [
    "記事構成への推奨事項"
  ],
  "raw_analysis": "詳細分析テキスト"
}
````

重要度(importance)の基準:

- 1.0: 必須（メインキーワードと同等）
- 0.7-0.9: 高重要度（見出しに含めるべき）
- 0.4-0.6: 中重要度（本文で言及）
- 0.1-0.3: 低重要度（補足的に使用）
  """

````

#### 2.3 出力パーサー

```python
class Step3BOutputParser:
    def parse(self, raw_content: str, keyword: str) -> CooccurrenceOutput:
        """LLM出力をパースして構造化"""
        # JSON抽出を試みる
        try:
            json_str = self._extract_json(raw_content)
            data = json.loads(json_str)

            # primary_keyword を補完
            if not data.get("primary_keyword"):
                data["primary_keyword"] = keyword

            return CooccurrenceOutput(**data)
        except (json.JSONDecodeError, ValidationError):
            # 自由形式からの抽出
            return self._extract_from_freeform(raw_content, keyword)

    def _extract_from_freeform(self, content: str, keyword: str) -> CooccurrenceOutput:
        """自由形式テキストからキーワードを抽出"""
        keywords = []

        # リスト形式のキーワードを抽出
        list_patterns = [
            r'[・\-\*]\s*([^\n]+)',
            r'\d+\.\s*([^\n]+)',
        ]
        for pattern in list_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # キーワードらしいものを抽出（短い文字列）
                if len(match) < 50 and not match.endswith('。'):
                    keywords.append(KeywordItem(
                        keyword=match.strip(),
                        category="cooccurrence",
                        importance=0.5,  # デフォルト
                    ))

        if not keywords:
            raise OutputParseError("No keywords extracted", raw=content)

        return CooccurrenceOutput(
            primary_keyword=keyword,
            cooccurrence_keywords=keywords,
            raw_analysis=content,
        )
````

### 3. 中途開始機構の実装

#### 3.1 競合サマリーの事前準備とキャッシュ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 競合サマリーのチェックポイント
    summaries_checkpoint = await self._load_checkpoint(ctx, "competitor_summaries")

    if summaries_checkpoint:
        competitor_summaries = summaries_checkpoint["summaries"]
    else:
        # Step1 データから競合サマリーを生成
        step1_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step1"
        ) or {}
        competitors = step1_data.get("competitors", [])

        competitor_summaries = self._prepare_competitor_summaries(competitors)

        # チェックポイント保存
        await self._save_checkpoint(ctx, "competitor_summaries", {
            "summaries": competitor_summaries,
            "original_count": len(competitors),
        })

    # ... プロンプト生成・LLM呼び出し ...

def _prepare_competitor_summaries(
    self,
    competitors: list[dict],
    max_competitors: int = 5,
    max_content_chars: int = 500,
) -> list[dict]:
    """競合サマリーの準備（品質スコア順にソート）"""
    # コンテンツ品質でソート
    scored_competitors = []
    for comp in competitors:
        content = comp.get("content", "")
        score = self._calculate_content_quality(content)
        scored_competitors.append((score, comp))

    scored_competitors.sort(key=lambda x: x[0], reverse=True)

    # 上位を選択してサマリー化
    summaries = []
    for _, comp in scored_competitors[:max_competitors]:
        summaries.append({
            "title": comp.get("title", ""),
            "content_preview": comp.get("content", "")[:max_content_chars],
            "url": comp.get("url", ""),
        })

    return summaries

def _calculate_content_quality(self, content: str) -> float:
    """コンテンツ品質スコア（0-1）"""
    if not content:
        return 0.0

    score = 0.0
    # 長さスコア
    score += min(len(content) / 5000, 0.3)
    # 構造スコア（見出しの存在）
    if re.search(r'#+\s|<h[1-6]>', content):
        score += 0.2
    # リストスコア
    if re.search(r'[・\-\*]\s', content):
        score += 0.1
    # 数値データスコア
    if re.search(r'\d+%|\d+円|\d+万', content):
        score += 0.2
    # 文の多様性
    sentences = content.split('。')
    if len(sentences) > 10:
        score += 0.2

    return min(score, 1.0)
```

---

## 特記事項：ワークフローの心臓部

### 重要性

Step3b は以下の理由で**ワークフローの心臓部**と位置づけられています：

1. **SEO の核心**: 共起キーワードは検索エンジン最適化の基盤
2. **差別化の源泉**: 競合が見落としているキーワードの発見
3. **コンテンツ品質の決定要因**: ここでの分析が最終記事の網羅性を決定

### 品質保証の強化

```python
# Step3b 専用の品質基準
STEP3B_QUALITY_THRESHOLDS = {
    "min_cooccurrence_keywords": 10,
    "min_lsi_keywords": 5,
    "min_long_tail": 3,
    "min_keyword_clusters": 2,
}

def _enforce_quality_standards(self, output: CooccurrenceOutput) -> None:
    """品質基準の強制"""
    issues = []

    if len(output.cooccurrence_keywords) < STEP3B_QUALITY_THRESHOLDS["min_cooccurrence_keywords"]:
        issues.append(f"cooccurrence_keywords count: {len(output.cooccurrence_keywords)}")

    if len(output.lsi_keywords) < STEP3B_QUALITY_THRESHOLDS["min_lsi_keywords"]:
        issues.append(f"lsi_keywords count: {len(output.lsi_keywords)}")

    if issues:
        activity.logger.warning(f"Quality below threshold: {issues}")
        # 警告のみ、失敗はさせない（心臓部なので慎重に）
```

---

## 優先度と実装順序

| 優先度   | 改善項目               | 工数見積 | 理由                         |
| -------- | ---------------------- | -------- | ---------------------------- |
| **最高** | 構造化出力スキーマ     | 3h       | ワークフロー心臓部の品質保証 |
| **最高** | 出力パーサー           | 3h       | キーワード活用の基盤         |
| **高**   | 品質チェック           | 2h       | 分析品質の担保               |
| **高**   | 競合サマリーキャッシュ | 2h       | 再実行効率化                 |
| **中**   | LLMエラー詳細分類      | 1h       | エラー対応改善               |
| **低**   | 競合データ品質ソート   | 1h       | 入力品質向上                 |

---

## テスト観点

1. **正常系**: 構造化キーワードリストが正しく生成される
2. **品質閾値**: キーワード数が基準を満たす
3. **競合不足**: 3件未満で適切にエラー
4. **パース失敗**: 自由形式からもキーワード抽出可能
5. **並列実行**: 3a/3c と同時実行で問題なし
6. **グラウンディングエラー**: Gemini 固有エラーでリトライ
