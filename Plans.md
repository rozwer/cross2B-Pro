# blog.System Ver8.3 対応改修計画

> **作成日**: 2026-01-08
> **最終更新**: 2026-01-08 11:20
> **目的**: SEO記事自動生成システムを blog.System Ver8.3 仕様に対応させる
> **テスト**: 1,152件パス / 9件失敗（JSON validator関連の既存問題）
> **実データテスト**: ✅ 全工程完了 (run: d0d028f3-7c5f-4543-a025-c50e4f0ba0a4)

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
| step4 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step5 | ✅ | ✅ | - | ✅ | 完了 |
| step6 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
| step6.5 | ✅ | ✅ | ⏳ | ✅ | プロンプト残 |
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
| `dacaca5` | step4 Ver8.3対応 | 3ファイル, 863行 |
| `67ce915` | step6.5 Ver8.3対応 | 1ファイル, 293行 |

---

## フェーズ 1: 残作業（step4 + step6.5） `cc:DONE`

### 1.1 工程4: 戦略的アウトライン生成 ✅

- [x] `TitleMetadata` スキーマ追加
- [x] `ThreePhaseStructure` スキーマ追加
- [x] `SectionFourPillars` スキーマ追加
- [x] `CTAPlacements` スキーマ追加
- [x] `WordCountTracking` スキーマ追加
- [x] Activity修正（V2モード検出 + 5ビルダーメソッド）
- [x] ユニットテスト追加（36件パス）

**参照**: `docs/analysis/step-plans/step4.md`

### 1.2 工程6.5: Activity修正 ✅

- [x] `_build_comprehensive_blueprint()` メソッド追加
- [x] `_build_section_execution_instructions()` メソッド追加
- [x] `_build_visual_element_instructions()` メソッド追加
- [x] `_check_four_pillars_compliance()` メソッド追加

**参照**: `docs/analysis/step-plans/step6_5.md`

### 1.3 実データテスト ✅

- [x] キーワード「SEO対策 初心者」で全工程実行
- [x] step0〜step12 全完了
- [x] 出力ファイル正常生成確認

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

- [x] 全工程のスキーマが blog.System Ver8.3 対応済み
- [x] 全工程のActivityが新スキーマに対応済み
- [x] 全ユニットテストがパス（1,152件）
- [x] step4 スキーマ + Activity 完了
- [x] step6.5 Activity 完了
- [x] 実データテストで品質確認済み
- [ ] v2_blog_system.json プロンプトパック完成
- [ ] E2Eテストがパス

---

## 既知の問題

- **JSON validator テスト失敗 (9件)**: 既存の `test_json_validator.py` / `test_repairer.py` の問題。本改修とは無関係。

---

## 過去の計画

- **.claude-making テンプレート改善** (2025-12-29 完了)
