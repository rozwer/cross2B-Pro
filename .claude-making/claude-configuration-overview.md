# Claude Code 設定・プラグイン概要ドキュメント

> 作成日: 2025-12-28
> 対象: 外部LLMとの設定レビュー用

---

## 目次

1. [.claude ディレクトリ構造](#1-claude-ディレクトリ構造)
2. [設定ファイル](#2-設定ファイル)
3. [エージェント (agents/)](#3-エージェント-agents)
4. [スキル (skills/)](#4-スキル-skills)
5. [コマンド (commands/)](#5-コマンド-commands)
6. [ルール (rules/)](#6-ルール-rules)
7. [状態管理 (state/)](#7-状態管理-state)
8. [メモリ (memory/)](#8-メモリ-memory)
9. [導入済みプラグイン](#9-導入済みプラグイン)

---

## 1. .claude ディレクトリ構造

```
.claude/
├── CLAUDE.md                 # メイン指示書（最高優先度）
├── settings.json             # 基本パーミッション設定
├── settings.local.json       # ローカル拡張パーミッション（大量のBash許可）
├── agents/                   # サブエージェント定義
│   ├── architect.md
│   ├── backend-implementer.md
│   ├── frontend-implementer.md
│   ├── prompt-engineer.md
│   ├── security-reviewer.md
│   ├── temporal-debugger.md
│   └── codex-reviewer.md
├── skills/                   # プロジェクト固有スキル
│   ├── langgraph-fundamentals/
│   ├── langgraph-multi-agent/
│   ├── langgraph-patterns/
│   ├── langgraph-persistence/
│   ├── prompt-authoring/
│   ├── security-review/
│   ├── tenant-db-ops/
│   └── workflow-step-impl/
├── commands/                 # スラッシュコマンド
│   ├── dev/
│   ├── debug/
│   ├── prompts/
│   ├── review/
│   └── workflow/
├── rules/                    # 実装ルール
│   ├── implementation.md
│   ├── workflow-contract.md
│   └── git-worktree.md
├── state/                    # セッション状態
│   ├── session.json
│   ├── generated-files.json
│   ├── tooling-policy.json
│   └── session-skills-used.json
└── memory/                   # セッションログ
    └── session-log.md
```

---

## 2. 設定ファイル

### CLAUDE.md（メイン指示書）

**役割**: プロジェクト全体の最高優先度指示書

**主要内容**:
- Source of Truth の定義（ROADMAP.md, workflow.md 等）
- 並列作業（worktree）ルールとブランチ戦略
- Codex 連携方法（`@codex-reviewer` subagent）
- テスト戦略（smoke/unit/integration/e2e）
- 開発スタイル（uv/npm、細かいコミット）
- 重要ルール: **フォールバック全面禁止**
- サブエージェント一覧
- リポジトリ構造

### settings.json（基本パーミッション）

**役割**: Claude Code の基本的なツール許可設定

**許可内容**:
- Git 操作（add, commit, status, diff, log, branch, checkout 等）
- 開発ツール（python, uv, npm, docker, temporal 等）
- ファイル操作（mkdir, rm, cp, mv, ls, find 等）
- 検索・加工（grep, sed, awk, jq 等）
- DB・ストレージ（psql, mc 等）
- 読み書き（Read, Edit, Write, Glob, Grep）
- Web（WebFetch, WebSearch）
- タスク管理（Task, Skill, TodoWrite）

### settings.local.json（ローカル拡張）

**役割**: プロジェクト固有の追加パーミッション

**特徴**:
- 基本パーミッションを継承
- 過去に実行された具体的なコマンドが多数追加（300行以上）
- 特定の RUN_ID や TOKEN を含むコマンドも許可リストに含まれる
- Codex 連携コマンド許可
- スキル許可（langgraph-fundamentals, code-review, workflow-step-impl 等）

---

## 3. エージェント (agents/)

| ファイル | 名前 | 用途 |
|----------|------|------|
| architect.md | @architect | 設計判断・分割方針、ROADMAPに沿った分割推奨 |
| backend-implementer.md | @backend-implementer | FastAPI/Temporal/DB/Storage実装（監査ログ必須） |
| frontend-implementer.md | @frontend-implementer | レビューUI実装（承認/却下/生成物閲覧） |
| prompt-engineer.md | @prompt-engineer | DB管理プロンプトの設計・バージョニング |
| security-reviewer.md | @security-reviewer | マルチテナント越境・監査・秘密情報レビュー |
| temporal-debugger.md | @temporal-debugger | Temporal履歴/リプレイ/決定性違反デバッグ |
| codex-reviewer.md | @codex-reviewer | Codex CLIでセカンドオピニオンレビュー |

### 各エージェントの詳細

#### architect.md
```markdown
- 仕様の矛盾/未決定を洗い出し、決定案を提示
- 実装をレビュー可能な粒度に分割（worktree境界）
- 参照: @仕様書/ROADMAP.md, temporal.md, database.md
```

#### backend-implementer.md
```markdown
- API契約とDBスキーマに沿って実装（監査ログ必須）
- Activity冪等性（input/output digest, output_path）を守る
- チェックリスト: tenant_id スコープ、監査ログ、冪等性、storage保存、フォールバック禁止
```

#### codex-reviewer.md
```markdown
- 実行方法:
  - `codex review --uncommitted` (未コミット変更)
  - `codex review --base develop` (ブランチ差分)
  - `codex review --commit <SHA>` (特定コミット)
```

---

## 4. スキル (skills/)

| ディレクトリ | 名前 | 用途 |
|--------------|------|------|
| langgraph-fundamentals/ | langgraph-fundamentals | StateGraph/State Schema/ノード/エッジの基礎 |
| langgraph-multi-agent/ | langgraph-multi-agent | Supervisor/Swarm/Agent-as-Tool パターン |
| langgraph-patterns/ | langgraph-patterns | Streaming/並列実行/Subgraph/エラー処理 |
| langgraph-persistence/ | langgraph-persistence | Checkpointing/Human-in-the-loop/Time-travel |
| prompt-authoring/ | prompt-authoring | DB管理プロンプトのversioning/variables/レンダリング |
| security-review/ | security-review | RBAC/監査ログ/秘密情報/越境/LLM注入レビュー |
| tenant-db-ops/ | tenant-db-ops | マルチテナントDB運用・マイグレーション |
| workflow-step-impl/ | workflow-step-impl | Temporal+LangGraph工程追加の実装テンプレ |

### workflow-step-impl の詳細

**templates/ サブディレクトリあり**:
- `activity_skeleton.py` - Activity実装のスケルトン
- `step_node_skeleton.py` - LangGraphノードのスケルトン

**チェックリスト**:
1. 仕様書で工程ID/入出力/承認ポイントを確定
2. 入力の正規化と `input_digest`（sha256）を定義
3. Activity 実装（冪等：既存出力があれば再計算しない）
4. 成果物は storage に保存、返すのは参照のみ
5. Temporal Workflow に組み込み（工程3後は signal 待機）
6. DB記録を追加
7. UI/APIを同時更新

---

## 5. コマンド (commands/)

### dev/（開発系）

| コマンド | ファイル | 用途 |
|----------|----------|------|
| /dev:up | up.md | Docker Compose で全サービス起動 |
| /dev:down | down.md | ローカル停止 |
| /dev:smoke | smoke.md | 環境/依存/構文/起動の最低限チェック |
| /dev:seed | seed.md | 初期データ投入（未整備） |
| /dev:worktree-new | worktree-new.md | git worktree 作成 |
| /dev:worktree-list | worktree-list.md | worktree 一覧 |
| /dev:worktree-remove | worktree-remove.md | worktree 削除 |

### debug/（デバッグ系）

| コマンド | ファイル | 用途 |
|----------|----------|------|
| /debug:trace-run | trace-run.md | run障害解析（API→DB→Temporal→storage） |
| /debug:replay | replay.md | Temporalリプレイ（決定性違反検出） |

### prompts/（プロンプト管理）

| コマンド | ファイル | 用途 |
|----------|----------|------|
| /prompts:preview-render | preview-render.md | プロンプトレンダリング結果プレビュー |
| /prompts:bump-version | bump-version.md | プロンプトバージョン更新 |

### workflow/（ワークフロー操作）

| コマンド | ファイル | 用途 |
|----------|----------|------|
| /workflow:new-run | new-run.md | 新規run/workflow開始 |
| /workflow:start-run | start-run.md | 既存run開始 |
| /workflow:approve-run | approve-run.md | 工程3承認（Temporal signal再開） |
| /workflow:fetch-artifacts | fetch-artifacts.md | 生成物取得 |

### review/（レビュー系）

| コマンド | ファイル | 用途 |
|----------|----------|------|
| /review:codex-review | codex-review.md | Codexセカンドオピニオンレビュー |

---

## 6. ルール (rules/)

### implementation.md（実装ルール）

**主要セクション**:
1. **API契約**: 38エンドポイントの定義（Runs/Artifacts/Step11/Step12/Other）
2. **Temporal + LangGraph**: 決定性、signal待機、冪等性
3. **成果物（Storage）**: output_path/output_digest/summary/metrics
4. **セキュリティ/マルチテナント**: 越境防止、監査ログ、秘密情報
5. **プロンプト管理**: DB管理、versioning、変数レンダリング
6. **フロントエンド**: ワークフロービュー、承認フロー
7. **環境構築・Docker**: 必要条件、サービス一覧
8. **テスト戦略**: テストレベル、禁止パターン
9. **CI/CD パイプライン**
10. **トラブルシューティング**

### workflow-contract.md（ワークフロー契約）

**主要ルール**:
- 工程3（3A/3B/3C）完了後は承認待ち
- 承認/却下/再実行は `audit_logs` に記録
- 成果物は storage に保存、参照のみ返す
- **冪等性必須**: 同一入力 → 同一出力
- **フォールバック禁止**: 別モデル/別プロバイダへの自動切替禁止
- **リトライ許可**: 同一条件で最大3回

### git-worktree.md（Git Worktree運用）

**主要ルール**:
- worktree は `.worktrees/<topic>/` に作成
- 1 worktree = 1 作業テーマ
- 同じファイルを複数 worktree で同時に触らない
- Python venv は worktree ごとに作成
- リモート操作は行わない

---

## 7. 状態管理 (state/)

### session.json
```json
{
  "session_id": "c1464970-0a7a-4b69-b74b-d3396e54c296",
  "started_at": "2025-12-28T11:15:31Z",
  "cwd": "/home/rozwer/案件",
  "project_name": "案件",
  "git": {
    "branch": "develop",
    "uncommitted_changes": 6,
    "last_commit": "f77b396"
  },
  "plans": { "exists": false, ... },
  "changes_this_session": [],
  "intent": "literal"
}
```

### generated-files.json
```json
{
  "lastCheckedPluginVersion": "2.6.11",
  "files": {
    ".claude/settings.local.json": { "templateVersion": "unknown", "fileHash": "...", "recordedAt": "..." },
    ".claude/settings.json": { "templateVersion": "unknown", "fileHash": "...", "recordedAt": "..." }
  }
}
```

### tooling-policy.json
```json
{
  "lsp": { "available": false, ... },
  "skills": { "index": [], "decision_required": false }
}
```

### session-skills-used.json
```json
{"used": [], "session_start": "2025-12-28T11:15:31Z"}
```

---

## 8. メモリ (memory/)

### session-log.md

セッション単位の作業ログ。重要な意思決定は `decisions.md`、再利用できる解法は `patterns.md` に昇格。

```markdown
## セッション: 2025-12-28T10:40:11Z
- session_id: `34227b69-cf1e-4f05-8639-db593d162ba4`
- project: `案件`
- branch: `develop`
- duration_minutes: 2
- changes: 0
```

---

## 9. 導入済みプラグイン

### 一覧

| プラグイン | マーケットプレース | バージョン | インストール日 |
|------------|-------------------|------------|----------------|
| document-skills | anthropic-agent-skills | unknown | 2025-11-17 |
| example-skills | anthropic-agent-skills | unknown | 2025-11-17 |
| pr-review-toolkit | claude-code-plugins | 1.0.0 | 2025-12-06 |
| superpowers | superpowers-marketplace | 3.6.2 | 2025-12-06 |
| **claude-mem** | thedotmack | **7.4.5** | 2025-12-22 |
| **claude-code-harness** | claude-code-harness-marketplace | **2.6.11** | 2025-12-28 |

### claude-mem（v7.4.5）

**概要**: Claude Code 用の永続メモリ圧縮システム

**機能**:
- 🧠 **Persistent Memory** - セッション間でコンテキストを保持
- ツール使用観測の自動キャプチャ
- セマンティック要約の生成
- MCP ベースの検索ツール提供

**設定**:
```json
// ~/.claude-mem/settings.json
{
  "CLAUDE_MEM_MODE": "harness--ja"
}
```

**データ**:
- SQLite DB: `~/.claude-mem/claude-mem.db`
- Vector DB: `~/.claude-mem/vector-db/`
- ログ: `~/.claude-mem/logs/`

### claude-code-harness（v2.6.11）

**概要**: 個人開発をプロ品質へ導く開発ハーネス

**コンセプト**: 「Plan → Work → Review」の自律サイクル

**解決する4つの問題**:
| 問題 | 症状 | 解決策 |
|------|------|--------|
| 迷う | 何をすべきかわからない | `/plan-with-agent` で整理 |
| 雑になる | 品質が落ちる | `/harness-review` で多観点チェック |
| 事故る | 危険な操作を実行 | Hooks で自動ガード |
| 忘れる | 前提が抜ける | SSOT + Claude-mem で継続 |

**主要コマンド**:
| コマンド | 何をする | 結果 |
|----------|----------|------|
| `/plan-with-agent` | 壁打ち → 計画化 | Plans.md 作成 |
| `/work` | 計画を実行 | 動くコード |
| `/harness-review` | 多観点レビュー | プロ品質 |

**v2.6 の新機能**:
- 品質判定ゲートシステム（TDD/Security/a11y/Performance 自動提案）
- Claude-mem 統合（`/harness-mem`）
- Skill 階層リマインダー

**提供スキル**:
- principles/（コア原則、diff-aware editing、repo context）
- impl/（feature実装、テスト作成）
- 2agent/（Cursor連携、2エージェント運用）
- session-init/（セッション初期化）
- workflow-guide/（ワークフローガイド）
- maintenance/（自動クリーンアップ）
- session-memory/（セッションメモリ）
- troubleshoot/（トラブルシューティング）
- deploy/（デプロイ設定、ヘルスチェック）
- parallel-workflows/（並列ワークフロー）
- ci/（CI失敗分析、テスト修正）
- auth/（認証実装）

### superpowers（v3.6.2）

**概要**: TDD、デバッグ、コラボレーションパターンのコアスキルライブラリ

**提供内容**:
- 20+ のバトルテスト済みスキル
- `/brainstorm`, `/write-plan`, `/execute-plan` コマンド
- スキル検索ツール
- SessionStart コンテキスト注入

### pr-review-toolkit（v1.0.0）

**概要**: PRレビュー支援ツールキット

**提供エージェント**:
- comment-analyzer: コメント精度分析
- pr-test-analyzer: テストカバレッジ分析
- type-design-analyzer: 型設計分析
- code-reviewer: コードレビュー
- silent-failure-hunter: サイレント失敗検出
- code-simplifier: コード簡素化

---

## 補足情報

### プラグイン格納場所

```
~/.claude/plugins/
├── installed_plugins.json    # インストール済みプラグイン一覧
├── known_marketplaces.json   # 登録済みマーケットプレース
├── cache/                    # プラグインキャッシュ
└── marketplaces/             # マーケットプレースソース
    ├── anthropic-agent-skills/
    ├── claude-code-plugins/
    ├── superpowers-marketplace/
    ├── thedotmack/           # claude-mem
    └── claude-code-harness-marketplace/
```

### Claude-mem データ格納場所

```
~/.claude-mem/
├── settings.json             # 設定（モード: harness--ja）
├── claude-mem.db             # SQLite メインDB
├── claude-mem.db-wal         # WAL
├── claude-mem.db-shm         # 共有メモリ
├── vector-db/                # Chroma ベクトルDB
├── worker.pid                # ワーカープロセスID
└── logs/                     # ワーカーログ
```

---

## 設定の問題点・改善候補

### settings.local.json の肥大化

現在 340 行以上のパーミッションが記録されており、以下の問題がある:
- 過去の一時的なコマンド（特定の RUN_ID, TOKEN を含む）が残っている
- 重複パターンが多い
- 整理・クリーンアップが必要

### 推奨アクション

1. `settings.local.json` の整理（一時的なコマンドの削除）
2. パターンベースの許可に統一（例: `Bash(RUN_ID=*:*)` ではなく必要なものだけ）
3. 定期的なパーミッションレビューの実施
