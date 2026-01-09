# 工程6: アウトライン強化版

## 入力スキーマ

```json
{
  "outline": "Step4Output - step4から",
  "primary_sources": "PrimarySource[] - step5から",
  "section_source_mapping": "object[] - step5から",
  "data_anchors": "object[] - step5から"
}
```

## 出力スキーマ（既存）

```python
class Step6Output(StepOutputBase):
    step: str = "step6"
    enhanced_outline: str
    sections: list[EnhancedSection]
    enhancement_summary: EnhancementSummary
    source_citations: dict[str, list[str]]
    original_outline_hash: str
    metrics: EnhancedOutlineMetrics
    quality: EnhancedOutlineQuality
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 一次情報配置 | 基本 | データアンカー明示 |
| 4本柱強化 | なし | 各セクション4本柱再確認 |
| 出典形式 | 任意 | 統一フォーマット |

### 追加フィールド
```json
{
  "data_anchor_placements": [
    {
      "section_title": "string",
      "anchor_type": "string - intro_impact/section_evidence/summary",
      "data_point": "string",
      "source_citation": "string"
    }
  ],
  "four_pillars_verification": {
    "sections_verified": "number",
    "issues_found": "string[]",
    "auto_corrections": "string[]"
  },
  "citation_format": {
    "style": "string - inline/footnote",
    "examples": "string[]"
  }
}
```

## 実装タスク

### 1. スキーマ拡張（schemas/step6.py）

- [x] `DataAnchorPlacement` モデル追加
- [x] `FourPillarsVerification` モデル追加
- [x] `CitationFormat` モデル追加
- [x] `Step6Output` に新フィールド追加

### 2. Activity実装（step6.py）

- [x] `_extract_data_anchor_placements()` メソッド追加
  - セクション別にデータポイント/出典を抽出
  - アンカータイプ（intro_impact/section_evidence/summary）を自動判定
- [x] `_verify_four_pillars()` メソッド追加
  - 神経科学/行動経済学/LLMO/KGI の4本柱をスコアリング
  - 問題点を自動検出
- [x] `_build_citation_format()` メソッド追加
- [x] `execute()` に集計ロジック統合

### 3. プロンプト更新（将来）

- [ ] 4本柱をより意識した生成指示

## テスト計画

### 単体テスト（tests/unit/worker/test_step6_analysis.py）

- [x] `DataAnchorPlacement` / `FourPillarsVerification` / `CitationFormat` のバリデーション
- [x] `_extract_data_anchor_placements()` のパターン抽出
- [x] `_verify_four_pillars()` のスコアリング
- [x] `_build_citation_format()` の出力形式

### 統合テスト

- [ ] step5 → step6 → step6.5 のデータフロー確認
- [ ] 4本柱スコアが step6.5 で参照可能か確認

## フロー変更の必要性

**なし**
