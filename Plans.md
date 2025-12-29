# ドキュメント整理・再設計 計画

> **作成日**: 2025-12-29
> **完了日**: 2025-12-29
> **目的**: docs/ と 仕様書/ の構成を再設計し、実態と乖離したドキュメントを整理する

---

## 完了サマリー

| フェーズ | 内容 | ステータス |
|---------|------|----------|
| 1 | 削除・アーカイブ | ✅ 完了 |
| 2 | ROADMAP.md 再構成 | ✅ 完了 |
| 3 | 仕様書の整合性確認 | ✅ 完了 |
| 4 | docs 整理・README 作成 | ✅ 完了 |
| 5 | CLAUDE.md との整合 | ✅ 完了 |

---

## 実施内容

### フェーズ1: 削除・アーカイブ
- `仕様書/_archive/` を削除（旧仕様で現行と矛盾）
- `docs/archive/` を作成し、古いファイルを移動
  - step-improvements/ → archive/step-improvements/
  - summaries/ → archive/phase-summaries/
  - prompts/ → archive/prompts/
  - plans/ → archive/plans/
  - screenshots/ → archive/screenshots/
- API テストレポートを reports/ へ移動

### フェーズ2: ROADMAP.md 再構成
- Step 1-8 形式から Phase 1-5 形式に書き換え
- 各 Phase の完了条件とテスト数を明記
- 今後の計画（Session A-F）を追記

### フェーズ3: 仕様書の整合性確認
- workflow.md: 最新工程構成を反映済み ✓
- REVIEW_FIX_SPEC.md: 修正仕様として保持 ✓
- backend/, frontend/: 実装と整合 ✓

### フェーズ4: docs 整理・README 作成
- docs/README.md を作成（目次・役割説明）
- claude-configuration-overview.md を .claude/docs/ へ移動

### フェーズ5: CLAUDE.md との整合
- Source of Truth セクションは正しく仕様書を参照 ✓
- 削除・移動したファイルへの参照なし ✓

---

## 新しいドキュメント構成

```
仕様書/                    ← 永続的な仕様（Source of Truth）
├── ROADMAP.md            ← 実装計画（Phase ベースに再構成）
├── workflow.md           ← 工程仕様（12工程）
├── REVIEW_FIX_SPEC.md    ← 修正仕様（進捗更新）
├── backend/              ← BE 技術仕様
│   ├── api.md
│   ├── database.md
│   ├── llm.md
│   └── temporal.md
├── frontend/             ← FE 技術仕様
│   └── ui.md
└── ref/                  ← 参照用サンプル出力

docs/                      ← 作業記録・ガイド・履歴
├── README.md             ← docs の目次（新規作成）
├── guides/               ← 運用ガイド
│   ├── RUN.md
│   ├── TEST.md
│   └── E2E_TEST_COMMANDS.md
├── migration/            ← 工程構成変更計画
│   ├── phase-plan.md
│   ├── phase-rationale.md
│   └── review-report.md
├── reports/              ← テスト・レビュー報告
│   └── *.md
└── archive/              ← 履歴保管（参照のみ）
    ├── phase-summaries/  ← Phase 1-5 サマリー
    ├── step-improvements/ ← 旧工程改善案
    └── prompts/          ← 旧プロンプト設定
```

---

## フェーズ 1: 削除・アーカイブ `cc:TODO`

不要ファイルの削除と古いファイルのアーカイブ化

- [ ] `仕様書/_archive/` を削除（旧仕様で現行と矛盾）
- [ ] `docs/archive/` ディレクトリを作成
- [ ] `docs/step-improvements/` を `docs/archive/step-improvements/` へ移動
- [ ] `docs/summaries/` を `docs/archive/phase-summaries/` へ移動
- [ ] `docs/prompts/` を `docs/archive/prompts/` へ移動
- [ ] `docs/plans/` を `docs/archive/plans/` へ移動
- [ ] `docs/api-test-report-2025-12-25.md` を `docs/reports/` へ移動
- [ ] `docs/api-test-report-2025-12-25-retest.md` を `docs/reports/` へ移動
- [ ] `docs/screenshots/` を `docs/archive/screenshots/` へ移動

---

## フェーズ 2: ROADMAP.md 再構成 `cc:TODO`

Phase ベースへの書き換え

- [ ] 現在の ROADMAP.md の内容を確認
- [ ] Phase 1-5 の完了状況を反映した構成に書き換え
- [ ] 各 Phase の成果物・テスト数を明記
- [ ] 今後の計画（Session A-F）を追記
- [ ] 古い Step 形式の記述を削除

---

## フェーズ 3: 仕様書の整合性確認 `cc:TODO`

実態との乖離を修正

- [ ] `仕様書/workflow.md` と実装コードの整合性確認
- [ ] `仕様書/REVIEW_FIX_SPEC.md` の修正状況を確認・更新
- [ ] `仕様書/backend/*.md` の内容が実装と一致するか確認
- [ ] `仕様書/frontend/ui.md` の内容が実装と一致するか確認
- [ ] `仕様書/PARALLEL_DEV_GUIDE.md` の内容確認・更新

---

## フェーズ 4: docs の整理・目次作成 `cc:TODO`

残った docs の整理と目次作成

- [ ] `docs/README.md` を作成（目次・役割説明）
- [ ] `docs/guides/` の内容を確認・更新
- [ ] `docs/migration/` の進捗状況を更新
- [ ] `docs/claude-configuration-overview.md` の配置を検討
- [ ] 不要な空ディレクトリを削除

---

## フェーズ 5: CLAUDE.md との整合 `cc:TODO`

CLAUDE.md の参照先を更新

- [ ] CLAUDE.md の「Source of Truth」セクションを確認
- [ ] 削除・移動したファイルへの参照がないか確認
- [ ] 必要に応じて CLAUDE.md を更新

---

## 次のアクション

ドキュメント整理は完了しました。

今後の開発タスクは `docs/migration/phase-plan.md` を参照してください。
