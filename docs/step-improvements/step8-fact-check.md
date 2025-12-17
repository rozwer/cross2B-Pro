# Step8: Fact Check - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step8.py` |
| Activity名 | `step8_fact_check` |
| 使用LLM | Gemini（グラウンディング対応） |
| 目的 | 記事内の事実・主張の検証 + FAQ生成 |
| 特記 | 3回のLLM呼び出し（claims抽出 → 検証 → FAQ生成） |

---

## 現状分析

### リトライ戦略

**現状**:
- 各LLM呼び出しで `Exception` キャッチ → `RETRYABLE`
- claims抽出失敗、検証失敗、FAQ生成失敗それぞれ個別に処理

**問題点**:
1. **claims抽出の品質検証なし**: 抽出された主張が適切か確認しない
2. **検証結果の構造化なし**: 自由形式テキストで保存
3. **矛盾検出ロジックが単純**: `"contradiction" in text` のみ
4. **FAQ品質の検証なし**

### フォーマット整形機構

**現状**:
- `claims`, `verification`, `faq` を自由形式テキストで保存
- `has_contradictions` フラグで矛盾有無を判定

**問題点**:
1. **主張リストが構造化されていない**: どの主張がどう検証されたか不明
2. **検証結果の信頼度なし**: 検証の確信度が分からない
3. **FAQの構造化なし**: Q&A 形式が保証されない

### 中途開始機構

**現状**:
- ステップ全体の冪等性のみ
- 3回のLLM呼び出し間にチェックポイントなし

**問題点**:
1. **claims抽出後の保存なし**: 検証中に失敗すると最初から
2. **検証後の保存なし**: FAQ生成で失敗すると検証からやり直し

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 claims抽出の品質検証

```python
class Step8FactCheck(BaseActivity):
    MIN_CLAIMS_COUNT = 3  # 最低3つの主張

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # Step 8.1: Claims抽出
        claims_result = await self._extract_claims(llm, polished_content)

        # 品質チェック
        if claims_result.count < self.MIN_CLAIMS_COUNT:
            activity.logger.warning(
                f"Low claims count: {claims_result.count}"
            )

        # ... 検証処理 ...

    def _validate_claims_quality(
        self,
        claims_text: str,
    ) -> QualityResult:
        """主張抽出の品質検証"""
        issues = []

        # 主張の数をカウント
        claim_indicators = [
            r'^\d+\.',
            r'^[\-\*]',
            r'^・',
        ]
        claim_count = sum(
            len(re.findall(p, claims_text, re.M))
            for p in claim_indicators
        )

        if claim_count < self.MIN_CLAIMS_COUNT:
            issues.append(f"too_few_claims: {claim_count}")

        # 具体性のチェック
        specificity_keywords = ["数値", "統計", "調査", "%", "円", "年"]
        has_specific = any(kw in claims_text for kw in specificity_keywords)
        if not has_specific:
            issues.append("no_specific_claims")

        return QualityResult(
            is_acceptable=len(issues) <= 1,
            issues=issues,
            claim_count=claim_count,
        )
```

#### 1.2 検証結果の確信度評価

```python
def _evaluate_verification_confidence(
    self,
    verification_text: str,
) -> VerificationConfidence:
    """検証結果の確信度を評価"""
    # 確信度キーワード
    high_confidence = ["確認できた", "verified", "correct", "正確"]
    medium_confidence = ["おそらく", "likely", "可能性", "probably"]
    low_confidence = ["不明", "unverified", "確認できない", "unclear"]

    verification_lower = verification_text.lower()

    scores = {
        "high": sum(1 for kw in high_confidence if kw in verification_lower),
        "medium": sum(1 for kw in medium_confidence if kw in verification_lower),
        "low": sum(1 for kw in low_confidence if kw in verification_lower),
    }

    # 矛盾の検出（より詳細に）
    contradiction_keywords = [
        "矛盾", "contradiction", "incorrect", "間違い",
        "誤り", "false", "不正確",
    ]
    contradictions_found = [
        kw for kw in contradiction_keywords
        if kw in verification_lower
    ]

    return VerificationConfidence(
        high_count=scores["high"],
        medium_count=scores["medium"],
        low_count=scores["low"],
        contradictions_found=contradictions_found,
        has_critical_issues=len(contradictions_found) >= 2,
    )
```

### 2. フォーマット整形機構の導入

#### 2.1 構造化出力スキーマ

```python
from pydantic import BaseModel, Field
from typing import Literal

class Claim(BaseModel):
    """検証対象の主張"""
    claim_id: str
    text: str
    source_section: str = ""
    claim_type: Literal["statistic", "fact", "opinion", "definition"]

class VerificationResult(BaseModel):
    """検証結果"""
    claim_id: str
    status: Literal["verified", "unverified", "contradicted", "partially_verified"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str = ""
    source: str = ""
    recommendation: str = ""

class FAQItem(BaseModel):
    """FAQ項目"""
    question: str
    answer: str
    related_claims: list[str] = Field(default_factory=list)

class Step8Output(BaseModel):
    """Step8 の構造化出力"""
    keyword: str
    claims: list[Claim]
    verification_results: list[VerificationResult]
    faq_items: list[FAQItem]
    summary: dict[str, int] = Field(
        default_factory=dict,
        description="status別の集計"
    )
    has_contradictions: bool = False
    critical_issues: list[str] = Field(default_factory=list)
    recommend_rejection: bool = False
```

