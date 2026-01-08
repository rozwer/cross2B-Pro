# blog.System Ver8.3 対応改修計画

> **作成日**: 2026-01-08
> **最終更新**: 2026-01-08 11:00
> **目的**: SEO記事自動生成システムを blog.System Ver8.3 仕様に対応させる
> **テスト**: 1,116件パス / 9件失敗（JSON validator関連の既存問題）

---

## 実装状況サマリー

| 工程 | スキーマ | Activity | プロンプト | テスト | 状態 |
|------|----------|----------|------------|--------|------|
| step0 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step1 | ✅ | ✅ | - | ✅ | 完了 |
| step1.5 | ✅ | ✅ | - | ✅ | 完了 |
| step2 | ✅ | ✅ | - | ✅ | 完了 |
| step3a | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step3b | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step3c | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step3.5 | ✅ | ✅ | ✅ | ✅ | 完了 |
| step4 | ⏳ | ⏳ | ⏳ | ⏳ | 未着手 |
| step5 | ✅ | ✅ | - | ✅ | 完了 |
| step6 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step6.5 | ✅ | ⏳ | ⏳ | ✅ | Activity残 |
| step7a | ✅ | ✅ | ✅ | ✅ | 完了 |
| step7b | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step8 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step9 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step10 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step11 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step12 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |

**凡例**: ✅ 完了 | ⏳ 未着手 | - 対象外

### 今回のコミット (2026-01-08)

| コミット | 内容 | 変更量 |
|----------|------|--------|
| `8b3f16b` | Schema変更 (step0-12) | 18ファイル, 2,464行 |
| `f7eaa2b` | Activity変更 (step0-12) | 19ファイル, 4,060行 |
| `40ecf61` | テスト追加 | 18ファイル, 8,400行 |
| `efac6fe` | プロンプトパック | 5ファイル, 381行 |
| `e820dc6` | API/UI修正 | 3ファイル |
| `61405a1` | 分析ドキュメント | 24ファイル, 4,150行 |
| `7f2d340` | blog.Systemプロンプト参照 | 66ファイル, 34,952行 |
| `6b7a164` | Plans.md更新 | 1ファイル |

---

## フェーズ 1: 残作業（step4 + step6.5） `cc:TODO`

### 1.1 工程4: 戦略的アウトライン生成 `[feature:tdd]`

**唯一のスキーマ未実装工程**

- [ ] `title_metadata` スキーマ追加
- [ ] `three_phase_structure` スキーマ追加
- [ ] `four_pillars_per_section` スキーマ追加
- [ ] `cta_placements` スキーマ追加
- [ ] `word_count_tracking` スキーマ追加
- [ ] Activity修正
- [ ] ユニットテスト追加

**参照**: `docs/analysis/step-plans/step4.md`

### 1.2 工程6.5: Activity修正

- [ ] `_prepare_integration_input()` に新フィールド追加
- [ ] `_build_section_execution_instructions()` メソッド追加
- [ ] 出力構築時に新フィールドを設定

**参照**: `docs/analysis/step-plans/step6_5.md`

---

## フェーズ 2: プロンプト統合 `cc:TODO`

### 2.1 v2_blog_system.json の完成

- [ ] step0 プロンプト追加
- [ ] step3a プロンプト追加
- [ ] step3b プロンプト追加
- [ ] step3c プロンプト追加
- [ ] step6 プロンプト追加
- [ ] step7b プロンプト追加
- [ ] step8 プロンプト追加
- [ ] step9 プロンプト追加
- [ ] step10 プロンプト追加
- [ ] step11 プロンプト追加
- [ ] step12 プロンプト追加

### 2.2 unified_knowledge.json 対応

- [ ] `loader.py` に `load_unified_knowledge()` メソッド追加

---

## フェーズ 3: 統合テスト `cc:TODO`

- [ ] 全工程通しテスト（v2_blog_system パック使用）
- [ ] 実データテスト（実際のキーワードで全工程実行）

---

## 完了基準

- [x] 全工程のスキーマが blog.System Ver8.3 対応済み（step4以外）
- [x] 全工程のActivityが新スキーマに対応済み（step4, step6.5以外）
- [x] 全ユニットテストがパス（1,116件）
- [ ] step4 スキーマ + Activity 完了
- [ ] step6.5 Activity 完了
- [ ] v2_blog_system.json プロンプトパック完成
- [ ] E2Eテストがパス
- [ ] 実データテストで品質確認済み

---

## 既知の問題

- **JSON validator テスト失敗 (9件)**: 既存の `test_json_validator.py` / `test_repairer.py` の問題。本改修とは無関係。

---

## 過去の計画

- **.claude-making テンプレート改善** (2025-12-29 完了)
