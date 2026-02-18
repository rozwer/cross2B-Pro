-- Migration: Create review_requests table
-- Date: 2026-01-19
-- Description: Store review requests and results in DB instead of fetching from GitHub API

-- Create review_requests table
CREATE TABLE IF NOT EXISTS review_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step VARCHAR(20) NOT NULL,

    -- Issue information (from GitHub)
    issue_number INTEGER,
    issue_url VARCHAR(500),
    issue_state VARCHAR(20),  -- open, closed

    -- Review status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending: not requested
    -- in_progress: issue created, waiting for review
    -- completed: review completed with result
    -- closed_without_result: issue closed without result

    -- Review result
    review_type VARCHAR(20),  -- all, fact, seo, quality
    review_result JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    CONSTRAINT uq_review_request_run_step_type UNIQUE(run_id, step, review_type)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_review_requests_run_id ON review_requests(run_id);
CREATE INDEX IF NOT EXISTS idx_review_requests_status ON review_requests(status);

-- Add check constraint for status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'valid_review_status'
    ) THEN
        ALTER TABLE review_requests ADD CONSTRAINT valid_review_status
        CHECK (status IN ('pending', 'in_progress', 'completed', 'closed_without_result'));
    END IF;
END $$;

-- Add trigger to update updated_at
CREATE OR REPLACE FUNCTION update_review_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_review_requests_updated_at ON review_requests;
CREATE TRIGGER update_review_requests_updated_at
    BEFORE UPDATE ON review_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_review_requests_updated_at();

-- Comment on table
COMMENT ON TABLE review_requests IS 'Stores review requests and results for article steps';
COMMENT ON COLUMN review_requests.status IS 'pending=not requested, in_progress=waiting for review, completed=has result, closed_without_result=issue closed without result';
