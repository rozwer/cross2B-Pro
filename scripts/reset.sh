#!/bin/bash
# =============================================================================
# Reset Script - Stop all services and remove data
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=============================================="
echo "SEO Article Generator - Reset"
echo "=============================================="
echo ""
echo "[WARNING] This will:"
echo "  - Stop all containers"
echo "  - Remove all containers"
echo "  - Remove all volumes (database data, storage)"
echo "  - Remove all networks"
echo ""

read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "[1/3] Stopping all containers..."
docker compose down --remove-orphans

echo ""
echo "[2/3] Removing volumes..."
docker compose down -v

echo ""
echo "[3/3] Removing orphaned containers and networks..."
docker compose rm -f
docker network prune -f --filter "label=com.docker.compose.project=案件" 2>/dev/null || true

echo ""
echo "=============================================="
echo "Reset complete!"
echo "=============================================="
echo ""
echo "To start fresh, run:"
echo "  ./scripts/bootstrap.sh"
echo ""
