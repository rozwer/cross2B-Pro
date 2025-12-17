# Step3c: Competitor Analysis - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step3c.py` |
| Activity名 | `step3c_competitor_analysis` |
| 使用LLM | Gemini（デフォルト） |
| 目的 | 競合分析・差別化戦略の策定 |
| 特記 | Step3a/3b と並列実行 |

---

## 現状分析

### リトライ戦略

**現状**:
- 汎用的な `Exception` キャッチで `RETRYABLE` 分類
- 並列実行時は `parallel.py` で管理
- LLM エラーの細分化なし（3a と異なる）

**問題点**:
1. **エラー分類が粗い**: すべての例外を同じように扱う
2. **競合データ品質の考慮なし**: step1 の品質が低い場合の対応なし
3. **分析深度の制御なし**: 競合数に応じた分析調整がない

### フォーマット整形機構

**現状**:
- `competitor_analysis` として自由形式テキスト保存
- 競合ごとに `url`, `title`, `content_length`, `content_preview` を渡す

**問題点**:
1. **差別化ポイントの構造化なし**: 何が差別化要因か不明確
2. **競合ごとの強み/弱みが未整理**: 比較分析が困難
3. **優先順位付けなし**: どの差別化が最も重要か判断不可

### 中途開始機構

**現状**:
- ステップ全体の冪等性のみ
- 競合分析データの準備後チェックポイントなし

**問題点**:
1. **競合データ加工のやり直し**: 毎回 step1 から再加工
2. **LLM 呼び出し前の状態保存なし**: プロンプト生成後に失敗すると最初から

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
)

