# 工程9: 最終リライト

## 入力スキーマ

```json
{
  "polished_draft": "Step7bOutput - step7bから",
  "factcheck_result": "Step8Output - step8から",
  "faq_items": "FAQItem[] - step8から"
}
```

## 出力スキーマ（既存）

```python
class Step9Output(StepOutputBase):
    final_content: str
    meta_description: str  # max_length=160
    changes_summary: list[RewriteChange]
    rewrite_metrics: RewriteMetrics
    internal_link_suggestions: list[str]
    quality_warnings: list[str]
    model: str
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| ファクトチェック反映 | あり | 詳細記録 |
| FAQ統合 | あり | 配置位置最適化 |
| SEO最終調整 | 基本 | 見出しSEO、内部リンク、ALTテキスト |
| 4本柱最終確認 | なし | 最終検証 |

### 追加フィールド
```json
{
  "factcheck_corrections": [
    {
      "claim_id": "string",
      "original": "string",
      "corrected": "string",
      "reason": "string"
    }
  ],
  "faq_placement": {
    "position": "string - before_conclusion/after_conclusion/separate_section",
    "items_count": "number"
  },
  "seo_final_adjustments": {
    "headings_optimized": "string[]",
    "internal_links_added": "number",
    "alt_texts_generated": "string[]",
    "meta_description_optimized": "boolean"
  },
  "four_pillars_final_verification": {
    "all_compliant": "boolean",
    "issues_remaining": "string[]",
    "manual_review_needed": "boolean"
  },
  "word_count_final": {
    "target": "number",
    "actual": "number",
    "variance": "number",
    "status": "string - achieved/補筆推奨/補筆必須/要約必須"
  }
}
```

## 実装タスク

- [ ] `factcheck_corrections` で修正記録
- [ ] `faq_placement` 最適化
- [ ] `seo_final_adjustments` 追加
- [ ] `four_pillars_final_verification` 追加
- [ ] `word_count_final` で最終文字数確認
- [ ] プロンプト更新

## テスト計画

- [ ] ファクトチェック修正の反映確認
- [ ] FAQ配置確認
- [ ] SEO調整確認
- [ ] 4本柱最終確認
- [ ] step10への引き継ぎ確認

## フロー変更の必要性

**なし**
