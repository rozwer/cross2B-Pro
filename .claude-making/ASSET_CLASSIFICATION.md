# .claude-making 資産分類リスト

> この文書は `.claude/` の全資産を分類し、`.claude-making` への移植方針を定義する

---

## 設計原則

| 配置先 | 基準 | 例 |
|--------|------|-----|
| **template/** | どのプロジェクトでも共通 | git, Docker, セキュリティ |
| **blueprint/** | 技術スタック依存（変数化） | ワークフロー, LLM, オーケストレーター |
| **除外** | このプロジェクト固有すぎる | プロンプトDB管理, テナントDB操作 |
| **オプション** | 特定ツール依存（有無選択） | Codex 連携 |

---

## SKILLS (24個)

| 資産 | 分類 | 理由 |
|------|------|------|
| `commit.md` | ✅ template | Git 操作は普遍的 |
| `push.md` | ✅ template | Git 操作は普遍的 |
| `pr.md` | ✅ template | Git 操作は普遍的 |
| `fix-bug.md` | ✅ template | バグ修正フローは普遍的 |
| `new-feature.md` | ✅ template | 機能追加フローは普遍的 |
| `refactor.md` | ✅ template | リファクタフローは普遍的 |
| `review.md` | ✅ template | コードレビューは普遍的 |
| `debug.md` | ✅ template | デバッグフローは普遍的 |
| `codebase-explore.md` | ✅ template | コード探索は普遍的 |
| `security-review.md` | ✅ template | セキュリティは普遍的 |
| `deploy.md` | ✅ template | デプロイは普遍的 |
| `docker.md` | ✅ template | Docker 操作は普遍的 |
| `docs.md` | ✅ template | ドキュメント作成は普遍的 |
| `git-commit-flow.md` | ⚠️ 検討 | `commit.md` と統合？ |
| `langgraph-fundamentals.md` | 🔧 blueprint | → `workflow-framework-fundamentals` |
| `langgraph-patterns.md` | 🔧 blueprint | → `workflow-framework-patterns` |
| `langgraph-multi-agent.md` | 🔧 blueprint | → `workflow-framework-multi-agent` |
| `langgraph-persistence.md` | 🔧 blueprint | → `workflow-framework-persistence` |
| `prompt-authoring.md` | 🔧 blueprint | → `llm-prompt-authoring` |
| `workflow-step-impl.md` | 🔧 blueprint | → `workflow-step-impl` (抽象化) |
| `endpoint_test.md` | 🔧 blueprint | → `api-test` (テスト系抽象化) |
| `fe_be_test.md` | 🔧 blueprint | → `integration-test` |
| `flow_test.md` | 🔧 blueprint | → `e2e-test` |
| `tenant-db-ops.md` | ❌ 除外 | プロジェクト固有すぎる |

**集計**: template=13, blueprint=10, 除外=1

---

## AGENTS (26個)

| 資産 | 分類 | 理由 |
|------|------|------|
| `architect.md` | ✅ template | 設計判断は普遍的 |
| `be-implementer.md` | ✅ template | BE実装は普遍的 |
| `fe-implementer.md` | ✅ template | FE実装は普遍的 |
| `commit-creator.md` | ✅ template | Git 操作は普遍的 |
| `pr-creator.md` | ✅ template | Git 操作は普遍的 |
| `pr-reviewer.md` | ✅ template | レビューは普遍的 |
| `diff-analyzer.md` | ✅ template | 差分分析は普遍的 |
| `error-analyzer.md` | ✅ template | エラー分析は普遍的 |
| `refactorer.md` | ✅ template | リファクタは普遍的 |
| `docker-manager.md` | ✅ template | Docker 管理は普遍的 |
| `deployer.md` | ✅ template | デプロイは普遍的 |
| `security-reviewer.md` | ✅ template | セキュリティは普遍的 |
| `log-investigator.md` | ✅ template | ログ調査は普遍的 |
| `api-doc-generator.md` | ✅ template | API ドキュメントは普遍的 |
| `readme-generator.md` | ✅ template | README 生成は普遍的 |
| `branch-manager.md` | ✅ template | Git 操作は普遍的 |
| `bugfix-handler.md` | ✅ template | バグ修正は普遍的 |
| `conflict-resolver.md` | ✅ template | コンフリクト解決は普遍的 |
| `push-handler.md` | ✅ template | Git 操作は普遍的 |
| `rebase-handler.md` | ✅ template | Git 操作は普遍的 |
| `stack-tracer.md` | ✅ template | スタックトレースは普遍的 |
| `integration-implementer.md` | ✅ template | 統合実装は普遍的 |
| `temporal-debugger.md` | 🔧 blueprint | → `orchestrator-debugger` |
| `prompt-engineer.md` | 🔧 blueprint | → `llm-prompt-engineer` |
| `prompt-tester.md` | 🔧 blueprint | → `llm-prompt-tester` |
| `codex-reviewer.md` | 🔶 オプション | Codex 使用時のみ |

**集計**: template=22, blueprint=3, オプション=1

---

## RULES (10個)

| 資産 | 分類 | 理由 |
|------|------|------|
| `asset-authoring.md` | ✅ template | 資産作成ルールは普遍的 |
| `dev-style.md` | ✅ template | 開発スタイルは普遍的（変数化） |
| `git-worktree.md` | ✅ template | worktree は普遍的 |
| `githooks.md` | ✅ template | Git フックは普遍的 |
| `implementation-quality.md` | ✅ template | 実装品質は普遍的 |
| `test-quality.md` | ✅ template | テスト品質は普遍的 |
| `subagent-usage.md` | ✅ template | サブエージェント使用は普遍的 |
| `workflow-contract.md` | 🔧 blueprint | ワークフロー固有部分を変数化 |
| `implementation.md` | 🔧 blueprint | プロジェクト固有部分を変数化 |
| `codex-integration.md` | 🔶 オプション | Codex 使用時のみ |

**集計**: template=7, blueprint=2, オプション=1

---

## COMMANDS (22個)

| 資産 | 分類 | 理由 |
|------|------|------|
| `dev/up.md` | ✅ template | Docker 操作は普遍的 |
| `dev/down.md` | ✅ template | Docker 操作は普遍的 |
| `dev/status.md` | ✅ template | 状態確認は普遍的 |
| `dev/logs.md` | ✅ template | ログ確認は普遍的 |
| `dev/health.md` | ✅ template | ヘルスチェックは普遍的 |
| `dev/smoke.md` | ✅ template | スモークテストは普遍的 |
| `dev/test.md` | ✅ template | テスト実行は普遍的 |
| `dev/worktree-list.md` | ✅ template | worktree は普遍的 |
| `dev/worktree-new.md` | ✅ template | worktree は普遍的 |
| `dev/worktree-remove.md` | ✅ template | worktree は普遍的 |
| `debug/replay.md` | 🔧 blueprint | → オーケストレーター用 |
| `debug/trace-run.md` | 🔧 blueprint | → オーケストレーター用 |
| `workflow/new-run.md` | 🔧 blueprint | → ワークフロー用 |
| `workflow/run.md` | 🔧 blueprint | → ワークフロー用 |
| `workflow/start-run.md` | 🔧 blueprint | → ワークフロー用 |
| `workflow/approve-run.md` | 🔧 blueprint | → ワークフロー用 |
| `workflow/fetch-artifacts.md` | 🔧 blueprint | → ワークフロー用 |
| `dev/seed.md` | ❌ 除外 | プロジェクト固有 |
| `run_flow.md` | ❌ 除外 | プロジェクト固有 |
| `prompts/bump-version.md` | ❌ 除外 | プロンプトDB固有 |
| `prompts/preview-render.md` | ❌ 除外 | プロンプトDB固有 |
| `review/codex-review.md` | 🔶 オプション | Codex 使用時のみ |

**集計**: template=10, blueprint=7, 除外=4, オプション=1

---

## MEMORY/ (新規)

| 資産 | 分類 | 理由 |
|------|------|------|
| `decisions.md` | ✅ template | 決定記録は普遍的 |
| `patterns.md` | ✅ template | パターン記録は普遍的 |
| `session-log.md` | ✅ template | セッションログは普遍的 |

**集計**: template=3

---

## 集計サマリー

| カテゴリ | template | blueprint | オプション | 除外 |
|----------|----------|-----------|-----------|------|
| skills | 13 | 10 | 0 | 1 |
| agents | 22 | 3 | 1 | 0 |
| rules | 7 | 2 | 1 | 0 |
| commands | 10 | 7 | 1 | 4 |
| memory | 3 | 0 | 0 | 0 |
| **合計** | **55** | **22** | **3** | **5** |
