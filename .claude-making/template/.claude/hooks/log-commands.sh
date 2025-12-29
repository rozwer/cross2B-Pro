#!/bin/bash
# PreToolUse hook: Bash コマンドのログ記録

# ログディレクトリ
LOG_DIR="${CLAUDE_PROJECT_DIR}/.claude/logs"
mkdir -p "$LOG_DIR"

# ログファイル（日付ごと）
LOG_FILE="$LOG_DIR/commands-$(date +%Y-%m-%d).log"

# 標準入力からツール情報を読み取り
INPUT=$(cat)

# Bash コマンドを抽出してログ
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
if [ -n "$COMMAND" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $COMMAND" >> "$LOG_FILE"
fi

# 常に許可（ログ記録のみ）
exit 0