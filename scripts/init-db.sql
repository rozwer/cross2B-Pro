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
-- Tenant Management Tables
-- =============================================================================

-- Tenants table: manages multi-tenant configuration
CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    database_url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert development tenant (uses same DB for simplicity)
INSERT INTO tenants (id, name, database_url, is_active)
VALUES (
    'dev-tenant-001',
    'Development Tenant',
    'postgresql+asyncpg://seo:seo_password@postgres:5432/seo_articles',
    true
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- Core Tables
-- =============================================================================

-- Runs table: tracks workflow executions
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    config JSONB NOT NULL DEFAULT '{}',
    input_data JSONB,
    current_step VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    error_code VARCHAR(100),
    step11_state JSONB,
    -- GitHub integration columns
    github_repo_url TEXT,                    -- e.g., https://github.com/owner/repo
    github_dir_path TEXT,                    -- e.g., keyword_20260114_123456
    -- GitHub Fix Guidance columns
    last_resumed_step VARCHAR(64),           -- last step resumed via /resume API
    fix_issue_number INTEGER,                -- GitHub issue number for fix guidance

    CONSTRAINT valid_status CHECK (status IN (
        'pending', 'workflow_starting', 'running', 'paused', 'waiting_approval',
        'waiting_step1_approval', 'waiting_image_input',
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
    error_code VARCHAR(50),  -- ErrorCategory enum value (RETRYABLE, NON_RETRYABLE, etc.)
    error_message TEXT,
    retry_count INT DEFAULT 0,

    CONSTRAINT valid_step_status CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'skipped'
    )),
    -- UNIQUE constraint for UPSERT operations
    CONSTRAINT uq_steps_run_step UNIQUE (run_id, step_name)
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

-- Audit logs table: immutable audit trail with chain hashing
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(128) NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    prev_hash VARCHAR(64),
    entry_hash VARCHAR(64) NOT NULL
);

-- Events table: audit log for all actions
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES steps(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    actor VARCHAR(255),
    tenant_id VARCHAR(64),
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

-- Error logs table: detailed error tracking for diagnostics
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step_id UUID REFERENCES steps(id) ON DELETE SET NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'activity',
    error_category VARCHAR(32) NOT NULL,
    error_type VARCHAR(128) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB,
    attempt INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_error_source CHECK (source IN (
        'llm', 'tool', 'validation', 'storage', 'activity', 'api'
    )),
    CONSTRAINT valid_error_category CHECK (error_category IN (
        'retryable', 'non_retryable', 'validation_fail'
    ))
);

-- Diagnostic reports table: LLM-generated failure analysis
CREATE TABLE IF NOT EXISTS diagnostic_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    root_cause_analysis TEXT NOT NULL,
    recommended_actions JSONB NOT NULL,
    resume_step VARCHAR(64),
    confidence_score DECIMAL(3, 2),
    llm_provider VARCHAR(32) NOT NULL,
    llm_model VARCHAR(128) NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    latency_ms INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Hearing templates table: reusable workflow input configurations
CREATE TABLE IF NOT EXISTS hearing_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(64) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_hearing_template_tenant_name UNIQUE (tenant_id, name)
);

-- GitHub sync status table: tracks sync between GitHub and MinIO
CREATE TABLE IF NOT EXISTS github_sync_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step VARCHAR(20) NOT NULL,
    github_sha VARCHAR(40),              -- Git commit SHA
    minio_digest VARCHAR(64),            -- SHA256 digest of MinIO content
    synced_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    CONSTRAINT valid_sync_status CHECK (status IN (
        'pending', 'synced', 'diverged', 'github_only', 'minio_only'
    )),
    CONSTRAINT uq_github_sync_run_step UNIQUE (run_id, step)
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

