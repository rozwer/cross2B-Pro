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
├── template/                        # そのまま転用可能な汎用資産
│   ├── .claude/
│   │   ├── settings.json
│   │   ├── skills/                  # 8 スキル
│   │   ├── agents/                  # 6 エージェント
│   │   ├── commands/dev/            # 4 コマンド
│   │   ├── rules/                   # 2 ルール
│   │   └── hooks/                   # 2 フック
│   └── .codex/                      # Codex 設定（オプション）
│
└── blueprint/                       # 変数付きテンプレート
    ├── CLAUDE.md.template           # メイン指示書
    ├── agents/                      # 専門エージェント
    ├── commands/                    # 専門コマンド
    ├── rules/                       # 専門ルール
    └── skills/                      # 専門スキル
```

---

## 実行フロー

```
Phase 1: プロジェクト分析
    ↓ 技術スタック検出、options.json 生成
Phase 2: ディレクトリ作成
    ↓ .claude/{agents,commands,hooks,rules,skills}
Phase 3: テンプレートコピー
    ↓ template/ → .claude/
Phase 4: ブループリント展開
    ↓ blueprint/*.template + options.json → .claude/
Phase 5: 検証
    ↓ 構造確認、JSON検証、変数展開確認
完了
```

---

## 汎用資産（template/）

プロジェクトに依存せず、そのままコピーして使える：

### Skills（8）

| スキル | 説明 |
|--------|------|
| `commit` | Git コミット作成 |
| `push` | リモートへのプッシュ |
| `pr` | プルリクエスト作成 |
| `fix-bug` | バグ修正フロー |
| `new-feature` | 新機能実装フロー |
| `refactor` | リファクタリング |
| `review` | コードレビュー |
| `debug` | デバッグ支援 |

### Agents（6）

| エージェント | 説明 |
|-------------|------|
| `architect` | 設計判断 |
| `diff-analyzer` | 差分分析 |
| `commit-creator` | コミット作成 |
| `pr-creator` | PR 作成 |
| `error-analyzer` | エラー分析 |
| `refactorer` | リファクタリング |

### Commands（4）

| コマンド | 説明 |
|----------|------|
| `/dev:up` | Docker 起動 |
| `/dev:down` | Docker 停止 |
| `/dev:status` | 状態確認 |
| `/dev:logs` | ログ表示 |

### Rules（2）

| ルール | 説明 |
|--------|------|
| `git-worktree` | 並列開発ルール |
| `subagent-usage` | サブエージェント使用ルール |

### Hooks（2）

| フック | 説明 |
|--------|------|
| `log-commands.sh` | Bash コマンドログ |
| `protect-files.py` | 重要ファイル保護 |

---

## ブループリント（blueprint/）

変数 `{{VAR}}` を含み、options.json の値で展開が必要：

| テンプレート | 説明 | 主要変数 |
|-------------|------|---------|
| `CLAUDE.md.template` | メイン指示書 | PROJECT_NAME, TECH_STACK, DOMAIN |
| `agents/implementer.md.template` | 実装エージェント | ROLE, TECH |
| `rules/dev-style.md.template` | 開発スタイル | PKG_MANAGER, GIT_STRATEGY |

---

## options.json の構造

Phase 1 で生成される設定ファイル：

```json
{
  "project": {
    "name": "my-project",
    "description": "プロジェクトの説明",
    "type": "webapp"
  },
  "tech_stack": {
    "backend": {
      "language": "python",
      "framework": "fastapi",
      "package_manager": "uv"
    },
    "frontend": {
      "framework": "nextjs",
      "language": "typescript"
    },
    "database": {
      "primary": "postgresql"
    },
    "infrastructure": {
      "container": "docker"
    }
  },
  "options": {
    "use_codex": false,
    "git_strategy": "gitflow"
  },
  "recommended_assets": {
    "skills": ["commit", "push", "pr"],
    "agents": ["architect", "be-implementer"],
    "rules": ["dev-style", "git-worktree"]
  }
}
```

---

## 関連ドキュメント

- [plan/00-overview.md](./plan/00-overview.md) - 実行フローの詳細
- [DESIGN_PHILOSOPHY.md](./DESIGN_PHILOSOPHY.md) - 設計思想
- [claude-configuration-overview.md](./claude-configuration-overview.md) - 設定・プラグインの詳細
