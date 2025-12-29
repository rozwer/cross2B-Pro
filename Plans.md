# .claude-making テンプレート改善計画

> **作成日**: 2025-12-29
> **目的**: .claude-making を完全なワンストップソリューションに改善する

---

## 概要

`.claude-making` を使えば、新規プロジェクトで `/setup-project` 一発で `.claude/` が完成する状態を目指す。

**資産分類の詳細**: `.claude-making/ASSET_CLASSIFICATION.md` 参照

| カテゴリ | template | blueprint | オプション | 除外 |
|----------|----------|-----------|-----------|------|
| skills | 13 | 10 | 0 | 1 |
| agents | 22 | 3 | 1 | 0 |
| rules | 7 | 2 | 1 | 0 |
| commands | 10 | 7 | 1 | 4 |
| memory | 3 | 0 | 0 | 0 |
| **合計** | **55** | **22** | **3** | **5** |

---

## フェーズ 1: template/ の拡充 `cc:完了`

✅ 完了（2025-12-29）

- [x] agents: 6 → 22（+16）
- [x] skills: 8 → 13（+5）
- [x] rules: 2 → 7（+5）
- [x] commands: 4 → 10（+6）
- [x] memory/: 新規作成（3ファイル）

---

## フェーズ 2: blueprint/ の拡充 `cc:TODO`

環境固有スキルの抽象化（22個）

- [ ] ワークフローフレームワーク系（5個）
- [ ] オーケストレーター系（3個）
- [ ] LLM 統合系（3個）
- [ ] テスト系（3個）
- [ ] ワークフローコマンド系（4個）
- [ ] ルール系（2個）

---

## フェーズ 3: オプション機能 `cc:TODO`

- [ ] Codex 連携（agents/rules/commands）
- [ ] options.json で `use_codex: true/false` 選択

---

## フェーズ 4: options.json スキーマ拡張 `cc:TODO`

- [ ] 技術スタック選択肢を追加
- [ ] Phase 1 分析で検出ロジックを更新
- [ ] Phase 4 展開で条件分岐ロジックを追加

---

## フェーズ 5: plan/ ドキュメント更新 `cc:TODO`

- [ ] `01-project-analysis.md` - 技術スタック検出
- [ ] `03-template-copy.md` - 新 template/ 資産
- [ ] `04-blueprint-customize.md` - 抽象化展開
- [ ] `05-validation.md` - 新チェック項目

---

## フェーズ 6: README.md 更新 `cc:TODO`

- [ ] template/ 資産一覧
- [ ] blueprint/ 説明
- [ ] options.json スキーマ
- [ ] 環境固有スキル作成ガイド

---

## 完了基準

- [ ] template/ が55個の汎用資産を持つ
- [ ] blueprint/ が22個の抽象化テンプレートを持つ
- [ ] オプション機能が選択可能
- [ ] `/setup-project` 一発で完了

---

## 過去の計画

- **ドキュメント整理・再設計** (2025-12-29 完了)