CREATE INDEX IF NOT EXISTS idx_error_logs_run_id ON error_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_step_id ON error_logs(step_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_source ON error_logs(source);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_diagnostic_reports_run_id ON diagnostic_reports(run_id);

CREATE INDEX IF NOT EXISTS idx_hearing_templates_tenant_id ON hearing_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_hearing_templates_name ON hearing_templates(name);

CREATE INDEX IF NOT EXISTS idx_github_sync_status_run_id ON github_sync_status(run_id);
CREATE INDEX IF NOT EXISTS idx_github_sync_status_status ON github_sync_status(status);
CREATE INDEX IF NOT EXISTS idx_runs_github_repo ON runs(github_repo_url) WHERE github_repo_url IS NOT NULL;

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

-- Apply trigger to hearing_templates table
DROP TRIGGER IF EXISTS update_hearing_templates_updated_at ON hearing_templates;
CREATE TRIGGER update_hearing_templates_updated_at
    BEFORE UPDATE ON hearing_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- LLM Provider & Model Tables
-- =============================================================================

-- LLM providers
CREATE TABLE IF NOT EXISTS llm_providers (
    id VARCHAR(32) PRIMARY KEY,
    display_name VARCHAR(64) NOT NULL,
    api_base_url TEXT,
    is_active BOOLEAN DEFAULT true NOT NULL
);

-- LLM models
CREATE TABLE IF NOT EXISTS llm_models (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(32) NOT NULL REFERENCES llm_providers(id),
    model_name VARCHAR(128) NOT NULL,
    model_class VARCHAR(32) NOT NULL,
    cost_per_1k_input_tokens NUMERIC(10, 6),
    cost_per_1k_output_tokens NUMERIC(10, 6),
    is_active BOOLEAN DEFAULT true NOT NULL
);

-- Step-to-LLM default mapping
CREATE TABLE IF NOT EXISTS step_llm_defaults (
    step VARCHAR(64) PRIMARY KEY,
    provider_id VARCHAR(32) NOT NULL REFERENCES llm_providers(id),
    model_class VARCHAR(32) NOT NULL
);

-- =============================================================================
-- Help Contents
-- =============================================================================

CREATE TABLE IF NOT EXISTS help_contents (
    id SERIAL PRIMARY KEY,
    help_key VARCHAR(128) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(64),
    display_order INTEGER DEFAULT 0 NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_help_contents_key ON help_contents(help_key);
CREATE INDEX IF NOT EXISTS idx_help_contents_category ON help_contents(category);

-- =============================================================================
-- API Settings (per tenant)
-- =============================================================================

CREATE TABLE IF NOT EXISTS api_settings (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    service VARCHAR(32) NOT NULL,
    api_key_encrypted TEXT,
    default_model VARCHAR(128),
    config JSONB,
    is_active BOOLEAN DEFAULT true NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_api_settings_tenant_service UNIQUE (tenant_id, service)
);

CREATE INDEX IF NOT EXISTS idx_api_settings_tenant ON api_settings(tenant_id);

-- =============================================================================
-- Review Requests
-- =============================================================================

CREATE TABLE IF NOT EXISTS review_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    step VARCHAR(20) NOT NULL,
    issue_number INTEGER,
    issue_url VARCHAR(500),
    issue_state VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_review_requests_run_id ON review_requests(run_id);
CREATE INDEX IF NOT EXISTS idx_review_requests_status ON review_requests(status);

-- =============================================================================
-- Initial Data: LLM Providers & Models
-- =============================================================================

-- Providers
INSERT INTO llm_providers (id, display_name, is_active) VALUES
    ('gemini',    'Google Gemini',    true),
    ('openai',    'OpenAI',           true),
    ('anthropic', 'Anthropic Claude', true)
ON CONFLICT (id) DO NOTHING;

-- Models (latest defaults)
INSERT INTO llm_models (provider_id, model_name, model_class, is_active) VALUES
    -- Gemini
    ('gemini',    'gemini-3-pro-preview',          'pro',      true),
    ('gemini',    'gemini-3-flash-preview',        'standard', true),
    ('gemini',    'gemini-2.5-flash',              'standard', true),
    ('gemini',    'gemini-2.5-pro',                'pro',      true),
    -- OpenAI
    ('openai',    'gpt-5.2',                       'standard', true),
    ('openai',    'gpt-5.2-pro',                   'pro',      true),
    ('openai',    'gpt-5.2-codex',                 'pro',      true),
    ('openai',    'gpt-5.1',                       'standard', true),
    ('openai',    'gpt-5.1-codex',                 'pro',      true),
    ('openai',    'gpt-5.1-codex-mini',            'standard', true),
    ('openai',    'gpt-5-codex',                   'pro',      true),
    -- Anthropic
    ('anthropic', 'claude-opus-4-6',               'pro',      true),
    ('anthropic', 'claude-sonnet-4-5-20250929',    'standard', true),
    ('anthropic', 'claude-haiku-4-5',              'standard', true),
    ('anthropic', 'claude-opus-4-5-20251124',      'pro',      true),
    ('anthropic', 'claude-sonnet-4-20250514',      'standard', true)
ON CONFLICT DO NOTHING;

COMMIT;
