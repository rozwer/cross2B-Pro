# ファイル整理・仕様書統合計画

> **作成日**: 2026-01-09
> **目的**: 散在するJSON/MDファイルを整理し、仕様書に統合

---

## 現状分析

### 問題点
- ルート直下に `AGENTS.md` が残存（CLAUDE.md と重複）
- `docs/migration/` に完了済み計画ファイルが残存
- `docs/analysis/` に工程別計画が二重管理
- `docs/reports/` に古いレポートが混在

### ファイル構成

| 場所 | ファイル数 | 状態 |
|------|----------|------|
| ルート直下 | 2 JSON + 1 MD | 維持 |
| docs/migration/ | 10 | 全てアーカイブ対象 |
| docs/analysis/ | 24 | 全てアーカイブ対象 |
| docs/reports/ | 12 | 選別してアーカイブ |
| 仕様書/ | 整理済み | 維持 |
| docs/guides/ | 4 | 維持 |
| docs/archive/ | 多数 | 維持 |

---

## フェーズ 1: docs/migration/ アーカイブ移動 `cc:DONE`

実装済み移行計画をアーカイブへ移動

- [x] `docs/archive/migration/` ディレクトリを作成
- [x] 以下を移動:
  - `docs/migration/md-to-json-migration.json`
  - `docs/migration/phase-plan.md`
  - `docs/migration/phase-rationale.md`
  - `docs/migration/review-report.md`
  - `docs/migration/sessions/` (6ファイル)
- [x] 空になった `docs/migration/` を削除

---

## フェーズ 2: docs/analysis/ アーカイブ移動 `cc:DONE`

工程計画は実装完了済み → アーカイブへ

- [x] `docs/archive/analysis/` ディレクトリを作成
- [x] 以下を移動:
  - `docs/analysis/prompt-comparison.md`
  - `docs/analysis/technical-impact.md`
  - `docs/analysis/integration-design.md`
  - `docs/analysis/step-plans/` (24ファイル)
- [x] 空になった `docs/analysis/` を削除

---

## フェーズ 3: docs/reports/ 整理 `cc:DONE`

### 3.1 アーカイブ移動（古いレポート）

- [x] `docs/archive/reports/` ディレクトリを作成（存在しない場合）
- [x] 以下を移動:
  - `2025-12-17_workflow_debug_status.json`
  - `e2e_test_summary_20251217.md`
  - `e2e_test_summary_20251217_2.md`
  - `security_review_20251217.md`
  - `gui_fullflow_test_todo.json`
  - `phase3_unused_infrastructure.json`
  - `phase_integration_gaps.json`
  - `api-test-report-2025-12-25.md`
  - `api-test-report-2025-12-25-retest.md`

### 3.2 維持するファイル（Codexレビュー差分）

以下は今後の参照用に維持:
- `codex_review_api.diff`
- `codex_review_worker.diff`
- `codex_review_ui.diff`

---

## フェーズ 4: 仕様書への統合確認 `cc:DONE`

### 4.1 仕様書の現状確認

既存の仕様書構成（維持）:

```
仕様書/
├── ROADMAP.md          # 実装計画 (Source of Truth)
├── workflow.md         # ワークフロー仕様 (Source of Truth)
├── PARALLEL_DEV_GUIDE.md
├── REVIEW_FIX_SPEC.md  # レビュー修正仕様
├── backend/
│   ├── api.md
│   ├── database.md
│   ├── llm.md
│   └── temporal.md
├── frontend/
│   └── ui.md
└── ref/                # 実装参考資料
    └── 各ステップ出力/
```

### 4.2 確認事項

- [x] アーカイブ移動したファイルの内容が仕様書に反映済みか確認
  - `REVIEW_FIX_SPEC.md` に `security_review_20251217.md` の内容が統合済み → OK
  - `ROADMAP.md` に `step-plans/*.md` の内容が反映済み → OK

---

## フェーズ 5: 最終確認 `cc:DONE`

- [x] ディレクトリ構成の最終確認
- [x] 不要な空ディレクトリの削除
- [x] git status で変更内容確認
- [ ] コミット

---

## 完了基準

- [x] 現状分析完了
- [x] `docs/migration/` → `docs/archive/migration/`
- [x] `docs/analysis/` → `docs/archive/analysis/`
- [x] `docs/reports/` 古いファイル → `docs/archive/reports/`
- [x] 仕様書への統合確認
- [ ] コミット完了

---

## 維持するファイル（削除・移動しない）

| ファイル | 理由 |
|---------|------|
| `AGENTS.md` | プロジェクト開発ガイド |
| `STRUCTURE.json` | テンプレート参考資料 |
| `langgraph.json` | 設定ファイル |
| `fe_be_inconsistencies.json` | FE/BE不整合分析レポート |
| `仕様書/` 配下全て | Source of Truth |
| `docs/guides/` | 運用ガイド |
| `docs/archive/` | 歴史記録 |
| `docs/reports/codex_review_*.diff` | レビュー参照用 |

---

## 過去の計画

- **blog.System Ver8.3 対応改修** (2026-01-08 完了)
- **.claude-making テンプレート改善** (2025-12-29 完了)
