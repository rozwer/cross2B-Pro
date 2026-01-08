# 工程3.5: 心情感情・人間味・体験エピソード

## 入力スキーマ

```json
{
  "keyword": "string - step0から",
  "personas": "UserPersona[] - step3aから",
  "three_phase_mapping": "object - step3aから"
}
```

## 出力スキーマ（既存）

```python
class Step3_5Output(StepOutputBase):
    step: str = "step3_5"
    emotional_analysis: EmotionalAnalysis
    human_touch_patterns: list[HumanTouchPattern]
    experience_episodes: list[ExperienceEpisode]
    emotional_hooks: list[str]
    raw_output: str
    parsed_data: dict | None
    metadata: HumanTouchMetadata
    quality: dict
    token_usage: dict
```

## blog.System との差分

| 観点 | 既存 | blog.System |
|------|------|-------------|
| 感情分析深度 | 基本 | 詳細（Phase別感情マップ） |
| エピソード数 | 任意 | 各フェーズ2-3個 |
| 共感ポイント | なし | 行動経済学6原則連動 |
| 配置指示 | 曖昧 | セクション別明示 |

### 追加フィールド
```json
{
  "phase_emotional_map": {
    "phase1": {
      "dominant_emotion": "string - 不安/焦り/危機感",
      "empathy_statements": "string[] - 共感文3個",
      "experience_episodes": "ExperienceEpisode[]"
    },
    "phase2": {
      "dominant_emotion": "string - 冷静/分析的",
      "empathy_statements": "string[]",
      "experience_episodes": "ExperienceEpisode[]"
    },
    "phase3": {
      "dominant_emotion": "string - 期待/決意",
      "empathy_statements": "string[]",
      "experience_episodes": "ExperienceEpisode[]"
    }
  },
  "behavioral_economics_hooks": {
    "loss_aversion_hook": "string",
    "social_proof_hook": "string",
    "authority_hook": "string",
    "scarcity_hook": "string"
  },
  "placement_instructions": [
    {
      "content_type": "string - empathy/episode/hook",
      "target_section": "string - H2タイトルまたは位置",
      "content": "string"
    }
  ]
}
```

## 実装タスク

### スキーマ拡張（apps/worker/activities/schemas/step3_5.py） ✅ 完了

- [x] `PhaseEmotionalData` モデル追加
- [x] `PhaseEmotionalMap` モデル追加
- [x] `BehavioralEconomicsHooks` モデル追加
- [x] `PlacementInstruction` モデル追加
- [x] `Step3_5Output` に新フィールド追加
  - `phase_emotional_map: PhaseEmotionalMap`
  - `behavioral_economics_hooks: BehavioralEconomicsHooks`
  - `placement_instructions: list[PlacementInstruction]`

### プロンプト更新（apps/api/prompts/packs/step3_5.json） ✅ 完了

- [x] step3_5 プロンプトに Phase別感情マップ生成指示を追加
- [x] 行動経済学4原則フック生成指示を追加
- [x] セクション別配置指示（placement_instructions）の出力形式を追加
- [x] 4本柱（神経科学、行動経済学、LLMO、KGI）の実装ガイドを追加
- [ ] unified_knowledge.json 対応（参照方法の追加）- 後続タスク

### Activity修正（apps/worker/activities/step3_5.py） ✅ 完了

- [x] 入力に `three_phase_mapping`（step3a から）を追加
- [x] `execute()` のパース処理を拡張
  - `_extract_phase_emotional_map()` メソッド追加
  - `_extract_behavioral_economics_hooks()` メソッド追加
  - `_extract_placement_instructions()` メソッド追加
- [x] output_data に新フィールドを追加
- [ ] 品質検証に新フィールドのチェックを追加 - 後続タスク

## テスト計画

### 単体テスト（tests/unit/activities/test_step3_5.py） ✅ 完了

- [x] `PhaseEmotionalData` のバリデーションテスト（4件）
- [x] `PhaseEmotionalMap` のバリデーションテスト（3件）
- [x] `BehavioralEconomicsHooks` のバリデーションテスト（3件）
- [x] `PlacementInstruction` のバリデーションテスト（4件）
- [x] `Step3_5OutputExtensions` テスト（3件）
- [x] 後方互換性テスト

**テスト結果**: 31件すべてパス ✅

### 統合テスト - 後続タスク

- [ ] Phase別エピソード生成確認（各フェーズ2-3個）
- [ ] 行動経済学フック生成確認（4原則すべて）
- [ ] placement_instructions の形式検証
- [ ] step4/step7a への引き継ぎデータ確認

## フロー変更の必要性

**なし**

## 実装順序

1. ~~スキーマ拡張（型定義）~~ ✅
2. ~~単体テスト追加（TDD）~~ ✅
3. ~~Activity修正（パース処理）~~ ✅
4. ~~プロンプト更新~~ ✅
5. 統合テスト - 後続タスク

## 実装完了日

**2026-01-08**
