#!/bin/bash
# =============================================================================
# SEO記事自動生成システム - 停止スクリプト
# =============================================================================
#
# 使用方法:
#   ./scripts/stop.sh          # 全サービス停止
#   ./scripts/stop.sh --all    # 全サービス停止 + ボリューム削除
#   ./scripts/stop.sh --docker # Dockerコンテナのみ停止
#   ./scripts/stop.sh --apps   # アプリケーションプロセスのみ停止
#

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# プロジェクトルートに移動
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ヘッダー表示
echo ""
echo "============================================================"
echo "  SEO記事自動生成システム - 停止スクリプト"
echo "============================================================"
echo ""

# オプション解析
STOP_ALL=false
STOP_DOCKER_ONLY=false
STOP_APPS_ONLY=false
DELETE_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            STOP_ALL=true
            DELETE_VOLUMES=true
            shift
            ;;
        --docker)
            STOP_DOCKER_ONLY=true
            shift
            ;;
        --apps)
            STOP_APPS_ONLY=true
            shift
            ;;
        --volumes)
            DELETE_VOLUMES=true
            shift
            ;;
        -h|--help)
            echo "使用方法: $0 [オプション]"
            echo ""
            echo "オプション:"
            echo "  --all      全サービス停止 + ボリューム削除"
            echo "  --docker   Dockerコンテナのみ停止"
            echo "  --apps     アプリケーションプロセスのみ停止"
            echo "  --volumes  Dockerボリュームも削除"
            echo "  -h, --help このヘルプを表示"
            exit 0
            ;;
        *)
            error "不明なオプション: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# アプリケーションプロセスの停止
# =============================================================================
stop_app_processes() {
    info "アプリケーションプロセスを停止中..."

    # uvicorn (API サーバー) の停止
    if pgrep -f "uvicorn apps.api.main:app" > /dev/null 2>&1; then
        pkill -f "uvicorn apps.api.main:app" 2>/dev/null || true
        success "API サーバー (uvicorn) を停止しました"
    else
        info "API サーバーは起動していません"
    fi

    # Temporal Worker の停止
    if pgrep -f "python -m apps.worker.main" > /dev/null 2>&1; then
        pkill -f "python -m apps.worker.main" 2>/dev/null || true
        success "Temporal Worker を停止しました"
    else
        info "Temporal Worker は起動していません"
    fi

    # Next.js 開発サーバーの停止
    if pgrep -f "next dev" > /dev/null 2>&1; then
        pkill -f "next dev" 2>/dev/null || true
        success "Next.js 開発サーバーを停止しました"
    elif pgrep -f "node.*apps/ui" > /dev/null 2>&1; then
        pkill -f "node.*apps/ui" 2>/dev/null || true
        success "Next.js サーバーを停止しました"
    else
        info "Next.js サーバーは起動していません"
    fi

    # LangGraph Studio の停止
    if pgrep -f "langgraph dev" > /dev/null 2>&1; then
        pkill -f "langgraph dev" 2>/dev/null || true
        success "LangGraph Studio を停止しました"
    else
        info "LangGraph Studio は起動していません"
    fi

    # ポート 3000, 8000 を使用しているプロセスの確認
    for port in 3000 8000 2024; do
        if lsof -i :$port > /dev/null 2>&1; then
            warn "ポート $port がまだ使用中です"
            lsof -i :$port | head -3
        fi
    done
}

# =============================================================================
# Dockerコンテナの停止
# =============================================================================
stop_docker_containers() {
    info "Dockerコンテナを停止中..."

    if ! command -v docker &> /dev/null; then
        warn "Docker がインストールされていません"
        return
    fi

    # docker compose で停止
    if [ -f "docker-compose.yml" ]; then
        if $DELETE_VOLUMES; then
            docker compose down -v 2>/dev/null || true
            success "Dockerコンテナとボリュームを削除しました"
        else
            docker compose down 2>/dev/null || true
            success "Dockerコンテナを停止しました"
        fi
    else
        warn "docker-compose.yml が見つかりません"
    fi

    # 残っているコンテナの確認
    remaining=$(docker ps --filter "name=seo-" --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$remaining" ]; then
        warn "以下のコンテナがまだ起動しています:"
        echo "$remaining"
    fi
}

# =============================================================================
# メイン処理
# =============================================================================

if $STOP_DOCKER_ONLY; then
    stop_docker_containers
elif $STOP_APPS_ONLY; then
    stop_app_processes
else
    # デフォルト: 両方停止
    stop_app_processes
    echo ""
    stop_docker_containers
fi

# =============================================================================
# 完了メッセージ
# =============================================================================
echo ""
echo "============================================================"
success "停止処理が完了しました"
echo "============================================================"
echo ""

# ポート使用状況の最終確認
info "ポート使用状況:"
for port in 3000 5432 7233 8000 8080 9000 9001; do
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "  ${YELLOW}●${NC} ポート $port: 使用中"
    else
        echo -e "  ${GREEN}○${NC} ポート $port: 空き"
    fi
done

echo ""
info "再起動するには:"
echo "  ./scripts/bootstrap.sh    # フル起動"
echo "  docker compose up -d      # Dockerのみ起動"
echo ""
