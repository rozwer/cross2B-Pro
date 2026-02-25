--
-- PostgreSQL database dump
--

\restrict 5GcHAFTfXAAplrHNgADtWuZqPMpT6vi3e7hBQonq43LgjiD53QpdEWgVJfAMyek

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: update_review_requests_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_review_requests_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: api_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_settings (
    id integer NOT NULL,
    tenant_id character varying(64) NOT NULL,
    service character varying(32) NOT NULL,
    api_key_encrypted text,
    default_model character varying(128),
    config jsonb,
    is_active boolean DEFAULT true NOT NULL,
    verified_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: api_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.api_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: api_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.api_settings_id_seq OWNED BY public.api_settings.id;


--
-- Name: artifacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.artifacts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    run_id uuid NOT NULL,
    step_id uuid,
    artifact_type character varying(100) NOT NULL,
    ref_path text NOT NULL,
    digest character varying(64) NOT NULL,
    content_type character varying(100),
    size_bytes bigint,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attempts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    step_id uuid NOT NULL,
    attempt_num integer NOT NULL,
    status character varying(50) NOT NULL,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone,
    input_digest character varying(64),
    output_digest character varying(64),
    error_message text,
    metrics jsonb
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    user_id character varying(64) NOT NULL,
    action character varying(64) NOT NULL,
    resource_type character varying(64) NOT NULL,
    resource_id character varying(128) NOT NULL,
    details jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    prev_hash character varying(64),
    entry_hash character varying(64) NOT NULL
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: diagnostic_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.diagnostic_reports (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    run_id uuid NOT NULL,
    root_cause_analysis text NOT NULL,
    recommended_actions jsonb NOT NULL,
    resume_step character varying(64),
    confidence_score numeric(3,2),
    llm_provider character varying(32) NOT NULL,
    llm_model character varying(128) NOT NULL,
    prompt_tokens integer,
    completion_tokens integer,
    latency_ms integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: error_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.error_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    run_id uuid NOT NULL,
    step_id uuid,
    source character varying(32) DEFAULT 'activity'::character varying NOT NULL,
    error_category character varying(32) NOT NULL,
    error_type character varying(128) NOT NULL,
    error_message text NOT NULL,
    stack_trace text,
    context jsonb,
    attempt integer DEFAULT 1,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_error_category CHECK (((error_category)::text = ANY ((ARRAY['retryable'::character varying, 'non_retryable'::character varying, 'validation_fail'::character varying])::text[]))),
    CONSTRAINT valid_error_source CHECK (((source)::text = ANY ((ARRAY['llm'::character varying, 'tool'::character varying, 'validation'::character varying, 'storage'::character varying, 'activity'::character varying, 'api'::character varying])::text[])))
);


--
-- Name: events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.events (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    run_id uuid,
    step_id uuid,
    event_type character varying(100) NOT NULL,
    actor character varying(255),
    tenant_id character varying(64),
    payload jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: github_sync_status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.github_sync_status (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    run_id uuid NOT NULL,
    step character varying(20) NOT NULL,
    github_sha character varying(40),
    minio_digest character varying(64),
    synced_at timestamp with time zone,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    CONSTRAINT valid_sync_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'synced'::character varying, 'diverged'::character varying, 'github_only'::character varying, 'minio_only'::character varying])::text[])))
);


