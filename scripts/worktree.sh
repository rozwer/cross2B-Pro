#!/bin/bash
# 並列開発用ヘルパースクリプト
# Usage: ./scripts/worktree.sh <command> [args]

set -euo pipefail

WORKTREE_DIR=".worktrees"
BASE_BRANCH="develop"

# 色付け
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# developブランチの最新化
sync_develop() {
    log_info "developブランチを最新化..."
    git fetch origin
    git checkout develop
    git pull origin develop
    log_success "develop最新化完了"
}

# worktree 新規作成
create() {
    local topic="${1:-}"
    local prefix="${2:-feat}"
    
    if [[ -z "$topic" ]]; then
        log_error "Usage: $0 create <topic> [prefix]"
        log_info "Example: $0 create llm-gemini feat"
        exit 1
    fi
    
    local branch="${prefix}/${topic}"
    local worktree_path="${WORKTREE_DIR}/${topic}"
    
    # developを最新化
    sync_develop
    
    # worktreeディレクトリ作成
    mkdir -p "$WORKTREE_DIR"
    
    # 既存チェック
    if [[ -d "$worktree_path" ]]; then
        log_error "Worktree already exists: $worktree_path"
        exit 1
    fi
    
    # worktree + ブランチ作成
    log_info "Creating worktree: $worktree_path (branch: $branch)"
    git worktree add -b "$branch" "$worktree_path" "$BASE_BRANCH"
    
    log_success "Worktree created!"
    echo ""
    echo "次のステップ:"
    echo "  cd $worktree_path"
    echo "  # 実装開始"
}

# worktree 一覧表示（状態付き）
list() {
    echo ""
    echo "=== Worktree 一覧 ==="
    echo ""
    
    git worktree list --porcelain | while read -r line; do
        if [[ $line == worktree* ]]; then
            local path="${line#worktree }"
            echo -e "${BLUE}📁 $path${NC}"
        elif [[ $line == branch* ]]; then
            local branch="${line#branch refs/heads/}"
            echo "   └── Branch: $branch"
        fi
    done
    
    echo ""
    
    # 各worktreeの変更状態
    if [[ -d "$WORKTREE_DIR" ]]; then
        echo "=== 変更状態 ==="
        for wt in "$WORKTREE_DIR"/*/; do
            if [[ -d "$wt" ]]; then
                local name=$(basename "$wt")
                local status=$(git -C "$wt" status --porcelain 2>/dev/null | head -3)
                if [[ -n "$status" ]]; then
                    echo -e "${YELLOW}⚠️  $name${NC}"
                    echo "$status" | sed 's/^/   /'
                else
                    echo -e "${GREEN}✓  $name${NC} (clean)"
                fi
            fi
        done
    fi
}

# worktree 削除
remove() {
    local topic="${1:-}"
    
    if [[ -z "$topic" ]]; then
        log_error "Usage: $0 remove <topic>"
        exit 1
    fi
    
    local worktree_path="${WORKTREE_DIR}/${topic}"
    
    if [[ ! -d "$worktree_path" ]]; then
        log_error "Worktree not found: $worktree_path"
        exit 1
    fi
    
    # 未コミットの変更確認
    local status=$(git -C "$worktree_path" status --porcelain 2>/dev/null)
    if [[ -n "$status" ]]; then
        log_warn "Uncommitted changes detected:"
        echo "$status"
        read -p "Continue? (y/N): " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            log_info "Aborted"
            exit 0
        fi
    fi
    
    # worktree 削除
    log_info "Removing worktree: $worktree_path"
    git worktree remove "$worktree_path" --force
    
    log_success "Worktree removed"
}

# 全worktreeのdevelopリベース
rebase_all() {
    log_info "Fetching origin..."
    git fetch origin
    
    for wt in "$WORKTREE_DIR"/*/; do
        if [[ -d "$wt" ]]; then
            local name=$(basename "$wt")
            log_info "Rebasing: $name"
            
            # 未コミットの変更がある場合はスキップ
            local status=$(git -C "$wt" status --porcelain 2>/dev/null)
            if [[ -n "$status" ]]; then
                log_warn "Skipping $name (uncommitted changes)"
                continue
            fi
            
            git -C "$wt" rebase origin/develop || {
                log_error "Rebase failed for $name. Aborting..."
                git -C "$wt" rebase --abort
            }
        fi
    done
    
    log_success "Rebase complete"
}

