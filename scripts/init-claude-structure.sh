#!/usr/bin/env bash
#
# .claude ディレクトリ構造を初期化するスクリプト
# ファイルは作成せず、ディレクトリ構造のみを作成
#
# Usage:
#   ./scripts/init-claude-structure.sh [target_dir]
#
# Arguments:
#   target_dir  - 対象ディレクトリ（デフォルト: カレントディレクトリ）
#

set -euo pipefail

# 色付き出力
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 対象ディレクトリ
TARGET_DIR="${1:-.}"
CLAUDE_DIR="${TARGET_DIR}/.claude"

echo -e "${BLUE}Creating .claude directory structure in: ${TARGET_DIR}${NC}"
echo ""

# ディレクトリ作成関数
create_dir() {
    local dir="$1"
    local desc="$2"
    mkdir -p "$dir"
    echo -e "${GREEN}[+]${NC} ${dir#$TARGET_DIR/} - ${desc}"
}

# メインディレクトリ
create_dir "$CLAUDE_DIR" "Claude Code 設定ルート"

# agents/ - サブエージェント定義
create_dir "$CLAUDE_DIR/agents" "サブエージェント定義（Task tool で呼び出す専門エージェント）"

# commands/ - スラッシュコマンド
create_dir "$CLAUDE_DIR/commands" "スラッシュコマンド定義（/command で呼び出すショートカット）"
create_dir "$CLAUDE_DIR/commands/dev" "開発環境の起動・停止・確認系"
create_dir "$CLAUDE_DIR/commands/debug" "デバッグ・調査系"
create_dir "$CLAUDE_DIR/commands/review" "レビュー系"

# hooks/ - フック定義
create_dir "$CLAUDE_DIR/hooks" "フック定義（イベントに応じて実行されるスクリプト）"

# rules/ - 詳細ルール
create_dir "$CLAUDE_DIR/rules" "詳細ルール定義（CLAUDE.md から参照される補足ルール）"

# skills/ - スキル定義
create_dir "$CLAUDE_DIR/skills" "スキル定義（特定タスク用のナレッジ＋手順）"

# .gitkeep ファイルを空ディレクトリに配置（任意）
for dir in "$CLAUDE_DIR"/*/; do
    if [ -d "$dir" ] && [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        touch "${dir}.gitkeep"
    fi
done
# commands のサブディレクトリにも
for dir in "$CLAUDE_DIR"/commands/*/; do
    if [ -d "$dir" ] && [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        touch "${dir}.gitkeep"
    fi
done

echo ""
echo -e "${BLUE}Directory structure created:${NC}"
echo ""
tree -a "$CLAUDE_DIR" 2>/dev/null || find "$CLAUDE_DIR" -type d | sort | sed 's|[^/]*/|  |g'

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "Next steps:"
echo "  1. Create CLAUDE.md        - Project instructions (highest priority)"
echo "  2. Create settings.json    - Tool permissions"
echo "  3. Add agents/*.md         - Specialized sub-agents"
echo "  4. Add commands/*/*.md     - Slash commands"
echo "  5. Add rules/*.md          - Detailed rules"
echo "  6. Add skills/*/SKILL.md   - Task-specific skills"
