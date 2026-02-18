-- Migration: Add error_code column to steps table
-- Date: 2026-01-12
-- Description: Adds error_code column to store ErrorCategory enum value for better error classification

-- Add error_code column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'steps' AND column_name = 'error_code'
    ) THEN
        ALTER TABLE steps ADD COLUMN error_code VARCHAR(50);
        COMMENT ON COLUMN steps.error_code IS 'ErrorCategory enum value (RETRYABLE, NON_RETRYABLE, VALIDATION_FAIL, etc.)';
    END IF;
END $$;