class Step3CCompetitorAnalysis(BaseActivity):
    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... 準備処理 ...

        try:
            response = await llm.generate(...)
        except (LLMRateLimitError, LLMTimeoutError) as e:
            raise ActivityError(
                f"LLM temporary failure: {e}",
                category=ErrorCategory.RETRYABLE,
                details={"llm_error": str(e)},
            ) from e
        except (LLMAuthenticationError, LLMInvalidRequestError) as e:
            raise ActivityError(
                f"LLM permanent failure: {e}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"llm_error": str(e)},
            ) from e
        except Exception as e:
            raise ActivityError(
                f"Unexpected error: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e
```

#### 1.2 競合データ品質チェック

```python
MIN_COMPETITORS = 2
MIN_CONTENT_PER_COMPETITOR = 200  # 最低200文字

async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    competitors = step1_data.get("competitors", [])

    # 品質チェック
    quality_competitors = [
        c for c in competitors
        if len(c.get("content", "")) >= MIN_CONTENT_PER_COMPETITOR
    ]

    if len(quality_competitors) < MIN_COMPETITORS:
        raise ActivityError(
            f"Insufficient quality competitors: {len(quality_competitors)} "
            f"(minimum: {MIN_COMPETITORS})",
            category=ErrorCategory.NON_RETRYABLE,
            details={
                "total_competitors": len(competitors),
                "quality_competitors": len(quality_competitors),
            },
        )

    # 品質の低い競合は警告のみ
    low_quality_count = len(competitors) - len(quality_competitors)
    if low_quality_count > 0:
        activity.logger.warning(
            f"Excluded {low_quality_count} low-quality competitors"
        )

    # ... 処理続行（quality_competitors を使用）...
```

#### 1.3 出力品質チェック

```python
def _validate_output_quality(self, content: str) -> QualityResult:
    """競合分析の品質チェック"""
    issues = []

    # 差別化に関する言及
    differentiation_keywords = [
        "差別化", "differentiation", "独自", "unique",
        "強み", "strength", "弱み", "weakness",
    ]
    found = sum(1 for kw in differentiation_keywords if kw in content.lower())
    if found < 2:
        issues.append("insufficient_differentiation_analysis")

    # 具体的な提案の存在
    recommendation_indicators = [
        "推奨", "recommend", "すべき", "should",
        "提案", "suggest", "戦略", "strategy",
    ]
    found_rec = sum(1 for kw in recommendation_indicators if kw in content.lower())
    if found_rec < 1:
        issues.append("no_recommendations")

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

class CompetitorProfile(BaseModel):
    """競合プロファイル"""
    url: str
    title: str
    strengths: list[str] = Field(..., min_length=1, description="強み")
    weaknesses: list[str] = Field(default_factory=list, description="弱み")
    content_focus: list[str] = Field(default_factory=list, description="注力領域")
    unique_value: str = Field(default="", description="独自の価値提案")
    threat_level: Literal["high", "medium", "low"] = "medium"

class DifferentiationStrategy(BaseModel):
    """差別化戦略"""
    category: Literal["content", "expertise", "format", "depth", "perspective"]
    description: str
    priority: Literal["must", "should", "nice_to_have"]
    implementation_hint: str

class GapOpportunity(BaseModel):
    """ギャップ機会"""
    gap_type: str  # "topic", "depth", "format", "audience"
    description: str
    competitors_missing: list[str]  # このギャップを埋めていない競合URL
    value_potential: float = Field(..., ge=0.0, le=1.0)

class CompetitorAnalysisOutput(BaseModel):
    """Step3c の構造化出力"""
    keyword: str
    competitor_profiles: list[CompetitorProfile] = Field(..., min_length=1)
    market_overview: str
    differentiation_strategies: list[DifferentiationStrategy] = Field(..., min_length=2)
    gap_opportunities: list[GapOpportunity] = Field(default_factory=list)
    content_recommendations: list[str] = Field(..., min_length=3)
    competitive_advantages: list[str] = Field(default_factory=list)
    raw_analysis: str
```

#### 2.2 プロンプトでの形式指定

```python
STEP3C_OUTPUT_FORMAT = """
以下のJSON形式で出力してください。競合分析は差別化戦略の基盤です。

```json
{
  "keyword": "分析対象キーワード",
  "competitor_profiles": [
    {
      "url": "競合URL",
      "title": "記事タイトル",
      "strengths": ["強み1", "強み2"],
      "weaknesses": ["弱み1"],
      "content_focus": ["注力トピック"],
      "unique_value": "独自の価値提案",
      "threat_level": "high|medium|low"
    }
  ],
  "market_overview": "市場全体の状況サマリー",
  "differentiation_strategies": [
    {
      "category": "content|expertise|format|depth|perspective",
      "description": "差別化戦略の説明",
      "priority": "must|should|nice_to_have",
      "implementation_hint": "実装のヒント"
    }
  ],
  "gap_opportunities": [
    {
      "gap_type": "topic|depth|format|audience",
      "description": "ギャップの説明",
      "competitors_missing": ["このギャップを埋めていない競合"],
      "value_potential": 0.0-1.0
    }
  ],
  "content_recommendations": [
    "具体的なコンテンツ推奨事項"
  ],
  "competitive_advantages": [
    "我々が持つべき競争優位"
  ],
  "raw_analysis": "詳細分析テキスト"
}
```

threat_level の基準:
- high: 同等以上の品質、SEO強い
- medium: 部分的に競合
- low: 品質低い or 異なるターゲット
"""
```

#### 2.3 出力パーサー

```python
class Step3COutputParser:
    def parse(self, raw_content: str, keyword: str) -> CompetitorAnalysisOutput:
        """LLM出力をパースして構造化"""
        try:
            json_str = self._extract_json(raw_content)
            data = json.loads(json_str)

            if not data.get("keyword"):
                data["keyword"] = keyword

            return CompetitorAnalysisOutput(**data)
        except (json.JSONDecodeError, ValidationError):
            return self._extract_from_freeform(raw_content, keyword)

    def _extract_from_freeform(
        self,
        content: str,
        keyword: str,
    ) -> CompetitorAnalysisOutput:
        """自由形式テキストから構造を抽出"""
        # 差別化戦略の抽出
        strategies = self._extract_differentiation_strategies(content)

        # 推奨事項の抽出
        recommendations = self._extract_recommendations(content)

        if not strategies and not recommendations:
            raise OutputParseError(
                "No differentiation strategies or recommendations found",
                raw=content,
            )

        return CompetitorAnalysisOutput(
            keyword=keyword,
            competitor_profiles=[],  # 自由形式からは抽出困難
            market_overview="",
            differentiation_strategies=strategies,
            gap_opportunities=[],
            content_recommendations=recommendations,
            competitive_advantages=[],
            raw_analysis=content,
        )

    def _extract_differentiation_strategies(
        self,
        content: str,
    ) -> list[DifferentiationStrategy]:
        """差別化戦略を抽出"""
        strategies = []

        # パターンマッチング
        patterns = [
            r"差別化(?:ポイント|戦略)?[：:]\s*(.+?)(?:\n|$)",
            r"(?:独自|ユニーク)な?(?:点|要素)[：:]\s*(.+?)(?:\n|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                strategies.append(DifferentiationStrategy(
                    category="content",  # デフォルト
                    description=match.strip(),
                    priority="should",
                    implementation_hint="",
                ))

        return strategies[:5]  # 最大5件
