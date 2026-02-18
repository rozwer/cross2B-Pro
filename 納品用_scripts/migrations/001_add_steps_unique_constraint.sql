-- =============================================================================
-- Migration 001: Add unique constraint on steps(run_id, step_name)
-- =============================================================================
-- This constraint is required for ON CONFLICT (UPSERT) operations in
-- /api/internal/steps/update endpoint.
--
-- The constraint was defined in init-db.sql but may be missing if the database
-- was created before the constraint was added.
--
-- Run: docker compose exec postgres psql -U seo -d seo_articles -f /path/to/this/file
-- Or:  cat scripts/migrations/001_add_steps_unique_constraint.sql | docker compose exec -T postgres psql -U seo -d seo_articles
-- =============================================================================

-- Add unique constraint if not exists
-- Note: PostgreSQL doesn't have "ADD CONSTRAINT IF NOT EXISTS", so we check first
DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_steps_run_step'
    ) THEN
        -- Check if index already exists (we created it manually)
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_steps_run_id_step_name'
        ) THEN
            -- Create as unique constraint (preferred)
            ALTER TABLE steps ADD CONSTRAINT uq_steps_run_step UNIQUE (run_id, step_name);
            RAISE NOTICE 'Added unique constraint uq_steps_run_step';
        ELSE
            -- Index exists, drop it and create proper constraint
            DROP INDEX idx_steps_run_id_step_name;
            ALTER TABLE steps ADD CONSTRAINT uq_steps_run_step UNIQUE (run_id, step_name);
            RAISE NOTICE 'Replaced index with unique constraint uq_steps_run_step';
        END IF;
    ELSE
        RAISE NOTICE 'Constraint uq_steps_run_step already exists';
    END IF;
END $$;

-- Verify
SELECT
    conname as constraint_name,
    contype as constraint_type
FROM pg_constraint
WHERE conrelid = 'steps'::regclass
  AND conname = 'uq_steps_run_step';
