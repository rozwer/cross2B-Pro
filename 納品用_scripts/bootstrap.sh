#!/bin/bash
# =============================================================================
# Bootstrap Script - Initialize and start all services
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=============================================="
echo "SEO Article Generator - Bootstrap"
echo "=============================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "[ERROR] .env file not found!"
    echo "Please create .env from .env.example:"
    echo "  cp .env.example .env"
    echo "Then fill in the required API keys."
    exit 1
fi

# Load environment variables
set -a
source .env
set +a

# Check required environment variables
REQUIRED_VARS=()
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo ""
    echo "[WARNING] Some environment variables are not set:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "The system will start but some features may not work."
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running. Please start Docker first."
    exit 1
fi

echo ""
echo "[1/4] Building Docker images..."
docker compose build

echo ""
echo "[2/4] Starting infrastructure services..."
docker compose up -d postgres minio temporal

echo ""
echo "[3/4] Waiting for services to be healthy..."
echo "  - Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-seo}" > /dev/null 2>&1; do
    sleep 1
done
echo "    PostgreSQL is ready!"

echo "  - Waiting for MinIO..."
until docker compose exec -T minio mc ready local > /dev/null 2>&1; do
    sleep 1
done
echo "    MinIO is ready!"

echo "  - Waiting for Temporal..."
TEMPORAL_RETRIES=30
TEMPORAL_COUNT=0
until docker compose exec -T temporal tctl --address temporal:7233 cluster health > /dev/null 2>&1; do
    sleep 2
    TEMPORAL_COUNT=$((TEMPORAL_COUNT + 1))
    if [ $TEMPORAL_COUNT -ge $TEMPORAL_RETRIES ]; then
        echo "    [WARNING] Temporal health check timed out, continuing anyway..."
        break
    fi
done
if [ $TEMPORAL_COUNT -lt $TEMPORAL_RETRIES ]; then
    echo "    Temporal is ready!"
fi

echo ""
echo "[4/4] Starting application services..."
docker compose up -d

echo ""
echo "=============================================="
echo "Bootstrap complete!"
echo "=============================================="
echo ""
echo "Services:"
echo "  - API:         http://localhost:${API_PORT:-8000}"
echo "  - UI:          http://localhost:${UI_PORT:-3000}"
echo "  - Temporal UI: http://localhost:${TEMPORAL_UI_PORT:-8080}"
echo "  - MinIO:       http://localhost:${MINIO_CONSOLE_PORT:-9001}"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
echo ""
echo "To stop all services:"
echo "  docker compose down"
echo ""
