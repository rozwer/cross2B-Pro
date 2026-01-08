# 工程7B: ブラッシュアップ

## 入力スキーマ

```json
{
  "draft": "Step7aOutput - step7aから",
  "target_word_count": "number - 確定値"
}
```

## 出力スキーマ（既存）

```python
class Step7bOutput(StepOutputBase):
    polished: str
    changes_summary: str
    change_count: int
    polish_metrics: PolishMetrics
    quality_warnings: list[str]
    model: str
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 調整項目 | 基本 | 語尾統一、一文長さ、接続詞 |
| 文字数維持 | 緩い | ±5%以内維持 |
| 4本柱維持 | なし | 変更時も維持確認 |

### 追加フィールド
```json
{
  "adjustment_details": {
    "sentence_length_fixes": "number",
    "connector_improvements": "number",
    "tone_unifications": "number",
    "technical_term_explanations_added": "number"
  },
  "word_count_comparison": {
    "before": "number",
    "after": "number",
    "change_percent": "number",
    "is_within_5_percent": "boolean"
  },
  "four_pillars_preservation": {
    "maintained": "boolean",
    "changes_affecting_pillars": "string[]"
  },
  "readability_improvements": {
    "avg_sentence_length_before": "number",
    "avg_sentence_length_after": "number",
    "target_range": "20-35文字"
  }
}
```

## 実装タスク

### スキーマ拡張（schemas/step7b.py） `cc:完了`

- [x] `AdjustmentDetails` モデル追加
  - sentence_length_fixes, connector_improvements, tone_unifications
  - technical_term_explanations_added, passive_to_active_conversions, redundancy_removals
- [x] `WordCountComparison` モデル追加
  - before, after, change_percent, is_within_5_percent
- [x] `FourPillarsPreservation` モデル追加
  - maintained, changes_affecting_pillars, pillar_status
- [x] `ReadabilityImprovements` モデル追加
  - avg_sentence_length_before/after, target_range_min/max
  - is_within_target, sentences_shortened/lengthened, complex_sentences_simplified
- [x] `Step7bOutputV2` モデル追加（既存 `Step7bOutput` と並列、後方互換）

### Activity修正（step7b.py） `cc:完了`

- [x] V2モード判定（`_is_v2_mode()`）
- [x] 4本柱キーワードパターン定義（`FOUR_PILLARS_PATTERNS`）
- [x] 平均文長計算（`_calculate_avg_sentence_length()`）
- [x] 4本柱維持確認（`_check_four_pillars_preservation()`）
- [x] 文字数比較計算（`_calculate_word_count_comparison()`）
- [x] 可読性改善計算（`_calculate_readability_improvements()`）
- [x] V2モード時の品質警告追加（±5%超過、4本柱削除）

### プロンプト更新 `cc:TODO`

- [ ] `v2_blog_system.json` 用の詳細プロンプト作成
  - ±5%維持の指示
  - 4本柱維持の指示

### テスト `cc:完了`

- [x] **スキーマテスト** (30テスト全パス)
  - `AdjustmentDetails` のバリデーション
  - `WordCountComparison` の5%判定
  - `FourPillarsPreservation` の維持判定
  - `ReadabilityImprovements` の目標範囲判定
  - `Step7bOutputV2` の後方互換性とシリアライズ

## テスト計画（残り）

- [ ] Activity単体テスト（LLMモック使用）
- [ ] 文字数変動5%以内確認（E2E）
- [ ] 4本柱維持確認（E2E）
- [ ] 可読性改善確認（E2E）
- [ ] step8への引き継ぎ確認（統合）

## フロー変更の必要性

**なし**
