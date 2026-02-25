#!/bin/bash
# =============================================================================
# Database Initialization Script
# Creates schema and loads seed data from dump files.
#
# Usage:
#   ./scripts/init-database.sh          # Normal: schema + seed
#   ./scripts/init-database.sh --reset  # Drop & recreate DB first
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load env
if [ -f .env ]; then
    set -a; source .env; set +a
fi

DB_USER="${POSTGRES_USER:-seo}"
DB_NAME="${POSTGRES_DB:-seo_articles}"
CONTAINER="seo-postgres"

SCHEMA_FILE="$SCRIPT_DIR/schema.sql"
SEED_FILE="$SCRIPT_DIR/seed.sql"

# ── Preflight checks ────────────────────────────
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[ERROR] Container '$CONTAINER' is not running."
    echo "  Run: docker compose up -d postgres"
    exit 1
fi

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "[ERROR] Schema file not found: $SCHEMA_FILE"
    exit 1
fi

if [ ! -f "$SEED_FILE" ]; then
    echo "[ERROR] Seed file not found: $SEED_FILE"
    exit 1
fi

echo "=============================================="
echo "SEO Article Generator - Database Init"
echo "=============================================="
echo "  Container: $CONTAINER"
echo "  Database:  $DB_NAME"
echo "  User:      $DB_USER"
echo ""

# ── Optional: reset database ────────────────────
if [ "$1" = "--reset" ]; then
    echo "[RESET] Dropping and recreating database '$DB_NAME'..."
    docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c "
        SELECT pg_terminate_backend(pid) FROM pg_stat_activity
        WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();
    " > /dev/null 2>&1 || true
    docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\";" 2>&1
    docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\";" 2>&1
    echo "  Database recreated."
    echo ""
fi

# ── Step 1: Apply schema ────────────────────────
echo "[1/2] Applying schema..."
docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$SCHEMA_FILE" > /dev/null 2>&1
echo "  Schema applied successfully."

# ── Step 2: Load seed data ──────────────────────
echo "[2/2] Loading seed data..."
docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" < "$SEED_FILE" > /dev/null 2>&1
echo "  Seed data loaded successfully."

# ── Verify ──────────────────────────────────────
echo ""
echo "Verification:"
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
    (SELECT count(*) FROM llm_providers)      AS providers,
    (SELECT count(*) FROM llm_models)         AS models,
    (SELECT count(*) FROM help_contents)      AS help_items,
    (SELECT count(*) FROM hearing_templates)  AS templates;
"

echo "=============================================="
echo "Database initialization complete!"
echo "=============================================="
