---
description: git worktree を作って並列実装を始める（.worktrees 配下）
allowed-tools: Bash
---

## 使い方

### 1) 作業テーマ名を決める

例：\`frontend-refactor\` / \`backend-api\` / \`feature-auth\`

### 2) worktree 作成（推奨：新ブランチを同時に作る）

\`\`\`bash
mkdir -p .worktrees
git worktree add -b "\$TOPIC_BRANCH" ".worktrees/\$TOPIC_DIR"
\`\`\`

例：

\`\`\`bash
TOPIC_DIR="feature-auth"
TOPIC_BRANCH="feat/auth"
mkdir -p .worktrees
git worktree add -b "\$TOPIC_BRANCH" ".worktrees/\$TOPIC_DIR"
\`\`\`

### 3) その worktree に移動して作業

\`\`\`bash
cd ".worktrees/\$TOPIC_DIR"
git status
\`\`\`

## 注意事項

- 同じファイルを複数 worktree で同時に触らない（衝突が起きやすい）
- 共有リソース（DB/ポート/ストレージパス）は worktree ごとに分けるか、起動は1つに絞る
- Python venv は worktree ごとに作る（共有すると依存やパスが壊れやすい）
