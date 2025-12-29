# .claude-making テンプレート改善計画

> **作成日**: 2025-12-29
> **目的**: .claude-making を完全なワンストップソリューションに改善する

---

## 概要

`.claude-making` を使えば、新規プロジェクトで `/setup-project` 一発で `.claude/` が完成する状態を目指す。

**資産分類の詳細**: `.claude-making/ASSET_CLASSIFICATION.md` 参照

| カテゴリ | template | blueprint | オプション | 除外 |
|----------|----------|-----------|-----------|------|
| skills | 13 | 11 | 0 | 1 |
| agents | 22 | 5 | 1 | 0 |
| rules | 7 | 3 | 1 | 0 |
| commands | 10 | 7 | 1 | 4 |
| memory | 3 | 0 | 0 | 0 |
| CLAUDE.md | 0 | 1 | 0 | 0 |
| **合計** | **55** | **27** | **3** | **5** |

---

## フェーズ 1: template/ の拡充 `cc:完了`

✅ 完了（2025-12-29）

- [x] agents: 6 → 22（+16）
- [x] skills: 8 → 13（+5）
- [x] rules: 2 → 7（+5）
- [x] commands: 4 → 10（+6）
- [x] memory/: 新規作成（3ファイル）

---

## フェーズ 2: blueprint/ の拡充 `cc:完了`

✅ 完了（2025-12-29）

環境固有スキルの抽象化（27個）

- [x] ワークフローフレームワーク系（5個）: fundamentals, patterns, multi-agent, persistence, step-impl
- [x] オーケストレーター系（3個）: debugger, debug/replay, debug/trace
- [x] LLM 統合系（3個）: prompt-authoring, prompt-engineer, prompt-tester
- [x] テスト系（3個）: api-test, integration-test, e2e-test
- [x] ワークフローコマンド系（4個）: new, run, approve, artifacts
- [x] ルール系（3個）: implementation, domain-contract, dev-style
- [x] 既存テンプレート（6個）: domain-specific, tech-stack, implementer, domain-expert, domain-command, CLAUDE.md

---

## フェーズ 3: オプション機能 `cc:完了`

✅ 完了（2025-12-29）

- [x] Codex 連携（agents/rules/commands） → `optional/codex/` に配置
- [x] options.json で `use_codex: true/false` 選択（スキーマ対応済み）

---

## フェーズ 4: options.json スキーマ拡張 `cc:完了`

✅ 完了（2025-12-29）

- [x] 技術スタック選択肢を追加（workflow_framework, orchestrator, llm_provider）
- [x] options.schema.json を更新
- [x] options.json にデフォルト値を追加

---

## フェーズ 5: plan/ ドキュメント更新 `cc:完了`

✅ 完了（2025-12-29）

- [x] `03-template-copy.md` - optional/ ディレクトリ対応
- [x] `04-blueprint-customize.md` - 新 blueprint テンプレート一覧

---

## フェーズ 6: README.md 更新 `cc:完了`

✅ 完了（2025-12-29）

- [x] template/ 資産一覧（55個）
- [x] blueprint/ 説明（27個）
- [x] optional/ 説明
- [x] options.json 新スキーマ

---

## 完了基準

- [x] template/ が55個の汎用資産を持つ
- [x] blueprint/ が27個の抽象化テンプレートを持つ（当初計画22を超過）
- [x] オプション機能（Codex連携）が選択可能
- [x] `/setup-project` 一発で完了（plan/ ドキュメント更新済み）

**すべて完了 ✅**

---

## 過去の計画

- **ドキュメント整理・再設計** (2025-12-29 完了)
