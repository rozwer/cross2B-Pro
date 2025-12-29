# .claude-making

新規プロジェクトで `.claude/` 構成を Claude Code が自律的に構築するためのテンプレート集。

## クイックスタート

### 方法1: 自動セットアップ（推奨）

1. `.claude-making/` をプロジェクトルートにコピー
2. Claude Code で以下を実行：

```
setup-project.md を読んで実行してください
```

Claude Code が対話形式でプロジェクトを分析し、自動でセットアップを実行。

### 方法2: 手動実行

```bash
# plan/ のドキュメントを順に実行
# 1. Phase 1: プロジェクト分析
# 2. Phase 2: ディレクトリ作成
# 3. Phase 3: テンプレートコピー
# 4. Phase 4: ブループリント展開
# 5. Phase 5: 検証
```

詳細は `plan/00-overview.md` を参照。

---

## ディレクトリ構造

```
.claude-making/
├── README.md                        # このファイル
├── setup-project.md                 # セットアップ実行スキル
├── DESIGN_PHILOSOPHY.md             # 設計思想
├── ASSET_CLASSIFICATION.md          # 資産分類詳細
├── options.json                     # プロジェクト設定（Phase 1 で生成）
├── options.schema.json              # options.json のスキーマ定義
├── claude-configuration-overview.md # 設定・プラグイン概要
│
├── plan/                            # Claude Code への実行指示書
│   ├── 00-overview.md               # 全体フロー
│   ├── 01-project-analysis.md       # Phase 1: 分析
│   ├── 02-structure-setup.md        # Phase 2: ディレクトリ作成
│   ├── 03-template-copy.md          # Phase 3: コピー
│   ├── 04-blueprint-customize.md    # Phase 4: 展開
│   └── 05-validation.md             # Phase 5: 検証
│
├── template/                        # そのまま転用可能な汎用資産（55個）
│   └── .claude/
│       ├── settings.json
│       ├── skills/                  # 13 スキル
│       ├── agents/                  # 22 エージェント
│       ├── commands/dev/            # 10 コマンド
│       ├── rules/                   # 7 ルール
│       ├── memory/                  # 3 テンプレート
│       └── hooks/                   # 3 フック
│
├── blueprint/                       # 変数付きテンプレート（27個）
│   ├── CLAUDE.md.template           # メイン指示書
│   ├── agents/                      # 5 テンプレート
│   ├── commands/                    # 7 テンプレート
│   ├── rules/                       # 3 テンプレート
│   └── skills/                      # 11 テンプレート
│
└── optional/                        # オプション機能
    └── codex/                       # Codex 連携（use_codex: true 時）
        ├── agents/codex-reviewer.md
        ├── commands/review/
        └── rules/codex-integration.md
```

---

## 実行フロー

```
Phase 1: プロジェクト分析
    ↓ 技術スタック検出、options.json 生成
Phase 2: ディレクトリ作成
    ↓ .claude/{agents,commands,hooks,rules,skills,memory}
Phase 3: テンプレートコピー
    ↓ template/ → .claude/, optional/ → .claude/（条件付き）
Phase 4: ブループリント展開
    ↓ blueprint/*.template + options.json → .claude/
Phase 5: 検証
    ↓ 構造確認、JSON検証、変数展開確認
完了
```

---

## 汎用資産（template/）- 55個

プロジェクトに依存せず、そのままコピーして使える：

### Skills（13）

| スキル | 説明 |
|--------|------|
| `commit` | Git コミット作成 |
| `push` | リモートへのプッシュ |
| `pr` | プルリクエスト作成 |
| `fix-bug` | バグ修正フロー |
| `new-feature` | 新機能実装フロー |
| `refactor` | リファクタリング |
| `review` | コードレビュー |
| `codebase-explore` | コードベース探索 |
| `security-review` | セキュリティレビュー |
| `deploy` | デプロイ支援 |
| `docker` | Docker 操作 |
| `docs` | ドキュメント生成 |
| `git-commit-flow` | Git フロー |

### Agents（22）

| エージェント | 説明 |
|-------------|------|
| `architect` | 設計判断 |
| `diff-analyzer` | 差分分析 |
| `commit-creator` | コミット作成 |
| `pr-creator` | PR 作成 |
| `pr-reviewer` | PR レビュー |
| `branch-manager` | ブランチ管理 |
| `rebase-handler` | リベース処理 |
| `push-handler` | プッシュ処理 |
| `conflict-resolver` | コンフリクト解決 |
| `error-analyzer` | エラー分析 |
| `stack-trace-analyzer` | スタックトレース分析 |
| `refactorer` | リファクタリング |
| `security-reviewer` | セキュリティレビュー |
| `deployer` | デプロイ実行 |
| `log-investigator` | ログ調査 |
| `api-doc-generator` | API ドキュメント生成 |
| `readme-generator` | README 生成 |
| `codebase-explorer` | コードベース探索 |
| `migration-runner` | マイグレーション実行 |
| `test-runner` | テスト実行 |
| `docker-manager` | Docker 管理 |
| `backup-manager` | バックアップ管理 |

