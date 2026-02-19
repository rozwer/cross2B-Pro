#!/bin/bash
# cross2B-Pro 起動スクリプト
# 使い方: ./start.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

echo "=== cross2B-Pro 起動 ==="
echo "フォルダ: $PROJECT_DIR"

# 1. Docker コンテナ起動
echo ""
echo "[1/4] Docker コンテナ起動..."
cd "$PROJECT_DIR"
docker compose up -d postgres minio temporal temporal-ui
echo "✅ Docker コンテナ起動完了"

# 2. DBマイグレーション確認
echo ""
echo "[2/4] DB状態確認..."
export DATABASE_URL=postgresql+asyncpg://seo:seo_password@127.0.0.1:25432/seo_articles
export COMMON_DATABASE_URL=postgresql+asyncpg://seo:seo_password@127.0.0.1:25432/seo_articles
echo "✅ DB接続設定済み"

# 3. FastAPI起動
echo ""
echo "[3/4] API サーバー起動 (port 28000)..."
uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 28000 &
API_PID=$!
sleep 3
echo "✅ API サーバー起動 (PID: $API_PID)"

# 4. Temporal Worker起動
echo ""
echo "[4/4] Temporal Worker 起動..."
uv run python3 -m apps.worker.main &
WORKER_PID=$!
sleep 2
echo "✅ Worker 起動 (PID: $WORKER_PID)"

echo ""
echo "=== 起動完了 ==="
echo "  API:           http://localhost:28000"
echo "  API Docs:      http://localhost:28000/docs"
echo "  Temporal UI:   http://localhost:28080"
echo "  MinIO:         http://localhost:29001 (minioadmin/minioadmin)"
echo ""
echo "フロントエンドは別ターミナルで: cd apps/ui && npm run dev"
echo "  UI:            http://localhost:23000"
echo ""
echo "停止するには Ctrl+C"

# シグナルを受け取ってクリーンアップ
cleanup() {
    echo "停止中..."
    kill $API_PID $WORKER_PID 2>/dev/null
    docker compose down
    echo "停止完了"
    exit 0
}
trap cleanup INT TERM

# フォアグラウンドで待機
wait $API_PID