```

### 3. 中途開始機構の実装

#### 3.1 競合分析データの準備とキャッシュ

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # 競合分析データのチェックポイント
    analysis_data_checkpoint = await self._load_checkpoint(ctx, "analysis_data")

    if analysis_data_checkpoint:
        competitor_analysis = analysis_data_checkpoint["competitor_analysis"]
    else:
        # Step1 データから競合分析データを準備
        step1_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step1"
        ) or {}
        competitors = step1_data.get("competitors", [])

        competitor_analysis = self._prepare_competitor_analysis(competitors)

        # チェックポイント保存
        await self._save_checkpoint(ctx, "analysis_data", {
            "competitor_analysis": competitor_analysis,
            "original_count": len(competitors),
        })

    # ... プロンプト生成・LLM呼び出し ...
```

#### 3.2 分析データの準備処理

```python
def _prepare_competitor_analysis(
    self,
    competitors: list[dict],
) -> list[dict]:
    """競合分析用データの準備"""
    analysis_data = []

    for comp in competitors:
        content = comp.get("content", "")

        # コンテンツから特徴を抽出
        features = self._extract_content_features(content)

        analysis_data.append({
            "url": comp.get("url", ""),
            "title": comp.get("title", ""),
            "content_length": len(content),
            "content_preview": content[:300],
            "features": features,
        })

    return analysis_data

def _extract_content_features(self, content: str) -> dict:
    """コンテンツから特徴を抽出"""
    return {
        "has_images": bool(re.search(r'<img|!\[', content)),
        "has_tables": bool(re.search(r'<table|\|.+\|', content)),
        "has_code": bool(re.search(r'```|<code>', content)),
        "heading_count": len(re.findall(r'^#+\s|<h[1-6]>', content, re.M)),
        "list_count": len(re.findall(r'^[\-\*]\s|^\d+\.', content, re.M)),
        "word_count": len(content.split()),
        "has_faq": bool(re.search(r'FAQ|よくある質問|Q&A', content, re.I)),
    }
```

---

## 並列実行における役割

### 3a/3b/3c の統合

```
Step3a（検索意図・ペルソナ）
    ↓
Step4で統合 → 「誰に」「何を」「どう差別化して」届けるか
    ↑
Step3b（キーワード戦略）
    ↑
Step3c（競合差別化）← このステップ
```

### Step4 への入力

```python
# Step4 での活用例
def prepare_step4_context(step3a, step3b, step3c):
    return {
        "target_audience": step3a.personas,  # 誰に
        "keyword_strategy": step3b.cooccurrence_keywords,  # 何を含めるか
        "differentiation": step3c.differentiation_strategies,  # どう差別化
        "gaps_to_fill": step3c.gap_opportunities,  # どのギャップを埋めるか
    }
```

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **高** | 構造化出力スキーマ | 2h | 差別化戦略の明確化 |
| **高** | 出力パーサー | 2h | Step4 での活用基盤 |
| **中** | 競合品質チェック | 1h | 分析品質の担保 |
| **中** | LLMエラー詳細分類 | 1h | エラー対応改善 |
| **中** | コンテンツ特徴抽出 | 2h | 分析の深化 |
| **低** | 分析データキャッシュ | 1h | 再実行効率化 |

---

## テスト観点

1. **正常系**: 差別化戦略が構造化されて出力される
2. **競合不足**: 2件未満で適切にエラー
3. **低品質競合**: 短いコンテンツが除外される
4. **パース失敗**: 自由形式から戦略・推奨抽出可能
5. **並列実行**: 3a/3b と同時実行で問題なし
6. **出力品質**: 差別化分析が含まれているか検証
