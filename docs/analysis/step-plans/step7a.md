# 工程7A: 本文生成（初稿）

## 入力スキーマ

```json
{
  "integration_package": "Step6_5Output - step6.5から",
  "human_touch_elements": "Step3_5Output - step3.5から",
  "target_word_count": "number - 確定値",
  "cta_specification": "object - step0から"
}
```

## 出力スキーマ（既存）

```python
class Step7aOutput(StepOutputBase):
    step: str = "step7a"
    draft: str
    sections: list[DraftSection]
    section_count: int
    cta_positions: list[str]
    quality_metrics: DraftQualityMetrics
    quality: DraftQuality
    stats: GenerationStats
    continued: bool
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 執筆ルール | 基本 | PREP法、1セクション400-600トークン |
| 4本柱実装 | なし | 各セクション実装必須 |
| 分割出力 | 任意 | 巨大時は3-5分割必須 |
| 文字数管理 | 概算 | セクション別トラッキング |

### 追加フィールド（必須）
```json
{
  "section_word_counts": [
    {
      "section_title": "string",
      "target": "number",
      "actual": "number",
      "variance": "number",
      "is_within_tolerance": "boolean"
    }
  ],
  "four_pillars_implementation": [
    {
      "section_title": "string",
      "neuroscience": { "applied": "boolean", "details": "string" },
      "behavioral_economics": { "principles_used": "string[]" },
      "llmo": { "token_count": "number", "is_independent": "boolean" },
      "kgi": { "cta_present": "boolean", "cta_type": "string | null" }
    }
  ],
  "cta_implementation": {
    "early": { "position": "number", "implemented": "boolean" },
    "mid": { "position": "number", "implemented": "boolean" },
    "final": { "position": "number", "implemented": "boolean" }
  },
  "word_count_tracking": {
    "target": "number",
    "current": "number",
    "remaining": "number",
    "progress_percent": "number"
  },
  "split_generation": {
    "total_parts": "number",
    "current_part": "number",
    "completed_sections": "string[]"
  }
}
```

## 実装タスク

### スキーマ拡張（apps/worker/activities/schemas/step7a.py） ✅ 完了

- [x] `SectionWordCount` モデル追加
- [x] `NeuroscienceImplementation` モデル追加
- [x] `BehavioralEconomicsImplementation` モデル追加
- [x] `LLMOImplementation` モデル追加
- [x] `KGIImplementation` モデル追加
- [x] `FourPillarsImplementation` モデル追加
- [x] `CTAPosition` モデル追加
- [x] `CTAImplementation` モデル追加
- [x] `WordCountTracking` モデル追加
- [x] `SplitGeneration` モデル追加
- [x] `Step7aOutput` に新フィールド追加
  - `section_word_counts: list[SectionWordCount]`
  - `four_pillars_implementation: list[FourPillarsImplementation]`
  - `cta_implementation: CTAImplementation`
  - `word_count_tracking: WordCountTracking`
  - `split_generation: SplitGeneration`

### Activity修正（apps/worker/activities/step7a.py） ✅ 完了

- [x] 新スキーマのインポート追加
- [x] `_extract_section_word_counts()` メソッド追加
- [x] `_extract_four_pillars_implementation()` メソッド追加
- [x] `_extract_cta_implementation()` メソッド追加
- [x] `_extract_word_count_tracking()` メソッド追加
- [x] `_extract_split_generation()` メソッド追加
- [x] `execute()` 内で新フィールドを抽出・追加

### プロンプト更新（apps/api/prompts/packs/step7a.json） ✅ 完了

- [x] PREP法ルール適用指示
- [x] 4本柱実装ガイド（神経科学、行動経済学、LLMO、KGI）
- [x] CTA配置ルール（early/mid/final）
- [x] セクション別文字数管理指示
- [x] 新しい出力スキーマ定義
- [x] 品質チェックポイント

### 単体テスト（tests/unit/activities/test_step7a_schemas.py） ✅ 完了

- [x] `SectionWordCount` テスト（4件）
- [x] `NeuroscienceImplementation` テスト（2件）
- [x] `BehavioralEconomicsImplementation` テスト（2件）
- [x] `LLMOImplementation` テスト（3件）
- [x] `KGIImplementation` テスト（2件）
- [x] `FourPillarsImplementation` テスト（3件）
- [x] `CTAPosition` テスト（3件）
- [x] `CTAImplementation` テスト（3件）
- [x] `WordCountTracking` テスト（4件）
- [x] `SplitGeneration` テスト（3件）
- [x] `Step7aOutputExtensions` テスト（4件）
- [x] `DraftSection` 回帰テスト（3件）

**テスト結果**: 36件すべてパス ✅

### 統合テスト - 後続タスク

- [ ] 文字数トラッキング精度確認
- [ ] 4本柱実装確認
- [ ] CTA配置確認
- [ ] 分割生成の動作確認
- [ ] step7bへの引き継ぎ確認

## フロー変更の必要性

**なし**

## 注意

**最長工程** - トークン制限に注意、分割生成を活用

## 実装完了日

**2026-01-08**
