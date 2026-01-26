#!/bin/bash
# commit-msg hook: Conventional Commits 形式を強制
# Migrated from .githooks/commit-msg

commit_msg_file="$1"
commit_msg=$(cat "$commit_msg_file")

# Conventional Commits パターン
pattern="^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .{1,72}"

if ! echo "$commit_msg" | grep -Eq "$pattern"; then
    echo ""
    echo "⚠️  コミットメッセージが Conventional Commits 形式ではありません"
    echo ""
    echo "正しい形式:"
    echo "  <type>(<scope>): <subject>"
    echo ""
    echo "例:"
    echo "  feat(llm): Gemini API クライアント実装"
    echo "  fix(validator): JSON末尾カンマの処理修正"
    echo "  docs(api): エンドポイント仕様を追記"
    echo ""
    echo "type: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
    echo ""
    exit 1
fi

exit 0
