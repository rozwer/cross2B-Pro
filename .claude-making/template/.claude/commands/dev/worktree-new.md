---
description: git worktree を作って並列実装を始める（.worktrees 配下）
---

## 使い方

### 1) 作業テーマ名を決める

例：`frontend-canvas` / `backend-api-contract` / `worker-idempotency`

### 2) worktree 作成（推奨：新ブランチを同時に作る）

```bash
mkdir -p .worktrees
git worktree add -b "$TOPIC_BRANCH" ".worktrees/$TOPIC_DIR"
```

例：

```bash
TOPIC_DIR="frontend-canvas"
TOPIC_BRANCH="feat/frontend-canvas"
mkdir -p .worktrees
git worktree add -b "$TOPIC_BRANCH" ".worktrees/$TOPIC_DIR"
```

### 3) その worktree に移動して作業

```bash
cd ".worktrees/$TOPIC_DIR"
git status
```