# smoke テスト実行
smoke() {
    local topic="${1:-}"
    local target_path="."
    
    if [[ -n "$topic" ]]; then
        target_path="${WORKTREE_DIR}/${topic}"
    fi
    
    log_info "Running smoke test in: $target_path"
    
    # Python環境チェック
    if [[ -f "$target_path/pyproject.toml" ]]; then
        log_info "Checking Python..."
        (cd "$target_path" && python -m py_compile apps/**/*.py 2>/dev/null) || log_warn "Python check failed"
    fi
    
    # 型チェック
    if command -v mypy &> /dev/null; then
        log_info "Running mypy..."
        (cd "$target_path" && mypy apps/ 2>/dev/null) || log_warn "mypy check failed"
    fi
    
    log_success "Smoke test complete"
}

# PRヘルパー（チェックリスト表示）
pr() {
    local topic="${1:-}"
    
    if [[ -z "$topic" ]]; then
        log_error "Usage: $0 pr <topic>"
        exit 1
    fi
    
    local worktree_path="${WORKTREE_DIR}/${topic}"
    local branch="feat/${topic}"
    
    echo ""
    echo "=== PR チェックリスト: $topic ==="
    echo ""
    
    # 変更ファイル
    echo "📝 変更ファイル:"
    git -C "$worktree_path" diff --stat "origin/develop...HEAD" 2>/dev/null || true
    echo ""
    
    # コミット一覧
    echo "📋 コミット一覧:"
    git -C "$worktree_path" log --oneline "origin/develop...HEAD" 2>/dev/null || true
    echo ""
    
    # チェックリスト
    echo "✅ マージ前チェックリスト:"
    echo "  [ ] smoke テスト通過"
    echo "  [ ] 型チェック通過 (mypy)"
    echo "  [ ] コードレビュー完了"
    echo "  [ ] 依存ブランチがマージ済み"
    echo ""
    
    # PRコマンド
    echo "🚀 PR作成:"
    echo "  gh pr create --base develop --head $branch --title \"feat: $topic\" --body \"\""
}

# 一括worktree作成（ROADMAPのStep用）
batch_create() {
    local step="${1:-}"
    
    case "$step" in
        "step1")
            log_info "Step 1: LLM クライアント群を作成..."
            create "llm-gemini"
            create "llm-openai"
            create "llm-anthropic"
            ;;
        "step3")
            log_info "Step 3: ツール群を作成..."
            create "tools-search"
            create "tools-fetch"
            create "tools-verify"
            create "tools-registry"
            ;;
        "step4")
            log_info "Step 4: 契約基盤を作成..."
            create "contract-state"
            create "contract-context"
            create "contract-adapter"
            ;;
        *)
            log_error "Usage: $0 batch <step1|step3|step4>"
            exit 1
            ;;
    esac
    
    log_success "Batch create complete"
    list
}

# ヘルプ
help() {
    cat << EOF
並列開発ヘルパースクリプト

Usage: $0 <command> [args]

Commands:
  create <topic> [prefix]   新規worktree作成 (default prefix: feat)
  list                      worktree一覧表示
  remove <topic>            worktree削除
  rebase                    全worktreeをdevelopでリベース
  smoke [topic]             smokeテスト実行
  pr <topic>                PRチェックリスト表示
  batch <step1|step3|step4> ROADMAPステップのworktree一括作成

Examples:
  $0 create llm-gemini            # feat/llm-gemini ブランチ + worktree作成
  $0 create security-patch hotfix # hotfix/security-patch ブランチ作成
  $0 batch step1                  # Step1の全worktree一括作成
  $0 list                         # 状態確認
  $0 remove llm-gemini            # 削除

EOF
}

# メイン
main() {
    local cmd="${1:-help}"
    shift || true
    
    case "$cmd" in
        create)    create "$@" ;;
        list)      list ;;
        remove)    remove "$@" ;;
        rebase)    rebase_all ;;
        smoke)     smoke "$@" ;;
        pr)        pr "$@" ;;
        batch)     batch_create "$@" ;;
        help|--help|-h) help ;;
        *)
            log_error "Unknown command: $cmd"
            help
            exit 1
            ;;
    esac
}

main "$@"
