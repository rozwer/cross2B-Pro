#!/bin/bash
# Clone a run for testing purposes
# Usage: ./scripts/clone_run_for_testing.sh [count]
# Default: creates 5 clones

set -e

SOURCE_RUN_ID="d666c9f8-85b9-4caa-b190-7069c5afa5ce"
TENANT_ID="dev-tenant-001"
COUNT=${1:-5}

echo "Creating $COUNT clones of run $SOURCE_RUN_ID..."

# Generate SQL for cloning
docker exec seo-postgres psql -U seo -d seo_articles << 'EOSQL'

-- Function to clone a run
CREATE OR REPLACE FUNCTION clone_run_for_testing(
    source_run_id UUID,
    tenant_id TEXT
) RETURNS UUID AS $$
DECLARE
    new_run_id UUID;
    source_config JSONB;
    step_rec RECORD;
    new_step_id UUID;
BEGIN
    -- Generate new run ID
    new_run_id := uuid_generate_v4();

    -- Get source config
    SELECT config INTO source_config FROM runs WHERE id = source_run_id;

    -- Insert new run (step10 completed, waiting for step11)
    INSERT INTO runs (id, tenant_id, status, current_step, config, created_at, updated_at)
    SELECT
        new_run_id,
        tenant_id,
        'waiting_image_input',
        'waiting_image_generation',
        source_config,
        NOW(),
        NOW()
    FROM runs WHERE id = source_run_id;

    -- Clone steps (except step11)
    FOR step_rec IN
        SELECT step_name, status, started_at, completed_at
        FROM steps
        WHERE run_id = source_run_id AND step_name != 'step11'
    LOOP
        new_step_id := uuid_generate_v4();
        INSERT INTO steps (id, run_id, step_name, status, started_at, completed_at, retry_count)
        VALUES (
            new_step_id,
            new_run_id,
            step_rec.step_name,
            step_rec.status,
            step_rec.started_at,
            step_rec.completed_at,
            0
        );
    END LOOP;

    RETURN new_run_id;
END;
$$ LANGUAGE plpgsql;

EOSQL

# Create clones
for i in $(seq 1 $COUNT); do
    NEW_ID=$(docker exec seo-postgres psql -U seo -d seo_articles -t -c \
        "SELECT clone_run_for_testing('$SOURCE_RUN_ID', '$TENANT_ID');")
    NEW_ID=$(echo $NEW_ID | tr -d ' ')

    echo "Created clone $i: $NEW_ID"

    # Copy artifacts in MinIO
    docker exec seo-minio mc cp -r \
        local/seo-gen-artifacts/tenants/$TENANT_ID/runs/$SOURCE_RUN_ID/ \
        local/seo-gen-artifacts/tenants/$TENANT_ID/runs/$NEW_ID/ \
        2>/dev/null || echo "  (MinIO copy skipped - will use source artifacts)"
done

echo ""
echo "Done! Created $COUNT test runs."
echo ""
echo "List new runs:"
docker exec seo-postgres psql -U seo -d seo_articles -c \
    "SELECT id, status, current_step, created_at FROM runs WHERE tenant_id = '$TENANT_ID' ORDER BY created_at DESC LIMIT $((COUNT + 2));"
