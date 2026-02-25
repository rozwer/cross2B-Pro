-- =============================================================================
-- Migration 004: Catch-up migration (全差分を一括適用)
-- =============================================================================
-- 数週間前のDBを最新のinit-db.sqlと同等にする包括マイグレーション。
-- 全操作がIF NOT EXISTSで冪等なので、何度実行しても安全。
--
-- 実行方法:
--   cat scripts/migrations/004_catchup_all.sql | docker compose exec -T postgres psql -U seo -d seo_articles
--
-- カバー範囲:
--   - runs テーブル: step11_state, github_*, last_resumed_step, fix_issue_number
--   - runs status制約: 新ステータス追加
--   - api_settings テーブル作成
--   - help_contents テーブル作成
--   - hearing_templates テーブル作成
--   - review_requests テーブル作成（migration 003 相当）
--   - steps unique制約 + error_code（migration 001-002 相当）
--   - llm_providers / llm_models シードデータ
--   - llm_models_id_seq 修正
-- =============================================================================

BEGIN;

-- ─── Extensions ───────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── runs: 新カラム追加 ───────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='step11_state') THEN
        ALTER TABLE runs ADD COLUMN step11_state JSONB;
        RAISE NOTICE 'Added runs.step11_state';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='github_repo_url') THEN
        ALTER TABLE runs ADD COLUMN github_repo_url TEXT;
        RAISE NOTICE 'Added runs.github_repo_url';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='github_dir_path') THEN
        ALTER TABLE runs ADD COLUMN github_dir_path TEXT;
        RAISE NOTICE 'Added runs.github_dir_path';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='last_resumed_step') THEN
        ALTER TABLE runs ADD COLUMN last_resumed_step VARCHAR(64);
        RAISE NOTICE 'Added runs.last_resumed_step';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='fix_issue_number') THEN
        ALTER TABLE runs ADD COLUMN fix_issue_number INTEGER;
        RAISE NOTICE 'Added runs.fix_issue_number';
    END IF;
END $$;

-- ─── runs: status制約を更新（新ステータス追加）──────────────
DO $$
BEGIN
    -- 古い制約を削除して再作成（新ステータスを含む）
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'valid_status' AND conrelid = 'runs'::regclass) THEN
        ALTER TABLE runs DROP CONSTRAINT valid_status;
    END IF;
    ALTER TABLE runs ADD CONSTRAINT valid_status CHECK (status IN (
        'pending', 'workflow_starting', 'running', 'paused', 'waiting_approval',
        'waiting_step1_approval', 'waiting_image_input',
        'completed', 'failed', 'cancelled'
    ));
    RAISE NOTICE 'Updated runs.valid_status constraint';
END $$;

-- ─── steps: unique制約 + error_code (migration 001-002) ──
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='steps' AND column_name='error_code') THEN
        ALTER TABLE steps ADD COLUMN error_code VARCHAR(50);
        RAISE NOTICE 'Added steps.error_code';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_steps_run_step') THEN
        -- インデックスが先に存在する場合は削除
        DROP INDEX IF EXISTS idx_steps_run_id_step_name;
        ALTER TABLE steps ADD CONSTRAINT uq_steps_run_step UNIQUE (run_id, step_name);
        RAISE NOTICE 'Added steps.uq_steps_run_step constraint';
    END IF;
END $$;

-- ─── api_settings テーブル ────────────────────────────────
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

-- ─── help_contents テーブル ───────────────────────────────
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

-- ─── hearing_templates テーブル ───────────────────────────
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
CREATE INDEX IF NOT EXISTS idx_hearing_templates_tenant ON hearing_templates(tenant_id);

-- ─── review_requests テーブル (migration 003) ────────────
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

-- ─── LLM providers & models シードデータ ─────────────────
INSERT INTO llm_providers (id, display_name, is_active) VALUES
    ('gemini',    'Google Gemini',    true),
    ('openai',    'OpenAI',           true),
    ('anthropic', 'Anthropic Claude', true)
ON CONFLICT (id) DO NOTHING;

INSERT INTO llm_models (provider_id, model_name, model_class, is_active) VALUES
    ('gemini',    'gemini-3-pro-preview',          'pro',      true),
    ('gemini',    'gemini-3-flash-preview',        'standard', true),
    ('gemini',    'gemini-2.5-flash',              'standard', true),
    ('gemini',    'gemini-2.5-pro',                'pro',      true),
    ('openai',    'gpt-5.2',                       'standard', true),
    ('openai',    'gpt-5.2-pro',                   'pro',      true),
    ('openai',    'gpt-5.2-codex',                 'pro',      true),
    ('openai',    'gpt-5.1',                       'standard', true),
    ('openai',    'gpt-5.1-codex',                 'pro',      true),
    ('openai',    'gpt-5.1-codex-mini',            'standard', true),
    ('openai',    'gpt-5-codex',                   'pro',      true),
    ('anthropic', 'claude-opus-4-6',               'pro',      true),
    ('anthropic', 'claude-sonnet-4-5-20250929',    'standard', true),
    ('anthropic', 'claude-haiku-4-5',              'standard', true),
    ('anthropic', 'claude-opus-4-5-20251124',      'pro',      true),
    ('anthropic', 'claude-sonnet-4-20250514',      'standard', true)
ON CONFLICT DO NOTHING;

-- ─── Sequence修正 ────────────────────────────────────────
SELECT setval('llm_models_id_seq', COALESCE((SELECT MAX(id) FROM llm_models), 0));

COMMIT;
