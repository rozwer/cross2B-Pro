---
description: Skills/Agents/Commands/Rules の作成・編集ガイドライン
---

## 資産の種類と用途

| 種類 | 用途 | 呼び出し方 | 配置先 |
|------|------|-----------|--------|
| **Skills** | ユーザー向けワークフロー | `/skill-name` | `.claude/skills/` |
| **Agents** | 内部処理の専門家 | `@agent-name` | `.claude/agents/` |
| **Commands** | 短縮形・引数付き操作 | `/namespace:command` | `.claude/commands/` |
| **Rules** | 常時適用されるルール | 自動読み込み | `.claude/rules/` |

---

## Skills の作成ルール

### ファイル形式

```markdown
---
name: skill-name
description: スキルの説明（Skill ツールの選択に使用）
---

# /skill-name - タイトル

## 概要
スキルが何をするか

## 使用例
`/skill-name` - 基本使用
`/skill-name --option` - オプション付き

## 実行フロー
1. Step 1
2. Step 2
...

## 使用するエージェント
- @agent-1: 役割
- @agent-2: 役割
```

### 命名規則

- **ケバブケース**: `fix-bug`, `new-feature`, `git-commit-flow`
- **動詞始まり推奨**: `fix-`, `add-`, `run-`, `check-`
- **省略形可**: `pr`（pull-request より）

### 配置例

```
.claude/skills/
├── fix-bug.md
├── new-feature.md
├── commit.md
├── pr.md
└── security-review.md
```

---

## Agents の作成ルール

### ファイル形式

```markdown
---
name: agent-name
description: エージェントの説明（Task ツールの選択に使用）
tools: 使用可能ツール（All tools / 限定リスト）
---

# @agent-name

## 役割
何を専門とするか

## 入力
期待する情報

## 出力
返す情報の形式

## 判断基準
どのような判断をするか
```

### 命名規則

- **ケバブケース**: `backend-implementer`, `code-reviewer`
- **役割を表す接尾辞**:
  - `-implementer`: 実装担当
  - `-reviewer`: レビュー担当
  - `-manager`: 管理担当
  - `-debugger`: デバッグ担当
  - `-analyzer`: 分析担当
  - `-creator`: 生成担当

### 配置例

```
.claude/agents/
├── backend-implementer.md
├── frontend-implementer.md
├── codex-reviewer.md
├── security-reviewer.md
├── docker-manager.md
└── temporal-debugger.md
```

---

## Commands の作成ルール

### ファイル形式

```markdown
---
description: コマンドの説明
allowed-tools: Bash, Task, ...
---

## 実行

具体的な実行手順

## 使用例

/namespace:command arg1 arg2
```

### 命名規則

- **namespace:command 形式**: `dev:up`, `workflow:run`
- **namespace 例**:
  - `dev:` - 開発環境操作
  - `workflow:` - ワークフロー操作
  - `debug:` - デバッグ操作
  - `prompts:` - プロンプト管理
- **短く明確に**: `up`, `down`, `logs`, `status`

### 配置例

```
.claude/commands/
├── dev/
│   ├── up.md
│   ├── down.md
│   ├── logs.md
│   └── status.md
├── workflow/
│   └── run.md
└── debug/
    └── trace-run.md
```

---

## Rules の作成ルール

### ファイル形式

```markdown
---
description: ルールの説明（セッション開始時に読み込まれる）
---

## セクション1

ルール内容

## セクション2

ルール内容
```

### 命名規則

- **ケバブケース**: `git-worktree`, `workflow-contract`
- **対象を明確に**: 何のルールか分かる名前
  - `subagent-usage` - サブエージェント使用
  - `asset-authoring` - 資産作成
  - `implementation` - 実装ルール

### 配置例

```
.claude/rules/
├── git-worktree.md
├── workflow-contract.md
├── implementation.md
├── subagent-usage.md
└── asset-authoring.md
```

---

## 編集時の注意

### 1. 既存資産の確認

新規作成前に重複や競合がないか確認：

```bash
# Skills の確認
ls .claude/skills/

# Agents の確認
ls .claude/agents/

# 名前で検索
grep -r "skill-name" .claude/
```

### 2. 後方互換性

- 既存の呼び出し方を壊さない
- 名前変更時は移行期間を設ける
- 廃止予定の資産は `deprecated` マークを付ける

### 3. テスト

新規・変更後は動作確認：

```
1. 呼び出しが正常に動作するか
2. 期待する出力が得られるか
3. エラーハンドリングが適切か
```

### 4. ドキュメント

- Plans.md に反映
- 必要に応じて CLAUDE.md を更新
- 変更履歴を残す

---

## 資産間の関係

```
Skills（ユーザー向け）
    │
    ├── 内部で Agents を呼び出し
    │   └── @backend-implementer
    │   └── @codex-reviewer
    │
    └── Commands と連携
        └── /dev:up

Rules（常時適用）
    │
    └── Skills/Agents/Commands の動作を制約
```

---

## チェックリスト

新規資産作成時：

- [ ] 命名規則に従っている
- [ ] ファイル形式が正しい
- [ ] 既存資産と重複していない
- [ ] 動作確認済み
- [ ] Plans.md に反映済み
