# 工程8: ファクトチェック・FAQ

## 入力スキーマ

```json
{
  "polished_draft": "Step7bOutput - step7bから",
  "primary_sources": "PrimarySource[] - step5から"
}
```

## 出力スキーマ（既存）

```python
class Step8Output(StepOutputBase):
    claims: list[Claim]
    verification_results: list[VerificationResult]
    faq_items: list[FAQItem]
    summary: VerificationSummary
    has_contradictions: bool
    critical_issues: list[str]
    recommend_rejection: bool
    model: str
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 検証項目 | 基本 | 数値、出典、時系列、論理 |
| 矛盾検出 | あり | 却下推奨フラグ強化 |
| FAQ生成 | あり | LLMO最適化形式 |
| 自動修正 | なし | 禁止（人間判断に委ねる） |

### 追加フィールド
```json
{
  "verification_categories": {
    "numeric_data": {
      "claims_checked": "number",
      "verified": "number",
      "issues": "string[]"
    },
    "source_accuracy": {
      "claims_checked": "number",
      "verified": "number",
      "issues": "string[]"
    },
    "timeline_consistency": {
      "claims_checked": "number",
      "verified": "number",
      "issues": "string[]"
    },
    "logical_consistency": {
      "claims_checked": "number",
      "verified": "number",
      "issues": "string[]"
    }
  },
  "faq_llmo_optimization": {
    "question_format_count": "number",
    "voice_search_friendly": "boolean",
    "structured_data_ready": "boolean"
  },
  "rejection_analysis": {
    "should_reject": "boolean",
    "severity": "string - critical/major/minor",
    "reasons": "string[]",
    "human_review_required": "boolean"
  }
}
```

## 実装タスク

- [ ] `verification_categories` で詳細検証分類
- [ ] `faq_llmo_optimization` 追加
- [ ] `rejection_analysis` 強化
- [ ] プロンプト更新
- [ ] 自動修正禁止ルール明示

## テスト計画

- [ ] 各検証カテゴリの動作確認
- [ ] 矛盾検出時の却下推奨確認
- [ ] FAQ生成品質確認
- [ ] step9への引き継ぎ確認

## フロー変更の必要性

**なし**

## 注意

**自動修正禁止** - 矛盾検出時は人間判断に委ねる