### Commands（10）

| コマンド | 説明 |
|----------|------|
| `/dev:up` | Docker 起動 |
| `/dev:down` | Docker 停止 |
| `/dev:status` | 状態確認 |
| `/dev:logs` | ログ表示 |
| `/dev:health` | ヘルスチェック |
| `/dev:smoke` | smoke テスト |
| `/dev:test` | テスト実行 |
| `/dev:worktree-new` | worktree 作成 |
| `/dev:worktree-list` | worktree 一覧 |
| `/dev:worktree-remove` | worktree 削除 |

### Rules（7）

| ルール | 説明 |
|--------|------|
| `git-worktree` | 並列開発ルール |
| `subagent-usage` | サブエージェント使用 |
| `asset-authoring` | 資産作成ガイド |
| `githooks` | Git hooks ルール |
| `dev-style` | 開発スタイル |
| `test-quality` | テスト品質保護 |
| `implementation-quality` | 実装品質保護 |

### Memory（3）

| ファイル | 説明 |
|----------|------|
| `decisions.md` | 設計判断記録 |
| `patterns.md` | コードパターン集 |
| `session-log.md` | セッションログ |

---

## ブループリント（blueprint/）- 27個

変数 `{{VAR}}` を含み、options.json の値で展開が必要：

### 必須テンプレート

| テンプレート | 説明 | 主要変数 |
|-------------|------|---------|
| `CLAUDE.md.template` | メイン指示書 | PROJECT_NAME, TECH_STACK |
| `rules/dev-style.md.template` | 開発スタイル | PKG_MANAGER, GIT_STRATEGY |
| `rules/implementation.md.template` | 実装ルール | BACKEND_FRAMEWORK |

### ワークフロー系（9）

| テンプレート | 展開条件 |
|-------------|---------|
| `skills/workflow-framework-fundamentals.md.template` | workflow_framework あり |
| `skills/workflow-framework-patterns.md.template` | workflow_framework あり |
| `skills/workflow-framework-multi-agent.md.template` | workflow_framework あり |
| `skills/workflow-framework-persistence.md.template` | workflow_framework あり |
| `skills/workflow-step-impl.md.template` | workflow_framework あり |
| `agents/orchestrator-debugger.md.template` | orchestrator あり |
| `commands/debug/replay.md.template` | orchestrator あり |
| `commands/debug/trace.md.template` | orchestrator あり |
| `commands/workflow/*.md.template` | orchestrator あり |

### LLM 統合系（3）

| テンプレート | 展開条件 |
|-------------|---------|
| `skills/llm-prompt-authoring.md.template` | llm_provider あり |
| `agents/llm-prompt-engineer.md.template` | llm_provider あり |
| `agents/llm-prompt-tester.md.template` | llm_provider あり |

### テスト系（3）

| テンプレート | 展開条件 |
|-------------|---------|
| `skills/api-test.md.template` | backend あり |
| `skills/integration-test.md.template` | 常に |
| `skills/e2e-test.md.template` | frontend あり |

---

## オプション機能（optional/）

`options.json` の設定に応じてコピーされる：

### Codex 連携

`use_codex: true` の場合にコピー：

| ファイル | 説明 |
|----------|------|
| `rules/codex-integration.md` | Codex 使用ガイド |
| `agents/codex-reviewer.md` | セルフレビュー |
| `commands/review/codex-review.md` | レビューコマンド |

---

## options.json の構造

Phase 1 で生成される設定ファイル：

```json
{
  "project": {
    "name": "my-project",
    "description": "プロジェクトの説明",
    "tech_stack": {
      "backend": "fastapi",
      "frontend": "nextjs",
      "database": "postgresql",
      "infrastructure": "docker"
    },
    "domain": "ecommerce"
  },
  "options": {
    "use_codex": false,
    "workflow_framework": "langgraph",
    "orchestrator": "temporal",
    "llm_provider": "openai",
    "multi_tenant": false,
    "use_docker": true,
    "git_strategy": "gitflow"
  },
  "plugins": {
    "claude_mem": true,
    "claude_code_harness": true,
    "superpowers": true
  }
}
```

---

## 関連ドキュメント

- [plan/00-overview.md](./plan/00-overview.md) - 実行フローの詳細
- [DESIGN_PHILOSOPHY.md](./DESIGN_PHILOSOPHY.md) - 設計思想
- [ASSET_CLASSIFICATION.md](./ASSET_CLASSIFICATION.md) - 資産分類詳細
- [claude-configuration-overview.md](./claude-configuration-overview.md) - 設定・プラグインの詳細
