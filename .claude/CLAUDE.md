# SEO記事自動生成システム / Claude Code 指示書

> **このファイルは最高優先度**。他のドキュメントと矛盾がある場合、このファイルを正とする。

## Source of Truth

| 用途 | ファイル |
|------|----------|
| **実装計画** | `仕様書/ROADMAP.md` |
| **ワークフロー** | `仕様書/workflow.md` |
| **並列開発** | `仕様書/PARALLEL_DEV_GUIDE.md` |
| **Backend** | `仕様書/backend/` |
| **Frontend** | `仕様書/frontend/` |

---

## 並列作業（worktree）

> **詳細ガイド**: `仕様書/PARALLEL_DEV_GUIDE.md`

### ブランチ戦略

```
main (master) ← 本番相当
  └── develop ← 開発統合ブランチ
        ├── feat/xxx ← 機能ブランチ（worktree分離）
        ├── fix/xxx  ← バグ修正
        └── hotfix/xxx ← 緊急修正（mainから分岐）
```

### CLIヘルパー

```bash
# worktree 一括操作
./scripts/worktree.sh create <topic>   # 新規作成
./scripts/worktree.sh list             # 一覧表示
./scripts/worktree.sh remove <topic>   # 削除
./scripts/worktree.sh batch step1      # Step1の全worktree一括作成
./scripts/worktree.sh rebase           # 全worktreeをdevelopでリベース
./scripts/worktree.sh pr <topic>       # PRチェックリスト表示
```

### スラッシュコマンド

| 操作 | コマンド |
|------|----------|
| 作成 | `/dev:worktree-new <branch>` |
| 一覧 | `/dev:worktree-list` |
| 削除 | `/dev:worktree-remove <branch>` |

### 推奨分割（ROADMAP準拠）

| Step | Worktrees |
|------|-----------|
| Step1 | `llm-gemini`, `llm-openai`, `llm-anthropic` |
| Step3 | `tools-search`, `tools-fetch`, `tools-verify`, `tools-registry` |
| Step4 | `contract-state`, `contract-context`, `contract-adapter` |

### ルール

- **develop/main への直接 push 禁止**（Git hooks で強制）
- **Conventional Commits 形式必須**（`feat:`, `fix:`, `docs:`...）
- **PR必須**、マージ前に smoke テスト通過
- **同一ファイルへの同時編集を避ける**

---

## Codex 連携

### 呼び出し方法

```bash
# プロジェクトローカルのCodexを使用
source .codex/env.sh
codex
```

### 使用場面

| 場面 | コマンド例 |
|------|-----------|
| コードレビュー | `/review:codex-review` |
| 設計レビュー | `@architect` で設計案を出す |
| セキュリティ | `@security-reviewer` で越境チェック |

### Codex Skills

`.codex/skills/` に専用スキルあり：
- `codex-reviewer` - コードレビュー
- `langgraph-*` - LangGraph実装パターン

---

## テスト

### テスト戦略

| レベル | 対象 | 実行タイミング |
|--------|------|---------------|
| smoke | 依存/構文/起動 | commit前 |
| unit | 関数単位 | push前 |
| integration | API/DB/Temporal | PR前 |
| e2e | 全工程通し | merge前 |

### コマンド

```bash
# smoke（最低限チェック）
/dev:smoke

# pytest
pytest apps/api/tests/
pytest apps/worker/tests/

# 型チェック
mypy apps/
```

### テストルール

- 新機能には必ずテストを書く
- カバレッジ目標: 80%以上（クリティカルパスは100%）
- モックは最小限（外部API/DB接続のみ）
- フォールバックテスト禁止（正常系のみテスト）

---

## 重要ルール

### フォールバック全面禁止

```
❌ 禁止：別モデル/別プロバイダ/別ツールへの自動切替、モックへ逃げる、壊れた出力の黙った採用
✅ 許容：同一条件でのリトライ（上限3回、ログ必須）、決定的修正（JSON末尾カンマ除去等、ログ必須）
```

### アーキテクチャ原則

- **Temporal = 実行の正**：待機/再開/リトライ/タイムアウト
- **LangGraph = 工程ロジック**：プロンプト、整形、検証
- **重い成果物は storage**：path/digest 参照のみ
- **マルチテナント越境禁止**：全て tenant_id スコープ
- **ローカル運用固定**：Postgres + MinIO + Temporal

---

## サブエージェント

| エージェント | 用途 |
|-------------|------|
| `@architect` | 設計判断・分割方針 |
| `@backend-implementer` | BE実装 |
| `@frontend-implementer` | FE実装 |
| `@prompt-engineer` | プロンプト設計 |
| `@security-reviewer` | セキュリティレビュー |
| `@temporal-debugger` | Temporalデバッグ |

---

## リポジトリ構造

```
.
├── .claude/
│   ├── CLAUDE.md           # ← このファイル
│   ├── agents/             # サブエージェント
│   ├── commands/           # スラッシュコマンド
│   ├── rules/              # 詳細ルール
│   └── skills/             # LangGraph等スキル
├── .codex/                 # Codex設定・スキル
├── .githooks/              # Git hooks（Conventional Commits強制等）
├── .worktrees/             # 並列開発用worktree格納ディレクトリ
├── scripts/
│   └── worktree.sh         # 並列開発CLIヘルパー
├── 仕様書/
│   ├── ROADMAP.md
│   ├── workflow.md
│   ├── PARALLEL_DEV_GUIDE.md  # 並列開発ガイド
│   ├── backend/
│   └── frontend/
├── apps/
│   ├── api/                # FastAPI
│   └── worker/             # Temporal Worker
├── langgraph-example/      # サンプル実装
└── ref/                    # 生成物参照
```

---

## クイックリファレンス

### よく使うコマンド

| 操作 | コマンド |
|------|----------|
| 起動 | `/dev:up` |
| 停止 | `/dev:down` |
| smoke | `/dev:smoke` |
| run開始 | `/workflow:new-run` |
| 承認 | `/workflow:approve-run` |

### 仕様参照

```
@仕様書/ROADMAP.md              → 実装計画
@仕様書/workflow.md             → 工程フロー
@仕様書/backend/temporal.md#approval → 承認フロー
@仕様書/backend/api.md#tools    → ツール仕様
```
