# SEO記事自動生成システム / Claude Code 指示書

> **このファイルは最高優先度**。他のドキュメントと矛盾がある場合、このファイルを正とする。

## Source of Truth（正となるドキュメント）

| 用途 | ファイル |
|------|----------|
| **実装計画（最優先）** | `仕様書/ROADMAP.md` |
| **工程詳細** | `仕様書/現行ワークフロー概要.md` |
| **技術仕様（API/DB/UI）** | `仕様書/システム仕様書_技術者向け.md` |

## 重要ルール

### フォールバック全面禁止

```
❌ 禁止：別モデル/別プロバイダ/別ツールへの自動切替、モックへ逃げる、壊れた出力の黙った採用
✅ 許容：同一条件でのリトライ（上限3回、ログ必須）、決定的修正（JSON末尾カンマ除去等、ログ必須）
```

### アーキテクチャ原則

- **Temporal = 実行の正**：待機/再開/リトライ/タイムアウトは Temporal に寄せる
- **LangGraph = 工程ロジック**：プロンプト、整形、検証。重い副作用は Activity 側
- **重い成果物は storage**：DB/State/Temporal履歴には `path/digest` 参照のみ
- **マルチテナント越境禁止**：DB/Storage/WS すべて `tenant_id` でスコープ
- **ローカル運用固定**：Postgres + MinIO + Temporal（docker-compose）

### 承認フロー

- 工程3完了後は **承認待ち**（Temporal signal で待機/再開）
- approve/reject は `audit_logs` に必ず記録

## リポジトリ構造

```
.
├── .claude/
│   ├── CLAUDE.md           # ← このファイル（最高優先）
│   ├── agents/             # サブエージェント定義
│   ├── commands/           # スラッシュコマンド
│   ├── rules/              # 詳細ルール（import用）
│   └── skills/             # プロジェクト固有スキル
├── 仕様書/
│   ├── ROADMAP.md          # 実装計画（正）
│   ├── 現行ワークフロー概要.md
│   └── システム仕様書_技術者向け.md
├── langgraph-example/      # LangGraph サンプル実装
└── ref/                    # 生成物/中間出力の参照置き場
```

## よく使う操作

| 操作 | コマンド |
|------|----------|
| ローカル起動 | `/dev:up` |
| ローカル停止 | `/dev:down` |
| 並列実装（worktree作成） | `/dev:worktree-new` |
| worktree一覧 | `/dev:worktree-list` |
| worktree削除 | `/dev:worktree-remove` |
| run開始 | `/workflow:new-run` |
| 承認 | `/workflow:approve-run` |
| 生成物取得 | `/workflow:fetch-artifacts` |

## コーディング規約

- Python 3.12、FastAPI、Temporal Python SDK、LangGraph
- 4スペースインデント、型ヒント必須
- snake_case（関数/変数）、PascalCase（クラス）
- `.env` にAPIキー等を保存、コミット禁止

## 詳細ルール（import）

詳細は以下を参照：
- @rules/implementation.md（実装ルール）
- @rules/workflow-contract.md（工程・成果物・承認待ち）
