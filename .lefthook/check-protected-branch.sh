#!/bin/bash
# pre-push hook: 保護ブランチへの直接push禁止
# Migrated from .githooks/pre-push

# 色定義
RED='\033[0;31m'
NC='\033[0m'

# 現在のブランチ
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)

# 保護ブランチ
PROTECTED_BRANCHES=("main" "master")

for branch in "${PROTECTED_BRANCHES[@]}"; do
    if [[ "$CURRENT_BRANCH" == "$branch" ]]; then
        echo -e "${RED}⚠️  直接 $branch への push は禁止されています${NC}"
        echo ""
        echo "正しいワークフロー:"
        echo "  1. ./scripts/worktree.sh create <topic>"
        echo "  2. feature ブランチで作業"
        echo "  3. PR を作成してマージ"
        echo ""
        echo "緊急時の回避（非推奨）:"
        echo "  git push --no-verify"
        echo ""
        exit 1
    fi
done

exit 0
