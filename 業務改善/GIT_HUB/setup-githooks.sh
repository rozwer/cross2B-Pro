#!/bin/bash
# Git Hooks セットアップスクリプト
# 使用方法: ./scripts/setup-githooks.sh

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# プロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$PROJECT_ROOT/.githooks"

echo ""
echo "🔧 Git Hooks セットアップを開始します..."
echo ""

# ===========================================
# 1. Git リポジトリの確認
# ===========================================
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}❌ Git リポジトリが見つかりません${NC}"
    echo "   $PROJECT_ROOT で git init を実行してください"
    exit 1
fi

echo -e "${GREEN}✓ Git リポジトリを確認${NC}"

# ===========================================
# 2. .githooks ディレクトリの作成
# ===========================================
if [ ! -d "$HOOKS_DIR" ]; then
    mkdir -p "$HOOKS_DIR"
    echo -e "${GREEN}✓ .githooks ディレクトリを作成${NC}"
else
    echo -e "${CYAN}ℹ .githooks ディレクトリは既に存在します${NC}"
fi

# ===========================================
# 3. hooks パスの設定
# ===========================================
CURRENT_HOOKS_PATH=$(git -C "$PROJECT_ROOT" config --get core.hooksPath 2>/dev/null || echo "")

if [ "$CURRENT_HOOKS_PATH" = ".githooks" ]; then
    echo -e "${CYAN}ℹ core.hooksPath は既に設定済みです${NC}"
else
    git -C "$PROJECT_ROOT" config core.hooksPath .githooks
    echo -e "${GREEN}✓ core.hooksPath を .githooks に設定${NC}"
fi

# ===========================================
# 4. 依存ツールの確認
# ===========================================
echo ""
echo "📦 依存ツールを確認中..."

check_tool() {
    local tool=$1
    local install_hint=$2
    if command -v "$tool" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $tool"
        return 0
    else
        echo -e "  ${YELLOW}⚠${NC} $tool が見つかりません"
        echo -e "    ${CYAN}→ $install_hint${NC}"
        return 1
    fi
}

MISSING_TOOLS=0

check_tool "ruff" "uv add ruff または pip install ruff" || MISSING_TOOLS=1
check_tool "mypy" "uv add mypy または pip install mypy" || MISSING_TOOLS=1
check_tool "bunx" "curl -fsSL https://bun.sh/install | bash" || MISSING_TOOLS=1
check_tool "uv" "curl -LsSf https://astral.sh/uv/install.sh | sh" || MISSING_TOOLS=1

if [ $MISSING_TOOLS -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}⚠ 一部のツールが見つかりません。該当するチェックはスキップされます${NC}"
fi

# ===========================================
# 5. フックファイルの確認と権限設定
# ===========================================
echo ""
echo "📝 フックファイルを確認中..."

HOOKS=("pre-commit" "prepare-commit-msg" "commit-msg" "post-checkout" "post-merge" "pre-push")

for hook in "${HOOKS[@]}"; do
    if [ -f "$HOOKS_DIR/$hook" ]; then
        chmod +x "$HOOKS_DIR/$hook"
        echo -e "  ${GREEN}✓${NC} $hook"
    else
        echo -e "  ${YELLOW}⚠${NC} $hook が見つかりません"
    fi
done

# ===========================================
# 6. 動作テスト
# ===========================================
echo ""
echo "🧪 動作テストを実行中..."

# pre-commit のテスト（構文チェックのみ）
if [ -f "$HOOKS_DIR/pre-commit" ]; then
    if bash -n "$HOOKS_DIR/pre-commit" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} pre-commit 構文OK"
    else
        echo -e "  ${RED}✗${NC} pre-commit 構文エラー"
    fi
fi

# commit-msg のテスト
if [ -f "$HOOKS_DIR/commit-msg" ]; then
    if bash -n "$HOOKS_DIR/commit-msg" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} commit-msg 構文OK"
    else
        echo -e "  ${RED}✗${NC} commit-msg 構文エラー"
    fi
fi

# ===========================================
# 完了
# ===========================================
echo ""
echo -e "${GREEN}✅ Git Hooks のセットアップが完了しました${NC}"
echo ""
echo "設定されたフック:"
echo "  • pre-commit      - コード品質チェック（lint, format, 秘密情報検出）"
echo "  • prepare-commit-msg - ブランチ名からプレフィックス自動生成"
echo "  • commit-msg      - Conventional Commits 形式を強制"
echo "  • post-checkout   - 依存更新通知"
echo "  • post-merge      - 依存自動更新・キャッシュクリア"
echo "  • pre-push        - 保護ブランチ・WIP検出・smoke テスト"
echo ""
echo "詳細: docs/guides/GIT_HOOKS.md"
echo ""

# ===========================================
# オプション: .gitignore への追加確認
# ===========================================
if [ -f "$PROJECT_ROOT/.gitignore" ]; then
    if ! grep -q "^\.githooks/$" "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
        echo -e "${CYAN}ℹ .githooks/ は .gitignore に含まれていません（チームで共有されます）${NC}"
    fi
fi

exit 0