#### 2.2 プロンプトでの形式指定

```python
STEP8_CLAIMS_FORMAT = """
記事から検証すべき主張を抽出してください。

出力形式：
```json
{
  "claims": [
    {
      "claim_id": "C1",
      "text": "主張の内容",
      "source_section": "該当セクション名",
      "claim_type": "statistic|fact|opinion|definition"
    }
  ]
}
```

抽出基準：
- 統計データ（数値、割合、調査結果）
- 事実の記述（歴史的事実、科学的事実）
- 定義や説明（用語の定義、概念の説明）
- 比較や評価（優劣の主張、推奨事項）
"""

STEP8_VERIFY_FORMAT = """
以下の主張を検証してください。

出力形式：
```json
{
  "verification_results": [
    {
      "claim_id": "C1",
      "status": "verified|unverified|contradicted|partially_verified",
      "confidence": 0.0-1.0,
      "evidence": "検証の根拠",
      "source": "情報源（あれば）",
      "recommendation": "修正が必要な場合の推奨"
    }
  ]
}
```

ステータス基準：
- verified: 確認できた（confidence > 0.8）
- partially_verified: 部分的に確認（0.5 < confidence <= 0.8）
- unverified: 確認できなかった（confidence <= 0.5）
- contradicted: 矛盾する情報を発見
"""
```

#### 2.3 FAQ構造化

```python
STEP8_FAQ_FORMAT = """
検証結果に基づいてFAQを生成してください。

出力形式：
```json
{
  "faq_items": [
    {
      "question": "読者が持ちそうな疑問",
      "answer": "回答",
      "related_claims": ["関連する主張のID"]
    }
  ]
}
```

FAQ生成基準：
- 検証で「unverified」「contradicted」となった主張に関連する疑問
- 読者が誤解しやすいポイント
- 追加情報が有益な項目
- 最低3つ、最大7つのFAQ
"""
```

### 3. 中途開始機構の実装

#### 3.1 各LLM呼び出し後のチェックポイント

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # Step 8.1: Claims抽出
    claims_checkpoint = await self._load_checkpoint(ctx, "claims_extracted")

    if claims_checkpoint:
        extracted_claims = claims_checkpoint["claims"]
    else:
        claims_response = await llm.generate(...)
        extracted_claims = self._parse_claims(claims_response.content)

        await self._save_checkpoint(ctx, "claims_extracted", {
            "claims": extracted_claims,
            "raw_response": claims_response.content,
        })

    # Step 8.2: 検証
    verify_checkpoint = await self._load_checkpoint(ctx, "verification_done")

    if verify_checkpoint:
        verification_results = verify_checkpoint["results"]
    else:
        verify_response = await llm.generate(...)
        verification_results = self._parse_verification(verify_response.content)

        await self._save_checkpoint(ctx, "verification_done", {
            "results": verification_results,
            "raw_response": verify_response.content,
        })

    # Step 8.3: FAQ生成
    faq_response = await llm.generate(...)
    faq_items = self._parse_faq(faq_response.content)

    return self._structure_output(
        extracted_claims,
        verification_results,
        faq_items,
    )
```

---

## ファクトチェックの重要性

### 品質ゲートとしての役割

```
[Step7b: ポリッシュ済みコンテンツ]
        ↓
[Step8: ファクトチェック] ← 品質ゲート
        ↓
    has_contradictions?
        ↓
    YES → recommend_rejection フラグ → UI で警告表示
    NO  → Step9 へ進行
```

### 矛盾検出時のアクション

```python
def _determine_rejection_recommendation(
    self,
    verification_results: list[VerificationResult],
) -> tuple[bool, list[str]]:
    """却下推奨の判定"""
    critical_issues = []

    contradicted_count = sum(
        1 for r in verification_results
        if r.status == "contradicted"
    )

    if contradicted_count >= 2:
        critical_issues.append(f"{contradicted_count} contradictions found")

    # 高確信度の矛盾
    high_confidence_contradictions = [
        r for r in verification_results
        if r.status == "contradicted" and r.confidence > 0.8
    ]
    if high_confidence_contradictions:
        critical_issues.append("High-confidence contradictions detected")

    recommend_rejection = len(critical_issues) > 0

    return recommend_rejection, critical_issues
```

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **最高** | 検証結果の構造化 | 3h | 矛盾の明確な追跡 |
| **高** | claims抽出の構造化 | 2h | 検証の基盤 |
| **高** | 確信度評価 | 2h | 矛盾検出の精度向上 |
| **中** | FAQ構造化 | 1h | Q&A形式の保証 |
| **中** | チェックポイント | 2h | 3回のLLM呼び出し効率化 |
| **低** | 品質検証 | 1h | claims数の保証 |

---

## テスト観点

1. **正常系**: 主張が抽出・検証され、FAQが生成される
2. **矛盾検出**: contradicted ステータスで recommend_rejection が true
3. **構造化パース**: JSON形式で正しくパースされる
4. **チェックポイント**: claims抽出後から再開できる
5. **最小claims数**: 3つ未満で警告
6. **確信度**: confidence スコアが正しく設定される
