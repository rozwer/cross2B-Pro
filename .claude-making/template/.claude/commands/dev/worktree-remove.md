---
description: worktree を安全に削除する（ローカルのみ）
allowed-tools: Bash
---

## 1) 対象 worktree がクリーンか確認

\`\`\`bash
cd ".worktrees/\$TOPIC_DIR"
git status
\`\`\`

## 2) worktree を削除

\`\`\`bash
cd - >/dev/null
git worktree remove ".worktrees/\$TOPIC_DIR"
\`\`\`

## 3) 後片付け（必要なら）

\`\`\`bash
git worktree prune
\`\`\`

## 注意事項

- 削除前に必ず \`git status\` でコミット漏れがないか確認
- リモートブランチは削除されない（必要なら別途削除）
