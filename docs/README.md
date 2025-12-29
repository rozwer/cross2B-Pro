# docs/ ディレクトリ

作業記録、ガイド、レポート、履歴を格納するディレクトリ。

> **仕様書は `仕様書/` を参照**（Source of Truth）

---

## ディレクトリ構成

```
docs/
├── README.md           ← このファイル
├── guides/             ← 運用ガイド
│   ├── RUN.md          ← 実行方法
│   ├── TEST.md         ← テスト実行方法
│   ├── E2E_TEST_COMMANDS.md
│   └── FE_BE_INTEGRATION_TEST.md
├── migration/          ← 工程構成変更計画
│   ├── phase-plan.md   ← 新工程の実装計画
│   ├── phase-rationale.md
│   └── review-report.md
├── reports/            ← テスト・レビュー報告
│   └── *.md
└── archive/            ← 履歴保管（参照のみ）
    ├── phase-summaries/  ← Phase 1-5 実装サマリー
    ├── step-improvements/  ← 旧工程改善案
    ├── prompts/          ← 旧プロンプト設定
    ├── plans/            ← 旧計画
    └── screenshots/      ← スクリーンショット
```

---

## 役割分担

| ディレクトリ | 役割 | 更新頻度 |
|-------------|------|---------|
| **仕様書/** | 永続的な仕様（ROADMAP, workflow, API等） | 設計変更時 |
| **docs/** | 作業記録・ガイド・履歴 | 作業時 |

---

## よく参照するファイル

| ファイル | 用途 |
|----------|------|
| `guides/RUN.md` | システム起動方法 |
| `guides/TEST.md` | テスト実行方法 |
| `migration/phase-plan.md` | 今後の工程追加計画 |

---

## archive について

`archive/` には過去の作業記録を保管しています。

- **phase-summaries/**: Phase 1-5 の実装完了サマリー
- **step-improvements/**: 旧工程の改善案（Phase 2-4 時点）
- **prompts/**: 旧プロンプト設定ドキュメント

これらは参照のみで、新しい実装には使用しないでください。
