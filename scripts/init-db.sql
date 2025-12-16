-- =============================================================================
-- Database Initialization Script
-- =============================================================================
-- This script runs when PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database for Temporal (if not using separate DB)
-- Note: Temporal auto-setup image handles its own schema

-- =============================================================================
-- Core Tables
-- =============================================================================

-- Runs table: tracks workflow executions
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    config JSONB NOT NULL DEFAULT '{}',
    input_data JSONB,
    current_step VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,

    CONSTRAINT valid_status CHECK (status IN (
        'pending', 'running', 'waiting_approval',
        'completed', 'failed', 'cancelled'
    ))
);

-- Steps table: tracks individual workflow steps
CREATE TABLE IF NOT EXISTS steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INT DEFAULT 0,

    CONSTRAINT valid_step_status CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'skipped'
    ))
);

-- Attempts table: tracks step execution attempts
CREATE TABLE IF NOT EXISTS attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    step_id UUID NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
    attempt_num INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    input_digest VARCHAR(64),
    output_digest VARCHAR(64),
    error_message TEXT,
    metrics JSONB,

    UNIQUE(step_id, attempt_num)
);

-- Artifacts table: tracks generated outputs
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES steps(id) ON DELETE SET NULL,
    artifact_type VARCHAR(100) NOT NULL,
    ref_path TEXT NOT NULL,
    digest VARCHAR(64) NOT NULL,
    content_type VARCHAR(100),
    size_bytes BIGINT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Events table: audit log for all actions
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES steps(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    actor VARCHAR(255),
    tenant_id UUID,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Prompts table: versioned prompt templates
CREATE TABLE IF NOT EXISTS prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    step_name VARCHAR(100) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(step_name, version)
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_runs_tenant_id ON runs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_steps_run_id ON steps(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_status ON steps(status);

CREATE INDEX IF NOT EXISTS idx_attempts_step_id ON attempts(step_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_step_id ON artifacts(step_id);

CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_tenant_id ON events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_prompts_step_name ON prompts(step_name);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(step_name, is_active) WHERE is_active = true;

-- =============================================================================
-- Functions
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to runs table
DROP TRIGGER IF EXISTS update_runs_updated_at ON runs;
CREATE TRIGGER update_runs_updated_at
    BEFORE UPDATE ON runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Initial Data
-- =============================================================================

-- Note: Prompt templates should be loaded from application code or separate migration
-- This ensures version control and proper deployment

COMMIT;