--
-- Name: hearing_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hearing_templates (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    data jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: help_contents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.help_contents (
    id integer NOT NULL,
    help_key character varying(128) NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    category character varying(64),
    display_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: help_contents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.help_contents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: help_contents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.help_contents_id_seq OWNED BY public.help_contents.id;


--
-- Name: llm_models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_models (
    id integer NOT NULL,
    provider_id character varying(32) NOT NULL,
    model_name character varying(128) NOT NULL,
    model_class character varying(32) NOT NULL,
    cost_per_1k_input_tokens numeric(10,6),
    cost_per_1k_output_tokens numeric(10,6),
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: llm_models_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.llm_models_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: llm_models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.llm_models_id_seq OWNED BY public.llm_models.id;


--
-- Name: llm_providers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.llm_providers (
    id character varying(32) NOT NULL,
    display_name character varying(64) NOT NULL,
    api_base_url text,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: prompts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prompts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    step_name character varying(100) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    content text NOT NULL,
    variables jsonb DEFAULT '[]'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: review_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_requests (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    run_id uuid NOT NULL,
    step character varying(20) NOT NULL,
    issue_number integer,
    issue_url character varying(500),
    issue_state character varying(20),
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    review_type character varying(20),
    review_result jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp without time zone
);


--
-- Name: TABLE review_requests; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.review_requests IS 'Stores review requests and results for article steps';


--
-- Name: COLUMN review_requests.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.review_requests.status IS 'pending=not requested, in_progress=waiting for review, completed=has result, closed_without_result=issue closed without result';


--
-- Name: runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.runs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id character varying(64) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    input_data jsonb,
    current_step character varying(100),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_message text,
    error_code character varying(100),
    step11_state jsonb,
    github_repo_url text,
    github_dir_path text,
    last_resumed_step character varying(64),
    fix_issue_number integer,
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'workflow_starting'::character varying, 'running'::character varying, 'paused'::character varying, 'waiting_approval'::character varying, 'waiting_step1_approval'::character varying, 'waiting_image_input'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: step_llm_defaults; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.step_llm_defaults (
    step character varying(64) NOT NULL,
    provider_id character varying(32) NOT NULL,
    model_class character varying(32) NOT NULL
);


--
-- Name: steps; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.steps (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    run_id uuid NOT NULL,
    step_name character varying(100) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_code character varying(50),
    error_message text,
    retry_count integer DEFAULT 0,
    CONSTRAINT valid_step_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'skipped'::character varying])::text[])))
);


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants (
    id character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    database_url text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: api_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_settings ALTER COLUMN id SET DEFAULT nextval('public.api_settings_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: help_contents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_contents ALTER COLUMN id SET DEFAULT nextval('public.help_contents_id_seq'::regclass);


--
-- Name: llm_models id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_models ALTER COLUMN id SET DEFAULT nextval('public.llm_models_id_seq'::regclass);


--
-- Name: api_settings api_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_settings
    ADD CONSTRAINT api_settings_pkey PRIMARY KEY (id);


--
-- Name: api_settings api_settings_tenant_id_service_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_settings
    ADD CONSTRAINT api_settings_tenant_id_service_key UNIQUE (tenant_id, service);


--
-- Name: artifacts artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_pkey PRIMARY KEY (id);


--
-- Name: attempts attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_pkey PRIMARY KEY (id);


--
-- Name: attempts attempts_step_id_attempt_num_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_step_id_attempt_num_key UNIQUE (step_id, attempt_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: diagnostic_reports diagnostic_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diagnostic_reports
    ADD CONSTRAINT diagnostic_reports_pkey PRIMARY KEY (id);


--
-- Name: error_logs error_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: github_sync_status github_sync_status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.github_sync_status
    ADD CONSTRAINT github_sync_status_pkey PRIMARY KEY (id);


--
-- Name: hearing_templates hearing_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hearing_templates
    ADD CONSTRAINT hearing_templates_pkey PRIMARY KEY (id);


--
-- Name: help_contents help_contents_help_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_contents
    ADD CONSTRAINT help_contents_help_key_key UNIQUE (help_key);


--
-- Name: help_contents help_contents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.help_contents
    ADD CONSTRAINT help_contents_pkey PRIMARY KEY (id);


--
-- Name: llm_models llm_models_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_pkey PRIMARY KEY (id);


--
-- Name: llm_models llm_models_provider_id_model_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_provider_id_model_name_key UNIQUE (provider_id, model_name);


--
-- Name: llm_providers llm_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_providers
    ADD CONSTRAINT llm_providers_pkey PRIMARY KEY (id);


--
-- Name: prompts prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_pkey PRIMARY KEY (id);


--
-- Name: prompts prompts_step_name_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_step_name_version_key UNIQUE (step_name, version);


--
-- Name: review_requests review_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_pkey PRIMARY KEY (id);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (id);


--
-- Name: step_llm_defaults step_llm_defaults_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step_llm_defaults
    ADD CONSTRAINT step_llm_defaults_pkey PRIMARY KEY (step);


--
-- Name: steps steps_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.steps
    ADD CONSTRAINT steps_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: api_settings uq_api_setting_tenant_service; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_settings
    ADD CONSTRAINT uq_api_setting_tenant_service UNIQUE (tenant_id, service);


--
-- Name: github_sync_status uq_github_sync_run_step; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.github_sync_status
    ADD CONSTRAINT uq_github_sync_run_step UNIQUE (run_id, step);


--
-- Name: hearing_templates uq_hearing_template_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hearing_templates
    ADD CONSTRAINT uq_hearing_template_tenant_name UNIQUE (tenant_id, name);


--
-- Name: review_requests uq_review_request_run_step_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT uq_review_request_run_step_type UNIQUE (run_id, step, review_type);


--
-- Name: steps uq_steps_run_step; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.steps
    ADD CONSTRAINT uq_steps_run_step UNIQUE (run_id, step_name);


--
-- Name: idx_artifacts_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_artifacts_run_id ON public.artifacts USING btree (run_id);


--
-- Name: idx_artifacts_step_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_artifacts_step_id ON public.artifacts USING btree (step_id);


--
-- Name: idx_attempts_step_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_attempts_step_id ON public.attempts USING btree (step_id);


--
-- Name: idx_diagnostic_reports_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_diagnostic_reports_run_id ON public.diagnostic_reports USING btree (run_id);


--
-- Name: idx_error_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_created_at ON public.error_logs USING btree (created_at DESC);


--
-- Name: idx_error_logs_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_run_id ON public.error_logs USING btree (run_id);


--
-- Name: idx_error_logs_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_source ON public.error_logs USING btree (source);


--
-- Name: idx_error_logs_step_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_error_logs_step_id ON public.error_logs USING btree (step_id);


--
-- Name: idx_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_created_at ON public.events USING btree (created_at DESC);


--
-- Name: idx_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_event_type ON public.events USING btree (event_type);


--
-- Name: idx_events_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_run_id ON public.events USING btree (run_id);


--
-- Name: idx_events_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_events_tenant_id ON public.events USING btree (tenant_id);


--
-- Name: idx_github_sync_status_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_github_sync_status_run_id ON public.github_sync_status USING btree (run_id);


--
-- Name: idx_github_sync_status_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_github_sync_status_status ON public.github_sync_status USING btree (status);


--
-- Name: idx_hearing_templates_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hearing_templates_name ON public.hearing_templates USING btree (name);


--
-- Name: idx_hearing_templates_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_hearing_templates_tenant_id ON public.hearing_templates USING btree (tenant_id);


--
-- Name: idx_help_contents_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_help_contents_category ON public.help_contents USING btree (category);


--
-- Name: idx_help_contents_help_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_help_contents_help_key ON public.help_contents USING btree (help_key);


--
-- Name: idx_prompts_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_prompts_active ON public.prompts USING btree (step_name, is_active) WHERE (is_active = true);


--
-- Name: idx_prompts_step_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_prompts_step_name ON public.prompts USING btree (step_name);


--
-- Name: idx_review_requests_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_review_requests_run_id ON public.review_requests USING btree (run_id);


--
-- Name: idx_review_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_review_requests_status ON public.review_requests USING btree (status);


--
-- Name: idx_runs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_created_at ON public.runs USING btree (created_at DESC);


--
-- Name: idx_runs_github_repo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_github_repo ON public.runs USING btree (github_repo_url) WHERE (github_repo_url IS NOT NULL);


--
-- Name: idx_runs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_status ON public.runs USING btree (status);


--
-- Name: idx_runs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_runs_tenant_id ON public.runs USING btree (tenant_id);


--
-- Name: idx_steps_run_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_steps_run_id ON public.steps USING btree (run_id);


--
-- Name: idx_steps_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_steps_status ON public.steps USING btree (status);


--
-- Name: ix_api_settings_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_api_settings_tenant_id ON public.api_settings USING btree (tenant_id);


--
-- Name: ix_help_contents_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_contents_category ON public.help_contents USING btree (category);


--
-- Name: ix_help_contents_help_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_help_contents_help_key ON public.help_contents USING btree (help_key);


--
-- Name: hearing_templates update_hearing_templates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_hearing_templates_updated_at BEFORE UPDATE ON public.hearing_templates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: review_requests update_review_requests_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_review_requests_updated_at BEFORE UPDATE ON public.review_requests FOR EACH ROW EXECUTE FUNCTION public.update_review_requests_updated_at();


--
-- Name: runs update_runs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_runs_updated_at BEFORE UPDATE ON public.runs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: artifacts artifacts_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: artifacts artifacts_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE SET NULL;


--
-- Name: attempts attempts_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE CASCADE;


--
-- Name: diagnostic_reports diagnostic_reports_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diagnostic_reports
    ADD CONSTRAINT diagnostic_reports_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: error_logs error_logs_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: error_logs error_logs_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE SET NULL;


--
-- Name: events events_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: events events_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE SET NULL;


--
-- Name: github_sync_status github_sync_status_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.github_sync_status
    ADD CONSTRAINT github_sync_status_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: llm_models llm_models_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.llm_providers(id);


--
-- Name: review_requests review_requests_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: step_llm_defaults step_llm_defaults_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.step_llm_defaults
    ADD CONSTRAINT step_llm_defaults_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.llm_providers(id);


--
-- Name: steps steps_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.steps
    ADD CONSTRAINT steps_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 5GcHAFTfXAAplrHNgADtWuZqPMpT6vi3e7hBQonq43LgjiD53QpdEWgVJfAMyek

