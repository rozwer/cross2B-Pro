# 工程4: 戦略的アウトライン生成

## 入力スキーマ

```json
{
  "keyword": "string - step0から",
  "query_analysis": "Step3aOutput - step3aから",
  "cooccurrence_keywords": "KeywordItem[] - step3bから",
  "competitor_analysis": "Step3cOutput - step3cから",
  "human_touch_elements": "Step3_5Output - step3.5から",
  "target_word_count": "number - step0またはstep3cから確定値",
  "cta_specification": "object - step0から"
}
```

## 出力スキーマ（既存）

```python
class Step4Output(BaseModel):
    step: str = "step4"
    keyword: str
    article_title: str
    meta_description: str
    outline: str
    sections: list[OutlineSection]  # level, title, description, target_word_count
    key_differentiators: list[str]
    metrics: OutlineMetrics
    quality: OutlineQuality
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 4本柱実装 | なし | 全H2に必須 |
| 3フェーズ構成 | なし | Phase1/2/3文字数配分 |
| CTA配置 | 簡易 | 3段階（Early/Mid/Final） |
| 文字数管理 | 目標のみ | セクション別target + 合計検証 |
| タイトルルール | なし | 32文字、括弧禁止、数字含む |

### 追加フィールド（必須）
```json
{
  "title_metadata": {
    "char_count": "number - 32文字前後",
    "contains_number": "boolean",
    "contains_keyword": "boolean",
    "no_brackets": "boolean"
  },
  "three_phase_structure": {
    "phase1": {
      "word_count_ratio": 0.10-0.15,
      "sections": "OutlineSection[]"
    },
    "phase2": {
      "word_count_ratio": 0.65-0.75,
      "sections": "OutlineSection[]"
    },
    "phase3": {
      "word_count_ratio": 0.10-0.15,
      "sections": "OutlineSection[]"
    }
  },
  "four_pillars_per_section": [
    {
      "section_title": "string",
      "neuroscience": { "cognitive_load": "string", "phase": "1|2|3" },
      "behavioral_economics": { "principles_applied": "string[]" },
      "llmo": { "token_target": 400-600, "question_heading": "boolean" },
      "kgi": { "cta_placement": "none|early|mid|final" }
    }
  ],
  "cta_placements": {
    "early": { "position": 650, "section": "string" },
    "mid": { "position": 2800, "section": "string" },
    "final": { "position": "target - 500", "section": "string" }
  },
  "word_count_tracking": {
    "target": "number",
    "sections_total": "number",
    "variance": "number",
    "is_within_tolerance": "boolean"
  }
}
```

## 実装タスク

- [ ] `title_metadata` でタイトルルール検証
- [ ] `three_phase_structure` で3フェーズ構成
- [ ] `four_pillars_per_section` で各H2に4本柱実装
- [ ] `cta_placements` で3段階CTA配置
- [ ] `word_count_tracking` で文字数管理
- [ ] プロンプト更新（詳細版）
- [ ] バリデーション強化

## テスト計画

- [ ] タイトルルール検証
- [ ] 3フェーズ文字数配分確認
- [ ] 4本柱実装確認
- [ ] CTA配置位置確認
- [ ] step5への引き継ぎ確認

## フロー変更の必要性

**なし**

## 重要

**4本柱必須実装** - 全H2セクションに4本柱を実装することが絶対要件
