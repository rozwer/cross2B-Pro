--
-- PostgreSQL database dump
--

\restrict Cyoi0n7h3qMV8nEbeDOnhhlvSnDZr3SvND9E7uS2vgvbpbkerImIe81aMVSKsP3

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
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: update_review_requests_updated_at(); Type: FUNCTION; Schema: public; Owner: seo
--

CREATE FUNCTION public.update_review_requests_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_review_requests_updated_at() OWNER TO seo;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: seo
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO seo;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: api_settings; Type: TABLE; Schema: public; Owner: seo
--

CREATE TABLE public.api_settings (
    id integer NOT NULL,
    tenant_id character varying(255) NOT NULL,
    service character varying(50) NOT NULL,
    api_key_encrypted text,
    default_model character varying(255),
    config jsonb,
    is_active boolean DEFAULT true,
    verified_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.api_settings OWNER TO seo;

--
-- Name: api_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: seo
--

CREATE SEQUENCE public.api_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.api_settings_id_seq OWNER TO seo;

--
-- Name: api_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: seo
--

ALTER SEQUENCE public.api_settings_id_seq OWNED BY public.api_settings.id;


--
-- Name: artifacts; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.artifacts OWNER TO seo;

--
-- Name: attempts; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.attempts OWNER TO seo;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.audit_logs OWNER TO seo;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: seo
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO seo;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: seo
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: diagnostic_reports; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.diagnostic_reports OWNER TO seo;

--
-- Name: error_logs; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.error_logs OWNER TO seo;

--
-- Name: events; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.events OWNER TO seo;

--
-- Name: github_sync_status; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.github_sync_status OWNER TO seo;

--
-- Name: hearing_templates; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.hearing_templates OWNER TO seo;

--
-- Name: help_contents; Type: TABLE; Schema: public; Owner: seo
--

CREATE TABLE public.help_contents (
    id integer NOT NULL,
    help_key character varying(128) NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    category character varying(64),
    display_order integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.help_contents OWNER TO seo;

--
-- Name: help_contents_id_seq; Type: SEQUENCE; Schema: public; Owner: seo
--

CREATE SEQUENCE public.help_contents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.help_contents_id_seq OWNER TO seo;

--
-- Name: help_contents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: seo
--

ALTER SEQUENCE public.help_contents_id_seq OWNED BY public.help_contents.id;


--
-- Name: llm_models; Type: TABLE; Schema: public; Owner: seo
--

CREATE TABLE public.llm_models (
    id integer NOT NULL,
    provider_id character varying(32) NOT NULL,
    model_name character varying(128) NOT NULL,
    model_class character varying(32) DEFAULT 'standard'::character varying NOT NULL,
    cost_per_1k_input_tokens numeric(10,6),
    cost_per_1k_output_tokens numeric(10,6),
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.llm_models OWNER TO seo;

--
-- Name: llm_models_id_seq; Type: SEQUENCE; Schema: public; Owner: seo
--

CREATE SEQUENCE public.llm_models_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.llm_models_id_seq OWNER TO seo;

--
-- Name: llm_models_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: seo
--

ALTER SEQUENCE public.llm_models_id_seq OWNED BY public.llm_models.id;


--
-- Name: llm_providers; Type: TABLE; Schema: public; Owner: seo
--

CREATE TABLE public.llm_providers (
    id character varying(32) NOT NULL,
    display_name character varying(64) NOT NULL,
    api_base_url text,
    is_active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.llm_providers OWNER TO seo;

--
-- Name: prompts; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.prompts OWNER TO seo;

--
-- Name: review_requests; Type: TABLE; Schema: public; Owner: seo
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
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone,
    CONSTRAINT valid_review_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'completed'::character varying, 'closed_without_result'::character varying])::text[])))
);


ALTER TABLE public.review_requests OWNER TO seo;

--
-- Name: TABLE review_requests; Type: COMMENT; Schema: public; Owner: seo
--

COMMENT ON TABLE public.review_requests IS 'Stores review requests and results for article steps';


--
-- Name: COLUMN review_requests.status; Type: COMMENT; Schema: public; Owner: seo
--

COMMENT ON COLUMN public.review_requests.status IS 'pending=not requested, in_progress=waiting for review, completed=has result, closed_without_result=issue closed without result';


--
-- Name: runs; Type: TABLE; Schema: public; Owner: seo
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
    github_repo_url character varying(500),
    github_dir_path character varying(500),
    last_resumed_step character varying(64),
    fix_issue_number integer,
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'workflow_starting'::character varying, 'running'::character varying, 'paused'::character varying, 'waiting_approval'::character varying, 'waiting_step1_approval'::character varying, 'waiting_image_input'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE public.runs OWNER TO seo;

--
-- Name: step_llm_defaults; Type: TABLE; Schema: public; Owner: seo
--

CREATE TABLE public.step_llm_defaults (
    step character varying(64) NOT NULL,
    provider_id character varying(32) NOT NULL,
    model_class character varying(32) NOT NULL
);


ALTER TABLE public.step_llm_defaults OWNER TO seo;

--
-- Name: steps; Type: TABLE; Schema: public; Owner: seo
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


ALTER TABLE public.steps OWNER TO seo;

--
-- Name: tenants; Type: TABLE; Schema: public; Owner: seo
--

CREATE TABLE public.tenants (
    id character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    database_url text NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.tenants OWNER TO seo;

--
-- Name: api_settings id; Type: DEFAULT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.api_settings ALTER COLUMN id SET DEFAULT nextval('public.api_settings_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: help_contents id; Type: DEFAULT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.help_contents ALTER COLUMN id SET DEFAULT nextval('public.help_contents_id_seq'::regclass);


--
-- Name: llm_models id; Type: DEFAULT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.llm_models ALTER COLUMN id SET DEFAULT nextval('public.llm_models_id_seq'::regclass);


--
-- Data for Name: api_settings; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.api_settings (id, tenant_id, service, api_key_encrypted, default_model, config, is_active, verified_at, created_at, updated_at) FROM stdin;
1	dev-tenant-001	serp	f9gWpZgwW+Oz6l3aMh/q9k096OJ9dj3a0ibobsvyr55LI8YHYxmFeycasGUwqgLnnv/t48bKj61fX/647zpAheURARCJuyrTNcBKL6Z0FGZKBcGK3YSRoi/+WUg=	\N	\N	t	2026-01-20 03:25:20.072392+00	2026-01-20 03:24:46.133581+00	2026-01-20 03:25:20.073055+00
2	dev-tenant-001	github	lP709yfFnbjWD6umwwcwKgdMZafg+rSyaCNFM4kRBh1vNWcHucEJ3/7fOlLUdZo+W0lABBMfvSzpqxXMWe8mtwbI7Mg=	\N	\N	t	2026-01-21 11:21:16.160568+00	2026-01-21 11:09:19.981944+00	2026-01-21 11:21:16.16748+00
\.


--
-- Data for Name: artifacts; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.artifacts (id, run_id, step_id, artifact_type, ref_path, digest, content_type, size_bytes, metadata, created_at) FROM stdin;
\.


--
-- Data for Name: attempts; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.attempts (id, step_id, attempt_num, status, started_at, completed_at, input_digest, output_digest, error_message, metrics) FROM stdin;
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.audit_logs (id, user_id, action, resource_type, resource_id, details, created_at, prev_hash, entry_hash) FROM stdin;
1	dev-user-001	create	run	7efb4e2e-75ec-44f5-9e27-cef12e693f91	{"keyword": "テストキーワード", "start_workflow": true}	2026-01-12 10:03:55.532129+00	\N	9847b1683505fcf24124c606cf6ea4648d63ba007f4e3541618c0b20baf2be18
2	dev-user-001	create	run	ea0d7e33-978c-4ac8-93c1-ce1d8604b37a	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 10:09:11.977149+00	9847b1683505fcf24124c606cf6ea4648d63ba007f4e3541618c0b20baf2be18	035de3aa7a0af38e54e77ee7e248f1b1b3b16c5eafabd8d2c31c8965dac60514
3	dev-user-001	create	hearing_template	6b3f94fe-574a-477c-bdef-eea60f5a66ae	{"name": "eラーニング企業向け", "description": "eラーニング 企業向けのデフォルトテンプレート"}	2026-01-12 10:10:39.781867+00	035de3aa7a0af38e54e77ee7e248f1b1b3b16c5eafabd8d2c31c8965dac60514	203c404e3a5032f9883358b2b0a325e2df3382621a51f9ab4dbd0ca1683a4d91
4	dev-user-001	create	run	9e568bbd-8d80-4fcf-9949-fc7dbbbc7e5e	{"keyword": "test", "start_workflow": true}	2026-01-12 10:12:44.349227+00	203c404e3a5032f9883358b2b0a325e2df3382621a51f9ab4dbd0ca1683a4d91	098b06dd365e9c04a39b2450845aa8969ee1dafb3263bb5fb0c26086407721ac
5	dev-user-001	create	run	409f872e-9d76-4d37-b24b-cd31affda582	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 10:17:27.562708+00	098b06dd365e9c04a39b2450845aa8969ee1dafb3263bb5fb0c26086407721ac	21717749f8e2a74ac4fc4800ff17d10f8230980b778705b5df1c408fa91efbd4
6	dev-user-001	cancel	run	409f872e-9d76-4d37-b24b-cd31affda582	{"bulk": true, "reason": "bulk_delete", "previous_status": "running"}	2026-01-12 10:19:47.337755+00	21717749f8e2a74ac4fc4800ff17d10f8230980b778705b5df1c408fa91efbd4	3b8a7874878ea1fda4b66bbf245aee3377344bba56256d40af933ede2c1ac4b3
7	dev-user-001	delete	run	409f872e-9d76-4d37-b24b-cd31affda582	{"bulk": true, "status": "cancelled"}	2026-01-12 10:19:47.340188+00	3b8a7874878ea1fda4b66bbf245aee3377344bba56256d40af933ede2c1ac4b3	112525408f00a254cafba8036de96dd906959af88513867ae663859a79934204
8	dev-user-001	cancel	run	9e568bbd-8d80-4fcf-9949-fc7dbbbc7e5e	{"bulk": true, "reason": "bulk_delete", "previous_status": "running"}	2026-01-12 10:19:47.399445+00	112525408f00a254cafba8036de96dd906959af88513867ae663859a79934204	377fac80887d14a566cea7fcf7277dfc47094a805c3f4cf7fa750cd2d1769ff7
9	dev-user-001	delete	run	9e568bbd-8d80-4fcf-9949-fc7dbbbc7e5e	{"bulk": true, "status": "cancelled"}	2026-01-12 10:19:47.402298+00	377fac80887d14a566cea7fcf7277dfc47094a805c3f4cf7fa750cd2d1769ff7	357923165e63a333d4a61e019a636c94dce081832914a595fb2e97e09ba31771
10	dev-user-001	cancel	run	ea0d7e33-978c-4ac8-93c1-ce1d8604b37a	{"bulk": true, "reason": "bulk_delete", "previous_status": "running"}	2026-01-12 10:19:47.445176+00	357923165e63a333d4a61e019a636c94dce081832914a595fb2e97e09ba31771	d3fa42cbd2093574a6e38375ebca8640868d18e88ccc81a7bdef612f4a25f9e2
11	dev-user-001	delete	run	ea0d7e33-978c-4ac8-93c1-ce1d8604b37a	{"bulk": true, "status": "cancelled"}	2026-01-12 10:19:47.448422+00	d3fa42cbd2093574a6e38375ebca8640868d18e88ccc81a7bdef612f4a25f9e2	db54ae70e17fd765e26fd2fb081e09dd65fbc3624fab2a4619c563ce761dd4f8
12	dev-user-001	cancel	run	7efb4e2e-75ec-44f5-9e27-cef12e693f91	{"bulk": true, "reason": "bulk_delete", "previous_status": "running"}	2026-01-12 10:19:47.490448+00	db54ae70e17fd765e26fd2fb081e09dd65fbc3624fab2a4619c563ce761dd4f8	b4cc94b4172910775462640d5f96419290b1b45f1d308229cb9abc13b2d3bd90
13	dev-user-001	delete	run	7efb4e2e-75ec-44f5-9e27-cef12e693f91	{"bulk": true, "status": "cancelled"}	2026-01-12 10:19:47.492421+00	b4cc94b4172910775462640d5f96419290b1b45f1d308229cb9abc13b2d3bd90	d99a5e35f17608127e41b250a19ca087846a99b8916c4c64ea82f52a2a9956b8
14	dev-user-001	create	run	25c54858-8ec4-4346-9a70-f84c44ba7724	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 10:22:25.468424+00	d99a5e35f17608127e41b250a19ca087846a99b8916c4c64ea82f52a2a9956b8	45a86efeb948bcc5d0cd605778159202df3ce6726582a62df8f0d68bc61a43cd
15	dev-user-001	create	run	42283246-a57c-46fe-a7ac-d78ed4261053	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 10:40:41.427707+00	45a86efeb948bcc5d0cd605778159202df3ce6726582a62df8f0d68bc61a43cd	60a9e70c326a7bdaac16cc25f1777ed3a1eae947a16053b060995b00abc4066c
16	dev-user-001	cancel	run	42283246-a57c-46fe-a7ac-d78ed4261053	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_approval"}	2026-01-12 10:55:33.985933+00	60a9e70c326a7bdaac16cc25f1777ed3a1eae947a16053b060995b00abc4066c	c6595c050163251ddb6f5d16ba76be782d93b0d9a4cc4abc04a10efbd06a915b
17	dev-user-001	delete	run	42283246-a57c-46fe-a7ac-d78ed4261053	{"bulk": true, "status": "cancelled"}	2026-01-12 10:55:33.990729+00	c6595c050163251ddb6f5d16ba76be782d93b0d9a4cc4abc04a10efbd06a915b	f7b0f4c94afc1ba5f3684b0ef3a8cd417609bae04545f9cacfaed37cf8a3db27
18	dev-user-001	create	run	3f5e67ed-8f6b-45e9-8b13-3e6071b5b682	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 10:55:47.030943+00	f7b0f4c94afc1ba5f3684b0ef3a8cd417609bae04545f9cacfaed37cf8a3db27	e9d20f286200f20e2589bd52a9c2253a2c13ca2d87f761ac38164a24e96f6f09
19	dev-user-001	cancel	run	3f5e67ed-8f6b-45e9-8b13-3e6071b5b682	{"bulk": true, "reason": "bulk_delete", "previous_status": "running"}	2026-01-12 11:04:02.328156+00	e9d20f286200f20e2589bd52a9c2253a2c13ca2d87f761ac38164a24e96f6f09	d5306072cf3f1e39c729589b80060c359e4518c73b749372f8d2a739e6ef6773
20	dev-user-001	delete	run	3f5e67ed-8f6b-45e9-8b13-3e6071b5b682	{"bulk": true, "status": "cancelled"}	2026-01-12 11:04:02.332664+00	d5306072cf3f1e39c729589b80060c359e4518c73b749372f8d2a739e6ef6773	8c3512e03c2912aef05d344197a3044578449c2934c91c6619be578b67dea4bf
21	dev-user-001	create	run	a6e1842b-6215-4a1b-8748-fd1d0136bcd1	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 11:04:14.680113+00	8c3512e03c2912aef05d344197a3044578449c2934c91c6619be578b67dea4bf	f8eb079b650930faaa31fa62ba15e63f38b0cdd5264ae26addb8f4649efdcd26
22	dev-user-001	cancel	run	a6e1842b-6215-4a1b-8748-fd1d0136bcd1	{"bulk": true, "reason": "bulk_delete", "previous_status": "running"}	2026-01-12 11:17:16.862698+00	f8eb079b650930faaa31fa62ba15e63f38b0cdd5264ae26addb8f4649efdcd26	202612f5fd2c0ac1e467c372d65c3568587a83115007b3ef73f1979d53b94fd5
23	dev-user-001	delete	run	a6e1842b-6215-4a1b-8748-fd1d0136bcd1	{"bulk": true, "status": "cancelled"}	2026-01-12 11:17:16.866925+00	202612f5fd2c0ac1e467c372d65c3568587a83115007b3ef73f1979d53b94fd5	c0938b9e920c624eaae056228e6847b180f15e42efc0fba4a2746d8b8a0c8f54
24	dev-user-001	create	run	4ba0793a-c9eb-4510-ad82-f708a0ed41c9	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 11:17:39.411296+00	c0938b9e920c624eaae056228e6847b180f15e42efc0fba4a2746d8b8a0c8f54	5b6a8729d6da1e6d294f6d328f527b64c23c4c50a77c2591b2ce31cc52a83e80
25	dev-user-001	create	run	f3ba955a-067c-49f3-93d9-ff9411bef30d	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 11:34:54.32592+00	5b6a8729d6da1e6d294f6d328f527b64c23c4c50a77c2591b2ce31cc52a83e80	441d298c251d0996bdedf4586decb760f19a17db572b0af1ae2f0029b13fcda7
26	dev-user-001	create	run	8dc3e642-35a9-4256-98f6-bed8e9facfad	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 11:46:31.182479+00	441d298c251d0996bdedf4586decb760f19a17db572b0af1ae2f0029b13fcda7	ad9f7aae30473f5d67ea4ec1bdd98b74bd7d055cad748d5df272520d1fdb91db
27	dev-user-001	create	run	c4142156-2d22-4679-88ed-e90fca8a023a	{"keyword": "リモートワーク 導入", "start_workflow": true}	2026-01-12 11:57:31.524352+00	ad9f7aae30473f5d67ea4ec1bdd98b74bd7d055cad748d5df272520d1fdb91db	2c9493177f57dbb8d3951d33957eff8ad409bbf5141141fdb90ea98415d6e506
28	dev-user-001	create	run	cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2	{"keyword": "リモートワーク 導入", "start_workflow": true}	2026-01-12 12:04:34.672487+00	2c9493177f57dbb8d3951d33957eff8ad409bbf5141141fdb90ea98415d6e506	99f6c4ed924d14f9304dd82ed2a8340d6d846446b8216cee06463b281930f70a
29	dev-user-001	approve	run	cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2	{"comment": null, "previous_status": "waiting_approval"}	2026-01-12 12:37:26.359559+00	99f6c4ed924d14f9304dd82ed2a8340d6d846446b8216cee06463b281930f70a	c0b510d0ac49bd5587dd6d68617812e4b816753338e65cb1b6b22b5c252cba80
32	dev-user-001	cancel	run	c4142156-2d22-4679-88ed-e90fca8a023a	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_approval"}	2026-01-12 12:44:07.113893+00	c0b510d0ac49bd5587dd6d68617812e4b816753338e65cb1b6b22b5c252cba80	7bf4d5c48e8faa6de9e2f92ae18479ce899cde3a0a22915bed2d606f416ed3c9
33	dev-user-001	delete	run	c4142156-2d22-4679-88ed-e90fca8a023a	{"bulk": true, "status": "cancelled"}	2026-01-12 12:44:07.117652+00	7bf4d5c48e8faa6de9e2f92ae18479ce899cde3a0a22915bed2d606f416ed3c9	c1bda93746b3bc7b067ed0049ff4f11d7ed598ab0027b04c0526525ced288636
34	dev-user-001	cancel	run	8dc3e642-35a9-4256-98f6-bed8e9facfad	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_approval"}	2026-01-12 12:44:07.289317+00	c1bda93746b3bc7b067ed0049ff4f11d7ed598ab0027b04c0526525ced288636	979df962ecf6dce4ea20bd99a59eb0bb90f33104a0a4606c4f4e3aba3d82bf7c
35	dev-user-001	delete	run	8dc3e642-35a9-4256-98f6-bed8e9facfad	{"bulk": true, "status": "cancelled"}	2026-01-12 12:44:07.292492+00	979df962ecf6dce4ea20bd99a59eb0bb90f33104a0a4606c4f4e3aba3d82bf7c	2e9f8b9728cc940125a58330f3e3fa3525da2ea71ccec1feb7bc87cf28b25e70
36	dev-user-001	cancel	run	25c54858-8ec4-4346-9a70-f84c44ba7724	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_approval"}	2026-01-12 12:44:07.396092+00	2e9f8b9728cc940125a58330f3e3fa3525da2ea71ccec1feb7bc87cf28b25e70	4c1ef82534a9ce4c9749d4dce7fbafde8582ef79a5f1715f32281d5019d07c6e
37	dev-user-001	delete	run	25c54858-8ec4-4346-9a70-f84c44ba7724	{"bulk": true, "status": "cancelled"}	2026-01-12 12:44:07.398331+00	4c1ef82534a9ce4c9749d4dce7fbafde8582ef79a5f1715f32281d5019d07c6e	42d652d5cb7bed9a8be0f9c9325c97f11cf862fdc19f29a2960cbb0224db959f
38	dev-user-001	cancel	run	4ba0793a-c9eb-4510-ad82-f708a0ed41c9	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_approval"}	2026-01-12 12:44:07.513892+00	42d652d5cb7bed9a8be0f9c9325c97f11cf862fdc19f29a2960cbb0224db959f	d19fd5816697806f1f61d88263ec31d6c5d47eb8715dcfc6f7915e7977c51f85
39	dev-user-001	delete	run	4ba0793a-c9eb-4510-ad82-f708a0ed41c9	{"bulk": true, "status": "cancelled"}	2026-01-12 12:44:07.515967+00	d19fd5816697806f1f61d88263ec31d6c5d47eb8715dcfc6f7915e7977c51f85	05d4867d6bde631c52dc48820b70e1af9c35f49d9a83edc3faa4ef664f6754a1
40	dev-user-001	cancel	run	f3ba955a-067c-49f3-93d9-ff9411bef30d	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_approval"}	2026-01-12 12:44:07.61861+00	05d4867d6bde631c52dc48820b70e1af9c35f49d9a83edc3faa4ef664f6754a1	dc5f1bf779672c27e2db8ee4d5f444010c9fb4f10aee161df8507b8955931d66
41	dev-user-001	delete	run	f3ba955a-067c-49f3-93d9-ff9411bef30d	{"bulk": true, "status": "cancelled"}	2026-01-12 12:44:07.62073+00	dc5f1bf779672c27e2db8ee4d5f444010c9fb4f10aee161df8507b8955931d66	291356ca9e07e0479b7e2ca0b5e87d5356e9f5dcd233ab21543e9cea4d90dc13
42	dev-user-001	resume	run	cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2	{"resume_from": "step4", "workflow_id": "cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2-resume-160d7c64", "deleted_steps": ["step4", "step5", "step6", "step6_5", "step7a", "step7b", "step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-12 12:46:40.419521+00	291356ca9e07e0479b7e2ca0b5e87d5356e9f5dcd233ab21543e9cea4d90dc13	9ffa1238f52f9beab74cb24c3a37491d5878cf6e1fa97575cc96222404eab18b
43	dev-user-001	resume	run	cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2	{"resume_from": "step4", "workflow_id": "cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2-resume-bd6f510a", "deleted_steps": ["step4", "step5", "step6", "step6_5", "step7a", "step7b", "step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 1}	2026-01-12 12:46:56.686504+00	9ffa1238f52f9beab74cb24c3a37491d5878cf6e1fa97575cc96222404eab18b	3eed1644f343db7f2e4ce523bd51c437836195cabbd81a99888b7a2f4ce6d464
44	dev-user-001	resume	run	cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2	{"resume_from": "step4", "workflow_id": "cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2-resume-11ebf590", "deleted_steps": ["step4", "step5", "step6", "step6_5", "step7a", "step7b", "step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 1}	2026-01-12 12:51:19.071484+00	3eed1644f343db7f2e4ce523bd51c437836195cabbd81a99888b7a2f4ce6d464	0439144f8323244764ddcb58a0fa88b16dac231c583d9c45f4ed39c96d33c7bf
45	dev-user-001	create	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 12:51:53.875435+00	0439144f8323244764ddcb58a0fa88b16dac231c583d9c45f4ed39c96d33c7bf	c9af6803fbf21a43ef5d15614d69a46357e7ecf546c3fb8c51f8bccbe67cf7d7
46	dev-user-001	approve	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"comment": null, "previous_status": "waiting_approval"}	2026-01-12 12:56:25.949104+00	c9af6803fbf21a43ef5d15614d69a46357e7ecf546c3fb8c51f8bccbe67cf7d7	e0f28d1245631880b9046988532e7a664298a5338ecdbdd61e9dd308cc658fe3
47	dev-user-001	resume	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"resume_from": "step8", "workflow_id": "e4829e0e-b71e-4e36-abb1-7b1a909540fe-resume-1dca2a89", "deleted_steps": ["step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 2}	2026-01-12 13:33:18.840959+00	e0f28d1245631880b9046988532e7a664298a5338ecdbdd61e9dd308cc658fe3	45092089c5feb0a46ed3d29c8368b3506a9c9dd3565acc58048a5c49a4086c5a
48	dev-user-001	resume	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"resume_from": "step8", "workflow_id": "e4829e0e-b71e-4e36-abb1-7b1a909540fe-resume-3b573600", "deleted_steps": ["step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 2}	2026-01-12 13:35:31.960318+00	45092089c5feb0a46ed3d29c8368b3506a9c9dd3565acc58048a5c49a4086c5a	e63b171904f62a7a571a6e2f1b9f9a06be2d73c02ff787458f01697ff44110dc
51	dev-user-001	resume	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"resume_from": "step9", "workflow_id": "e4829e0e-b71e-4e36-abb1-7b1a909540fe-resume-a2ea93b9", "deleted_steps": ["step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-12 13:51:50.437016+00	f72a9a992d4ca966f7f0cf9ddd071ba9a7dac1d51eabc0b09b2cdd9889824dec	08f733b65d1767b4b2e4cf60d0c0bff7ea3eb5abee90f53a5169e2081338bbf6
49	dev-user-001	resume	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"resume_from": "step8", "workflow_id": "e4829e0e-b71e-4e36-abb1-7b1a909540fe-resume-0b7b4078", "deleted_steps": ["step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-12 13:43:07.150972+00	e63b171904f62a7a571a6e2f1b9f9a06be2d73c02ff787458f01697ff44110dc	e6a86acf9e7211388fea4e3a2bfc2ec078df4ee3d512083399bb53d5e70d6d8a
50	dev-user-001	resume	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"resume_from": "step8", "workflow_id": "e4829e0e-b71e-4e36-abb1-7b1a909540fe-resume-61764fd0", "deleted_steps": ["step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-12 13:45:31.759547+00	e6a86acf9e7211388fea4e3a2bfc2ec078df4ee3d512083399bb53d5e70d6d8a	f72a9a992d4ca966f7f0cf9ddd071ba9a7dac1d51eabc0b09b2cdd9889824dec
52	dev-user-001	resume	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"resume_from": "step8", "workflow_id": "e4829e0e-b71e-4e36-abb1-7b1a909540fe-resume-a7f5b7ce", "deleted_steps": ["step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-12 14:08:27.90361+00	08f733b65d1767b4b2e4cf60d0c0bff7ea3eb5abee90f53a5169e2081338bbf6	872585493bbeef79148dd2424dab3a5ac1e9c365b21f7a5235aef1c8472e5d61
53	system	step10.articles_generated	step	step10	{"run_id": "e4829e0e-b71e-4e36-abb1-7b1a909540fe", "articles": [{"word_count": 4291, "output_digest": "d6d8cc30c0132c1f", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3873, "output_digest": "16647e1bdeee8b36", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 3852, "output_digest": "ec1046762fa17a1b", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2937, "output_digest": "3351a5eb9ed4dc27", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-01-12 14:20:02.550452+00	872585493bbeef79148dd2424dab3a5ac1e9c365b21f7a5235aef1c8472e5d61	46ff5a6f96151559a5dfdb2243991faaea20e382e9037b1cc36d35d2b06225be
54	dev-user-001	step11_settings_submitted	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"image_count": 3}	2026-01-12 14:27:59.193778+00	46ff5a6f96151559a5dfdb2243991faaea20e382e9037b1cc36d35d2b06225be	54ebfb5b87db4807d2e36cc3f68031201799a42af5bca44079d77284012c873a
55	dev-user-001	retry	step	e4829e0e-b71e-4e36-abb1-7b1a909540fe/step11	{"new_attempt_id": "5138357b-181c-491a-a5c8-a6bae9fbd37e", "previous_status": "failed"}	2026-01-12 14:33:18.18432+00	54ebfb5b87db4807d2e36cc3f68031201799a42af5bca44079d77284012c873a	c602c90c8976f613692789e46ffb304716f208afaf431272862ae9479e2e0b9e
56	dev-user-001	retry	step	e4829e0e-b71e-4e36-abb1-7b1a909540fe/step11	{"new_attempt_id": "c8fdc43d-ebb0-4ded-bcd3-10a092e03d53", "previous_status": "failed"}	2026-01-12 14:41:47.985509+00	c602c90c8976f613692789e46ffb304716f208afaf431272862ae9479e2e0b9e	c30fda202f77d704193921eeef370aeb6a9a0b80a106ed4c4a19f540189bc1f7
57	dev-user-001	retry	step	e4829e0e-b71e-4e36-abb1-7b1a909540fe/step11	{"new_attempt_id": "6c7f2ebf-7b15-4492-b89e-46ceb5d1b755", "previous_status": "failed"}	2026-01-12 14:57:01.405705+00	c30fda202f77d704193921eeef370aeb6a9a0b80a106ed4c4a19f540189bc1f7	67d04094b8e5040e3770036624c30b5cdc8b33755671a35246cca271eba53748
58	dev-user-001	retry	step	e4829e0e-b71e-4e36-abb1-7b1a909540fe/step11	{"new_attempt_id": "be4e1ba5-217d-4705-b711-d2def24e86cf", "previous_status": "failed"}	2026-01-12 15:02:36.588418+00	67d04094b8e5040e3770036624c30b5cdc8b33755671a35246cca271eba53748	c5e1d9b5383af3b05f95b4119d5d38f93e9eadbf1fb6a45fd6446ad7798df506
59	dev-user-001	step11_completed	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"image_count": 3}	2026-01-12 15:42:52.19288+00	c5e1d9b5383af3b05f95b4119d5d38f93e9eadbf1fb6a45fd6446ad7798df506	51d6889c11105a2a77342d4cc97d58595f94a3b6a3df3260588a82be853d98e0
60	dev-user-001	create	run	6f18c5b0-f20e-47dc-8414-a00120857ab5	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 22:47:15.159192+00	51d6889c11105a2a77342d4cc97d58595f94a3b6a3df3260588a82be853d98e0	63e452f3f818b0cc2570f4809ada30c90e116cbc17b0fe8712a5828c0b313684
61	dev-user-001	approve	run	6f18c5b0-f20e-47dc-8414-a00120857ab5	{"comment": null, "previous_status": "waiting_approval"}	2026-01-12 22:57:48.614569+00	63e452f3f818b0cc2570f4809ada30c90e116cbc17b0fe8712a5828c0b313684	063fbf571633eec7d119f53a8d6adb791641761be0437e333eaecff210159528
62	system	step10.articles_generated	step	step10	{"run_id": "6f18c5b0-f20e-47dc-8414-a00120857ab5", "articles": [{"word_count": 7535, "output_digest": "159158bfecad3ccd", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3975, "output_digest": "6c8f5283a0a8ccde", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4546, "output_digest": "5fc1b9e3ff6a6454", "article_number": 3, "variation_type": "実践編"}, {"word_count": 3144, "output_digest": "595e101fecd988b0", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-01-12 23:19:22.330742+00	063fbf571633eec7d119f53a8d6adb791641761be0437e333eaecff210159528	fbfea775d1d8b103d729c67c4451dc5dc0d3b218cff1fafedfeeba36fea093d5
63	dev-user-001	step11_settings_submitted	run	6f18c5b0-f20e-47dc-8414-a00120857ab5	{"image_count": 3}	2026-01-12 23:19:40.880843+00	fbfea775d1d8b103d729c67c4451dc5dc0d3b218cff1fafedfeeba36fea093d5	e454956e095181aac3f67c8dc295c5fd760469daaded773a79cb7f60c9c9f80e
64	dev-user-001	step11_completed	run	6f18c5b0-f20e-47dc-8414-a00120857ab5	{"image_count": 3}	2026-01-12 23:20:39.332355+00	e454956e095181aac3f67c8dc295c5fd760469daaded773a79cb7f60c9c9f80e	ac0c799e99bbb9a4a2e0ac9eade27798d77978183dd09b1b68b30e8dfbe224bf
65	dev-user-001	delete	run	6f18c5b0-f20e-47dc-8414-a00120857ab5	{"bulk": true, "status": "waiting_image_input"}	2026-01-12 23:47:47.424988+00	ac0c799e99bbb9a4a2e0ac9eade27798d77978183dd09b1b68b30e8dfbe224bf	4398e8072029341111affcb5c7b59d8fffa6851fdf1bebe9083082914ab7c129
66	dev-user-001	delete	run	e4829e0e-b71e-4e36-abb1-7b1a909540fe	{"bulk": true, "status": "completed"}	2026-01-12 23:47:47.734096+00	4398e8072029341111affcb5c7b59d8fffa6851fdf1bebe9083082914ab7c129	12287e9c7fa21185a0751198628ae022123191f400fc998e4d922a857cec0ca8
67	dev-user-001	delete	run	cfd4fbcc-a423-4dd8-b2e4-872d3ff3aac2	{"bulk": true, "status": "failed"}	2026-01-12 23:47:48.08013+00	12287e9c7fa21185a0751198628ae022123191f400fc998e4d922a857cec0ca8	bdf5398ff8a87b4d4854fabd26e219cc830b4fc3c1aa1decbb4f3206df4fee78
68	dev-user-001	create	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-12 23:48:13.807405+00	bdf5398ff8a87b4d4854fabd26e219cc830b4fc3c1aa1decbb4f3206df4fee78	7ef1020f3596c899876daae59fa53076ab06705333d82a9567e0dba7ea9f901a
69	dev-user-001	approve	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"comment": null, "previous_status": "waiting_approval"}	2026-01-13 00:06:51.315545+00	7ef1020f3596c899876daae59fa53076ab06705333d82a9567e0dba7ea9f901a	9aefa39259da28aed37e8c83cc0c8541fc366ed6a19fb0beafeb8dab6e4400b8
118	dev-user-001	pause	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"previous_status": "running"}	2026-01-16 11:24:06.658083+00	aca03e3f92164b990e6a8f3c4f6136414eb11c963535d5ef2cdf31a075f3319e	26c2a2d961fe39ba0ae7f0967600172b02a8d0c4dcb573c7fcd673adef1aecc2
70	system	step10.articles_generated	step	step10	{"run_id": "2ecbafd2-fbce-4122-9452-4b31c3ee825d", "articles": [{"word_count": 3275, "output_digest": "3afda58ce9b9ff3d", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3812, "output_digest": "a78bda2abd4d044f", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4411, "output_digest": "275f734cef0d6734", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2995, "output_digest": "96dda4d348440d61", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-01-13 00:26:23.873272+00	9aefa39259da28aed37e8c83cc0c8541fc366ed6a19fb0beafeb8dab6e4400b8	aef8fe374a00ddae148082209d7b456d52ed0e2db1b095ce582d3756b58f02de
71	dev-user-001	step11_settings_submitted	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"image_count": 3}	2026-01-13 00:33:27.389473+00	aef8fe374a00ddae148082209d7b456d52ed0e2db1b095ce582d3756b58f02de	a3b193f1e84f4fc0e20dab5893ef17450b01c0bfcc80ca94ecb931464b4ed6cf
72	dev-user-001	step11_completed	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"image_count": 3}	2026-01-13 00:58:44.47538+00	a3b193f1e84f4fc0e20dab5893ef17450b01c0bfcc80ca94ecb931464b4ed6cf	132d78988d524b83e76d636321d156305c991b0926e7c3788604df87b5d7b429
73	dev-user-001	step11_completed	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"image_count": 3}	2026-01-13 00:59:28.813482+00	132d78988d524b83e76d636321d156305c991b0926e7c3788604df87b5d7b429	a37b9bebf2a8730643d4d74ee16cb4ac73c92c2599ec6e49d898e434a6b015d3
74	dev-user-001	step11_settings_submitted	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"image_count": 3}	2026-01-13 02:03:59.256739+00	a37b9bebf2a8730643d4d74ee16cb4ac73c92c2599ec6e49d898e434a6b015d3	d38b2930bde49d8b04dfa86a1bb7b106507864210ada4d90b7b14699b34f5b82
75	dev-user-001	step11_completed	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"image_count": 3}	2026-01-13 02:07:01.003302+00	d38b2930bde49d8b04dfa86a1bb7b106507864210ada4d90b7b14699b34f5b82	08e741560477fb1ac75c40b6b3c294a6eeb96291afa7c8f52ab3bc81f06852e2
76	dev-user-001	create	run	56322d2b-0abf-442d-809e-958385d0c917	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-14 00:07:27.462093+00	08e741560477fb1ac75c40b6b3c294a6eeb96291afa7c8f52ab3bc81f06852e2	134acca0bd74d543e1e4f748e7aa19e9ee68f0d6a9df893df0ec61f2f99399ab
77	dev-user-001	create	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-14 01:44:55.733773+00	134acca0bd74d543e1e4f748e7aa19e9ee68f0d6a9df893df0ec61f2f99399ab	5feadd1425e4f3f23b877a6dcb85412d92efd06c0d9cf07e817afb842fa2ddbd
78	dev-user-001	approve	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"comment": null, "previous_status": "waiting_approval"}	2026-01-14 02:03:27.33489+00	5feadd1425e4f3f23b877a6dcb85412d92efd06c0d9cf07e817afb842fa2ddbd	d7c215de8f3abf97ac6519538c3a3c6cc9091eee59cf70a797f28ac2f63deb2a
79	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:03:38.974069+00	d7c215de8f3abf97ac6519538c3a3c6cc9091eee59cf70a797f28ac2f63deb2a	712c0b2588b2120d28041781106c8ce4c8594fe2139c0f95243f3ebe4669a696
80	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:03:40.617626+00	712c0b2588b2120d28041781106c8ce4c8594fe2139c0f95243f3ebe4669a696	916e3bbccc01ec4be9470fd3bac1d6ba20c26efa2fea5511a5b016269f44b56b
81	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:03:45.255515+00	916e3bbccc01ec4be9470fd3bac1d6ba20c26efa2fea5511a5b016269f44b56b	e47c8af40f039e0b56843b577cbd3c8e04160769e092eca3c395e2120f571054
82	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:03:46.275418+00	e47c8af40f039e0b56843b577cbd3c8e04160769e092eca3c395e2120f571054	727952ffafc59d0bf1350de43484f3f11de5e1aaf5734554b92b6d4883cae806
83	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:03:46.99739+00	727952ffafc59d0bf1350de43484f3f11de5e1aaf5734554b92b6d4883cae806	4a09aa77ae137f543ad547a3a4784a43bec74e423f15aa4173f139cf2fd71c01
84	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:06:51.42408+00	4a09aa77ae137f543ad547a3a4784a43bec74e423f15aa4173f139cf2fd71c01	c8f31b4354fb26096f1c1cd04c0fbedb2eeaf0b5bda1acc0ca5c508299e668cd
85	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:06:52.468414+00	c8f31b4354fb26096f1c1cd04c0fbedb2eeaf0b5bda1acc0ca5c508299e668cd	ddb49959154ae23e042b215e4e5d02b273201b53926d628e647fd5bdc2864dfd
86	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:06:53.125289+00	ddb49959154ae23e042b215e4e5d02b273201b53926d628e647fd5bdc2864dfd	4c64f2186e8e6d5b57ba0503e0ef847791240e379e1a8b7786edf83193e20ecd
87	dev-user-001	pause	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:06:56.58764+00	4c64f2186e8e6d5b57ba0503e0ef847791240e379e1a8b7786edf83193e20ecd	3df5111e4be3f86000f60f60417801a76c995684d6de82e363a73e41f2672f79
88	dev-user-001	cancel	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"previous_status": "running"}	2026-01-14 02:07:04.903136+00	3df5111e4be3f86000f60f60417801a76c995684d6de82e363a73e41f2672f79	3bb91dfccc4163c19411d94189c1512d4d681a9b3ce1ea82c78e0ee6d0bdee16
89	dev-user-001	delete	run	1ee2aeb1-a647-4ba6-bb66-84208d8ad100	{"status": "cancelled", "keyword": "eラーニング 企業"}	2026-01-14 02:07:04.947794+00	3bb91dfccc4163c19411d94189c1512d4d681a9b3ce1ea82c78e0ee6d0bdee16	155d28b9f8ffef728ffd504288804b51ea0848e27bc97fe7ffe35b9cc4517330
90	dev-user-001	create	run	9502fa0f-e471-4531-98dc-2c76cbe7020c	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-14 02:07:18.547109+00	155d28b9f8ffef728ffd504288804b51ea0848e27bc97fe7ffe35b9cc4517330	92becb887bd4ffe51c6697bb8862477e69f69f987d542ffbbb11bd014cf67a39
91	dev-user-001	pause	run	9502fa0f-e471-4531-98dc-2c76cbe7020c	{"previous_status": "running"}	2026-01-14 02:07:33.363229+00	92becb887bd4ffe51c6697bb8862477e69f69f987d542ffbbb11bd014cf67a39	88befbed6b1c19c7687d5714da907e847a7e38ccd17b7a501734cd1b0c9c1970
92	dev-user-001	approve	run	9502fa0f-e471-4531-98dc-2c76cbe7020c	{"comment": null, "previous_status": "waiting_approval"}	2026-01-14 03:53:32.789022+00	88befbed6b1c19c7687d5714da907e847a7e38ccd17b7a501734cd1b0c9c1970	7448605bc1c35051db9631a184076464b65c80d5d54114b92c5b26efcdaacc4b
93	dev-user-001	continue	run	9502fa0f-e471-4531-98dc-2c76cbe7020c	{"current_step": "post_approval", "previous_status": "paused"}	2026-01-14 04:06:12.180952+00	7448605bc1c35051db9631a184076464b65c80d5d54114b92c5b26efcdaacc4b	f7310d7cce8ad8c1dcbd1d179802a12b0f9d68f35185a64973ce73ac38289b28
96	dev-user-001	reject	run	71fe623d-a7d7-4500-9c8b-decc7824f110	{"reason": "3-Aが不適切", "previous_status": "waiting_approval"}	2026-01-14 05:02:10.197186+00	cd77991706aea00c660a5cca8b22d88bd5f1163290eb3657c9b2973c6efb476f	a0aebd761ab7be88a86127c8ebd3da2886e45b0c2e3acfb188d12a6a240f4ca3
141	dev-user-001	delete	run	de000005-0000-0000-0000-000000000005	{"bulk": true, "status": "failed"}	2026-01-20 04:45:56.21107+00	7666ebd40f0d277bb46b7fd6536a32cdc815f6a572a12987ea4e45f2a912cec9	e80e8698802051c00c3f7b3e0a198d271e1bcc4f03de7ef5ea3bd74656edd5b0
94	system	step10.articles_generated	step	step10	{"run_id": "9502fa0f-e471-4531-98dc-2c76cbe7020c", "articles": [{"word_count": 7599, "output_digest": "417090aabb7a2736", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 4592, "output_digest": "2a04155740e5fd6d", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4690, "output_digest": "db96ab3e8a81595f", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2668, "output_digest": "171ed4eee6b286cc", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-01-14 04:28:51.278156+00	f7310d7cce8ad8c1dcbd1d179802a12b0f9d68f35185a64973ce73ac38289b28	33b0621e23b174e83b9c2b3d03c72bb7618600a8658967d8b2a1a79a2160b435
95	dev-user-001	create	run	71fe623d-a7d7-4500-9c8b-decc7824f110	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-14 04:56:45.449459+00	33b0621e23b174e83b9c2b3d03c72bb7618600a8658967d8b2a1a79a2160b435	cd77991706aea00c660a5cca8b22d88bd5f1163290eb3657c9b2973c6efb476f
97	dev-user-001	create	run	375481da-2a52-4485-affa-c94ecffb8f2a	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-14 05:13:16.639101+00	a0aebd761ab7be88a86127c8ebd3da2886e45b0c2e3acfb188d12a6a240f4ca3	5bd2202cbe58a38f2ddd3dfaa9b9da074347b82c47567fd6be5d09731ad8c458
98	dev-user-001	cancel	run	375481da-2a52-4485-affa-c94ecffb8f2a	{"previous_status": "running"}	2026-01-14 05:18:16.335331+00	5bd2202cbe58a38f2ddd3dfaa9b9da074347b82c47567fd6be5d09731ad8c458	b5a19b0b0062a8a8a9a4a626b0a872de9f2a6727fb8b22a5a4bf4d18d53a6941
99	dev-user-001	delete	run	375481da-2a52-4485-affa-c94ecffb8f2a	{"bulk": true, "status": "cancelled"}	2026-01-14 05:22:26.640173+00	b5a19b0b0062a8a8a9a4a626b0a872de9f2a6727fb8b22a5a4bf4d18d53a6941	8c651549e0046b5c5c6b6ccecbf6c5456551661c58b60740b590f953fb6c984c
100	dev-user-001	delete	run	71fe623d-a7d7-4500-9c8b-decc7824f110	{"bulk": true, "status": "failed"}	2026-01-14 05:22:26.735494+00	8c651549e0046b5c5c6b6ccecbf6c5456551661c58b60740b590f953fb6c984c	078423d45bcfff83ee8e1e19adaeae97d246b6d979a1a27f242096e9929e0c64
101	dev-user-001	delete	run	9502fa0f-e471-4531-98dc-2c76cbe7020c	{"bulk": true, "status": "failed"}	2026-01-14 05:22:26.813602+00	078423d45bcfff83ee8e1e19adaeae97d246b6d979a1a27f242096e9929e0c64	ebbb20a7abe2b8deacb032d1444700955b177c53a6136899471c6498c39668e4
102	dev-user-001	cancel	run	56322d2b-0abf-442d-809e-958385d0c917	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_approval"}	2026-01-14 05:22:27.057882+00	ebbb20a7abe2b8deacb032d1444700955b177c53a6136899471c6498c39668e4	2de598d813e7786f195d334d8456b472a4a347d36ea0f63d43f899016e3e56bb
103	dev-user-001	delete	run	56322d2b-0abf-442d-809e-958385d0c917	{"bulk": true, "status": "cancelled"}	2026-01-14 05:22:27.061523+00	2de598d813e7786f195d334d8456b472a4a347d36ea0f63d43f899016e3e56bb	8abe6c55467c11f0f18ed1269858764a8eb054abe91e043d4a9dfcb13d9c388f
104	dev-user-001	delete	run	de000001-0001-4000-8000-000000000001	{"bulk": true, "status": "failed"}	2026-01-14 05:22:27.14915+00	8abe6c55467c11f0f18ed1269858764a8eb054abe91e043d4a9dfcb13d9c388f	627e4b4fe8c2ee7dd4dbb800625fba72d2c313ca55d750370d5c2fe76b82db37
105	dev-user-001	delete	run	de000002-0002-4000-8000-000000000002	{"bulk": true, "status": "waiting_image_input"}	2026-01-14 05:22:27.169919+00	627e4b4fe8c2ee7dd4dbb800625fba72d2c313ca55d750370d5c2fe76b82db37	2a0eb43a5a66034efdbaefe0b19c0098329f569c343c49a66a82192e1b27b36b
106	dev-user-001	delete	run	2ecbafd2-fbce-4122-9452-4b31c3ee825d	{"bulk": true, "status": "completed"}	2026-01-14 05:22:27.2318+00	2a0eb43a5a66034efdbaefe0b19c0098329f569c343c49a66a82192e1b27b36b	9c5424adbd7bc21fb63b23eddae9ca4e10b59274ba9e9d5922a5aaefcf930d1b
107	dev-user-001	create	run	d78f2e9a-d984-4155-be9c-7ca78980f66e	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-14 05:22:40.882736+00	9c5424adbd7bc21fb63b23eddae9ca4e10b59274ba9e9d5922a5aaefcf930d1b	3961e5aba17f8d0978b77fedc875de845c6e9ecf3597bf7491b48ecd8a80a5d8
108	dev-user-001	step3_review	run	d78f2e9a-d984-4155-be9c-7ca78980f66e	{"approved": ["step3b"], "retrying": ["step3a", "step3c"], "next_action": "waiting_retry_completion", "retry_counts": {"step3a": 1, "step3c": 1}, "step_instructions": {"step3a": "修正のテスト", "step3c": "修正のテスト"}}	2026-01-14 05:27:31.976897+00	3961e5aba17f8d0978b77fedc875de845c6e9ecf3597bf7491b48ecd8a80a5d8	bff8786aa11914d0c6df235124b1d3436efd8f223670337df002143fb605a36b
109	dev-user-001	step3_review	run	d78f2e9a-d984-4155-be9c-7ca78980f66e	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-01-14 05:29:22.843736+00	bff8786aa11914d0c6df235124b1d3436efd8f223670337df002143fb605a36b	b5a27d527f39598db99b22ee7acea6d7f40cd5dddb74eeb213d0251f803e9bd1
110	dev-user-001	create	run	3bf5c695-4c4c-4cad-ae18-7534dbd367a8	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-14 06:23:32.552352+00	b5a27d527f39598db99b22ee7acea6d7f40cd5dddb74eeb213d0251f803e9bd1	69dba8f28697509295c255dca313ddb86d516d7ba73e00f04f9bc09cd01a6f35
111	dev-user-001	step3_review	run	3bf5c695-4c4c-4cad-ae18-7534dbd367a8	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-01-14 06:30:06.155579+00	69dba8f28697509295c255dca313ddb86d516d7ba73e00f04f9bc09cd01a6f35	36a255f132b368ba8009966894b3034c2322a2314b92547bc3845f2b4627d17f
112	dev-user-001	pause	run	3bf5c695-4c4c-4cad-ae18-7534dbd367a8	{"previous_status": "running"}	2026-01-14 06:31:35.809149+00	36a255f132b368ba8009966894b3034c2322a2314b92547bc3845f2b4627d17f	2978f66fbe83de87ee26121d2e54c177e093bceb4aeea8febb96388b8a817ac5
113	dev-user-001	delete	run	d78f2e9a-d984-4155-be9c-7ca78980f66e	{"bulk": true, "status": "failed"}	2026-01-16 09:22:56.456647+00	2978f66fbe83de87ee26121d2e54c177e093bceb4aeea8febb96388b8a817ac5	d314575775d9919aad7212cd530cb8c4765c9823d18ff3ac0baa875787495d5e
114	dev-user-001	cancel	run	3bf5c695-4c4c-4cad-ae18-7534dbd367a8	{"reason": "delete", "previous_status": "paused"}	2026-01-16 09:22:58.762158+00	d314575775d9919aad7212cd530cb8c4765c9823d18ff3ac0baa875787495d5e	825751657bfeece55861834abe86c201c9114b40dfd9a878abc8ba6b9d6c2f98
115	dev-user-001	delete	run	3bf5c695-4c4c-4cad-ae18-7534dbd367a8	{"status": "cancelled", "keyword": "eラーニング 企業"}	2026-01-16 09:22:58.766595+00	825751657bfeece55861834abe86c201c9114b40dfd9a878abc8ba6b9d6c2f98	7f76192448f8e87c65ad62ff63ab9f8bf79d6eb0cad7045daab07043a2072ebc
116	dev-user-001	create	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-16 11:14:33.034851+00	7f76192448f8e87c65ad62ff63ab9f8bf79d6eb0cad7045daab07043a2072ebc	97417ae365ae34204eadd08b85d0200e0c5cf1c80c295035e8e4c7a6a7c7e5df
117	dev-user-001	step3_review	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-01-16 11:23:33.341751+00	97417ae365ae34204eadd08b85d0200e0c5cf1c80c295035e8e4c7a6a7c7e5df	aca03e3f92164b990e6a8f3c4f6136414eb11c963535d5ef2cdf31a075f3319e
119	dev-user-001	resume	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"resume_from": "step5", "workflow_id": "48b17938-48a5-45ff-af7a-88a163cb85d4", "deleted_steps": ["step5", "step6", "step6_5", "step7a", "step7b", "step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-16 12:35:13.691997+00	26c2a2d961fe39ba0ae7f0967600172b02a8d0c4dcb573c7fcd673adef1aecc2	558273d6884ad4543d8e07881c31df7219e50f2348008dc636db9eab6de15df9
120	dev-user-001	resume	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"resume_from": "step5", "workflow_id": "48b17938-48a5-45ff-af7a-88a163cb85d4", "deleted_steps": ["step5", "step6", "step6_5", "step7a", "step7b", "step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-16 12:39:09.214292+00	558273d6884ad4543d8e07881c31df7219e50f2348008dc636db9eab6de15df9	a263291f7a448eebf333410776f746ff8eb0d2b6eee6b34dad2ce00a764470d8
121	dev-user-001	resume	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"resume_from": "step5", "workflow_id": "48b17938-48a5-45ff-af7a-88a163cb85d4", "deleted_steps": ["step5", "step6", "step6_5", "step7a", "step7b", "step8", "step9", "step10", "step11", "step12"], "deleted_artifacts_count": 0}	2026-01-16 12:39:45.494306+00	a263291f7a448eebf333410776f746ff8eb0d2b6eee6b34dad2ce00a764470d8	872bb1b25fb582042d48cdfe6fc7cb7cf075f3f638fc9962b57c121941c6f36a
122	system	step10.articles_generated	step	step10	{"run_id": "48b17938-48a5-45ff-af7a-88a163cb85d4", "articles": [{"word_count": 3652, "output_digest": "812c1b04a3487997", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3966, "output_digest": "5ecc7d3904079fb2", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4243, "output_digest": "21d37ebfa10deae6", "article_number": 3, "variation_type": "実践編"}, {"word_count": 3008, "output_digest": "b26751a19041bc50", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-01-16 12:57:24.902024+00	872bb1b25fb582042d48cdfe6fc7cb7cf075f3f638fc9962b57c121941c6f36a	764323312bc66de131b70b94c60dd6a8bfbf3a6da500c52dd08310c369fe6ece
123	dev-user-001	step11_settings_submitted	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"image_count": 3}	2026-01-16 12:57:58.731647+00	764323312bc66de131b70b94c60dd6a8bfbf3a6da500c52dd08310c369fe6ece	92610445bba1a05e1bb414374b4fab3ddda7b1ebb3cfd07f5b04a40235d45e35
126	dev-user-001	step11_completed	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"image_count": 3}	2026-01-16 13:09:47.215345+00	92610445bba1a05e1bb414374b4fab3ddda7b1ebb3cfd07f5b04a40235d45e35	0e36d5940b90b07422441405b6f7edbdcdc3f658666e06c3682be6e156a8f627
127	dev-user-001	generate	step12	48b17938-48a5-45ff-af7a-88a163cb85d4	{"output_path": "storage/dev-tenant-001/48b17938-48a5-45ff-af7a-88a163cb85d4/step12/output.json", "articles_count": 4}	2026-01-16 13:18:17.923654+00	0e36d5940b90b07422441405b6f7edbdcdc3f658666e06c3682be6e156a8f627	c83598fcd1666ca39e7d99767a7c95d964c87e0790207755f0c4858eb8b27fbe
128	dev-user-001	delete	run	de000006-0000-0000-0000-000000000006	{"status": "completed", "keyword": "リモートワーク導入ガイド"}	2026-01-18 06:27:41.092432+00	c83598fcd1666ca39e7d99767a7c95d964c87e0790207755f0c4858eb8b27fbe	7b1eed8654c4dced8e2b28f3c65ebb91f7986ce7fae2a2135fbc141f34a6c7f4
129	dev-user-001	create	run	3c350a98-ba86-4853-b87a-5bbc3ba88770	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-19 07:14:23.290941+00	7b1eed8654c4dced8e2b28f3c65ebb91f7986ce7fae2a2135fbc141f34a6c7f4	7179b6581bd791f1bdde53b83f907092c58f840e6e214ca403d147cee3a8a927
130	dev-user-001	step3_review	run	3c350a98-ba86-4853-b87a-5bbc3ba88770	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-01-19 07:25:58.005456+00	7179b6581bd791f1bdde53b83f907092c58f840e6e214ca403d147cee3a8a927	2f277f1ca582499cacc12e8d45b950d6dce9c2082300ae8659693abde0781109
131	dev-user-001	retry	step	3c350a98-ba86-4853-b87a-5bbc3ba88770/step8	{"new_attempt_id": "84a46a7a-8a59-42d8-a13e-a985719c4d62", "previous_status": "failed"}	2026-01-19 07:34:14.225737+00	2f277f1ca582499cacc12e8d45b950d6dce9c2082300ae8659693abde0781109	66d6be0fe41dd825739cd80c39628c9679e6b58470ad6ec21678e598886367c1
132	dev-user-001	retry	step	3c350a98-ba86-4853-b87a-5bbc3ba88770/step8	{"new_attempt_id": "38de009c-a83d-4030-9c2d-0d417a715bb3", "previous_status": "failed"}	2026-01-19 07:43:22.458571+00	66d6be0fe41dd825739cd80c39628c9679e6b58470ad6ec21678e598886367c1	1c932935aa8abfac0652507d7fcf787a72d7076855a244ba8998c81d1f22892e
133	system	step10.articles_generated	step	step10	{"run_id": "3c350a98-ba86-4853-b87a-5bbc3ba88770", "articles": [{"word_count": 3755, "output_digest": "205f807e5701aaf3", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3670, "output_digest": "e5907982b899aaf4", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4505, "output_digest": "27b75a0b99c2a9c1", "article_number": 3, "variation_type": "実践編"}, {"word_count": 3104, "output_digest": "a8d53ac305ad9129", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-01-19 07:56:32.095347+00	1c932935aa8abfac0652507d7fcf787a72d7076855a244ba8998c81d1f22892e	4f8f73a80a9949dfdabb987e9c3a2667b215b750ed0b2ff925ca8ac1b3bf2793
134	dev-tenant-001	update_setting	api_setting	serp	{"service": "serp", "is_active": true, "has_api_key": true, "default_model": null}	2026-01-20 03:24:46.204298+00	4f8f73a80a9949dfdabb987e9c3a2667b215b750ed0b2ff925ca8ac1b3bf2793	40f65c8ff755521836feca97faf23ec0d4d966dc3564e55647bc7f3f6f0bdf21
135	dev-tenant-001	update_setting	api_setting	serp	{"service": "serp", "is_active": true, "has_api_key": true, "default_model": null}	2026-01-20 03:25:13.852707+00	40f65c8ff755521836feca97faf23ec0d4d966dc3564e55647bc7f3f6f0bdf21	09a5562e2f7347811908f3a796e2735fb54fc901ccfdd32d242118a4f04dc053
136	dev-user-001	create	run	5076ed84-160d-4997-802c-fda8e8765115	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-20 04:30:37.821164+00	09a5562e2f7347811908f3a796e2735fb54fc901ccfdd32d242118a4f04dc053	f0df5eba5456b92bbcc51e845db2de366b61e238844d95f4e7b97389f3803a91
137	dev-user-001	cancel	run	5076ed84-160d-4997-802c-fda8e8765115	{"bulk": true, "reason": "bulk_delete", "previous_status": "running"}	2026-01-20 04:45:55.801853+00	f0df5eba5456b92bbcc51e845db2de366b61e238844d95f4e7b97389f3803a91	648597fbd252ae5ac4785da5adfa14a6916cbc444e81e50e23da930ede855e83
138	dev-user-001	delete	run	5076ed84-160d-4997-802c-fda8e8765115	{"bulk": true, "status": "cancelled"}	2026-01-20 04:45:55.80742+00	648597fbd252ae5ac4785da5adfa14a6916cbc444e81e50e23da930ede855e83	867d51559a622fce29f633aa7609ab5f9ba6b55afaf9fd6e98a6ac7266155312
139	dev-user-001	cancel	run	3c350a98-ba86-4853-b87a-5bbc3ba88770	{"bulk": true, "reason": "bulk_delete", "previous_status": "waiting_image_input"}	2026-01-20 04:45:55.914835+00	867d51559a622fce29f633aa7609ab5f9ba6b55afaf9fd6e98a6ac7266155312	523b7ac334b42c4f3fa4065b865f1b5fa623e367937a15653190570a88173515
140	dev-user-001	delete	run	3c350a98-ba86-4853-b87a-5bbc3ba88770	{"bulk": true, "status": "cancelled"}	2026-01-20 04:45:55.919827+00	523b7ac334b42c4f3fa4065b865f1b5fa623e367937a15653190570a88173515	7666ebd40f0d277bb46b7fd6536a32cdc815f6a572a12987ea4e45f2a912cec9
142	dev-user-001	delete	run	48b17938-48a5-45ff-af7a-88a163cb85d4	{"bulk": true, "status": "completed"}	2026-01-20 04:45:56.283508+00	e80e8698802051c00c3f7b3e0a198d271e1bcc4f03de7ef5ea3bd74656edd5b0	54858801c28e4817989a11df9ce5a2d182eddd3dea3b1406c116a8bffbeaed1f
144	dev-user-001	delete	run	de000002-0000-0000-0000-000000000002	{"status": "cancelled", "keyword": "コンテンツマーケティング戦略2025"}	2026-01-20 04:46:12.000167+00	dc506e04c2bac6a45599a0f71e3a4d098ca9ce23a00478b08c676ab227389506	312ea86ffc41e823091c2329ce4b7dec0ac4f278125b2df3210af46b6c3e6b25
148	dev-user-001	delete	run	de000003-0000-0000-0000-000000000003	{"status": "cancelled", "keyword": "AI活用による業務効率化"}	2026-01-20 04:46:19.37125+00	a48eb9759373d3a955ba0f3cf0b13a71c1ee53586b54fdd90f9588eeaf31330f	abb5edd97af71799e449ced08e79dad193b78214d00628581662a293f5f81662
151	dev-user-001	create	run	233e0dbe-99c7-4daf-a338-ebb7d604407d	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-20 04:47:40.829117+00	1303fa06f99bf9cebbbb2fc347f7ceabc3b35c86e6a1dd8db7cdc1ecc09348a9	294610a236d166af78e48b1e32c0f41e3210c6b689c25ab8e59cc2ac8d28d2db
153	dev-tenant-001	update_setting	api_setting	github	{"service": "github", "is_active": true, "has_api_key": true, "default_model": null}	2026-01-21 11:09:20.017298+00	7fa2b48e85d367c0dad8ec48150721fd7d0a82f8c2c878a8b0346412292c3243	989d52852fdf13c43337f441f987ace081d98dc6c6691155413f18cb466a3d6f
143	dev-user-001	cancel	run	de000002-0000-0000-0000-000000000002	{"previous_status": "running"}	2026-01-20 04:46:11.97001+00	54858801c28e4817989a11df9ce5a2d182eddd3dea3b1406c116a8bffbeaed1f	dc506e04c2bac6a45599a0f71e3a4d098ca9ce23a00478b08c676ab227389506
146	dev-user-001	delete	run	de000001-0000-0000-0000-000000000001	{"status": "cancelled", "keyword": "SEOキーワード分析のコツ"}	2026-01-20 04:46:14.094038+00	856bd13f9b7a50ae099a2c195992133006832b0dba58e9241000103925c814de	a7e67d4094758b9c81c6e7752124f75466b2bf0e298b63370e514605220b9145
147	dev-user-001	cancel	run	de000003-0000-0000-0000-000000000003	{"previous_status": "waiting_approval"}	2026-01-20 04:46:19.347173+00	a7e67d4094758b9c81c6e7752124f75466b2bf0e298b63370e514605220b9145	a48eb9759373d3a955ba0f3cf0b13a71c1ee53586b54fdd90f9588eeaf31330f
152	dev-user-001	create	run	4bbee384-96a1-4272-a2e8-7789b3d40e5a	{"keyword": "eラーニング 企業", "start_workflow": true}	2026-01-20 04:52:33.935422+00	294610a236d166af78e48b1e32c0f41e3210c6b689c25ab8e59cc2ac8d28d2db	7fa2b48e85d367c0dad8ec48150721fd7d0a82f8c2c878a8b0346412292c3243
145	dev-user-001	cancel	run	de000001-0000-0000-0000-000000000001	{"previous_status": "pending"}	2026-01-20 04:46:14.068127+00	312ea86ffc41e823091c2329ce4b7dec0ac4f278125b2df3210af46b6c3e6b25	856bd13f9b7a50ae099a2c195992133006832b0dba58e9241000103925c814de
149	dev-user-001	cancel	run	de000004-0000-0000-0000-000000000004	{"reason": "delete", "previous_status": "paused"}	2026-01-20 04:46:21.309428+00	abb5edd97af71799e449ced08e79dad193b78214d00628581662a293f5f81662	4a9f3a417ce344b3cc9866939df09085ca8a19e9541c653d96f32e051300a71c
150	dev-user-001	delete	run	de000004-0000-0000-0000-000000000004	{"status": "cancelled", "keyword": "クラウドセキュリティ入門"}	2026-01-20 04:46:21.311441+00	4a9f3a417ce344b3cc9866939df09085ca8a19e9541c653d96f32e051300a71c	1303fa06f99bf9cebbbb2fc347f7ceabc3b35c86e6a1dd8db7cdc1ecc09348a9
154	dev-user-001	create	run	c43cadf2-7969-4bc2-8c1d-166be7238371	{"keyword": "ドライバー 採用 難しい", "start_workflow": true}	2026-02-03 11:36:45.907037+00	989d52852fdf13c43337f441f987ace081d98dc6c6691155413f18cb466a3d6f	24c21709926397be659c2caf830f516cc98015badbba8a4f3f96e6ec54a8a37e
155	dev-user-001	create	run	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	{"keyword": "従業員 募集 こない", "start_workflow": true}	2026-02-03 11:36:46.014075+00	24c21709926397be659c2caf830f516cc98015badbba8a4f3f96e6ec54a8a37e	d2cb0d50e428935f4102150f5041f821d0a5e6ba3be51a7e148e1300ba8dc73a
156	dev-user-001	create	run	67c73686-f144-42a5-b52c-96e02c1e04e6	{"keyword": "自動車整備士 採用難しい", "start_workflow": true}	2026-02-03 11:36:46.072643+00	d2cb0d50e428935f4102150f5041f821d0a5e6ba3be51a7e148e1300ba8dc73a	7e99aaa4d636cd94acbfec601ee0cf01abdc7bebea9d2662d5e81e5f6a65aa56
157	dev-user-001	create	run	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	{"keyword": "営業 採用 難しい", "start_workflow": true}	2026-02-03 11:36:46.126391+00	7e99aaa4d636cd94acbfec601ee0cf01abdc7bebea9d2662d5e81e5f6a65aa56	aea2e1552d2aa647d1b9f834aaee3aa6764d25f8c55a7cab422653fd5224b704
158	dev-user-001	approve_step1	run	c43cadf2-7969-4bc2-8c1d-166be7238371	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 11:38:41.649508+00	aea2e1552d2aa647d1b9f834aaee3aa6764d25f8c55a7cab422653fd5224b704	ac0a9d2cabeb4a30dd85ca7e83cf3958aed7aaef3dca5decb1259689890089ea
159	dev-user-001	approve_step1	run	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 11:38:41.737627+00	ac0a9d2cabeb4a30dd85ca7e83cf3958aed7aaef3dca5decb1259689890089ea	60839f54826cacee7eb59a951f57d5f64bf746186c1f00da290b71395237c0c1
160	dev-user-001	approve_step1	run	67c73686-f144-42a5-b52c-96e02c1e04e6	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 11:38:41.810348+00	60839f54826cacee7eb59a951f57d5f64bf746186c1f00da290b71395237c0c1	6147642f5116c5de77678cda51bcaf0e5b90bc86b74d2636e8c2d98bde1e2f1c
161	dev-user-001	approve_step1	run	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 11:38:41.886931+00	6147642f5116c5de77678cda51bcaf0e5b90bc86b74d2636e8c2d98bde1e2f1c	2b1fd9598986f70d9cab65b97a9573b0f22799866c8cc071d5191a3575a24278
162	dev-user-001	step3_review	run	c43cadf2-7969-4bc2-8c1d-166be7238371	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-02-03 11:42:00.561374+00	2b1fd9598986f70d9cab65b97a9573b0f22799866c8cc071d5191a3575a24278	033aa3225157b07a466c601b8a0047933897ec9a9f77991c02627f1563ef85ad
163	dev-user-001	step3_review	run	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-02-03 11:42:00.602171+00	033aa3225157b07a466c601b8a0047933897ec9a9f77991c02627f1563ef85ad	3111e0c046192e5b4cfe2cb23e445f8c33dc3b42d60d2b654114f832ebb78521
164	dev-user-001	step3_review	run	67c73686-f144-42a5-b52c-96e02c1e04e6	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-02-03 11:42:00.644236+00	3111e0c046192e5b4cfe2cb23e445f8c33dc3b42d60d2b654114f832ebb78521	0ddc0844eb6ebcc6d6e9d02587302aa4170d97e4f90dd587b2295cf5c57f9d0a
165	dev-user-001	step3_review	run	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	{"approved": ["step3a", "step3b", "step3c"], "retrying": [], "next_action": "proceed_to_step3_5", "retry_counts": {}, "step_instructions": {}}	2026-02-03 11:42:00.686781+00	0ddc0844eb6ebcc6d6e9d02587302aa4170d97e4f90dd587b2295cf5c57f9d0a	63055d3b8e56d09932691ed93b977331a7faa0d8344e7e52e1eedb9194bd5ddc
166	dev-user-001	retry	step	67c73686-f144-42a5-b52c-96e02c1e04e6/step8	{"new_attempt_id": "29ee8a1a-7a75-4942-9f26-3ce6939c0238", "previous_status": "failed"}	2026-02-03 11:47:26.693208+00	63055d3b8e56d09932691ed93b977331a7faa0d8344e7e52e1eedb9194bd5ddc	cd67e3762c351b27b83f2fbe0ee20ef898bf3c521472bd2526ab292b30a236cc
167	dev-user-001	retry	step	67c73686-f144-42a5-b52c-96e02c1e04e6/step8	{"new_attempt_id": "5eca8c56-b0b7-423c-8034-082f053b7339", "previous_status": "failed"}	2026-02-03 11:49:42.447529+00	cd67e3762c351b27b83f2fbe0ee20ef898bf3c521472bd2526ab292b30a236cc	ef60bc07e42a92cecd03fdfb0bd6170a0589831800ed9c2621517775a358c7d2
168	system	step10.articles_generated	step	step10	{"run_id": "c43cadf2-7969-4bc2-8c1d-166be7238371", "articles": [{"word_count": 5275, "output_digest": "3c531f4b92cbcbb9", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3086, "output_digest": "092786e499e3114f", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4930, "output_digest": "6e557758b46e9392", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2019, "output_digest": "ddccb8b167a5a5e6", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 11:50:31.738329+00	ef60bc07e42a92cecd03fdfb0bd6170a0589831800ed9c2621517775a358c7d2	0ccaed86a6cd21922c091b214ecc43c7cf4e20eca36995ba2026046ecbe1db19
169	system	step10.articles_generated	step	step10	{"run_id": "ca9bed12-f1fd-41a6-95b3-43e3fe74c238", "articles": [{"word_count": 10150, "output_digest": "718a332f5301527f", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3438, "output_digest": "0526a2ba45dbf19c", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 3923, "output_digest": "e00378eb4321d40c", "article_number": 3, "variation_type": "実践編"}, {"word_count": 1771, "output_digest": "0b4fd371a8e14663", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 11:50:41.876857+00	0ccaed86a6cd21922c091b214ecc43c7cf4e20eca36995ba2026046ecbe1db19	799090908091fe82246d8941142a9a7f29d8dcf386fd6d2a69a394e8b57eb47f
177	dev-user-001	create	run	40186126-cf83-4b8f-a524-d9ad733d4938	{"keyword": "ドライバー採用難しい", "start_workflow": true}	2026-02-03 13:24:28.217963+00	e431ab271162c81324b08afd5f4ee9786817f93061a210f1bc776cc49426cc9e	ac350fc6807feee3791473ef819af77cb4905cb72bc975095585cb653da9fd81
170	system	step10.articles_generated	step	step10	{"run_id": "c6445773-8f0c-4a5d-a5fe-fd229b3cc05f", "articles": [{"word_count": 5904, "output_digest": "fc858eb23b93eae4", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3363, "output_digest": "85282b33380258bb", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4112, "output_digest": "ae6fa2c1ad5c6538", "article_number": 3, "variation_type": "実践編"}, {"word_count": 1545, "output_digest": "2e2b77c345323840", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 11:51:08.376042+00	799090908091fe82246d8941142a9a7f29d8dcf386fd6d2a69a394e8b57eb47f	ae839c1555f114d1545429006bbdb65a46960d7dc5434e3d39d77ad90855fddf
171	dev-user-001	step11_skipped	run	c43cadf2-7969-4bc2-8c1d-166be7238371	{}	2026-02-03 11:52:15.504944+00	ae839c1555f114d1545429006bbdb65a46960d7dc5434e3d39d77ad90855fddf	a59bcbc53c8ba9e7c921a5c58a4aa73223d6f667d9b8825aaeb2308465efef89
172	dev-user-001	step11_skipped	run	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	{}	2026-02-03 11:52:15.562791+00	a59bcbc53c8ba9e7c921a5c58a4aa73223d6f667d9b8825aaeb2308465efef89	d6c969e9b8e5d32a2d37bf7167761439d831e0d89296daaadcb296394cff9602
173	dev-user-001	step11_skipped	run	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	{}	2026-02-03 11:52:15.607502+00	d6c969e9b8e5d32a2d37bf7167761439d831e0d89296daaadcb296394cff9602	831a28a0c504d7005cd91cd214dd3d4bd7d69a37c6ca79dbc618b3ddd294093f
174	system	step10.articles_generated	step	step10	{"run_id": "67c73686-f144-42a5-b52c-96e02c1e04e6", "articles": [{"word_count": 8366, "output_digest": "a135bb655b9e8b59", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 2994, "output_digest": "e2e970e0508b9a97", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 3610, "output_digest": "1f85c08a2aaa2692", "article_number": 3, "variation_type": "実践編"}, {"word_count": 1840, "output_digest": "745be804470b8c8a", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 11:54:57.331144+00	831a28a0c504d7005cd91cd214dd3d4bd7d69a37c6ca79dbc618b3ddd294093f	33d81356a55ef67141a2f7c3e549d13aa9155938a01b769838bb098e36eddfce
175	dev-user-001	step11_skipped	run	67c73686-f144-42a5-b52c-96e02c1e04e6	{}	2026-02-03 11:57:02.028845+00	33d81356a55ef67141a2f7c3e549d13aa9155938a01b769838bb098e36eddfce	e431ab271162c81324b08afd5f4ee9786817f93061a210f1bc776cc49426cc9e
185	dev-user-001	approve_step1	run	4d711f0b-58c6-4217-8325-cfd18b0d577b	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 13:25:48.591789+00	81febddbecdbe33eb12fd3ad82f27e2b2964d83ac78d315bfbaaecd4de23757e	17b117cc01f8ede4936007a2e77df5bb84c1b56600ea102fbafdabe6f8011e23
188	dev-user-001	approve	run	64133ae9-85fe-4e72-a3f4-4089044e4fc8	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 13:47:14.340199+00	91e8fdc01cb6ada2e7ce1979cbbe0d3537ffa07e836948e5c96d9e9efe2026e9	5ca4f12143bb66a4921bca1deb919a41aea539b5b71e2d1682eed7c2d0713cf0
190	dev-user-001	approve	run	90dcfdc4-ebc1-4746-a09f-a9476d268565	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 13:47:14.531767+00	f51148bb8799d802b24ef8c9397ff2b18087d643c497adbe44c6b577b456e5dc	d6101b0b18671cebeedea8f6b5739913983c0d1b78b4ad9d557c1fc7df9b08b4
193	system	step10.articles_generated	step	step10	{"run_id": "9250e89e-ab21-419b-8b02-4d623b275c67", "articles": [{"word_count": 9301, "output_digest": "150133106d69f975", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 2368, "output_digest": "fd9f465992a0c598", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4807, "output_digest": "9ac9429f45b7de96", "article_number": 3, "variation_type": "実践編"}, {"word_count": 534, "output_digest": "8b3972d105a17d51", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 13:56:35.760655+00	2dfda04fe5b89f74322f4b85b5205d9dea548c23a3f8bdc259f990da0c654747	6897550df7503fc693a67a38bf6c1d18130d0ee39dc86afd7d4c22ed80ba273a
178	dev-user-001	create	run	f92d9d06-2bbb-404a-8cee-7f574d87c12b	{"keyword": "ドライバー採用難しい", "start_workflow": true}	2026-02-03 13:24:36.223658+00	ac350fc6807feee3791473ef819af77cb4905cb72bc975095585cb653da9fd81	3eb96a09d339901093cfaae20987d8fe35806ba7602c1edc18ee00d335c03ad5
181	dev-user-001	create	run	4d711f0b-58c6-4217-8325-cfd18b0d577b	{"keyword": "自動車整備士採用難しい", "start_workflow": true}	2026-02-03 13:24:51.348393+00	550fc61ebfb4abbf89ffd3f12280140a1233f50dad0cf992198cfefb23ce910d	50597422531dcfda685a2118bef3a9c5b0409c530f6594e812c46c895c70ec79
183	dev-user-001	approve_step1	run	9250e89e-ab21-419b-8b02-4d623b275c67	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 13:25:48.408624+00	f6f967eaf549ebde4f9360cd8ed0e4d5aa2f18743c017f52d01e3b2ee2e7c991	643feb13c0f3d36219a8fdd8dbd9072aeb8161a67a66a2f6860dc87ae1e79955
186	dev-user-001	approve_step1	run	90dcfdc4-ebc1-4746-a09f-a9476d268565	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 13:25:48.649538+00	17b117cc01f8ede4936007a2e77df5bb84c1b56600ea102fbafdabe6f8011e23	46365dcceb9e7b00e32e50d469538742779e4755a1c5cd331374878beb5de457
189	dev-user-001	approve	run	4d711f0b-58c6-4217-8325-cfd18b0d577b	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 13:47:14.423828+00	5ca4f12143bb66a4921bca1deb919a41aea539b5b71e2d1682eed7c2d0713cf0	f51148bb8799d802b24ef8c9397ff2b18087d643c497adbe44c6b577b456e5dc
191	system	step10.articles_generated	step	step10	{"run_id": "4d711f0b-58c6-4217-8325-cfd18b0d577b", "articles": [{"word_count": 4389, "output_digest": "e4c6ec7eb67cfb92", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3138, "output_digest": "9c7f1fc4e0fd34c4", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4393, "output_digest": "8f3859505557940c", "article_number": 3, "variation_type": "実践編"}, {"word_count": 213, "output_digest": "b8d09ba141ba6e10", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 13:55:53.346655+00	d6101b0b18671cebeedea8f6b5739913983c0d1b78b4ad9d557c1fc7df9b08b4	9ea82b588d1a1aa6d6929cafa3224ccfbc4ca121c46e0fa5f07a9027f47d4dc3
192	system	step10.articles_generated	step	step10	{"run_id": "90dcfdc4-ebc1-4746-a09f-a9476d268565", "articles": [{"word_count": 7144, "output_digest": "33c8ef9fa12282e2", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3173, "output_digest": "47018f6eceb0ee18", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 3411, "output_digest": "ca554fbb43596268", "article_number": 3, "variation_type": "実践編"}, {"word_count": 1191, "output_digest": "ffa1da428ea7bc21", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 13:56:09.919633+00	9ea82b588d1a1aa6d6929cafa3224ccfbc4ca121c46e0fa5f07a9027f47d4dc3	2dfda04fe5b89f74322f4b85b5205d9dea548c23a3f8bdc259f990da0c654747
179	dev-user-001	create	run	9250e89e-ab21-419b-8b02-4d623b275c67	{"keyword": "ドライバー採用難しい", "start_workflow": true}	2026-02-03 13:24:51.154714+00	3eb96a09d339901093cfaae20987d8fe35806ba7602c1edc18ee00d335c03ad5	4e965eb3850119e4ea18fd632a85270232f088b973ee66f737828f6dc7370fbc
182	dev-user-001	create	run	90dcfdc4-ebc1-4746-a09f-a9476d268565	{"keyword": "営業採用難しい", "start_workflow": true}	2026-02-03 13:24:51.412712+00	50597422531dcfda685a2118bef3a9c5b0409c530f6594e812c46c895c70ec79	f6f967eaf549ebde4f9360cd8ed0e4d5aa2f18743c017f52d01e3b2ee2e7c991
187	dev-user-001	approve	run	9250e89e-ab21-419b-8b02-4d623b275c67	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 13:47:14.196102+00	46365dcceb9e7b00e32e50d469538742779e4755a1c5cd331374878beb5de457	91e8fdc01cb6ada2e7ce1979cbbe0d3537ffa07e836948e5c96d9e9efe2026e9
180	dev-user-001	create	run	64133ae9-85fe-4e72-a3f4-4089044e4fc8	{"keyword": "従業員募集こない", "start_workflow": true}	2026-02-03 13:24:51.278444+00	4e965eb3850119e4ea18fd632a85270232f088b973ee66f737828f6dc7370fbc	550fc61ebfb4abbf89ffd3f12280140a1233f50dad0cf992198cfefb23ce910d
184	dev-user-001	approve_step1	run	64133ae9-85fe-4e72-a3f4-4089044e4fc8	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 13:25:48.52894+00	643feb13c0f3d36219a8fdd8dbd9072aeb8161a67a66a2f6860dc87ae1e79955	81febddbecdbe33eb12fd3ad82f27e2b2964d83ac78d315bfbaaecd4de23757e
194	dev-user-001	step11_skipped	run	9250e89e-ab21-419b-8b02-4d623b275c67	{}	2026-02-03 22:40:27.035022+00	6897550df7503fc693a67a38bf6c1d18130d0ee39dc86afd7d4c22ed80ba273a	1a7c62a98ee947e262875e038f6605cecb3e127255a5800d968b24018823d834
195	dev-user-001	step11_skipped	run	4d711f0b-58c6-4217-8325-cfd18b0d577b	{}	2026-02-03 22:40:27.11103+00	1a7c62a98ee947e262875e038f6605cecb3e127255a5800d968b24018823d834	f17f26de8b42af11ddf5056372c17b540909983ded22f962bec6512166b68636
196	dev-user-001	step11_skipped	run	90dcfdc4-ebc1-4746-a09f-a9476d268565	{}	2026-02-03 22:40:27.150694+00	f17f26de8b42af11ddf5056372c17b540909983ded22f962bec6512166b68636	7487b5b20b153748d0aedad9d84883ac3d63a1cf21b02a6d138adb05b3f1b6ac
197	dev-user-001	retry	step	64133ae9-85fe-4e72-a3f4-4089044e4fc8/step6_5	{"new_attempt_id": "900bda38-b39f-402a-9cf6-ae670f901c9a", "previous_status": "failed"}	2026-02-03 22:40:38.880049+00	7487b5b20b153748d0aedad9d84883ac3d63a1cf21b02a6d138adb05b3f1b6ac	eef9804e85c24feb2ca0c8e46d5d55702a147746dd757ac80de0bf99814a1850
198	system	step10.articles_generated	step	step10	{"run_id": "64133ae9-85fe-4e72-a3f4-4089044e4fc8", "articles": [{"word_count": 2894, "output_digest": "26d9536b6a0875f9", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 2868, "output_digest": "897a8a389cc18ed5", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4399, "output_digest": "77ba4cde2d090fb8", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2127, "output_digest": "5e13962465ec875c", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 22:45:48.532784+00	eef9804e85c24feb2ca0c8e46d5d55702a147746dd757ac80de0bf99814a1850	62ef662e4c0031e9fa38d0c4fc1d3a0f5b170aca9e5e1e1d925f1bbd33840ba4
199	dev-user-001	step11_skipped	run	64133ae9-85fe-4e72-a3f4-4089044e4fc8	{}	2026-02-03 22:46:27.749687+00	62ef662e4c0031e9fa38d0c4fc1d3a0f5b170aca9e5e1e1d925f1bbd33840ba4	d726637c44debf91f8062135f2dce1482056b05615d01ae077ead347533c153f
200	dev-user-001	create	run	0e87f430-0bda-4e81-9a38-aa67f402ac42	{"keyword": "ドライバー採用難しい", "start_workflow": true}	2026-02-03 23:14:05.483472+00	d726637c44debf91f8062135f2dce1482056b05615d01ae077ead347533c153f	f26cd5fd4b8741cd29c6ec1486b5976b8996c07c2674e6f76df30f4a6cee68a9
201	dev-user-001	create	run	3941a942-8c1a-4244-a34b-5005a080d96a	{"keyword": "従業員募集こない", "start_workflow": true}	2026-02-03 23:14:05.566014+00	f26cd5fd4b8741cd29c6ec1486b5976b8996c07c2674e6f76df30f4a6cee68a9	41a1c2c3a2f7e1d1e3d177efd2f0597099f9a3389d6f0f465a823762e00fcfcd
202	dev-user-001	create	run	29e2016a-8679-48f0-85c6-d237ecc8d30e	{"keyword": "自動車整備士採用難しい", "start_workflow": true}	2026-02-03 23:14:05.63724+00	41a1c2c3a2f7e1d1e3d177efd2f0597099f9a3389d6f0f465a823762e00fcfcd	0e24e0ceff75536dcc78d6386f115f744d8e85de28586e8d9a1491c2adaa4691
203	dev-user-001	create	run	67dc0b59-5ff5-4d35-8fcb-92de7bdadcb4	{"keyword": "営業採用難しい", "start_workflow": true}	2026-02-03 23:14:05.754841+00	0e24e0ceff75536dcc78d6386f115f744d8e85de28586e8d9a1491c2adaa4691	20454da36f8d6d2132a397b88d9334c0aa618540c25575d201f53c24e0f6a9ed
204	dev-user-001	create	run	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	{"keyword": "ドライバー採用難しい", "start_workflow": true}	2026-02-03 23:14:37.065946+00	20454da36f8d6d2132a397b88d9334c0aa618540c25575d201f53c24e0f6a9ed	6243d6c07d11f18eea6f9c71d84fe7df254f4b6cb2e719194db8ebd05dc62079
205	dev-user-001	create	run	ce77e4a2-9c91-44d9-aade-32054e4443fa	{"keyword": "従業員募集こない", "start_workflow": true}	2026-02-03 23:14:48.262181+00	6243d6c07d11f18eea6f9c71d84fe7df254f4b6cb2e719194db8ebd05dc62079	9c14359f42934bf6361ab8b3995b8ff1ea74a04c7925bf1e9f8b22b4f937e879
206	dev-user-001	create	run	b7005fcd-2bd4-4017-9e27-b8213ff93061	{"keyword": "自動車整備士採用難しい", "start_workflow": true}	2026-02-03 23:14:48.312707+00	9c14359f42934bf6361ab8b3995b8ff1ea74a04c7925bf1e9f8b22b4f937e879	f07c45fb9c7881affb1f76c5b98e2ccfa2bfcd6195859bbc52a410fe590412cc
207	dev-user-001	create	run	736be378-e6ef-4450-afa8-be57caf8d1bc	{"keyword": "営業採用難しい", "start_workflow": true}	2026-02-03 23:14:48.367428+00	f07c45fb9c7881affb1f76c5b98e2ccfa2bfcd6195859bbc52a410fe590412cc	5415b61e7ec27cc44d9aa433fc6fcba64cea810a3e6883da589adedd12bea164
208	dev-user-001	approve_step1	run	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 23:16:51.310898+00	5415b61e7ec27cc44d9aa433fc6fcba64cea810a3e6883da589adedd12bea164	7779b5bb55aa9f9d04a3253dc9f7b962dd48ac2b352392a67ca6ddd580e2d88c
209	dev-user-001	approve_step1	run	ce77e4a2-9c91-44d9-aade-32054e4443fa	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 23:16:51.405484+00	7779b5bb55aa9f9d04a3253dc9f7b962dd48ac2b352392a67ca6ddd580e2d88c	e895ca0d669f7e57592e9f440a2de57d2f37146951211abe95661472ceaadac5
210	dev-user-001	approve_step1	run	b7005fcd-2bd4-4017-9e27-b8213ff93061	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 23:16:51.536175+00	e895ca0d669f7e57592e9f440a2de57d2f37146951211abe95661472ceaadac5	3fc1fb5d9961f0416e46fa28844a4d3f20131e5e0c5a92749b093e61e7c1b6a8
211	dev-user-001	approve_step1	run	736be378-e6ef-4450-afa8-be57caf8d1bc	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-03 23:16:51.654295+00	3fc1fb5d9961f0416e46fa28844a4d3f20131e5e0c5a92749b093e61e7c1b6a8	6f7b8b0c6b1ece274f9ca26c48b5146201ea7911d1e5eb4632c60d838974096f
212	dev-user-001	approve	run	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 23:20:56.979425+00	6f7b8b0c6b1ece274f9ca26c48b5146201ea7911d1e5eb4632c60d838974096f	89ff3fbfb2574bb05b1872ab71b2ac039ec1e37ca1b408324445f9ec1887a4ac
213	dev-user-001	approve	run	ce77e4a2-9c91-44d9-aade-32054e4443fa	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 23:20:57.020525+00	89ff3fbfb2574bb05b1872ab71b2ac039ec1e37ca1b408324445f9ec1887a4ac	c51ee1776dc0e66ecd3f14c2aa703efc3d65882ac73db3c7b20ad7dc82b446bb
214	dev-user-001	approve	run	b7005fcd-2bd4-4017-9e27-b8213ff93061	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 23:20:57.068221+00	c51ee1776dc0e66ecd3f14c2aa703efc3d65882ac73db3c7b20ad7dc82b446bb	c0241c106588e06f45c608e5a0d722b4c103f76df547f1e4701ee44441dbdde0
215	dev-user-001	approve	run	736be378-e6ef-4450-afa8-be57caf8d1bc	{"comment": null, "previous_status": "waiting_approval"}	2026-02-03 23:20:57.108185+00	c0241c106588e06f45c608e5a0d722b4c103f76df547f1e4701ee44441dbdde0	fa91c1826aa38b8f252ae43ce7188e74486c5cb3743a147378b61625cbac007a
252	dev-user-001	approve_step1	run	fe080707-f401-4ceb-812e-4612e5293992	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 03:43:50.392491+00	f622facda153e73ad03cd399a3ae329dcaf7c9c7e6e4f6352d69072b3ab94daf	ed803bc486870cd10dff47af390df6b3b2344875939db4a02f88d22d1950f82f
216	dev-user-001	retry	step	b7005fcd-2bd4-4017-9e27-b8213ff93061/step8	{"new_attempt_id": "9479bbdd-fbd6-4076-a1fe-5cf5c61819d4", "previous_status": "failed"}	2026-02-03 23:33:08.6965+00	fa91c1826aa38b8f252ae43ce7188e74486c5cb3743a147378b61625cbac007a	9ff0b115bc569b3afd8e055914006dbf300fef654a93c3820e3fb853a01edee8
217	system	step10.articles_generated	step	step10	{"run_id": "efbb3c80-e3d6-4b8b-93f2-bb4a53915a30", "articles": [{"word_count": 2932, "output_digest": "237b208b58ca13b3", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 4023, "output_digest": "27c53711ebf8c005", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 3788, "output_digest": "93af90e1f4af36ab", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2293, "output_digest": "e38b63d3c1283c73", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 23:38:48.314007+00	9ff0b115bc569b3afd8e055914006dbf300fef654a93c3820e3fb853a01edee8	beb3556b565cf0cb5bb555f4de5b583c25d732a90e05555b38eee9670588b0b6
226	dev-user-001	approve_step1	run	2628769a-47a4-41bf-9666-44c43d8bda4d	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 00:15:04.464357+00	43fb8173529152a95c0d1ccf5f7ec1eb78b375cf4883edcb359394ad23d10555	079d864c26bcd23a8ccbe3d7d84da16c2a4ee3a0d714773dc68565c70ff15536
227	dev-user-001	approve	run	2628769a-47a4-41bf-9666-44c43d8bda4d	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 00:18:05.89897+00	079d864c26bcd23a8ccbe3d7d84da16c2a4ee3a0d714773dc68565c70ff15536	d6a02c4477caa56cb2fd800df2289442f71c0bfc3a0a7d3261c4bfe3d31f4ab0
218	system	step10.articles_generated	step	step10	{"run_id": "ce77e4a2-9c91-44d9-aade-32054e4443fa", "articles": [{"word_count": 3879, "output_digest": "a4c3735a541696ab", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 4550, "output_digest": "b1e33fa3481c2064", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 3928, "output_digest": "b3bfdd658225c832", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2690, "output_digest": "b92e057b268dc9db", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 23:39:01.73092+00	beb3556b565cf0cb5bb555f4de5b583c25d732a90e05555b38eee9670588b0b6	47121edf1cd8aff09917597625203e1a53dafc6d03e9002373abd5fe516a3e6b
228	system	step10.articles_generated	step	step10	{"run_id": "2628769a-47a4-41bf-9666-44c43d8bda4d", "articles": [{"word_count": 3819, "output_digest": "3b233512222d1dc0", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3926, "output_digest": "b8194565a2f3a977", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4770, "output_digest": "c70b53206a29e13d", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2388, "output_digest": "504759478d592f3e", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-04 00:34:44.93413+00	d6a02c4477caa56cb2fd800df2289442f71c0bfc3a0a7d3261c4bfe3d31f4ab0	73e707b157348626cb9619202981175767fe8a13bacae1b0345185e5313b8f86
219	system	step10.articles_generated	step	step10	{"run_id": "b7005fcd-2bd4-4017-9e27-b8213ff93061", "articles": [{"word_count": 3985, "output_digest": "bbded1626088c129", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 4570, "output_digest": "8d668365862b5dd9", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4292, "output_digest": "59a3464b5812c571", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2403, "output_digest": "5366bf478ad1c57b", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 23:43:53.624763+00	47121edf1cd8aff09917597625203e1a53dafc6d03e9002373abd5fe516a3e6b	75c4a38c9ce1dbed6dd3bcede09c277a2051904170fcd8768f6c2a7c95a95ddf
220	dev-user-001	step11_skipped	run	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	{}	2026-02-03 23:44:34.104711+00	75c4a38c9ce1dbed6dd3bcede09c277a2051904170fcd8768f6c2a7c95a95ddf	10079418235c6395c439c2f7364a9b4e61b5e5b4e02cbf8468feaa0cfdd0bba1
221	dev-user-001	step11_skipped	run	ce77e4a2-9c91-44d9-aade-32054e4443fa	{}	2026-02-03 23:44:34.151065+00	10079418235c6395c439c2f7364a9b4e61b5e5b4e02cbf8468feaa0cfdd0bba1	7bc227e96fa0c6135cc2a614da998478632487b285088c0889e414800efc007a
223	dev-user-001	step11_skipped	run	b7005fcd-2bd4-4017-9e27-b8213ff93061	{}	2026-02-03 23:44:56.939907+00	b57f78f546e677345d2608668e1497c587b87d538b36c64f38a8b1f7fcdb5403	d277fba4c4e7f5d1a66c555fd7c6c5c1ea617ce131870cfa15669a9b81389ccb
224	dev-user-001	step11_skipped	run	736be378-e6ef-4450-afa8-be57caf8d1bc	{}	2026-02-03 23:44:57.016636+00	d277fba4c4e7f5d1a66c555fd7c6c5c1ea617ce131870cfa15669a9b81389ccb	0f86fe19f5ecadf247ece6fee8772c41f8c0f266154fa963d4160a808e2dc084
229	dev-user-001	step11_skipped	run	2628769a-47a4-41bf-9666-44c43d8bda4d	{}	2026-02-04 00:35:32.657244+00	73e707b157348626cb9619202981175767fe8a13bacae1b0345185e5313b8f86	25a476a89eaee2b79e4a36fca48176434e95c1dd9ca93df82046fd9533e53296
222	system	step10.articles_generated	step	step10	{"run_id": "736be378-e6ef-4450-afa8-be57caf8d1bc", "articles": [{"word_count": 7389, "output_digest": "9e38d72b4dc041f1", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3837, "output_digest": "0c45fee6beeee83e", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4572, "output_digest": "68d7266a43ffa770", "article_number": 3, "variation_type": "実践編"}, {"word_count": 2643, "output_digest": "a52d1cd2c71de8a9", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-03 23:44:41.863857+00	7bc227e96fa0c6135cc2a614da998478632487b285088c0889e414800efc007a	b57f78f546e677345d2608668e1497c587b87d538b36c64f38a8b1f7fcdb5403
225	dev-user-001	create	run	2628769a-47a4-41bf-9666-44c43d8bda4d	{"keyword": "ドライバー 採用 難しい", "start_workflow": true}	2026-02-04 00:14:21.928375+00	0f86fe19f5ecadf247ece6fee8772c41f8c0f266154fa963d4160a808e2dc084	43fb8173529152a95c0d1ccf5f7ec1eb78b375cf4883edcb359394ad23d10555
230	dev-user-001	create	run	0af170e5-6cff-40f4-8de4-b8e85f5c9912	{"keyword": "ドライバー 採用 難しい", "start_workflow": true}	2026-02-04 00:37:59.981937+00	25a476a89eaee2b79e4a36fca48176434e95c1dd9ca93df82046fd9533e53296	42801ce9acf207615f3a81a8a9d2b3737abb867556aea48166c528ec550cfa2f
231	dev-user-001	create	run	a5bcf4f3-d9e4-4ce2-b6d0-6deaf1194ac2	{"keyword": "ドライバー 採用 難しい", "start_workflow": true}	2026-02-04 00:43:59.914254+00	42801ce9acf207615f3a81a8a9d2b3737abb867556aea48166c528ec550cfa2f	9c86bba45a1cf2b4bd3b72c5551a61ae3f117e1ade92c1cbe5fced9c547eea63
232	dev-user-001	approve_step1	run	a5bcf4f3-d9e4-4ce2-b6d0-6deaf1194ac2	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 00:46:38.410587+00	9c86bba45a1cf2b4bd3b72c5551a61ae3f117e1ade92c1cbe5fced9c547eea63	291fe9cf02e466d07c5c148431d51ffe3d05f067506b6b18b769b1a60e5adbd2
233	dev-user-001	create	run	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	{"keyword": "ドライバー 採用 難しい", "start_workflow": true}	2026-02-04 00:47:57.588131+00	291fe9cf02e466d07c5c148431d51ffe3d05f067506b6b18b769b1a60e5adbd2	395de4048dcd6e239f15188e0b62fd9468116da9fcb1668a0cc47f80011c9801
234	dev-user-001	approve_step1	run	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 00:48:34.959283+00	395de4048dcd6e239f15188e0b62fd9468116da9fcb1668a0cc47f80011c9801	0bcba28fa3e4220d963ccf595a998c9951f06dc0705e693fc870d6b673ecc4fb
235	dev-user-001	create	run	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	{"keyword": "ドライバー 採用 難しい", "start_workflow": true}	2026-02-04 03:00:27.864523+00	0bcba28fa3e4220d963ccf595a998c9951f06dc0705e693fc870d6b673ecc4fb	2423f24076db41f52c74c7ecdc70b2b19b701c0d86ae5966e694699c0d3d9787
236	dev-user-001	approve_step1	run	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 03:02:35.294948+00	2423f24076db41f52c74c7ecdc70b2b19b701c0d86ae5966e694699c0d3d9787	afc10618db8fd0e1659985d5cb22288a436d493d520c3c85e80272f653db1c08
237	dev-user-001	create	run	fcb7741f-dd21-4ca3-98f6-1befc7c49129	{"keyword": "ドライバー 採用 難しい", "start_workflow": true}	2026-02-04 03:14:19.900768+00	afc10618db8fd0e1659985d5cb22288a436d493d520c3c85e80272f653db1c08	b08b6a536d83548e0d6f8244dd39468358e8d9579e8ef93efc43f758893a4245
238	dev-user-001	approve_step1	run	fcb7741f-dd21-4ca3-98f6-1befc7c49129	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 03:20:06.61514+00	b08b6a536d83548e0d6f8244dd39468358e8d9579e8ef93efc43f758893a4245	8cc83a58c7b47bc70f8a40b2021e57dc20261114c42f74b5cffe45d57a7887e2
239	dev-user-001	create	run	edda5f45-cc65-43e2-8030-837e22e237d4	{"keyword": "営業 採用 難しい", "start_workflow": true}	2026-02-04 03:28:50.656299+00	8cc83a58c7b47bc70f8a40b2021e57dc20261114c42f74b5cffe45d57a7887e2	0b9d03b2777d74d1873cf807710f3f115926c774efc07bccf1b750d955a77120
240	dev-user-001	create	run	83bb3054-6602-47a6-80f1-7b724c30fa69	{"keyword": "トラックドライバー 求人 書き方", "start_workflow": true}	2026-02-04 03:29:12.815521+00	0b9d03b2777d74d1873cf807710f3f115926c774efc07bccf1b750d955a77120	50298654fcaf198dbd70ad5208b42c00500373344c944b49521c7a3b61e796e9
241	dev-user-001	create	run	c46548f7-2a8d-4370-a937-9090a5afce03	{"keyword": "営業 採用 難しい", "start_workflow": true}	2026-02-04 03:29:29.400776+00	50298654fcaf198dbd70ad5208b42c00500373344c944b49521c7a3b61e796e9	eb6e7c441d93eab856d33950b8c7ba20d6e2fad6a9a363e72b7d42bc0b9e1878
242	dev-user-001	create	run	3022c25f-f16b-4816-877c-90cb9847bfb6	{"keyword": "トラックドライバー 求人 書き方", "start_workflow": true}	2026-02-04 03:29:30.18348+00	eb6e7c441d93eab856d33950b8c7ba20d6e2fad6a9a363e72b7d42bc0b9e1878	dbc9c149edbe2fa1de5ff46d21f06d7a7df2ad94d505099a5c145aec1a8cb79d
243	dev-user-001	create	run	1e9fdb8e-bed1-4055-99aa-b0df904b2331	{"keyword": "トラックドライバー 求人 書き方", "start_workflow": true}	2026-02-04 03:32:23.533582+00	dbc9c149edbe2fa1de5ff46d21f06d7a7df2ad94d505099a5c145aec1a8cb79d	d243a337a229d5e3df2a77618cd874f80f20b82b2fbaeecdb08504e9dd177852
244	dev-user-001	create	run	ba2e4594-2fde-472f-9548-01f281cbc05a	{"keyword": "営業 採用 難しい", "start_workflow": true}	2026-02-04 03:34:42.076722+00	d243a337a229d5e3df2a77618cd874f80f20b82b2fbaeecdb08504e9dd177852	9ebc127f8e4bd385cd3417e89efb1da2ee4ccda0ee58e835f1663f18515037ad
245	dev-user-001	create	run	c4f11f16-312e-4634-abc7-1a83a5196cd1	{"keyword": "トラックドライバー 求人 書き方", "start_workflow": true}	2026-02-04 03:34:59.946081+00	9ebc127f8e4bd385cd3417e89efb1da2ee4ccda0ee58e835f1663f18515037ad	af9e44a91bdb35bbb517e4a79f6ef947233c5cd546adb77ba4d3903b64b60bee
246	dev-user-001	approve_step1	run	ba2e4594-2fde-472f-9548-01f281cbc05a	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 03:36:24.475879+00	af9e44a91bdb35bbb517e4a79f6ef947233c5cd546adb77ba4d3903b64b60bee	992fb2c805c9104ca4d62b03b29d713600f39bf61481b93310d631996aa82f83
247	dev-user-001	approve_step1	run	c4f11f16-312e-4634-abc7-1a83a5196cd1	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 03:37:01.466778+00	992fb2c805c9104ca4d62b03b29d713600f39bf61481b93310d631996aa82f83	4f38522f8b3876ff09d29089a093468d495cb410df847b809d6c26743d13e853
248	dev-user-001	cancel	run	c4f11f16-312e-4634-abc7-1a83a5196cd1	{"previous_status": "running"}	2026-02-04 03:42:08.21168+00	4f38522f8b3876ff09d29089a093468d495cb410df847b809d6c26743d13e853	20d0babb3dde10a893fe02e1f5591d0844ddd2b56c80fd9b86e5191eaae47f11
249	dev-user-001	cancel	run	ba2e4594-2fde-472f-9548-01f281cbc05a	{"previous_status": "running"}	2026-02-04 03:42:08.905398+00	20d0babb3dde10a893fe02e1f5591d0844ddd2b56c80fd9b86e5191eaae47f11	3b500d20f2de7ee59864aa2f037deb95fd4e4e2c61b0c4e204e7155e9567b6a4
250	dev-user-001	create	run	2b0d02af-428d-4d33-ac92-bd35bb86b465	{"keyword": "トラックドライバー 求人 書き方", "start_workflow": true}	2026-02-04 03:42:27.890859+00	3b500d20f2de7ee59864aa2f037deb95fd4e4e2c61b0c4e204e7155e9567b6a4	ba4432eac9d596af9b59831294f4edd38f751347ca470b41bdc8a0e1b573ae48
251	dev-user-001	create	run	fe080707-f401-4ceb-812e-4612e5293992	{"keyword": "トラックドライバー 求人 書き方", "start_workflow": true}	2026-02-04 03:43:23.305627+00	ba4432eac9d596af9b59831294f4edd38f751347ca470b41bdc8a0e1b573ae48	f622facda153e73ad03cd399a3ae329dcaf7c9c7e6e4f6352d69072b3ab94daf
253	dev-user-001	create	run	460ee6fe-60bb-4454-83f9-30be3232b345	{"keyword": "トラックドライバー 求人 書き方", "start_workflow": true}	2026-02-04 03:44:20.420412+00	ed803bc486870cd10dff47af390df6b3b2344875939db4a02f88d22d1950f82f	1605c3cc978f229cddb40df46bff0fe46e0b9f04d2344fdcdcf04ff7b087da2e
254	dev-user-001	approve_step1	run	460ee6fe-60bb-4454-83f9-30be3232b345	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 03:45:27.690693+00	1605c3cc978f229cddb40df46bff0fe46e0b9f04d2344fdcdcf04ff7b087da2e	40e777b0bcd06d8d38972fb13a79134e90a6965bea165488e7eda18fe48ca01d
255	dev-user-001	approve	run	fe080707-f401-4ceb-812e-4612e5293992	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 03:45:53.70267+00	40e777b0bcd06d8d38972fb13a79134e90a6965bea165488e7eda18fe48ca01d	39247a39604d504301e419503812091b873f116f75abdf2311b024debab30e65
256	dev-user-001	approve	run	460ee6fe-60bb-4454-83f9-30be3232b345	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 03:49:07.972362+00	39247a39604d504301e419503812091b873f116f75abdf2311b024debab30e65	c445dd0ed0674c4cc2c759dea57a6a7d5d3492e96cee4c8f7fee2b780f2c7349
257	dev-user-001	retry	step	460ee6fe-60bb-4454-83f9-30be3232b345/step6_5	{"new_attempt_id": "bc2cce9e-36fd-4f24-811c-6f17baa500f9", "previous_status": "failed"}	2026-02-04 04:00:56.465668+00	c445dd0ed0674c4cc2c759dea57a6a7d5d3492e96cee4c8f7fee2b780f2c7349	e5ecd973eaea7e445bbcba9f1f57fea07a817ade09581ce93f847ff2a8358b86
258	dev-user-001	create	run	a1c79a6b-4c53-4837-8db9-c60b2a9219d4	{"keyword": "ドライバー 採用", "start_workflow": true}	2026-02-04 07:22:00.290145+00	e5ecd973eaea7e445bbcba9f1f57fea07a817ade09581ce93f847ff2a8358b86	9f13d87f12f7c053c0b35defc59092b9b7c88de38bd85374e3232932ae53327d
259	dev-user-001	create	run	f8d40443-72e7-4705-afb6-09dc53a76743	{"keyword": "ドライバー 採用", "start_workflow": true}	2026-02-04 07:23:37.98843+00	9f13d87f12f7c053c0b35defc59092b9b7c88de38bd85374e3232932ae53327d	6248f467407d5f279fc34fc97cb125dd575531634d9f0fd00e79ab529e3d417d
260	dev-user-001	approve_step1	run	f8d40443-72e7-4705-afb6-09dc53a76743	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 07:26:52.978395+00	6248f467407d5f279fc34fc97cb125dd575531634d9f0fd00e79ab529e3d417d	173114e3eaec73d3c3097ce389a28d1a901746de09384fefc9489fd0b9246b62
261	dev-user-001	approve	run	f8d40443-72e7-4705-afb6-09dc53a76743	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 08:09:05.34529+00	173114e3eaec73d3c3097ce389a28d1a901746de09384fefc9489fd0b9246b62	8fc8a719c68c1eae0ec43adb9c52bde4428a27dbdae2077f9b7531067e11f628
262	dev-user-001	create	run	02e16ff7-b095-429e-902c-dadc644bc252	{"keyword": "ドライバー 採用", "start_workflow": true}	2026-02-04 08:11:27.995977+00	8fc8a719c68c1eae0ec43adb9c52bde4428a27dbdae2077f9b7531067e11f628	ef0fd4445a1dc46a8f599cbde9bb7b5b78c77a8e42d812f4ece9e90e40a59f52
263	dev-user-001	approve_step1	run	02e16ff7-b095-429e-902c-dadc644bc252	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 08:12:00.011656+00	ef0fd4445a1dc46a8f599cbde9bb7b5b78c77a8e42d812f4ece9e90e40a59f52	6ae7c3c68d571450dc8d5bba2c0dbafdcc7b5c90ecae3183c5473869a9535cd5
264	dev-user-001	approve	run	02e16ff7-b095-429e-902c-dadc644bc252	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 08:14:56.836179+00	6ae7c3c68d571450dc8d5bba2c0dbafdcc7b5c90ecae3183c5473869a9535cd5	61c84d3ae857c2376171bc3d897dac6c14dcfdc4f3db03361cbc29b03f857b13
265	dev-user-001	create	run	894a1783-f00d-431b-89fc-f3ed0984cc1a	{"keyword": "ドライバー 採用", "start_workflow": true}	2026-02-04 08:17:07.691903+00	61c84d3ae857c2376171bc3d897dac6c14dcfdc4f3db03361cbc29b03f857b13	383b8a2b163265a272be7d3ad6ee4d34f28616814c21461f15ba2b949ee86ca0
266	dev-user-001	approve_step1	run	894a1783-f00d-431b-89fc-f3ed0984cc1a	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 10:39:03.975099+00	383b8a2b163265a272be7d3ad6ee4d34f28616814c21461f15ba2b949ee86ca0	aa3a6ae397e11fea651a91ab62155538bcb1e75d98c1c7cc63c3c44e3c1dcce6
267	dev-user-001	approve	run	894a1783-f00d-431b-89fc-f3ed0984cc1a	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 10:40:04.145734+00	aa3a6ae397e11fea651a91ab62155538bcb1e75d98c1c7cc63c3c44e3c1dcce6	b0a799111aea8a862299c3c12c4729aff1e6cde42534557d2e6adde3f40ccb1d
268	dev-user-001	create	run	34d18bb2-1742-43d7-82da-feec95f2294d	{"keyword": "ドライバー 採用", "start_workflow": true}	2026-02-04 10:43:03.632696+00	b0a799111aea8a862299c3c12c4729aff1e6cde42534557d2e6adde3f40ccb1d	1bf405ed18c90e2076f987c15f0aab9405b579543966c85ab94b6ffc83c18350
269	dev-user-001	approve_step1	run	34d18bb2-1742-43d7-82da-feec95f2294d	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 10:45:22.094021+00	1bf405ed18c90e2076f987c15f0aab9405b579543966c85ab94b6ffc83c18350	9267fc61f778f1fd12edf7a9211c38e89f9c4d6b04bdfb184bf056d3fdfb9e49
270	dev-user-001	approve	run	34d18bb2-1742-43d7-82da-feec95f2294d	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 10:48:19.595413+00	9267fc61f778f1fd12edf7a9211c38e89f9c4d6b04bdfb184bf056d3fdfb9e49	7b20e909acf436d41f8bbca338bb95684abf004496e5cea72511ca2cbe2c1834
271	dev-user-001	create	run	a87b2257-2fbf-4635-b21b-7f0779261103	{"keyword": "ドライバー 採用", "start_workflow": true}	2026-02-04 10:50:05.134604+00	7b20e909acf436d41f8bbca338bb95684abf004496e5cea72511ca2cbe2c1834	491ce9345a55942c8cd023b5d5a68a8a62da37156be745255d56d4a95d54efde
272	dev-user-001	approve_step1	run	a87b2257-2fbf-4635-b21b-7f0779261103	{"comment": null, "previous_status": "waiting_step1_approval"}	2026-02-04 10:50:49.202913+00	491ce9345a55942c8cd023b5d5a68a8a62da37156be745255d56d4a95d54efde	115e5c2f03f5b93d5bbac9b17351689b7ff3a160be35d13bce54fbd207557a7c
273	dev-user-001	approve	run	a87b2257-2fbf-4635-b21b-7f0779261103	{"comment": null, "previous_status": "waiting_approval"}	2026-02-04 10:53:43.899741+00	115e5c2f03f5b93d5bbac9b17351689b7ff3a160be35d13bce54fbd207557a7c	a8ef5ee583df6fc4ac424d16bfb98f66fb715f351f122cee8e98feb34129fbf9
274	dev-user-001	create	run	7fefa4b1-e1db-4cb9-9812-6e87946f3aa8	{"keyword": "ドライバー 採用", "start_workflow": true}	2026-02-04 11:01:16.186457+00	a8ef5ee583df6fc4ac424d16bfb98f66fb715f351f122cee8e98feb34129fbf9	52a4ead4ca113dd2e09693478878a505e6499615960088cba949766424988cb9
275	dev-user-001	retry	step	a87b2257-2fbf-4635-b21b-7f0779261103/step7a	{"new_attempt_id": "cf954e2e-10e2-465f-8206-07c918d7e134", "previous_status": "failed"}	2026-02-04 11:01:42.94744+00	52a4ead4ca113dd2e09693478878a505e6499615960088cba949766424988cb9	0cce22593d2562efd0c62a6083540a6f25b71bf6b788c7b0d00621d213bce1b0
276	dev-user-001	retry	step	a87b2257-2fbf-4635-b21b-7f0779261103/step7a	{"new_attempt_id": "676555dc-b650-4014-bf78-02eba506a5f9", "previous_status": "failed"}	2026-02-04 11:05:39.552989+00	0cce22593d2562efd0c62a6083540a6f25b71bf6b788c7b0d00621d213bce1b0	29196cc5aa6ad57d1ac1d46d4e469344dae1ce4dc604a59e77c10e587fa89aba
277	dev-user-001	retry	step	a87b2257-2fbf-4635-b21b-7f0779261103/step9	{"new_attempt_id": "7a594934-79a9-495b-b22b-28e085220c6e", "previous_status": "failed"}	2026-02-04 11:12:56.469373+00	29196cc5aa6ad57d1ac1d46d4e469344dae1ce4dc604a59e77c10e587fa89aba	1e5ca56281eee21bb8ee714dbe0f9b2baa6c110f646540c87cfdad400df5564a
278	system	step10.articles_generated	step	step10	{"run_id": "a87b2257-2fbf-4635-b21b-7f0779261103", "articles": [{"word_count": 12844, "output_digest": "ee0eaf2b767f845c", "article_number": 1, "variation_type": "メイン記事"}, {"word_count": 3084, "output_digest": "6bff100dadeb830d", "article_number": 2, "variation_type": "初心者向け"}, {"word_count": 4670, "output_digest": "1c9c8f665b5b7b94", "article_number": 3, "variation_type": "実践編"}, {"word_count": 1992, "output_digest": "d36b796adb44a76e", "article_number": 4, "variation_type": "まとめ・比較"}], "tenant_id": "dev-tenant-001", "article_count": 4}	2026-02-04 11:17:47.198634+00	1e5ca56281eee21bb8ee714dbe0f9b2baa6c110f646540c87cfdad400df5564a	e3a128aeaa3de637764f68e25ffc40ecda8f376fab6171ab7319edb95430ddbd
279	dev-user-001	step11_skipped	run	a87b2257-2fbf-4635-b21b-7f0779261103	{}	2026-02-04 11:18:39.816909+00	e3a128aeaa3de637764f68e25ffc40ecda8f376fab6171ab7319edb95430ddbd	7c8c069fa0f04ed50c457c1ed07e0e1e7168ba74ea591758270de4d6a8710dae
\.


--
-- Data for Name: diagnostic_reports; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.diagnostic_reports (id, run_id, root_cause_analysis, recommended_actions, resume_step, confidence_score, llm_provider, llm_model, prompt_tokens, completion_tokens, latency_ms, created_at) FROM stdin;
\.


--
-- Data for Name: error_logs; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.error_logs (id, run_id, step_id, source, error_category, error_type, error_message, stack_trace, context, attempt, created_at) FROM stdin;
\.


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.events (id, run_id, step_id, event_type, actor, tenant_id, payload, created_at) FROM stdin;
\.


--
-- Data for Name: github_sync_status; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.github_sync_status (id, run_id, step, github_sha, minio_digest, synced_at, status) FROM stdin;
\.


--
-- Data for Name: hearing_templates; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.hearing_templates (id, tenant_id, name, description, data, created_at, updated_at) FROM stdin;
6b3f94fe-574a-477c-bdef-eea60f5a66ae	dev-tenant-001	eラーニング企業向け	eラーニング 企業向けのデフォルトテンプレート	{"cta": {"type": "single", "single": {"url": "https://example.com/inquiry", "text": "無料相談はこちら", "description": "eラーニング導入についてのご相談"}, "staged": null, "position_mode": "ai"}, "keyword": {"status": "decided", "main_keyword": "eラーニング 企業", "theme_topics": null, "related_keywords": null, "selected_keyword": null, "competition_level": "medium", "monthly_search_volume": "1000-5000"}, "business": {"target_cv": "inquiry", "description": "eラーニングシステムの提供", "target_audience": "企業の人事・教育担当者", "target_cv_other": null, "company_strengths": "豊富な導入実績と柔軟なカスタマイズ対応"}, "strategy": {"child_topics": null, "article_style": "standalone"}, "word_count": {"mode": "ai_balanced", "target": null}}	2026-01-12 10:10:39.772915+00	2026-01-12 10:10:39.772919+00
\.


--
-- Data for Name: help_contents; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.help_contents (id, help_key, title, content, category, display_order, is_active, created_at, updated_at) FROM stdin;
1	wizard.step1.business	事業情報の入力	## 事業情報とは\n\nワークフローで生成される記事の基盤となる情報です。\n\n### 入力項目\n\n- **事業名・サービス名**: 記事内で言及される正式名称\n- **事業概要**: 何を提供しているか（100〜300文字推奨）\n- **強み・特徴**: 競合との差別化ポイント\n- **ターゲット市場**: 想定する顧客層\n\n### ポイント\n\n具体的に書くほど、生成される記事の品質が向上します。\n曖昧な表現（「良いサービス」など）は避け、数値や具体例を含めてください。	wizard	10	t	2026-01-17 01:26:21.994299	2026-01-17 01:26:21.994299
2	wizard.step1.target	ターゲット読者	## ターゲット読者の設定\n\n記事を読んでほしい人物像を明確にします。\n\n### 設定項目\n\n- **年齢層**: 20代、30〜40代、シニアなど\n- **職業・役職**: 経営者、マーケター、エンジニアなど\n- **課題・悩み**: どんな問題を抱えているか\n- **検索意図**: なぜこのキーワードで検索するか\n\n### なぜ重要か\n\nターゲットが明確だと：\n- 適切なトーン・語彙で記事が生成される\n- 読者のニーズに沿った構成になる\n- コンバージョンにつながりやすい\n\n「誰にでも」向けた記事は、結局誰にも刺さりません。	wizard	20	t	2026-01-17 01:26:22.000461	2026-01-17 01:26:22.000461
3	wizard.step2.keyword	キーワード選定	## キーワード選定\n\nSEO記事の核となるキーワードを設定します。\n\n### 入力方法\n\n1. **メインキーワード**: 記事の主軸となる検索語（必須）\n2. **サブキーワード**: 関連する補助的なキーワード（任意）\n3. **除外キーワード**: 避けたい表現やNG語（任意）\n\n### 選定のコツ\n\n- 検索ボリュームと競合度のバランスを考慮\n- ロングテールキーワードも有効\n- ユーザーの検索意図を想像する\n\n### AI提案機能\n\n「キーワード提案」ボタンで、事業情報を基にしたキーワード候補を取得できます。	wizard	30	t	2026-01-17 01:26:22.003697	2026-01-17 01:26:22.003697
4	workflow.overview	全体フロー	## SEO記事生成ワークフロー\n\n高品質なSEO記事を自動生成するワークフローです。**4種類のバリエーション記事**を一度に生成します。\n\n### フロー概要図\n\n```\n┌─────────────────────────────────────────────────────────┐\n│  【前半】人間確認あり（約15〜20分）                       │\n│                                                         │\n│  工程0 → 工程1 → 工程1.5 → 工程2 → 工程3A/3B/3C（並列） │\n│  [KW選定] [競合取得] [スコア付与] [検証]  [分析3種]      │\n│                                         ↓               │\n│                                    ★承認待ち★          │\n└─────────────────────────────────────────────────────────┘\n                          ↓ 承認後\n┌─────────────────────────────────────────────────────────┐\n│  【後半】一気通貫実行（約40〜50分）                       │\n│                                                         │\n│  工程3.5 → 工程4 → 工程5 → 工程6 → 工程6.5              │\n│  [Human要素] [戦略]  [一次情報] [強化]  [統合]           │\n│                          ↓                              │\n│  工程7A → 工程7B → 工程8 → 工程9 → 工程10               │\n│  [初稿]   [推敲]   [ファクト] [最終] [4記事生成]         │\n│                          ↓                              │\n│  工程11（オプション）→ 工程12                           │\n│  [画像生成]            [WordPress形式変換]              │\n└─────────────────────────────────────────────────────────┘\n```\n\n### 所要時間の目安\n\n| 条件 | 総所要時間 | 備考 |\n|------|-----------|------|\n| 標準（承認即時） | 約60分 | 承認待ち時間除く |\n| 画像生成あり | +10〜15分 | 画像枚数による |\n| 混雑時 | 最大90分 | API応答遅延時 |\n\n### ステータス一覧\n\n| ステータス | 意味 | 次のアクション |\n|-----------|------|---------------|\n| **実行中** | 工程処理中 | 完了を待つ |\n| **承認待ち** | 人間の確認が必要 | レビューして承認/却下 |\n| **完了** | 全工程終了 | ダウンロード可能 |\n| **失敗** | エラー発生 | エラー確認後、再試行 |\n\n### トラブルシューティング\n\n| 症状 | 原因 | 対処 |\n|------|------|------|\n| 工程が長時間止まる | API応答遅延 | 10分待っても進まなければ再試行 |\n| 承認後に進まない | Signal未送信 | ページ再読込後、再度承認 |\n| 全工程失敗 | APIキー問題 | 設定画面でAPIキーを確認 |	workflow	10	t	2026-01-17 01:26:22.006673	2026-01-17 01:26:22.006673
5	workflow.step3	並列分析（3A/3B/3C）	## 並列分析工程\n\n工程3では3つの分析を**同時並列**で実行します。この工程完了後に**承認待ち**となります。\n\n### 並列実行の図解\n\n```\n        ┌─────────────┐\n        │  工程2完了   │\n        └──────┬──────┘\n               │\n       ┌───────┼───────┐\n       ↓       ↓       ↓\n   ┌───────┐┌───────┐┌───────┐\n   │  3A   ││  3B   ││  3C   │  ← 同時実行（約3分）\n   │トーン ││ FAQ  ││統計   │\n   └───┬───┘└───┬───┘└───┬───┘\n       └───────┼───────┘\n               ↓\n        ┌─────────────┐\n        │ ★承認待ち★ │\n        └─────────────┘\n```\n\n### 3A: トーン分析\n\n競合記事から最適な文体・トーンを分析します。\n\n**出力例:**\n```json\n{\n  "formality": "やや丁寧（です・ます調）",\n  "expertise_level": "中級者向け",\n  "voice": "第三者視点、客観的"\n}\n```\n\n### 3B: FAQ抽出\n\n検索意図から想定される質問と回答を生成します。\n\n**出力例:**\n- Q: 〇〇と△△の違いは？\n- Q: 初心者でも使えますか？\n- Q: 料金はいくらですか？\n\n### 3C: 統計データ収集\n\n記事の信頼性を高める数値データを収集します。\n\n**出力例:**\n- 「〇〇市場は2024年に△△億円規模（出典: XX調査）」\n- 「導入企業の85%が効果を実感（出典: YY白書）」\n\n### 所要時間\n\n| 条件 | 時間 |\n|------|------|\n| 標準 | 約3分 |\n| API混雑時 | 最大5分 |\n\n### トラブルシューティング\n\n| 症状 | 原因 | 対処 |\n|------|------|------|\n| 1つだけ失敗 | API一時エラー | 失敗した工程のみ再試行 |\n| 全て失敗 | APIキー問題 | 設定画面で確認 |\n| 結果が薄い | 競合データ不足 | 工程1の結果を確認 |	workflow	20	t	2026-01-17 01:26:22.010127	2026-01-17 01:26:22.010127
6	workflow.approval	承認・却下の操作方法	## 承認フローの詳細ガイド\n\n工程3（並列分析：3A/3B/3C）が完了すると、ワークフローは「承認待ち」状態で一時停止します。この段階で人間が内容を確認し、次の工程に進むかどうかを判断します。\n\n### 画面の見方\n\nワークフロー詳細画面の上部に、オレンジ色の「承認待ち」バッジが表示されます。画面中央には、工程3の出力サマリー（トーン分析結果・FAQ候補・収集された統計データ）がタブ形式で並び、それぞれの内容をプレビューできます。画面下部に「承認」（緑色）と「却下」（赤色）の2つのボタンが配置されています。\n\n### 承認の判断基準\n\n以下の観点で出力内容を確認してください：\n\n| 確認観点 | チェックポイント |\n|---------|----------------|\n| **トーン（3A）** | ターゲット読者に適した文体か、専門用語の量は適切か |\n| **FAQ（3B）** | 想定される質問が網羅されているか、回答が的確か |\n| **統計（3C）** | 信頼できる出典か、数値は最新か、記事との関連性 |\n\n### 操作手順\n\n**承認する場合**：\n1. 各タブの内容を確認\n2. 「承認」ボタン（緑色、画面右下）をクリック\n3. 確認ダイアログで「承認して続行」を選択\n4. 工程4（詳細アウトライン）が自動的に開始\n\n**却下する場合**：\n1. 「却下」ボタン（赤色）をクリック\n2. 却下理由を入力（必須、50文字以上推奨）\n3. 再実行する工程を選択（デフォルト：工程3全体）\n4. 「却下を確定」をクリック\n\n### ベストプラクティス\n\n- **迷ったら却下**：品質に疑問があれば再実行する方が最終品質は高まります\n- **具体的な理由を記載**：「トーンが硬すぎる」より「30代女性向けなので、もう少し親しみやすい表現に」と具体的に\n- **部分再実行を活用**：3Aのみ問題なら3Aだけ再実行し、3B/3Cは維持できます	workflow	30	t	2026-01-17 01:26:22.013142	2026-01-17 01:26:22.013142
7	github.issue	Issue作成	## GitHub Issue連携\n\n生成した記事に関するIssueを自動作成できます。\n\n### 用途\n\n- 記事のレビュー依頼\n- 修正タスクの管理\n- 公開スケジュールの追跡\n\n### 作成されるIssue\n\n```\nタイトル: [記事] {キーワード} - レビュー依頼\n本文:\n- 記事概要\n- 生成日時\n- ワークフローへのリンク\n- チェックリスト\n```\n\n### 設定\n\n事前にGitHubリポジトリとの連携設定が必要です。\n設定画面でリポジトリURLとアクセストークンを登録してください。	github	10	t	2026-01-17 01:26:22.015886	2026-01-17 01:26:22.015886
8	github.pr	PR管理	## Pull Request管理\n\n記事をMarkdownファイルとしてPRを作成できます。\n\n### 機能\n\n- **自動ブランチ作成**: `article/{keyword}-{date}` 形式\n- **ファイル配置**: 指定ディレクトリに記事を追加\n- **PR本文生成**: 記事情報を含むテンプレート\n\n### ワークフロー例\n\n1. 記事生成完了\n2. 「PRを作成」ボタンをクリック\n3. 確認画面でタイトル・本文を編集\n4. PRが作成される\n5. レビュー後マージ\n\n### 注意事項\n\n- 連携リポジトリへの書き込み権限が必要\n- ブランチ保護ルールがある場合、直接マージ不可の場合あり	github	20	t	2026-01-17 01:26:22.018079	2026-01-17 01:26:22.018079
9	review.types	レビュータイプと品質管理サイクル	## レビュータイプと品質管理\n\nレビュー機能は、記事の品質を担保するための**最終防衛ライン**です。公開前に必ず実行し、品質基準を満たしているか確認してください。\n\n### ワークフロー全体での位置づけ\n\nレビューは「工程10」に相当し、生成（工程7）→ファクトチェック（工程8）→品質向上（工程9）を経た記事の最終確認を行います。ここでOKが出れば公開準備へ進みます。\n\n### レビュータイプの使い分け\n\n| タイプ | いつ重要か | 見落としがちな問題 |\n|--------|-----------|-------------------|\n| **SEO** | 検索流入を狙う記事 | メタディスクリプション不足 |\n| **読みやすさ** | 一般読者向け記事 | 専門用語の過多 |\n| **事実確認** | データを扱う記事 | 出典リンク切れ |\n| **ブランド** | 企業公式コンテンツ | トーンの不一致 |\n\n### 効率的なレビュー運用\n\n1. **全タイプ一括実行**: 最初は全観点でレビュー\n2. **弱点集中**: 過去に指摘が多い観点を重点確認\n3. **定期的な基準見直し**: 月次で品質基準を更新\n\n### チーム運用での品質基準\n\n複数人で運用する場合は、「公開OK」の基準を明文化しておいてください。例：「SEOスコア70以上 AND Critical指摘ゼロ」など。	review	10	t	2026-01-17 01:26:22.020829	2026-01-17 01:26:22.020829
10	wizard.step1.strategy	記事戦略の選択	## 記事戦略\n\n生成する記事の全体戦略を選択します。\n\n### 標準（単一記事）\n\n- 1つのキーワードに対して1記事を生成\n- シンプルなSEO記事に最適\n- 初めての方におすすめ\n\n### トピッククラスター\n\n- メインキーワードを中心に、関連記事群を設計\n- 内部リンク構造を自動生成\n- 中〜大規模なコンテンツ戦略向け\n\n### 選択の基準\n\n| 状況 | 推奨戦略 |\n|------|----------|\n| 単発の記事が必要 | 標準 |\n| サイト全体のSEOを強化したい | トピッククラスター |\n| 特定テーマで権威性を確立したい | トピッククラスター |\n| 試しに使ってみたい | 標準 |\n\n### 注意点\n\nトピッククラスターは複数記事を生成するため、処理時間とコストが増加します。	wizard	15	t	2026-01-17 01:26:22.024184	2026-01-17 01:26:22.024184
11	wizard.step2.related	関連キーワードの活用	## 関連キーワード\n\nメインキーワードと一緒に使用する関連語句です。\n\n### 関連キーワードの種類\n\n- **共起語**: メインキーワードと一緒に検索されやすい語\n- **類義語**: 同じ意味を持つ別の表現\n- **派生語**: メインキーワードから派生した語句\n- **ロングテール**: より具体的な検索フレーズ\n\n### 設定方法\n\n1. 「関連キーワードを追加」をクリック\n2. キーワードを入力（カンマ区切りで複数可）\n3. AI提案機能も活用可能\n\n### 活用のコツ\n\n- 5〜10個程度が目安\n- 無理に詰め込まない（自然な文章が優先）\n- 検索意図が異なるものは避ける\n\n### 記事への反映\n\n関連キーワードは本文中に自然な形で組み込まれます。\n無理な詰め込みはせず、読みやすさを優先します。	wizard	35	t	2026-01-17 01:26:22.026837	2026-01-17 01:26:22.026837
12	wizard.step2.volume	検索ボリュームの見方	## 検索ボリューム\n\nキーワードが月間でどれくらい検索されているかの指標です。\n\n### ボリュームの目安\n\n| ボリューム | 評価 | 特徴 |\n|-----------|------|------|\n| 10,000以上 | 高 | 競合が激しい、上位表示が難しい |\n| 1,000〜10,000 | 中 | バランスが良い、狙い目 |\n| 100〜1,000 | 低〜中 | ロングテール、コンバージョン率高め |\n| 100未満 | 低 | ニッチ、特定ニーズ向け |\n\n### 注意点\n\n- ボリュームだけで判断しない\n- 競合度も合わせて確認\n- ビジネスとの関連性を重視\n\n### トレンドの確認\n\n検索ボリュームは季節や時事によって変動します。\n表示されるデータは過去12ヶ月の平均値です。\n\n### 推奨する選び方\n\n- 最初は中〜低ボリュームから始める\n- 実績を積んでから高ボリュームに挑戦\n- ニッチキーワードの積み重ねも有効	wizard	40	t	2026-01-17 01:26:22.030257	2026-01-17 01:26:22.030257
13	wizard.step3.type	記事タイプの選び方	## 記事タイプの選び方\n\n**読者の検索意図**に最適なタイプを選ぶことで、記事の効果が大きく変わります。\n\n### タイプ別の特徴と具体例\n\n| タイプ | 向いているキーワード例 | 生成される記事イメージ |\n|--------|----------------------|---------------------|\n| **網羅型** | 「SEOとは」「確定申告 やり方」 | 基礎から応用まで体系的に解説 |\n| **深掘り型** | 「React Hooks 使い方」「投資信託 リスク」 | 1つのテーマを徹底的に掘り下げ |\n| **比較型** | 「WordPress vs Wix」「転職サイト おすすめ」 | 複数の選択肢をメリデメ比較 |\n| **ハウツー型** | 「YouTube 始め方」「確定申告 書き方」 | STEP1→2→3の手順形式 |\n| **リスト型** | 「副業 おすすめ10選」「時短家電 ランキング」 | 箇条書き・番号付きで整理 |\n\n### よくある間違い\n\n| 状況 | 間違った選択 | 正しい選択 |\n|------|------------|-----------|\n| 「〇〇 比較」で検索されるKW | 網羅型 | **比較型** |\n| 「〇〇 やり方」で検索されるKW | リスト型 | **ハウツー型** |\n| 初心者向けの入門記事 | 深掘り型 | **網羅型** |\n\n### プロのコツ\n\n1. **検索結果を確認**: 上位記事がどのタイプか見てみる\n2. **読者の次のアクション**: 読後に何をしてほしいかで選ぶ\n3. **迷ったら網羅型**: 最も汎用性が高い\n\n### 複合タイプの活用\n\n2つまで組み合わせ可能。例：\n- 「網羅型＋ハウツー型」→ 基礎知識＋実践手順\n- 「比較型＋リスト型」→ 複数商品の比較ランキング	wizard	50	t	2026-01-17 01:26:22.033844	2026-01-17 01:26:22.033844
24	workflow.step10	工程10: 最終出力	## 工程10: 最終出力\n\n品質向上済みの記事を最終形式で出力します。\n\n### 処理内容\n\n1. **最終整形**\n   - Markdown形式の最終調整\n   - 見出し番号の正規化\n   - 空白・改行の整理\n\n2. **メタ情報生成**\n   - SEOタイトル（60文字以内）\n   - メタディスクリプション（120文字以内）\n   - OGP情報\n\n3. **品質スコア算出**\n   - 総合スコア\n   - 各観点別スコア（SEO、可読性、独自性）\n\n### 所要時間\n\n約30秒〜1分\n\n### 出力形式\n\n- **Markdown**: 記事本文\n- **JSON**: メタ情報・スコア\n- **HTML**: プレビュー用\n\n### 次のステップ\n\nこの後、画像生成（工程11）またはWordPress形式変換（工程12）に進みます。\n画像生成をスキップすることも可能です。\n\n### ダウンロード\n\nこの時点で記事をダウンロードできます。\n形式：Markdown / HTML / JSON	workflow	70	t	2026-01-17 01:26:22.06647	2026-01-17 01:26:22.06647
14	wizard.step3.cta	CTAの設計と配置	## CTA（Call To Action）の設計\n\n**CTA = 読者に起こしてほしい具体的なアクション**。記事のゴールを達成するための重要な要素です。\n\n### CTAタイプと具体例\n\n| CTAタイプ | 具体例 | 向いている記事 |\n|----------|-------|--------------|\n| **資料請求** | 「無料ホワイトペーパーをダウンロード」 | BtoB、専門性の高い記事 |\n| **問い合わせ** | 「無料相談を予約する」 | サービス紹介、比較記事 |\n| **会員登録** | 「30日間無料で試す」 | SaaS、ツール紹介記事 |\n| **購入** | 「今すぐ購入」「カートに入れる」 | EC、商品レビュー記事 |\n| **メルマガ** | 「最新情報を受け取る」 | ブログ、情報系記事 |\n\n### 配置位置の効果\n\n| 位置 | 効果 | クリック率目安 |\n|------|------|--------------|\n| 記事冒頭（導入後） | 即決ユーザー向け | 低（1-2%） |\n| 記事中盤 | 興味が高まった瞬間 | 中（2-3%） |\n| **記事末尾** | 読了者向け、最も効果的 | **高（3-5%）** |\n| 複数配置 | 機会損失を防ぐ | 合計で最大化 |\n\n### よくある間違い\n\n- **CTAと記事内容のミスマッチ**: 「SEOとは」の記事に「今すぐ購入」\n- **押しつけがましいCTA**: 記事より目立つボタン、過度な繰り返し\n- **行動が不明確**: 「詳しくはこちら」→何が起きるか分からない\n\n### ベストプラクティス\n\n1. **1記事1ゴール**: メインCTAは1種類に絞る\n2. **価値を先に**: 「無料で〇〇がわかる」のように得られるものを明示\n3. **ハードルを下げる**: 「1分で完了」「クレカ登録不要」\n\n### CTAを設定しない方がいい場合\n\n- 純粋な情報提供記事（用語解説など）\n- ブランド認知目的の記事\n- まだ信頼関係が築けていない初期接点の記事	wizard	55	t	2026-01-17 01:26:22.037174	2026-01-17 01:26:22.037174
15	wizard.step4.wordcount	文字数の決め方	## 文字数の決め方\n\n**「何文字書くか」ではなく「読者が必要とする情報量」**で考えるのがポイントです。\n\n### キーワード別の文字数目安\n\n| キーワードの特徴 | 文字数目安 | 理由 |\n|----------------|-----------|------|\n| 「〇〇とは」（入門） | 2,000〜3,000字 | 基本情報を簡潔に |\n| 「〇〇 やり方」（実践） | 3,000〜5,000字 | 手順+補足説明 |\n| 「〇〇 比較」（検討） | 4,000〜6,000字 | 複数項目の詳細比較 |\n| 「〇〇 おすすめ」（まとめ） | 5,000〜8,000字 | 複数選択肢の紹介 |\n| 専門的な解説 | 6,000〜10,000字 | 深い情報+事例 |\n\n### よくある間違い\n\n| 間違い | なぜダメか | 改善策 |\n|--------|----------|--------|\n| 「長いほどSEOに強い」 | 冗長な記事は離脱率UP | **競合の平均文字数を参考に** |\n| 「短く簡潔に」 | 情報不足で検索意図を満たせない | **読者の疑問を網羅する** |\n| 「きっちり〇〇文字」 | 文字数稼ぎで質が下がる | **内容優先、文字数は結果** |\n\n### プロの決め方\n\n1. **競合記事を3〜5本チェック**: 上位表示されている記事の文字数を確認\n2. **検索意図から逆算**: 「この疑問に答えるには何が必要？」\n3. **足りない情報を追加**: 競合にない独自価値を加える\n\n### 文字数別の記事イメージ\n\n```\n1,500字以下 → ニュースや速報（読了1-2分）\n2,000〜3,000字 → 標準的なブログ記事（読了3-5分）\n4,000〜5,000字 → しっかり解説記事（読了7-10分）\n6,000字以上 → 完全ガイド・長編解説（読了10分以上）\n```\n\n### 設定のコツ\n\n- **初めてなら3,000〜4,000字**: 最もバランスが良い\n- **実際は±20%の変動あり**: 内容の充実度を優先\n- **読了時間も意識**: 長すぎると離脱率が上がる	wizard	60	t	2026-01-17 01:26:22.040394	2026-01-17 01:26:22.040394
16	wizard.step5.cta	CTA詳細設定のコツ	## CTA詳細設定\n\nCTAの効果を最大化するための具体的な設定方法です。\n\n### CTAテキストの書き方\n\n**良い例と悪い例**\n\n| NG例 | なぜダメか | 改善例 |\n|------|----------|--------|\n| 「こちら」 | 何が起きるか不明 | 「無料資料をダウンロード」 |\n| 「送信」 | 冷たい印象 | 「無料で相談する」 |\n| 「登録」 | メリットが不明 | 「30日間無料で試す」 |\n| 「クリック」 | 価値が伝わらない | 「特典を受け取る」 |\n\n### 効果的なCTAの公式\n\n```\n[動詞] + [得られるもの] + [ハードル軽減]\n\n例：\n「無料で」+「SEOガイドを」+「今すぐダウンロード」\n「3分で」+「見積もりを」+「取得する」\n「登録なしで」+「デモを」+「体験する」\n```\n\n### 訴求ポイントのパターン\n\n| パターン | 具体例 | 効果 |\n|---------|-------|------|\n| **限定性** | 「今週末まで」「先着100名」 | 緊急性を演出 |\n| **無料** | 「0円」「無料」「タダ」 | 心理的ハードルを下げる |\n| **簡単** | 「1分で完了」「入力3項目」 | 面倒くささを解消 |\n| **安心** | 「しつこい営業なし」「いつでも解約OK」 | 不安を払拭 |\n| **実績** | 「10,000社導入」「満足度98%」 | 信頼性を向上 |\n\n### リンク先URLの注意点\n\n- **専用LP推奨**: 記事から直接トップページはNG\n- **遷移を最小化**: フォームは記事のすぐ次のページに\n- **モバイル対応**: スマホで見やすいか必ず確認\n\n### CTA周辺の文章（リードコピー）\n\nCTAボタンの直前に置く説得文も重要：\n\n```\n悪い例：\n「お問い合わせはこちら」\n\n良い例：\n「ここまで読んでいただいた方限定で、\nSEO診断レポートを無料でプレゼント中。\nサイトの改善ポイントが3分でわかります。」\n```\n\n### チェックリスト\n\n- [ ] CTAテキストに動詞が含まれている\n- [ ] 得られる価値が明確\n- [ ] ハードルを下げる要素がある\n- [ ] 記事内容とCTAが一致している\n- [ ] モバイルでもタップしやすいサイズ	wizard	70	t	2026-01-17 01:26:22.043239	2026-01-17 01:26:22.043239
17	wizard.step6.confirm	最終確認のチェックポイント	## 最終確認画面\n\n**ワークフロー開始前の最後の砦**。ここで見逃すと、やり直しにコストがかかります。\n\n### 必ず確認すべき5項目\n\n| 確認項目 | よくあるミス | チェック方法 |\n|---------|------------|------------|\n| **キーワード** | 誤字脱字、表記ゆれ | 声に出して読む |\n| **ターゲット** | 抽象的すぎる | 「この人は実在する？」と問う |\n| **記事タイプ** | 検索意図と不一致 | 競合上位を再確認 |\n| **文字数** | 多すぎ/少なすぎ | 競合の平均と比較 |\n| **CTA** | 記事内容とミスマッチ | 読者の次の行動を想像 |\n\n### 見落としやすいポイント\n\n**1. キーワードの表記ゆれ**\n```\nNG: 「引越し」と「引っ越し」が混在\nOK: どちらかに統一（検索ボリュームで判断）\n```\n\n**2. 事業情報の具体性**\n```\nNG: 「良いサービスを提供」\nOK: 「導入企業の95%が1年以上継続利用」\n```\n\n**3. ターゲットの絞り込み**\n```\nNG: 「ビジネスマン全般」\nOK: 「経理経験3年未満の中小企業担当者」\n```\n\n### 見積もり情報の見方\n\n| 項目 | 目安 | 超えている場合 |\n|------|------|--------------|\n| 所要時間 | 10〜20分 | 文字数を減らす検討 |\n| APIコスト | 50〜100円 | 文字数・画像枚数を見直し |\n| 画像枚数 | 3〜5枚 | 本当に必要か再検討 |\n\n### 修正が必要な場合\n\n- **「編集」ボタン**: 各セクションから直接戻れる\n- **「戻る」ボタン**: 1ステップずつ戻る\n- **最初から**: 大幅な変更なら新規作成がおすすめ\n\n### 開始前の最終チェックリスト\n\n- [ ] キーワードに誤字脱字がない\n- [ ] 競合上位の記事タイプと一致している\n- [ ] ターゲット像が具体的\n- [ ] 文字数が妥当（競合比較済み）\n- [ ] CTAが記事の目的に合っている\n- [ ] 見積もりコストが予算内\n\n### 開始後は変更不可\n\n> ワークフロー開始後は設定変更できません。\n> 「なんか違う」と思ったら、ここで止まって見直してください。\n> やり直しのコストは、確認のコストよりはるかに大きいです。	wizard	80	t	2026-01-17 01:26:22.045832	2026-01-17 01:26:22.045832
25	workflow.step11	工程11: 画像生成	## 工程11: 画像生成\n\n記事に挿入する画像をAIで生成します（オプション）。\n\n### 概要\n\n- 記事内容に基づいた画像を自動生成\n- 挿入位置を指定可能\n- 複数の画像スタイルから選択\n\n### 処理フロー\n\n1. **設定確認**: 画像枚数・スタイルを指定\n2. **位置提案**: AIが最適な挿入位置を提案\n3. **指示入力**: 各画像の生成指示を編集\n4. **生成実行**: 画像を生成\n5. **レビュー**: 結果を確認、必要に応じて再生成\n6. **統合**: 記事に画像を組み込み\n\n### 所要時間\n\n画像1枚あたり約30秒〜1分\n\n### スキップする場合\n\n「画像生成をスキップ」を選択すると、工程12に直接進みます。\n後から画像を追加したい場合は、再度工程11を実行できます。\n\n### 詳細設定\n\n詳しくは「画像生成」カテゴリのヘルプを参照してください。	workflow	80	t	2026-01-17 01:26:22.069683	2026-01-17 01:26:22.069683
18	workflow.step0	工程0: キーワード分析	## 工程0: キーワード分析\n\nワークフローの起点となる工程です。入力されたキーワードを多角的に分析し、記事戦略の土台を構築します。\n\n### 処理フロー図\n\n```\n┌──────────────┐\n│ キーワード入力 │\n└──────┬───────┘\n       ↓\n┌──────────────┐\n│ 検索意図分析  │ ← 4タイプに分類\n└──────┬───────┘\n       ↓\n┌──────────────┐\n│ 関連KW拡張   │ ← サジェスト・共起語\n└──────┬───────┘\n       ↓\n┌──────────────┐\n│ 出力: 分析JSON│\n└──────────────┘\n```\n\n### 検索意図の4タイプ\n\n| タイプ | 意味 | 例 |\n|--------|------|-----|\n| Informational | 情報収集 | 「〇〇とは」「〇〇 やり方」 |\n| Navigational | 特定サイト | 「△△ 公式」「□□ ログイン」 |\n| Commercial | 比較検討 | 「〇〇 おすすめ」「△△ 比較」 |\n| Transactional | 購入・申込 | 「〇〇 購入」「△△ 申し込み」 |\n\n### 出力例\n\n```json\n{\n  "main_keyword": "クラウド会計 比較",\n  "search_intent": "Commercial",\n  "related_keywords": ["freee", "マネーフォワード", "弥生"],\n  "suggested_headings": ["選び方", "機能比較", "料金比較"]\n}\n```\n\n### 所要時間と変動要因\n\n| 条件 | 時間 |\n|------|------|\n| 標準 | 約1〜2分 |\n| 関連KW多数 | 最大3分 |\n\n### トラブルシューティング\n\n| 症状 | 原因 | 対処 |\n|------|------|------|\n| 関連KWが少ない | ニッチすぎるKW | より一般的なKWを試す |\n| 検索意図が不適切 | KWが曖昧 | より具体的なKWに変更 |	workflow	5	t	2026-01-17 01:26:22.049118	2026-01-17 01:26:22.049118
19	workflow.step1	工程1: 競合記事収集	## 工程1: 競合記事収集\n\n検索上位の競合記事をスクレイピングし、分析用データを収集します。\n\n### 処理フロー図\n\n```\n┌──────────────┐\n│ Google検索   │ ← キーワードで検索\n└──────┬───────┘\n       ↓\n┌──────────────┐\n│ 上位10〜20件 │ ← URL・タイトル取得\n│ 記事を取得   │\n└──────┬───────┘\n       ↓\n┌──────────────────────┐\n│ 各記事をスクレイピング │\n│ ・見出し構造(H1〜H4)   │\n│ ・本文テキスト        │\n│ ・文字数・段落数      │\n└──────┬───────────────┘\n       ↓\n┌──────────────┐\n│ 出力: CSV    │\n└──────────────┘\n```\n\n### 収集される情報\n\n| 項目 | 説明 | 用途 |\n|------|------|------|\n| URL | 記事のアドレス | 参照用 |\n| タイトル | ページタイトル | タイトル設計の参考 |\n| 見出し構造 | H1〜H4の階層 | 構成案の参考 |\n| 本文 | 記事全文 | トーン・内容分析 |\n| 文字数 | 総文字数 | 目標文字数の参考 |\n\n### 出力例（CSV形式）\n\n```\nrank,url,title,word_count,h2_count\n1,https://example.com/article1,クラウド会計とは,5200,8\n2,https://example.com/article2,会計ソフト比較,4800,6\n```\n\n### 所要時間と変動要因\n\n| 条件 | 時間 | 理由 |\n|------|------|------|\n| 標準 | 約2〜3分 | 10記事程度 |\n| 記事が長い | 最大5分 | スクレイピング量増加 |\n| アクセス制限 | +1〜2分 | リトライ発生 |\n\n### トラブルシューティング\n\n| 症状 | 原因 | 対処 |\n|------|------|------|\n| 取得件数が少ない | アクセス制限 | 時間を置いて再試行 |\n| 一部記事が空 | JS描画サイト | 分析対象から除外 |\n| 文字化け | エンコード問題 | 自動補正あり |	workflow	12	t	2026-01-17 01:26:22.051974	2026-01-17 01:26:22.051974
20	workflow.step2	工程2: 競合データ検証	## 工程2: 競合データ検証\n\n工程1で収集した競合データを検証し、記事構成案の素案を作成します。\n\n### 処理フロー図\n\n```\n┌────────────────┐\n│ 工程1のCSV読込 │\n└──────┬─────────┘\n       ↓\n┌────────────────┐\n│ データ品質検証 │\n│ ・重複チェック │\n│ ・文字数確認   │\n│ ・見出し整合性 │\n└──────┬─────────┘\n       ↓\n┌────────────────┐\n│ スコアリング   │ ← 各記事に品質スコア付与\n└──────┬─────────┘\n       ↓\n┌────────────────┐\n│ 構成案素案作成 │\n└────────────────┘\n```\n\n### 品質スコアの基準\n\n| スコア | 基準 | 扱い |\n|--------|------|------|\n| A (80-100) | 文字数十分、見出し構造良好 | 重点参考 |\n| B (60-79) | 標準的な品質 | 参考 |\n| C (40-59) | 一部データ欠損 | 補助的参考 |\n| D (0-39) | 品質不足 | 除外 |\n\n### 出力例\n\n```markdown\n## 推奨構成案（素案）\n\n### H2候補\n1. クラウド会計とは（競合8/10記事で採用）\n2. 主要サービス比較（競合7/10記事で採用）\n3. 選び方のポイント（競合6/10記事で採用）\n4. 料金プラン（競合5/10記事で採用）\n\n### 推奨文字数: 4,500〜5,500字\n（競合平均: 5,100字）\n```\n\n### 所要時間\n\n| 条件 | 時間 |\n|------|------|\n| 標準 | 約1〜2分 |\n| データ量多い | 最大3分 |\n\n### トラブルシューティング\n\n| 症状 | 原因 | 対処 |\n|------|------|------|\n| スコアが全体的に低い | 競合データ不足 | 工程1を再実行 |\n| 構成案が貧弱 | ニッチなKW | 関連KWを追加 |\n| 処理が長い | CSV行数過多 | 上位10件に絞る |	workflow	15	t	2026-01-17 01:26:22.055043	2026-01-17 01:26:22.055043
21	workflow.step4-6	工程4-6: アウトライン生成	## 工程4-6: アウトライン生成フロー\n\n並列分析（3A/3B/3C）の結果を統合し、詳細なアウトラインを作成します。\n\n### 工程4: 統合アウトライン\n\n並列分析の結果を1つの構成案に統合：\n- トーン設定の反映\n- FAQ要素の組み込み\n- 統計データの配置計画\n\n### 工程5: 詳細化\n\n各セクションの詳細を決定：\n- 小見出しの追加\n- 段落構成の設計\n- 引用・事例の配置\n\n### 工程6: 最終調整\n\nSEO最適化と読みやすさの調整：\n- キーワード密度の確認\n- 見出し階層の最適化\n- 文字数配分の微調整\n\n### 承認ポイント\n\n工程3完了後に承認が必要です。\nアウトラインを確認し、問題なければ承認してください。\n\n### 修正が必要な場合\n\n却下して、修正理由を記入してください。\n指定工程から再実行されます。	workflow	40	t	2026-01-17 01:26:22.057657	2026-01-17 01:26:22.057657
22	workflow.step7	工程7: 本文生成	## 工程7: 本文生成\n\nアウトラインに基づいて、記事本文を生成します。\n\n### 処理内容\n\n1. **セクション別生成**\n   - 各見出しに対応する本文を作成\n   - 前後の文脈を考慮した一貫性確保\n   - 指定トーンでの文章生成\n\n2. **要素の組み込み**\n   - FAQ（質問と回答）\n   - 統計データと出典\n   - 事例・具体例\n\n3. **構造化**\n   - 段落分け\n   - リスト・表の作成\n   - 強調・引用の適用\n\n### 所要時間\n\n文字数により変動（3,000字で約2〜3分）\n\n### 出力\n\n- 完成度の高い記事本文\n- Markdown形式で構造化\n- メタ情報（タイトル、description）\n\n### 品質チェック\n\n生成された本文は次工程でファクトチェック・品質向上が行われます。\nこの時点では下書き品質とお考えください。	workflow	50	t	2026-01-17 01:26:22.06042	2026-01-17 01:26:22.06042
23	workflow.step8-9	工程8-9: ファクトチェック・品質向上	## 工程8-9: ファクトチェック・品質向上\n\n生成された本文の品質を検証・向上させます。\n\n### 工程8: ファクトチェック\n\n事実確認と信頼性の検証：\n\n| チェック項目 | 内容 |\n|-------------|------|\n| 統計データ | 出典の確認、数値の妥当性 |\n| 主張 | 根拠の有無、論理の整合性 |\n| 固有名詞 | 正式名称、スペルミス |\n| 日付・期間 | 時制の適切性 |\n\n### 工程9: 品質向上\n\n文章品質の改善：\n\n- **可読性向上**: 長文の分割、難解な表現の平易化\n- **SEO最適化**: キーワード密度、内部リンク\n- **エンゲージメント**: 導入文の改善、結論の強化\n- **一貫性**: トーン・表現の統一\n\n### 所要時間\n\n各工程約1〜2分\n\n### 出力\n\n- 検証済み記事本文\n- ファクトチェックレポート\n- 改善箇所のハイライト\n\n### 問題が見つかった場合\n\n自動修正可能なものは修正されます。\n重大な問題は警告として表示されます。	workflow	60	t	2026-01-17 01:26:22.06367	2026-01-17 01:26:22.06367
26	workflow.step12	工程12: WordPress HTML	## 工程12: WordPress形式変換\n\n記事をWordPressに投稿可能なHTML形式に変換します。\n\n### 処理内容\n\n1. **HTML変換**\n   - Markdown → HTML\n   - WordPress互換の構造\n   - クラス・ID付与\n\n2. **画像処理**\n   - img タグの生成\n   - alt 属性の設定\n   - キャプション追加\n\n3. **SEO要素**\n   - 構造化データ（JSON-LD）\n   - Open Graph タグ\n   - Twitter Card\n\n### 出力形式\n\n```html\n<!-- 記事本文 -->\n<article class="seo-article">\n  <h1>タイトル</h1>\n  <p>本文...</p>\n</article>\n\n<!-- メタ情報 -->\n<script type="application/ld+json">\n  {...}\n</script>\n```\n\n### ダウンロード\n\n- **HTMLファイル**: そのままWordPressに貼り付け可能\n- **画像ファイル**: 別途アップロード用\n\n### 注意事項\n\n- テーマによってはスタイルの調整が必要\n- 画像URLは相対パスで出力されます\n- カスタムフィールドは手動設定が必要	workflow	90	t	2026-01-17 01:26:22.072336	2026-01-17 01:26:22.072336
27	workflow.retry	工程の再実行手順	## 工程再実行の詳細ガイド\n\nエラー発生時や出力品質に問題がある場合、特定の工程だけを再実行できます。全体を最初からやり直す必要はありません。\n\n### 再実行が必要なケース\n\n| 状況 | 原因例 | 対処 |\n|------|--------|------|\n| エラーで工程が失敗 | APIタイムアウト、一時的な障害 | 同一工程を再実行 |\n| 出力内容が不十分 | トーンが合わない、情報不足 | 同一工程を再実行 |\n| 前工程の修正が必要 | 構成案の見直し | 該当工程から再実行 |\n\n### 画面操作手順\n\n**Step 1: 工程パネルを開く**\nワークフロー詳細画面で、左側の工程一覧から再実行したい工程をクリックします。選択された工程は青色のハイライトで表示されます。\n\n**Step 2: 再実行ボタンを押す**\n工程詳細パネル右上の「再実行」ボタン（円形矢印アイコン、青色）をクリックします。失敗した工程の場合は、ボタンがオレンジ色で強調表示されています。\n\n**Step 3: 再実行範囲を選択**\nダイアログで以下のいずれかを選択：\n- **この工程のみ**：選択した工程だけを再実行\n- **この工程以降すべて**：選択した工程から最終工程まで再実行\n\n**Step 4: 実行を確定**\n「実行」ボタンをクリックすると再実行が開始されます。\n\n### 依存関係の注意点\n\n工程間には依存関係があります。例えば工程2を再実行すると、工程3A/3B/3Cも自動的に再実行対象になります。ダイアログに影響範囲が表示されるので、確認してから実行してください。\n\n### 再実行できない場合\n\n- **実行中の工程**：完了を待つか、キャンセルが必要\n- **承認済み工程の前工程**：承認を取り消してから再実行\n\n### コストと履歴\n\n再実行にはAPIコストが発生します（通常実行と同等）。すべての再実行は監査ログに記録され、「履歴」タブで確認できます。	workflow	100	t	2026-01-17 01:26:22.075364	2026-01-17 01:26:22.075364
28	workflow.artifacts	成果物の確認とダウンロード	## 成果物（アーティファクト）の確認方法\n\n各工程で生成された成果物は、ワークフロー詳細画面からいつでも確認・ダウンロードできます。\n\n### 成果物の種類と用途\n\n| 工程 | 成果物 | 形式 | 活用シーン |\n|------|--------|------|-----------|\n| 工程0 | キーワード分析 | JSON | SEO戦略の確認 |\n| 工程1 | 競合分析 | JSON/CSV | 競合サイト調査 |\n| 工程2 | 構成案 | Markdown | 記事構成の確認 |\n| 工程3A | トーン分析 | JSON | 文体の確認 |\n| 工程3B | FAQ | JSON | Q&Aセクション素材 |\n| 工程3C | 統計データ | JSON | 引用データ確認 |\n| 工程7 | 記事本文 | Markdown | 編集・レビュー |\n| 工程10 | 最終記事 | Markdown/HTML | 公開前最終確認 |\n| 工程11 | 画像 | PNG/JPG | サイト掲載用 |\n| 工程12 | WordPress HTML | HTML | CMS投稿用 |\n\n### 確認手順\n\n**Step 1: 工程を選択**\n左側の工程一覧から、確認したい工程をクリックします。完了済みの工程には緑色のチェックマークが表示されています。\n\n**Step 2: 成果物タブを開く**\n工程詳細パネルで「成果物」タブ（ファイルアイコン）をクリックします。\n\n**Step 3: プレビューまたはダウンロード**\n- **プレビュー**：「目」アイコンをクリック（形式に応じた表示）\n- **ダウンロード**：「DL」ボタンをクリック\n\n### プレビュー機能の詳細\n\n| 形式 | プレビュー内容 |\n|------|---------------|\n| Markdown | レンダリングされた見やすい表示 |\n| JSON | シンタックスハイライト付き、折りたたみ可能 |\n| HTML | 実際のブラウザ表示に近いプレビュー |\n| 画像 | サムネイル表示、クリックで拡大 |\n\n### 一括ダウンロード\n\n画面右上の「全てダウンロード」ボタンで、全工程の成果物をZIP形式で一括取得できます。フォルダ構造は `工程名/ファイル名` の形式です。\n\n### 保存期間と注意事項\n\n成果物は**30日間**保存されます。期限後は自動削除されるため、必要なファイルは早めにダウンロードしてください。ダウンロード履歴は監査ログに記録されます。	workflow	110	t	2026-01-17 01:26:22.078796	2026-01-17 01:26:22.078796
29	image.settings	画像設定	## 画像設定\n\n生成する画像の基本設定を行います。\n\n### 設定項目\n\n#### 画像枚数\n- 最小: 1枚\n- 最大: 10枚\n- 推奨: 3〜5枚（記事3,000字あたり）\n\n#### 画像スタイル\n\n| スタイル | 特徴 | 適したケース |\n|---------|------|-------------|\n| **写真風** | リアルな写真のような画像 | ビジネス記事、事例紹介 |\n| **イラスト** | 手描き風のイラスト | 親しみやすい解説記事 |\n| **インフォグラフィック** | 図解・データ可視化 | 比較記事、統計解説 |\n| **アイコン風** | シンプルなアイコン | 手順説明、リスト記事 |\n| **抽象的** | 概念を表す抽象画像 | コンセプト説明 |\n\n#### サイズ\n\n- **横長（16:9）**: アイキャッチ、本文内\n- **正方形（1:1）**: SNSシェア用\n- **縦長（9:16）**: スマホ向け\n\n### ブランドカラー\n\n指定した色を画像に反映できます。\nHEXコード（#FFFFFF形式）で入力してください。	image	10	t	2026-01-17 01:26:22.082098	2026-01-17 01:26:22.082098
30	image.positions	挿入位置の選び方	## 画像挿入位置\n\n記事内のどこに画像を配置するかを決定します。\n\n### AI提案機能\n\n「位置を提案」ボタンで、AIが最適な挿入位置を提案します：\n- 見出しの直後\n- 概念説明の箇所\n- データ・統計の箇所\n- 手順の区切り\n\n### 手動選択\n\n記事プレビューで任意の位置をクリックして追加できます。\n\n### 推奨配置\n\n| 位置 | 効果 | 推奨度 |\n|------|------|--------|\n| アイキャッチ | 第一印象、SNSシェア | ★★★ |\n| 導入部後 | 読者の関心維持 | ★★★ |\n| 各H2見出し後 | セクション区切り | ★★☆ |\n| 手順の合間 | 理解促進 | ★★☆ |\n| 結論前 | 印象付け | ★☆☆ |\n\n### 注意点\n\n- 画像が多すぎると読み込み速度に影響\n- 文脈に合った位置を選ぶ\n- モバイル表示も考慮\n\n### 位置の変更\n\nドラッグ&ドロップで位置を変更できます。\n削除は画像横の「×」ボタンで行えます。	image	20	t	2026-01-17 01:26:22.085011	2026-01-17 01:26:22.085011
31	image.instructions	画像指示の書き方	## 画像生成指示\n\n各画像に対して、生成AIへの指示を編集できます。\n\n### 基本構成\n\n```\n[被写体] + [状況・動作] + [スタイル・雰囲気]\n```\n\n### 良い指示の例\n\n```\n✅ 「オフィスでノートPCを使って仕事をしている30代のビジネスマン、\n    明るい自然光、プロフェッショナルな雰囲気」\n\n✅ 「データ分析を示す棒グラフと円グラフ、\n    青と緑を基調としたモダンなインフォグラフィック」\n\n✅ 「スマートフォンを操作する手元のクローズアップ、\n    白い背景、ミニマルなスタイル」\n```\n\n### 避けるべき指示\n\n```\n❌ 「いい感じの画像」（曖昧すぎる）\n❌ 「〇〇社の製品写真」（著作権の問題）\n❌ 「有名人の顔」（肖像権の問題）\n```\n\n### 指示のコツ\n\n1. **具体的に**: 抽象的な表現は避ける\n2. **視覚的に**: 見た目を詳細に描写\n3. **一貫性**: ブランドトーンを維持\n\n### AIの自動補完\n\n空欄の場合、記事内容から自動生成されます。\n編集で微調整することを推奨します。	image	30	t	2026-01-17 01:26:22.087508	2026-01-17 01:26:22.087508
32	image.review	生成画像の確認・リトライ	## 画像のレビュー\n\n生成された画像を確認し、必要に応じて再生成します。\n\n### 確認画面\n\n各画像について以下が表示されます：\n- サムネイル画像\n- 生成に使用した指示\n- 生成日時\n\n### 評価オプション\n\n| 操作 | 説明 |\n|------|------|\n| **承認** | この画像を採用 |\n| **リトライ** | 同じ指示で再生成 |\n| **指示変更** | 指示を編集して再生成 |\n| **削除** | この画像を使用しない |\n\n### リトライのコツ\n\n同じ指示でも結果は毎回異なります。\n気に入らない場合は2〜3回リトライしてみてください。\n\n### 指示変更時のポイント\n\n- 何が気に入らないか明確にする\n- 「〜ではなく〜」形式で伝える\n- 例：「暗すぎる」→「明るい照明で、白を基調とした背景」\n\n### 一括操作\n\n- 「全て承認」: 全画像を採用\n- 「全てリトライ」: 全画像を再生成\n\n### コストについて\n\nリトライ1回につき、1画像分のコストが発生します。	image	40	t	2026-01-17 01:26:22.090797	2026-01-17 01:26:22.090797
33	image.preview	プレビューの見方	## 画像プレビュー\n\n画像を記事に統合した状態をプレビューで確認できます。\n\n### プレビュー画面\n\n- 記事本文と画像の統合表示\n- 実際のWebページに近い見た目\n- デスクトップ/モバイル切り替え\n\n### 確認ポイント\n\n1. **配置のバランス**\n   - 画像が偏っていないか\n   - テキストとのバランス\n\n2. **サイズ感**\n   - 大きすぎ/小さすぎないか\n   - 画面幅に対する比率\n\n3. **文脈との整合**\n   - 前後のテキストと関連しているか\n   - 説明として適切か\n\n4. **読み込み体験**\n   - スクロール時の画像出現タイミング\n   - ページ全体の重さ\n\n### 表示モード\n\n| モード | 説明 |\n|--------|------|\n| デスクトップ | PC表示（幅1200px） |\n| タブレット | タブレット表示（幅768px） |\n| モバイル | スマホ表示（幅375px） |\n\n### 問題がある場合\n\n- 位置変更: ドラッグ&ドロップ\n- 画像変更: 該当画像の「編集」\n- 削除: 該当画像の「×」\n\n### 確定\n\nプレビューで問題なければ「統合を確定」で次に進みます。	image	50	t	2026-01-17 01:26:22.094	2026-01-17 01:26:22.094
34	articles.list	記事一覧と全体管理	## 記事一覧画面\n\n記事一覧は、SEOコンテンツ制作の**司令塔**となる画面です。ここから全記事の状況を把握し、優先度を決めて作業を進めます。\n\n### ワークフロー全体での位置づけ\n\n一覧画面は「どの記事に今注力すべきか」を判断する起点です。ステータスとレビュー状態を組み合わせて確認し、次のアクションを決定します。\n\n### 表示カラムの活用\n\n| カラム | 確認ポイント |\n|--------|-------------|\n| ステータス | 「承認待ち」を最優先で対応 |\n| レビュー | 「要修正」は早めに対処 |\n| 更新日 | 長期間放置されていないか |\n\n### 効率的な管理のコツ\n\n1. **朝一で「承認待ち」を確認**: 工程3完了後の承認作業を溜めない\n2. **「失敗」は即対応**: 原因特定→再実行のサイクルを素早く回す\n3. **完了記事は週次で棚卸し**: 公開待ちが溜まっていないか確認\n\n### チーム運用時の注意\n\n複数人で運用する場合は、担当者カラムでフィルタして自分の担当記事に集中してください。他者の作業中記事に手を出さないことがトラブル防止の基本です。	articles	10	t	2026-01-17 01:26:22.096826	2026-01-17 01:26:22.096826
35	articles.filter	検索・フィルタで効率化	## 検索・フィルタ機能\n\n記事が増えてくると、目的の記事を探すのに時間がかかります。フィルタ機能を使いこなして、**管理工数を半分以下**に削減してください。\n\n### 日常業務での活用パターン\n\n| 場面 | おすすめフィルタ |\n|------|----------------|\n| 朝の確認 | ステータス「承認待ち」 |\n| レビュー作業 | 「完了」+「未レビュー」 |\n| トラブル対応 | ステータス「失敗」 |\n| 週次棚卸し | 「完了」+期間「過去7日」 |\n\n### 保存フィルタの活用（時短のコツ）\n\n毎日同じフィルタを設定するのは時間の無駄です。よく使う条件は保存して1クリックで呼び出してください。\n\n**おすすめ保存フィルタ**:\n- 「今日の承認待ち」: ステータス「承認待ち」+期間「今日」\n- 「レビュー対象」: 「完了」+「未レビュー」\n- 「要対応」: ステータス「失敗」OR レビュー「要修正」\n\n### チーム運用でのフィルタ共有\n\n保存したフィルタはチーム内で共有できます。新人が入った際に、まず「おすすめフィルタ」を教えることで立ち上がりが早くなります。\n\n### 大量記事管理のベストプラクティス\n\n100件を超えたら、デフォルト表示を「未完了のみ」に変更することを推奨します。完了済み記事はアーカイブとして別管理する運用も検討してください。	articles	20	t	2026-01-17 01:26:22.099931	2026-01-17 01:26:22.099931
36	articles.status	ステータス管理と品質サイクル	## ステータス管理の考え方\n\nステータスは記事の「健康状態」を示す指標です。適切に管理することで、**公開事故を防ぎ**、チーム全体の生産性を向上させます。\n\n### ステータスとワークフローの関係\n\n| ステータス | ワークフロー上の意味 | 注意点 |\n|-----------|---------------------|--------|\n| 未レビュー | 工程10未実施 | 公開前に必ずレビュー |\n| 要修正 | 品質基準未達 | 放置するとボトルネックに |\n| レビュー済み | 公開準備OK | 速やかに次工程へ |\n\n### ステータス別の対応優先度\n\n1. **最優先**: 「要修正」→ 品質問題を放置しない\n2. **高**: 「未レビュー」→ 溜めると作業が滞留\n3. **中**: 「レビュー済み」→ 公開タイミングを計画\n\n### チーム運用のベストプラクティス\n\n- **日次で「要修正」ゼロを目指す**: 翌日に持ち越さない文化づくり\n- **ステータス更新はリアルタイムで**: 作業完了後すぐに変更\n- **手動変更は理由をメモ**: 監査ログで追跡可能に\n\n### よくある問題と対処法\n\n| 問題 | 原因 | 対処 |\n|------|------|------|\n| 「要修正」が溜まる | 担当者不明 | 担当者を明確に割り当て |\n| 同じ指摘が繰り返される | 根本原因未対応 | プロンプト設定を見直し |\n| ステータスが古い | 更新忘れ | 日次確認をルーティン化 |	articles	30	t	2026-01-17 01:26:22.102521	2026-01-17 01:26:22.102521
37	review.results	レビュー結果の活用と改善サイクル	## レビュー結果の読み方\n\nレビュー結果は単なる「点数表」ではありません。**次のアクションを決める判断材料**として活用してください。\n\n### ワークフローでの位置づけ\n\nレビュー結果は「工程10」の出力です。この結果を元に「公開」「修正」「再生成」の判断を下します。ここでの判断が最終品質を決定します。\n\n### 総合スコアと判断基準\n\n| スコア | 評価 | 推奨アクション |\n|--------|------|---------------|\n| 90〜100 | 優秀 | 即公開OK |\n| 70〜89 | 良好 | 軽微修正→公開 |\n| 50〜69 | 要改善 | 該当工程を再実行 |\n| 50未満 | 要大幅修正 | 設定見直し→再生成 |\n\n### 効率的な結果分析のコツ\n\n1. **Critical（🔴）を最優先**: まずCriticalがゼロかを確認\n2. **傾向を把握**: 同じ種類の指摘が複数あれば根本原因を疑う\n3. **スコア推移を確認**: 再レビュー時は前回比較で改善度を確認\n\n### チーム運用での基準統一\n\n「公開OK」の基準をチームで明文化してください。例えば「SEOスコア75以上 AND Criticalゼロ」など。曖昧な基準は品質のばらつきを生みます。\n\n### よくある分析の落とし穴\n\n- スコアだけ見て指摘内容を確認しない\n- Info（🔵）を無視して同じ指摘を繰り返す\n- 履歴を見ずに同じ修正を何度もやる	review	20	t	2026-01-17 01:26:22.105453	2026-01-17 01:26:22.105453
38	review.action	レビュー後のアクションと改善サイクル	## レビュー後のアクション\n\nレビュー結果を受けて「何をするか」を迅速に判断することが、**制作効率と品質の両立**につながります。\n\n### ワークフローでの位置づけ\n\nレビュー後のアクションは「工程10」から「工程11（画像生成）または公開準備」への橋渡しです。ここで適切な判断を下さないと、後工程で手戻りが発生します。\n\n### 判断フローチャート\n\n1. **Criticalゼロ？** → No: 該当箇所を修正\n2. **スコア70以上？** → No: 該当工程を再実行\n3. **全観点クリア？** → No: 弱い観点を改善\n4. **すべてYes** → 次の工程へ進む\n\n### 効率的な修正アプローチ\n\n| 指摘の傾向 | 効率的な対応 |\n|-----------|-------------|\n| 同じ種類が3件以上 | 根本原因を特定→工程再実行 |\n| 散発的な軽微指摘 | 個別に手動修正 |\n| SEO関連が多い | プロンプト設定を見直し |\n\n### チーム運用での効率化\n\n- **週次レビュー会**: 頻出指摘をチームで共有し、プロンプトを改善\n- **ナレッジ蓄積**: 効果的だった修正パターンを記録\n- **担当者ローテ**: 特定の人に修正が集中しないよう分散\n\n### よくある非効率パターン\n\n- スコアだけ見て「OK」と判断→Critical見落とし\n- 毎回同じ指摘を手動修正→設定を見直すべき\n- 全指摘を一人で対応→チームで分担すべき	review	30	t	2026-01-17 01:26:22.108779	2026-01-17 01:26:22.108779
39	github.branch	ブランチ操作	## ブランチ操作\n\n記事をGitHubで管理する際のブランチ操作です。\n\n### 自動ブランチ命名\n\n記事作成時、自動でブランチが作成されます：\n\n```\narticle/{keyword}-{YYYYMMDD}\n例: article/seo-tools-20250115\n```\n\n### 命名ルール\n\n- 日本語キーワードはローマ字変換\n- スペースはハイフンに変換\n- 特殊文字は除去\n- 最大50文字\n\n### 手動でブランチ名を変更\n\n1. PR作成画面で「詳細設定」を開く\n2. 「ブランチ名」フィールドを編集\n3. 保存\n\n### ブランチの状態\n\n| 状態 | 説明 |\n|------|------|\n| 作成済み | ブランチ作成完了 |\n| プッシュ済み | リモートに反映済み |\n| PRオープン | PR作成済み |\n| マージ済み | mainに統合完了 |\n\n### ブランチ保護との関係\n\nリポジトリにブランチ保護ルールがある場合：\n- 直接pushができない場合があります\n- PR経由でのマージが必要です\n- CIが必須の場合は通過を待ちます\n\n### ブランチの削除\n\nマージ後、不要になったブランチは：\n- PR画面から「ブランチを削除」\n- または設定で自動削除を有効化\n\n### 注意事項\n\n- 同名ブランチが存在する場合はエラーになります\n- 日付でユニーク性を確保していますが、同日複数作成時は連番が付きます	github	30	t	2026-01-17 01:26:22.11191	2026-01-17 01:26:22.11191
40	settings.apikeys	APIキー設定	## APIキー設定\n\n各種AIサービスのAPIキーを設定します。\n\n### 必要なAPIキー\n\n| サービス | 用途 | 必須 |\n|---------|------|------|\n| **Gemini** | 記事生成（メイン） | ○ |\n| **OpenAI** | 記事生成（代替） | △ |\n| **Anthropic** | 記事生成（代替） | △ |\n| **画像生成API** | 画像生成 | △ |\n\n※ 少なくとも1つの記事生成用APIキーが必要\n\n### 設定方法\n\n1. 設定画面で「APIキー」タブを開く\n2. 対象サービスの「編集」をクリック\n3. APIキーを入力\n4. 「保存」をクリック\n5. 接続テストで確認\n\n### APIキーの取得\n\n各サービスの公式サイトで取得：\n- [Google AI Studio](https://makersuite.google.com/app/apikey)\n- [OpenAI Platform](https://platform.openai.com/api-keys)\n- [Anthropic Console](https://console.anthropic.com/)\n\n### セキュリティ\n\n- APIキーは暗号化して保存されます\n- 画面には一部のみ表示（`sk-***...***`）\n- 削除は即時反映されます\n\n### トラブルシューティング\n\n| エラー | 原因 | 対処 |\n|--------|------|------|\n| Invalid API Key | キーが無効 | 再発行して入力し直す |\n| Rate Limit | 制限超過 | 時間をおいて再試行 |\n| Quota Exceeded | 使用量超過 | プランをアップグレード |	settings	10	t	2026-01-17 01:26:22.115074	2026-01-17 01:26:22.115074
41	settings.models	モデル選択の基準	## モデル選択\n\n記事生成に使用するAIモデルを選択します。\n\n### 利用可能なモデル\n\n#### Gemini（Google）\n| モデル | 特徴 | 推奨用途 |\n|--------|------|---------|\n| gemini-2.0-flash | 高速・低コスト | 大量生成、テスト |\n| gemini-1.5-pro | 高品質・高コスト | 重要な記事 |\n\n#### OpenAI\n| モデル | 特徴 | 推奨用途 |\n|--------|------|---------|\n| gpt-4o | バランス良好 | 汎用的な記事 |\n| gpt-4o-mini | 高速・低コスト | 大量生成 |\n\n#### Anthropic\n| モデル | 特徴 | 推奨用途 |\n|--------|------|---------|\n| claude-3.5-sonnet | 自然な文章 | 読みやすさ重視 |\n| claude-3-haiku | 高速 | 大量生成 |\n\n### 選択の基準\n\n| 優先事項 | 推奨モデル |\n|---------|-----------|\n| コスト重視 | gemini-2.0-flash, gpt-4o-mini |\n| 品質重視 | gemini-1.5-pro, gpt-4o |\n| 速度重視 | gemini-2.0-flash, claude-3-haiku |\n| 日本語品質 | claude-3.5-sonnet |\n\n### デフォルト設定\n\n設定画面で各工程のデフォルトモデルを設定できます。\nワークフロー作成時に個別に変更も可能です。\n\n### コスト目安\n\n1記事（3,000字）あたり：\n- 低コストモデル: 約10〜30円\n- 高品質モデル: 約50〜100円	settings	20	t	2026-01-17 01:26:22.118225	2026-01-17 01:26:22.118225
42	settings.prompts	プロンプト編集の注意点	## プロンプト編集\n\n各工程で使用するプロンプトをカスタマイズできます。\n\n### 編集可能な項目\n\n- システムプロンプト（AIの振る舞い）\n- ユーザープロンプト（具体的な指示）\n- 出力フォーマット指定\n\n### 変数の使用\n\nプロンプト内で使用できる変数：\n\n```\n{keyword}      - メインキーワード\n{business}     - 事業情報\n{target}       - ターゲット読者\n{word_count}   - 目標文字数\n{article_type} - 記事タイプ\n{tone}         - トーン設定\n```\n\n### 編集時の注意\n\n#### やってはいけないこと\n\n- 変数名の変更（`{keyword}` → `{kw}`）\n- 必須変数の削除\n- 出力形式の大幅な変更\n\n#### 推奨する変更\n\n- トーンの調整\n- 具体例の追加\n- 禁止事項の追加\n\n### バージョン管理\n\n- 変更は新バージョンとして保存されます\n- 過去のバージョンに戻すことが可能\n- 本番使用前にテストを推奨\n\n### テスト方法\n\n1. 「プレビュー」で変数展開を確認\n2. 「テスト実行」でサンプル生成\n3. 問題なければ「公開」\n\n### ロールバック\n\n問題が発生した場合：\n1. プロンプト設定画面を開く\n2. 「バージョン履歴」をクリック\n3. 戻したいバージョンを選択\n4. 「このバージョンを適用」\n\n### サポート\n\nプロンプト編集でお困りの場合は、サポートにお問い合わせください。	settings	30	t	2026-01-17 01:26:22.121438	2026-01-17 01:26:22.121438
\.


--
-- Data for Name: llm_models; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.llm_models (id, provider_id, model_name, model_class, cost_per_1k_input_tokens, cost_per_1k_output_tokens, is_active) FROM stdin;
1	gemini	gemini-3-pro-preview	pro	\N	\N	t
2	gemini	gemini-2.5-pro	pro	\N	\N	t
3	gemini	gemini-2.5-flash	standard	\N	\N	t
4	gemini	gemini-2.0-flash	standard	\N	\N	t
5	gemini	gemini-1.5-pro	pro	\N	\N	t
6	gemini	gemini-1.5-flash	standard	\N	\N	t
7	openai	gpt-5.2	pro	\N	\N	t
8	openai	gpt-5.2-pro	pro	\N	\N	t
9	openai	gpt-4o	standard	\N	\N	t
10	openai	gpt-4o-mini	standard	\N	\N	t
11	openai	gpt-4-turbo	standard	\N	\N	t
12	anthropic	claude-sonnet-4-5-20250929	standard	\N	\N	t
13	anthropic	claude-opus-4-5-20251101	pro	\N	\N	t
14	anthropic	claude-sonnet-4-20250514	standard	\N	\N	t
15	anthropic	claude-opus-4-20250514	pro	\N	\N	t
16	anthropic	claude-3-5-sonnet-20241022	standard	\N	\N	t
\.


--
-- Data for Name: llm_providers; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.llm_providers (id, display_name, api_base_url, is_active) FROM stdin;
gemini	Google Gemini	\N	t
openai	OpenAI	\N	t
anthropic	Anthropic Claude	\N	t
\.


--
-- Data for Name: prompts; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.prompts (id, step_name, version, content, variables, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: review_requests; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.review_requests (id, run_id, step, issue_number, issue_url, issue_state, status, review_type, review_result, created_at, updated_at, completed_at) FROM stdin;
\.


--
-- Data for Name: runs; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.runs (id, tenant_id, status, config, input_data, current_step, created_at, updated_at, started_at, completed_at, error_message, error_code, step11_state, github_repo_url, github_dir_path, last_resumed_step, fix_issue_number) FROM stdin;
b7005fcd-2bd4-4017-9e27-b8213ff93061	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "自動車整備士採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "自動車整備士採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "自動車整備士採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 23:14:48.306233+00	2026-02-03 23:44:57.55628+00	2026-02-03 23:14:48.306233+00	2026-02-03 23:27:22.470005+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
c43cadf2-7969-4bc2-8c1d-166be7238371	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": "ドライバーの人材獲得に悩んでいる採用担当者", "additional_requirements": null}, "keyword": "ドライバー 採用 難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": true, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": "ドライバーの人材獲得に悩んでいる採用担当者", "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": "ドライバーの人材獲得に悩んでいる採用担当者", "additional_requirements": null}	completed	2026-02-03 11:36:45.880402+00	2026-02-03 11:52:16.452823+00	2026-02-03 11:36:45.880402+00	2026-02-03 11:52:16.477582+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
edda5f45-cc65-43e2-8030-837e22e237d4	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}, "keyword": "営業 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "google"}, "step_configs": null, "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}	{"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}	step0	2026-02-04 03:28:50.646114+00	2026-02-04 03:28:56.897313+00	2026-02-04 03:28:50.646114+00	2026-02-04 03:28:56.902518+00	step0_keyword_selection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
0e87f430-0bda-4e81-9a38-aa67f402ac42	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-03 23:14:05.312217+00	2026-02-03 23:14:21.935507+00	2026-02-03 23:14:05.312217+00	\N	\N	\N	\N	\N	\N	\N	\N
29e2016a-8679-48f0-85c6-d237ecc8d30e	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "自動車整備士採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "自動車整備士採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "自動車整備士採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-03 23:14:05.631445+00	2026-02-03 23:14:24.036517+00	2026-02-03 23:14:05.631445+00	\N	\N	\N	\N	\N	\N	\N	\N
3941a942-8c1a-4244-a34b-5005a080d96a	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "従業員募集こない", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "従業員募集こない", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "従業員募集こない", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-03 23:14:05.559448+00	2026-02-03 23:14:30.009824+00	2026-02-03 23:14:05.559448+00	\N	\N	\N	\N	\N	\N	\N	\N
67c73686-f144-42a5-b52c-96e02c1e04e6	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "自動車整備士 採用難しい", "competitor_urls": null, "target_audience": "自動車整備士の採用に悩んでいる整備工場の経営者・人事担当者", "additional_requirements": null}, "keyword": "自動車整備士 採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": true, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": "自動車整備士の採用に悩んでいる整備工場の経営者・人事担当者", "additional_requirements": null}	{"format": "legacy", "keyword": "自動車整備士 採用難しい", "competitor_urls": null, "target_audience": "自動車整備士の採用に悩んでいる整備工場の経営者・人事担当者", "additional_requirements": null}	completed	2026-02-03 11:36:46.06473+00	2026-02-03 11:57:02.505982+00	2026-02-03 11:36:46.06473+00	2026-02-03 11:45:57.439787+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
ce77e4a2-9c91-44d9-aade-32054e4443fa	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "従業員募集こない", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "従業員募集こない", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "従業員募集こない", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 23:14:48.255856+00	2026-02-03 23:44:34.900431+00	2026-02-03 23:14:48.255856+00	2026-02-03 23:44:34.906445+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
83bb3054-6602-47a6-80f1-7b724c30fa69	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "トラックドライバー 求人 書き方", "options": {"retry_limit": 3, "repair_enabled": true, "enable_step1_approval": true}, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-2.5-pro-preview-05-06", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "blog"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step0	2026-02-04 03:29:12.80896+00	2026-02-04 03:29:16.257978+00	2026-02-04 03:29:12.80896+00	2026-02-04 03:29:16.26283+00	step0_keyword_selection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
67dc0b59-5ff5-4d35-8fcb-92de7bdadcb4	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "営業採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "営業採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "営業採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-03 23:14:05.680213+00	2026-02-03 23:14:24.54864+00	2026-02-03 23:14:05.680213+00	\N	\N	\N	\N	\N	\N	\N	\N
736be378-e6ef-4450-afa8-be57caf8d1bc	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "営業採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "営業採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "営業採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 23:14:48.360122+00	2026-02-03 23:44:57.657288+00	2026-02-03 23:14:48.360122+00	2026-02-03 23:44:57.662398+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
2628769a-47a4-41bf-9666-44c43d8bda4d	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用 難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-04 00:14:21.894114+00	2026-02-04 00:35:33.151418+00	2026-02-04 00:14:21.894114+00	2026-02-04 00:35:33.156589+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	dev-tenant-001	waiting_approval	{"input": {"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_approval	2026-02-04 00:47:57.581451+00	2026-02-04 03:17:03.193351+00	2026-02-04 00:47:57.581451+00	\N	\N	\N	\N	\N	\N	\N	\N
64133ae9-85fe-4e72-a3f4-4089044e4fc8	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "従業員募集こない", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "従業員募集こない", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "従業員募集こない", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 13:24:51.271974+00	2026-02-03 22:46:26.656253+00	2026-02-03 13:24:51.271974+00	2026-02-03 13:52:18.173693+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 23:14:37.058883+00	2026-02-03 23:44:34.813954+00	2026-02-03 23:14:37.058883+00	2026-02-03 23:44:34.829421+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
40186126-cf83-4b8f-a524-d9ad733d4938	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-03 13:24:28.194774+00	2026-02-03 13:24:35.738597+00	2026-02-03 13:24:28.194774+00	\N	\N	\N	\N	\N	\N	\N	\N
3022c25f-f16b-4816-877c-90cb9847bfb6	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "トラックドライバー 求人 書き方", "options": {"retry_limit": 3, "repair_enabled": true, "enable_step1_approval": true}, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-2.5-pro-preview-05-06", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "google"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step0	2026-02-04 03:29:30.177086+00	2026-02-04 03:29:33.707358+00	2026-02-04 03:29:30.177086+00	2026-02-04 03:29:33.712699+00	step0_keyword_selection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
ba2e4594-2fde-472f-9548-01f281cbc05a	dev-tenant-001	cancelled	{"input": {"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}, "keyword": "営業 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}	{"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}	step3a	2026-02-04 03:34:42.070996+00	2026-02-04 03:42:08.903903+00	2026-02-04 03:34:42.070996+00	2026-02-04 03:42:08.920945+00	\N	\N	\N	\N	\N	\N	\N
02e16ff7-b095-429e-902c-dadc644bc252	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step5	2026-02-04 08:11:27.974284+00	2026-02-04 08:15:54.523659+00	2026-02-04 08:11:27.974284+00	2026-02-04 08:15:54.529063+00	step5_primary_collection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
0af170e5-6cff-40f4-8de4-b8e85f5c9912	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step0	2026-02-04 00:37:59.872359+00	2026-02-04 00:39:53.323632+00	2026-02-04 00:37:59.872359+00	2026-02-04 00:39:53.330637+00	step0_keyword_selection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
a5bcf4f3-d9e4-4ce2-b6d0-6deaf1194ac2	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step2	2026-02-04 00:43:59.903159+00	2026-02-04 00:46:41.928628+00	2026-02-04 00:43:59.903159+00	2026-02-04 00:46:41.934093+00	step2_csv_validation: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
c46548f7-2a8d-4370-a937-9090a5afce03	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}, "keyword": "営業 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}	{"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "中小企業の人事担当者・経営者", "additional_requirements": null}	step0	2026-02-04 03:29:29.393747+00	2026-02-04 03:31:16.714601+00	2026-02-04 03:29:29.393747+00	2026-02-04 03:31:16.719924+00	step0_keyword_selection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
4d711f0b-58c6-4217-8325-cfd18b0d577b	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "自動車整備士採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "自動車整備士採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "自動車整備士採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 13:24:51.342863+00	2026-02-03 22:40:28.275528+00	2026-02-03 13:24:51.342863+00	2026-02-03 22:40:28.282233+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
f92d9d06-2bbb-404a-8cee-7f574d87c12b	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-03 13:24:36.214854+00	2026-02-03 13:24:40.579416+00	2026-02-03 13:24:36.214854+00	\N	\N	\N	\N	\N	\N	\N	\N
460ee6fe-60bb-4454-83f9-30be3232b345	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": "採用担当者", "additional_requirements": null}, "keyword": "トラックドライバー 求人 書き方", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": true, "max_tokens": null, "temperature": 0.7}, "platform": "gemini"}, "step_configs": [{"model": "claude-opus-4-5-20251101", "step_id": "step9", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}], "competitor_urls": null, "target_audience": "採用担当者", "additional_requirements": null}	{"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": "採用担当者", "additional_requirements": null}	step10	2026-02-04 03:44:20.413044+00	2026-02-04 04:13:56.067541+00	2026-02-04 03:44:20.413044+00	2026-02-04 03:58:50.559196+00	step10_final_output: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
894a1783-f00d-431b-89fc-f3ed0984cc1a	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step5	2026-02-04 08:17:07.684196+00	2026-02-04 10:41:14.126021+00	2026-02-04 08:17:07.684196+00	2026-02-04 10:41:14.132287+00	step5_primary_collection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
34d18bb2-1742-43d7-82da-feec95f2294d	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step5	2026-02-04 10:43:03.622788+00	2026-02-04 10:49:38.70564+00	2026-02-04 10:43:03.622788+00	2026-02-04 10:49:38.711035+00	step5_primary_collection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
de000007-0000-0000-0000-000000000007	dev-tenant-001	waiting_image_input	{"model_config": {"model": "gemini-2.0-flash", "options": {}, "platform": "gemini"}}	{"keyword": "データ分析入門ガイド", "format_type": "legacy", "target_audience": "ビジネスアナリスト"}	step11	2026-01-18 06:05:22.647129+00	2026-01-18 06:26:21.869604+00	2026-01-18 06:07:22.647129+00	\N	\N	\N	{"phase": "waiting_positions", "settings": {"generate_images": true}}	\N	\N	\N	\N
1e9fdb8e-bed1-4055-99aa-b0df904b2331	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "トラックドライバー 求人 書き方", "options": {"retry_limit": 3, "repair_enabled": true, "enable_step1_approval": true}, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": true, "max_tokens": null, "temperature": 0.7}, "platform": "gemini"}, "step_configs": [{"model": "gemini-3-pro-preview", "step_id": "step0", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step1", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step2", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3a", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3b", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3c", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step4", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step5", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6_5", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step7a", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.8, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step7b", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.6, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step8", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step9", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step10", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}], "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step0	2026-02-04 03:32:23.526477+00	2026-02-04 03:34:39.738192+00	2026-02-04 03:32:23.526477+00	2026-02-04 03:34:39.743359+00	step0_keyword_selection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
9250e89e-ab21-419b-8b02-4d623b275c67	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 13:24:51.143485+00	2026-02-03 22:40:28.277807+00	2026-02-03 13:24:51.143485+00	2026-02-03 22:40:28.285346+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	dev-tenant-001	waiting_approval	{"input": {"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_approval	2026-02-04 03:00:27.832816+00	2026-02-04 03:16:03.992454+00	2026-02-04 03:00:27.832816+00	\N	\N	\N	\N	\N	\N	\N	\N
90dcfdc4-ebc1-4746-a09f-a9476d268565	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "営業採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "営業採用難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "営業採用難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-03 13:24:51.407017+00	2026-02-03 22:40:28.279658+00	2026-02-03 13:24:51.407017+00	2026-02-03 22:40:28.288255+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
fe080707-f401-4ceb-812e-4612e5293992	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "トラックドライバー 求人 書き方", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": true, "max_tokens": null, "temperature": 0.7}, "platform": "gemini"}, "step_configs": [{"model": "gemini-3-pro-preview", "step_id": "step0", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step1", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step2", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3a", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3b", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3c", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step4", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step5", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6_5", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step7a", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.8, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step7b", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.6, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step8", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step9", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step10", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}], "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step6_5	2026-02-04 03:43:23.197454+00	2026-02-04 03:55:25.579017+00	2026-02-04 03:43:23.197454+00	2026-02-04 03:55:25.585178+00	step6_5_integration_package: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
a87b2257-2fbf-4635-b21b-7f0779261103	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	completed	2026-02-04 10:50:05.128483+00	2026-02-04 11:18:40.317994+00	2026-02-04 10:50:05.128483+00	2026-02-04 11:00:28.139576+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
a1c79a6b-4c53-4837-8db9-c60b2a9219d4	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "google"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step0	2026-02-04 07:21:59.884951+00	2026-02-04 07:22:04.533262+00	2026-02-04 07:21:59.884951+00	2026-02-04 07:22:04.542668+00	step0_keyword_selection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "従業員 募集 こない", "competitor_urls": null, "target_audience": "従業員の募集に苦戦している中小企業の経営者・採用担当者", "additional_requirements": null}, "keyword": "従業員 募集 こない", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": true, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": "従業員の募集に苦戦している中小企業の経営者・採用担当者", "additional_requirements": null}	{"format": "legacy", "keyword": "従業員 募集 こない", "competitor_urls": null, "target_audience": "従業員の募集に苦戦している中小企業の経営者・採用担当者", "additional_requirements": null}	completed	2026-02-03 11:36:46.007138+00	2026-02-03 11:52:16.545693+00	2026-02-03 11:36:46.007138+00	2026-02-03 11:52:16.551318+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
7fefa4b1-e1db-4cb9-9812-6e87946f3aa8	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-04 11:01:16.180634+00	2026-02-04 11:01:26.198996+00	2026-02-04 11:01:16.180634+00	\N	\N	\N	\N	\N	\N	\N	\N
f8d40443-72e7-4705-afb6-09dc53a76743	dev-tenant-001	failed	{"input": {"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step5	2026-02-04 07:23:37.946183+00	2026-02-04 08:10:01.330351+00	2026-02-04 07:23:37.946183+00	2026-02-04 08:10:01.343211+00	step5_primary_collection: Activity task failed	ACTIVITY_FAILED	\N	\N	\N	\N	\N
233e0dbe-99c7-4daf-a338-ebb7d604407d	dev-tenant-001	failed	{"input": {"data": {"cta": {"type": "single", "single": {"url": "https://example.com/inquiry", "text": "無料相談はこちら", "description": "eラーニング導入についてのご相談"}, "staged": null, "position_mode": "ai"}, "keyword": {"status": "decided", "main_keyword": "eラーニング 企業", "theme_topics": null, "related_keywords": [{"volume": "500-1K", "keyword": "法人向けeラーニング"}, {"volume": "500-1K", "keyword": "企業研修 eラーニング"}], "selected_keyword": null, "competition_level": "medium", "monthly_search_volume": "1000-5000"}, "business": {"target_cv": "inquiry", "description": "eラーニングシステムの提供", "target_audience": "企業の人事・教育担当者", "target_cv_other": null, "company_strengths": "豊富な導入実績と柔軟なカスタマイズ対応"}, "strategy": {"child_topics": null, "article_style": "standalone"}, "confirmed": true, "word_count": {"mode": "ai_balanced", "target": null}, "format_type": "article_hearing_v1"}, "format": "article_hearing_v1", "keyword": "eラーニング 企業", "competitor_urls": null, "target_audience": "企業の人事・教育担当者", "additional_requirements": "【事業内容】eラーニングシステムの提供\\n【自社の強み】豊富な導入実績と柔軟なカスタマイズ対応\\n【目標CV】問い合わせ獲得\\n【記事スタイル】標準記事（スタンドアロン）\\n【文字数モード】バランス型（競合平均±5%）\\n【CTA】無料相談はこちら (https://example.com/inquiry)"}, "keyword": "eラーニング 企業", "options": {"retry_limit": 3, "repair_enabled": true, "enable_step1_approval": true}, "pack_id": "default", "tool_config": {"page_fetch": true, "serp_fetch": true, "url_verify": true, "pdf_extract": false}, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": true, "max_tokens": null, "temperature": 0.7}, "platform": "gemini"}, "step_configs": [{"model": "gemini-3-pro-preview", "step_id": "step0", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step1", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step2", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3a", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3b", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3c", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step4", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step5", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6_5", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step7a", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.8, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step7b", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.6, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step8", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step9", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step10", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}], "competitor_urls": null, "target_audience": "企業の人事・教育担当者", "additional_requirements": "【事業内容】eラーニングシステムの提供\\n【自社の強み】豊富な導入実績と柔軟なカスタマイズ対応\\n【目標CV】問い合わせ獲得\\n【記事スタイル】標準記事（スタンドアロン）\\n【文字数モード】バランス型（競合平均±5%）\\n【CTA】無料相談はこちら (https://example.com/inquiry)"}	{"data": {"cta": {"type": "single", "single": {"url": "https://example.com/inquiry", "text": "無料相談はこちら", "description": "eラーニング導入についてのご相談"}, "staged": null, "position_mode": "ai"}, "keyword": {"status": "decided", "main_keyword": "eラーニング 企業", "theme_topics": null, "related_keywords": [{"volume": "500-1K", "keyword": "法人向けeラーニング"}, {"volume": "500-1K", "keyword": "企業研修 eラーニング"}], "selected_keyword": null, "competition_level": "medium", "monthly_search_volume": "1000-5000"}, "business": {"target_cv": "inquiry", "description": "eラーニングシステムの提供", "target_audience": "企業の人事・教育担当者", "target_cv_other": null, "company_strengths": "豊富な導入実績と柔軟なカスタマイズ対応"}, "strategy": {"child_topics": null, "article_style": "standalone"}, "confirmed": true, "word_count": {"mode": "ai_balanced", "target": null}, "format_type": "article_hearing_v1"}, "format": "article_hearing_v1", "keyword": "eラーニング 企業", "competitor_urls": null, "target_audience": "企業の人事・教育担当者", "additional_requirements": "【事業内容】eラーニングシステムの提供\\n【自社の強み】豊富な導入実績と柔軟なカスタマイズ対応\\n【目標CV】問い合わせ獲得\\n【記事スタイル】標準記事（スタンドアロン）\\n【文字数モード】バランス型（競合平均±5%）\\n【CTA】無料相談はこちら (https://example.com/inquiry)"}	waiting_step1_approval	2026-01-20 04:47:40.815874+00	2026-01-20 04:48:40.919741+00	2026-01-20 04:47:40.815874+00	\N	\N	\N	\N	https://github.com/rozwer/test-seo	eラーニング_企業_20260120_044740	\N	\N
ca9bed12-f1fd-41a6-95b3-43e3fe74c238	dev-tenant-001	completed	{"input": {"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "営業職の採用が難航している企業の採用担当者・人事担当者", "additional_requirements": null}, "keyword": "営業 採用 難しい", "options": null, "pack_id": "default", "tool_config": null, "model_config": {"model": "gemini-2.0-flash", "options": {"grounding": true, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": "営業職の採用が難航している企業の採用担当者・人事担当者", "additional_requirements": null}	{"format": "legacy", "keyword": "営業 採用 難しい", "competitor_urls": null, "target_audience": "営業職の採用が難航している企業の採用担当者・人事担当者", "additional_requirements": null}	completed	2026-02-03 11:36:46.118567+00	2026-02-03 11:52:16.547753+00	2026-02-03 11:36:46.118567+00	2026-02-03 11:52:16.554531+00	\N	\N	{"error": null, "phase": "skipped", "images": [], "sections": [], "settings": null, "positions": [], "instructions": [], "analysis_summary": ""}	\N	\N	\N	\N
fcb7741f-dd21-4ca3-98f6-1befc7c49129	dev-tenant-001	waiting_approval	{"input": {"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "ドライバー 採用 難しい", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": null, "max_tokens": null, "temperature": null}, "platform": "gemini"}, "step_configs": null, "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "ドライバー 採用 難しい", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_approval	2026-02-04 03:14:19.885355+00	2026-02-04 03:21:33.04252+00	2026-02-04 03:14:19.885355+00	\N	\N	\N	\N	\N	\N	\N	\N
4bbee384-96a1-4272-a2e8-7789b3d40e5a	dev-tenant-001	waiting_step1_approval	{"input": {"data": {"cta": {"type": "single", "single": {"url": "https://example.com/inquiry", "text": "無料相談はこちら", "description": "eラーニング導入についてのご相談"}, "staged": null, "position_mode": "ai"}, "keyword": {"status": "decided", "main_keyword": "eラーニング 企業", "theme_topics": null, "related_keywords": [{"volume": "200-400", "keyword": "法人向けeラーニング"}, {"volume": "100-200", "keyword": "eラーニングシステム 比較 企業"}], "selected_keyword": null, "competition_level": "medium", "monthly_search_volume": "1000-5000"}, "business": {"target_cv": "inquiry", "description": "eラーニングシステムの提供", "target_audience": "企業の人事・教育担当者", "target_cv_other": null, "company_strengths": "豊富な導入実績と柔軟なカスタマイズ対応"}, "strategy": {"child_topics": null, "article_style": "standalone"}, "confirmed": true, "word_count": {"mode": "ai_balanced", "target": null}, "format_type": "article_hearing_v1"}, "format": "article_hearing_v1", "keyword": "eラーニング 企業", "competitor_urls": null, "target_audience": "企業の人事・教育担当者", "additional_requirements": "【事業内容】eラーニングシステムの提供\\n【自社の強み】豊富な導入実績と柔軟なカスタマイズ対応\\n【目標CV】問い合わせ獲得\\n【記事スタイル】標準記事（スタンドアロン）\\n【文字数モード】バランス型（競合平均±5%）\\n【CTA】無料相談はこちら (https://example.com/inquiry)"}, "keyword": "eラーニング 企業", "options": {"retry_limit": 3, "repair_enabled": true, "enable_step1_approval": true}, "pack_id": "default", "tool_config": {"page_fetch": true, "serp_fetch": true, "url_verify": true, "pdf_extract": false}, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": true, "max_tokens": null, "temperature": 0.7}, "platform": "gemini"}, "step_configs": [{"model": "gemini-3-pro-preview", "step_id": "step0", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step1", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step2", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3a", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3b", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3c", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step4", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step5", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6_5", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step7a", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.8, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step7b", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.6, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step8", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step9", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step10", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}], "competitor_urls": null, "target_audience": "企業の人事・教育担当者", "additional_requirements": "【事業内容】eラーニングシステムの提供\\n【自社の強み】豊富な導入実績と柔軟なカスタマイズ対応\\n【目標CV】問い合わせ獲得\\n【記事スタイル】標準記事（スタンドアロン）\\n【文字数モード】バランス型（競合平均±5%）\\n【CTA】無料相談はこちら (https://example.com/inquiry)"}	{"data": {"cta": {"type": "single", "single": {"url": "https://example.com/inquiry", "text": "無料相談はこちら", "description": "eラーニング導入についてのご相談"}, "staged": null, "position_mode": "ai"}, "keyword": {"status": "decided", "main_keyword": "eラーニング 企業", "theme_topics": null, "related_keywords": [{"volume": "200-400", "keyword": "法人向けeラーニング"}, {"volume": "100-200", "keyword": "eラーニングシステム 比較 企業"}], "selected_keyword": null, "competition_level": "medium", "monthly_search_volume": "1000-5000"}, "business": {"target_cv": "inquiry", "description": "eラーニングシステムの提供", "target_audience": "企業の人事・教育担当者", "target_cv_other": null, "company_strengths": "豊富な導入実績と柔軟なカスタマイズ対応"}, "strategy": {"child_topics": null, "article_style": "standalone"}, "confirmed": true, "word_count": {"mode": "ai_balanced", "target": null}, "format_type": "article_hearing_v1"}, "format": "article_hearing_v1", "keyword": "eラーニング 企業", "competitor_urls": null, "target_audience": "企業の人事・教育担当者", "additional_requirements": "【事業内容】eラーニングシステムの提供\\n【自社の強み】豊富な導入実績と柔軟なカスタマイズ対応\\n【目標CV】問い合わせ獲得\\n【記事スタイル】標準記事（スタンドアロン）\\n【文字数モード】バランス型（競合平均±5%）\\n【CTA】無料相談はこちら (https://example.com/inquiry)"}	waiting_step1_approval	2026-01-20 04:52:33.927296+00	2026-01-20 04:53:33.188745+00	2026-01-20 04:52:33.927296+00	\N	\N	\N	\N	https://github.com/rozwer/test-seo	eラーニング_企業_20260120_045233	\N	\N
c4f11f16-312e-4634-abc7-1a83a5196cd1	dev-tenant-001	cancelled	{"input": {"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "トラックドライバー 求人 書き方", "options": {"retry_limit": 3, "repair_enabled": true, "enable_step1_approval": true}, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": true, "max_tokens": null, "temperature": 0.7}, "platform": "gemini"}, "step_configs": [{"model": "gemini-3-pro-preview", "step_id": "step0", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step1", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step2", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3a", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3b", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3c", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step4", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step5", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6_5", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step7a", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.8, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step7b", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.6, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step8", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step9", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step10", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}], "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	step3_parallel	2026-02-04 03:34:59.939667+00	2026-02-04 03:42:08.209627+00	2026-02-04 03:34:59.939667+00	2026-02-04 03:42:08.24114+00	\N	\N	\N	\N	\N	\N	\N
2b0d02af-428d-4d33-ac92-bd35bb86b465	dev-tenant-001	waiting_step1_approval	{"input": {"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}, "keyword": "トラックドライバー 求人 書き方", "options": null, "pack_id": "v3_blog_system", "tool_config": null, "model_config": {"model": "gemini-3-pro-preview", "options": {"grounding": true, "max_tokens": null, "temperature": 0.7}, "platform": "gemini"}, "step_configs": [{"model": "gemini-3-pro-preview", "step_id": "step0", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step1", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step2", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3a", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3b", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step3c", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step4", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step5", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.7, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step6_5", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step7a", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.8, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step7b", "platform": "gemini", "grounding": false, "retry_limit": 3, "temperature": 0.6, "repair_enabled": true}, {"model": "gemini-3-pro-preview", "step_id": "step8", "platform": "gemini", "grounding": true, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step9", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.5, "repair_enabled": true}, {"model": "claude-opus-4.5", "step_id": "step10", "platform": "anthropic", "grounding": false, "retry_limit": 3, "temperature": 0.3, "repair_enabled": true}], "competitor_urls": null, "target_audience": null, "additional_requirements": null}	{"format": "legacy", "keyword": "トラックドライバー 求人 書き方", "competitor_urls": null, "target_audience": null, "additional_requirements": null}	waiting_step1_approval	2026-02-04 03:42:27.882439+00	2026-02-04 03:43:41.128538+00	2026-02-04 03:42:27.882439+00	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: step_llm_defaults; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.step_llm_defaults (step, provider_id, model_class) FROM stdin;
\.


--
-- Data for Name: steps; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.steps (id, run_id, step_name, status, started_at, completed_at, error_code, error_message, retry_count) FROM stdin;
92eed838-78a9-44fe-a9a2-80767cea0b8c	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step7a	completed	2026-02-03 11:45:29.83327+00	2026-02-03 11:45:59.883685+00	\N	\N	0
82526a9f-ad4f-4780-8d29-3857d121dfa9	c43cadf2-7969-4bc2-8c1d-166be7238371	step3_5	completed	2026-02-03 11:42:00.64993+00	2026-02-03 11:42:08.001567+00	\N	\N	0
315a4099-3eb4-40cf-9527-5afa0411dfca	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step3_5	completed	2026-02-03 11:42:00.719586+00	2026-02-03 11:42:08.125627+00	\N	\N	0
198b86e2-196c-4d7a-8837-19db80f5f995	233e0dbe-99c7-4daf-a338-ebb7d604407d	step1_5	completed	2026-01-20 04:48:12.424402+00	2026-01-20 04:48:35.970413+00	\N	\N	0
53f2c5a8-8a3a-4361-8488-1fe729421875	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step8	completed	2026-02-03 11:45:29.340922+00	2026-02-03 11:46:22.156831+00	\N	\N	0
a1a30f22-5d2f-4a84-9ab2-97580b90fef6	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step7b	completed	2026-02-03 11:45:59.976371+00	2026-02-03 11:46:31.576901+00	\N	\N	0
5c3b9d43-735a-4d22-b619-c2caddae7ab1	c43cadf2-7969-4bc2-8c1d-166be7238371	step0	completed	2026-02-03 11:36:47.525957+00	2026-02-03 11:36:51.41857+00	\N	\N	0
111ba420-853f-4169-94b5-4aa4d5522449	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step0	completed	2026-02-03 11:36:47.925223+00	2026-02-03 11:36:51.511214+00	\N	\N	0
7ea5b465-57e5-4379-9ba3-ea0dca96ac24	67c73686-f144-42a5-b52c-96e02c1e04e6	step0	completed	2026-02-03 11:36:47.954975+00	2026-02-03 11:36:51.544281+00	\N	\N	0
683158b0-75a1-4d72-a6ae-c435716bce98	c43cadf2-7969-4bc2-8c1d-166be7238371	step8	completed	2026-02-03 11:45:55.789253+00	2026-02-03 11:46:36.230278+00	\N	\N	0
a4005d9e-f13b-41b6-bbb3-6a6ec88ad6fb	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step0	completed	2026-02-03 11:36:47.982764+00	2026-02-03 11:36:52.075489+00	\N	\N	0
3eee90f5-138e-4b4e-84b0-9641471b8890	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step9	completed	2026-02-03 11:46:22.240873+00	2026-02-03 11:47:03.608128+00	\N	\N	0
05280d8d-de62-4cbb-abfe-f3fad1b42119	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step1	completed	2026-02-03 11:36:52.164871+00	2026-02-03 11:37:00.94381+00	\N	\N	0
268e388d-355f-47be-8542-aeb4441f6195	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step1_5	completed	2026-02-03 11:37:01.036216+00	2026-02-03 11:37:01.150027+00	\N	\N	0
fc450509-0db4-44f2-a1ed-ad6700c96df3	c43cadf2-7969-4bc2-8c1d-166be7238371	step1	completed	2026-02-03 11:36:51.574288+00	2026-02-03 11:37:06.522637+00	\N	\N	0
b5f40630-9285-49ed-9861-b4b109d003d9	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step8	completed	2026-02-03 11:46:31.672461+00	2026-02-03 11:47:22.39017+00	\N	\N	0
1dc1564d-82a4-4567-81bc-6cf503c764f7	c43cadf2-7969-4bc2-8c1d-166be7238371	step1_5	completed	2026-02-03 11:37:06.645782+00	2026-02-03 11:37:06.733234+00	\N	\N	0
0c29ee5c-e7b3-4497-b91f-b11a65ed4d79	67c73686-f144-42a5-b52c-96e02c1e04e6	step1	completed	2026-02-03 11:36:51.69218+00	2026-02-03 11:37:07.067093+00	\N	\N	0
95d46974-3d0d-44d7-a0c5-db2eafff1708	67c73686-f144-42a5-b52c-96e02c1e04e6	step1_5	completed	2026-02-03 11:37:07.148712+00	2026-02-03 11:37:07.221067+00	\N	\N	0
46bd9dd4-61b5-4a68-bf1e-f41d5cce6a5d	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step1	completed	2026-02-03 11:36:51.634201+00	2026-02-03 11:37:12.150757+00	\N	\N	0
fdddc0c6-a474-415d-91f0-1feb1eef6ee2	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step1_5	completed	2026-02-03 11:37:12.249082+00	2026-02-03 11:37:12.333228+00	\N	\N	0
f845600a-a323-43f0-b954-a953cb7037e1	c43cadf2-7969-4bc2-8c1d-166be7238371	step9	completed	2026-02-03 11:46:36.324785+00	2026-02-03 11:47:44.439087+00	\N	\N	0
65472744-f7da-4154-b9c4-ce7f2f85353c	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step9	completed	2026-02-03 22:42:41.224746+00	2026-02-03 22:43:27.535563+00	\N	\N	0
202fb8b9-2e28-4909-9b88-231794663831	c43cadf2-7969-4bc2-8c1d-166be7238371	step10	completed	2026-02-03 11:47:44.521617+00	2026-02-03 11:50:40.60606+00	\N	\N	0
b8148c69-6a91-471e-a9fd-608facd56be0	c43cadf2-7969-4bc2-8c1d-166be7238371	step2	completed	2026-02-03 11:38:41.773567+00	2026-02-03 11:38:42.148095+00	\N	\N	0
ac194aee-4af2-4200-b7be-2b34ff8e4551	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step2	completed	2026-02-03 11:38:41.973591+00	2026-02-03 11:38:42.476356+00	\N	\N	0
e49fb00c-b2a1-45dd-b03e-e02ef7550161	67c73686-f144-42a5-b52c-96e02c1e04e6	step9	completed	2026-02-03 11:51:02.271083+00	2026-02-03 11:51:47.79441+00	\N	\N	0
3d942feb-efd3-4ec0-9e44-f00ece5c56a5	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step2	completed	2026-02-03 11:38:42.171128+00	2026-02-03 11:38:42.633631+00	\N	\N	0
035c1212-7bf5-4c29-acf0-317ff46d0398	67c73686-f144-42a5-b52c-96e02c1e04e6	step2	completed	2026-02-03 11:38:42.122602+00	2026-02-03 11:38:42.633802+00	\N	\N	0
24363e2e-559e-4333-98dd-e24677cf7536	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step3a	completed	2026-02-03 11:38:43.056194+00	2026-02-03 11:38:45.29132+00	\N	\N	0
d4afa245-d9f2-49ba-a774-84c185c28169	c43cadf2-7969-4bc2-8c1d-166be7238371	step3a	completed	2026-02-03 11:38:42.548846+00	2026-02-03 11:38:49.770804+00	\N	\N	0
c9d46359-0944-489d-9312-192eabbe8b33	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step3a	completed	2026-02-03 11:38:42.747277+00	2026-02-03 11:38:51.092557+00	\N	\N	0
0785c6c3-1cec-4ea1-bf66-df7d3b5bac44	67c73686-f144-42a5-b52c-96e02c1e04e6	step3a	completed	2026-02-03 11:38:42.985154+00	2026-02-03 11:38:53.344237+00	\N	\N	0
12567364-ed72-43f6-964a-98836e2d3fe0	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step3c	completed	2026-02-03 11:38:42.99864+00	2026-02-03 11:39:22.084216+00	\N	\N	0
aa3b51d1-66af-45d9-9d68-06482d8eef13	c43cadf2-7969-4bc2-8c1d-166be7238371	step3c	completed	2026-02-03 11:38:42.615305+00	2026-02-03 11:39:28.352564+00	\N	\N	0
f82797d3-8fa5-41e2-8a41-81ff40ed00e9	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step3c	completed	2026-02-03 11:38:42.750754+00	2026-02-03 11:39:31.179518+00	\N	\N	0
b344f4d9-c695-47a8-8b54-52b010c46c86	67c73686-f144-42a5-b52c-96e02c1e04e6	step3c	completed	2026-02-03 11:38:42.940985+00	2026-02-03 11:39:34.276777+00	\N	\N	0
2ad02cf3-00ae-493a-96b9-4a6a31e4b639	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step3b	completed	2026-02-03 11:38:42.750436+00	2026-02-03 11:40:40.128579+00	\N	\N	0
0dcda8f1-1256-4734-9399-1425dc95d300	c43cadf2-7969-4bc2-8c1d-166be7238371	step3b	completed	2026-02-03 11:38:42.656088+00	2026-02-03 11:40:50.626824+00	\N	\N	0
2626033e-0ca9-4d3e-b326-37a5e6f99840	67c73686-f144-42a5-b52c-96e02c1e04e6	step3b	completed	2026-02-03 11:38:42.890379+00	2026-02-03 11:41:20.542028+00	\N	\N	0
056203d3-6210-4dc7-842f-a6d17905636a	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step3b	completed	2026-02-03 11:38:43.055907+00	2026-02-03 11:41:23.874382+00	\N	\N	0
d7985ff6-b40e-4bc3-bd0d-f217cf4303e3	67c73686-f144-42a5-b52c-96e02c1e04e6	step3_5	completed	2026-02-03 11:42:00.797567+00	2026-02-03 11:42:09.94772+00	\N	\N	0
ba91543c-0beb-4081-a9cf-960a63bab6d9	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step3_5	completed	2026-02-03 11:42:00.797807+00	2026-02-03 11:42:12.812985+00	\N	\N	0
88b19fd6-effe-4254-a4fb-b8cacb379cb3	67c73686-f144-42a5-b52c-96e02c1e04e6	step4	completed	2026-02-03 11:42:10.043437+00	2026-02-03 11:42:27.790821+00	\N	\N	0
6f161749-0d1d-46dd-a598-6704faceb613	c43cadf2-7969-4bc2-8c1d-166be7238371	step4	completed	2026-02-03 11:42:08.125818+00	2026-02-03 11:42:28.481622+00	\N	\N	0
a1f6b66e-84a4-479b-8558-5dde753e849d	233e0dbe-99c7-4daf-a338-ebb7d604407d	step0	completed	2026-01-20 04:47:40.979026+00	2026-01-20 04:47:59.029594+00	\N	\N	0
99d7cf5b-3b6a-449d-8d08-8b1a67dee28b	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step4	completed	2026-02-03 11:42:08.218752+00	2026-02-03 11:42:29.379648+00	\N	\N	0
8b8a8393-8898-4119-b878-ffed9e0cdf02	233e0dbe-99c7-4daf-a338-ebb7d604407d	step1	completed	2026-01-20 04:47:59.123157+00	2026-01-20 04:48:12.328102+00	\N	\N	0
8a8bee51-44a1-4fdb-8864-44ca7ec9f249	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step4	completed	2026-02-03 11:42:12.902961+00	2026-02-03 11:42:31.513959+00	\N	\N	0
db047615-eab1-46ab-aafa-25ad2b72e986	c43cadf2-7969-4bc2-8c1d-166be7238371	step5	completed	2026-02-03 11:42:28.564694+00	2026-02-03 11:43:25.752033+00	\N	\N	0
5fe16e66-a573-4593-8602-11bd8f91f4fc	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step5	completed	2026-02-03 11:42:31.62066+00	2026-02-03 11:43:28.31367+00	\N	\N	0
10fdf28c-3159-43c9-9132-95c019058f22	4bbee384-96a1-4272-a2e8-7789b3d40e5a	step0	completed	2026-01-20 04:52:34.060415+00	2026-01-20 04:52:51.529022+00	\N	\N	0
26756f10-0a23-451e-b23d-ac2ad5c45f0e	67c73686-f144-42a5-b52c-96e02c1e04e6	step5	completed	2026-02-03 11:42:27.88172+00	2026-02-03 11:43:37.178377+00	\N	\N	0
c63eb0d8-e17d-4381-84ab-4e99d5c70603	4bbee384-96a1-4272-a2e8-7789b3d40e5a	step1	completed	2026-01-20 04:52:51.621225+00	2026-01-20 04:53:02.17614+00	\N	\N	0
c41edaf0-b797-4afd-9a02-dd7417d3c5ee	4bbee384-96a1-4272-a2e8-7789b3d40e5a	step1_5	completed	2026-01-20 04:53:02.287805+00	2026-01-20 04:53:33.034972+00	\N	\N	0
1c26bb9e-f4d4-49c8-9778-29674e64015f	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step6	completed	2026-02-03 11:43:28.396423+00	2026-02-03 11:43:50.401056+00	\N	\N	0
76b2e148-ead3-4bfa-8860-d10cb7a8e070	67c73686-f144-42a5-b52c-96e02c1e04e6	step6	completed	2026-02-03 11:43:37.266287+00	2026-02-03 11:43:55.409842+00	\N	\N	0
99b6acd9-c8c5-4311-b10a-a8c439e7c7d6	c43cadf2-7969-4bc2-8c1d-166be7238371	step6	completed	2026-02-03 11:43:25.848581+00	2026-02-03 11:43:59.955118+00	\N	\N	0
83f5b9fb-7926-4e6a-a4f8-09c33ec6f07a	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step5	completed	2026-02-03 11:42:29.478408+00	2026-02-03 11:44:13.232171+00	\N	\N	0
4d812a61-5426-4706-a2b4-455f27b30290	67c73686-f144-42a5-b52c-96e02c1e04e6	step6_5	completed	2026-02-03 11:43:55.500332+00	2026-02-03 11:44:27.481339+00	\N	\N	0
255c8642-b024-48d3-ab05-a97b5714fa6f	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step6_5	completed	2026-02-03 11:43:50.483034+00	2026-02-03 11:44:29.509857+00	\N	\N	0
4a8ff516-aea5-438b-bc0a-310306ff677a	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step6	completed	2026-02-03 11:44:13.323146+00	2026-02-03 11:44:34.931832+00	\N	\N	0
281e6bac-53f6-4b9d-acbd-a52e0ec71130	67c73686-f144-42a5-b52c-96e02c1e04e6	step7a	completed	2026-02-03 11:44:27.571869+00	2026-02-03 11:44:58.147001+00	\N	\N	0
6ae93db2-caa9-43ef-8fc6-3f48ae336255	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step7a	completed	2026-02-03 11:44:29.600779+00	2026-02-03 11:44:59.966635+00	\N	\N	0
43ed9c52-357d-4077-add8-0077b39d1f06	c43cadf2-7969-4bc2-8c1d-166be7238371	step6_5	completed	2026-02-03 11:44:34.497961+00	2026-02-03 11:45:04.742807+00	\N	\N	0
b10382db-c6ab-4140-893a-a3d0137d0066	c43cadf2-7969-4bc2-8c1d-166be7238371	step7a	completed	2026-02-03 11:45:04.821002+00	2026-02-03 11:45:26.188792+00	\N	\N	0
830d7e72-3914-48b5-88fd-cd456417b1fe	67c73686-f144-42a5-b52c-96e02c1e04e6	step7b	completed	2026-02-03 11:44:58.242093+00	2026-02-03 11:45:27.211082+00	\N	\N	0
4bd01c61-15d9-4ab8-9e0f-5c50f89cdc38	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step7b	completed	2026-02-03 11:45:00.055921+00	2026-02-03 11:45:29.248644+00	\N	\N	0
8dd47041-5cb5-4376-922e-864db582a9ee	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step6_5	completed	2026-02-03 11:45:02.689105+00	2026-02-03 11:45:29.753953+00	\N	\N	0
49d952fc-c5ad-4d51-b844-6a293a8eedba	c43cadf2-7969-4bc2-8c1d-166be7238371	step7b	completed	2026-02-03 11:45:26.282034+00	2026-02-03 11:45:55.70078+00	\N	\N	0
f66a3246-f2a1-4122-92a0-6dd321da3827	736be378-e6ef-4450-afa8-be57caf8d1bc	step4	completed	2026-02-03 23:21:22.943474+00	2026-02-03 23:22:25.145878+00	\N	\N	0
9d70e8fb-81a3-43bc-ae42-b493e2e6788e	02e16ff7-b095-429e-902c-dadc644bc252	step3_5	completed	2026-02-04 08:14:56.923056+00	2026-02-04 08:15:10.871307+00	\N	\N	0
42955b9e-937e-40dd-bc72-34ccc455b7f1	ce77e4a2-9c91-44d9-aade-32054e4443fa	step5	completed	2026-02-03 23:22:20.198579+00	2026-02-03 23:24:42.1701+00	\N	\N	0
6b67938f-ac1e-4e90-abe2-eecaa15943e3	4d711f0b-58c6-4217-8325-cfd18b0d577b	step6_5	completed	2026-02-03 13:49:31.260624+00	2026-02-03 13:49:56.395482+00	\N	\N	0
5bfa00b5-8a95-4c96-adf7-898638e2b9e0	9250e89e-ab21-419b-8b02-4d623b275c67	step6	completed	2026-02-03 13:49:35.911362+00	2026-02-03 13:50:03.9036+00	\N	\N	0
efe68187-4fc5-4ef8-bf13-6b88968586a2	4d711f0b-58c6-4217-8325-cfd18b0d577b	step7a	completed	2026-02-03 13:49:56.546288+00	2026-02-03 13:50:16.110332+00	\N	\N	0
f3314172-8c7c-4867-939e-152970447f07	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step9	completed	2026-02-03 11:47:22.49369+00	2026-02-03 11:48:03.801418+00	\N	\N	0
85711f71-ad9f-42c7-947b-21dbb8818166	90dcfdc4-ebc1-4746-a09f-a9476d268565	step6	completed	2026-02-03 13:50:18.693488+00	2026-02-03 13:50:45.120702+00	\N	\N	0
75501b51-3baa-473d-aa9f-b88c23e15556	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step10	completed	2026-02-03 11:47:03.686952+00	2026-02-03 11:50:50.44831+00	\N	\N	0
e355050f-4180-45b4-a6bb-ead289fa7ba2	67c73686-f144-42a5-b52c-96e02c1e04e6	step8	completed	2026-02-03 11:49:42.607234+00	2026-02-03 11:51:02.180298+00	\N	\N	0
27ff2844-221d-476b-94af-f7cabb8fc1bb	c43cadf2-7969-4bc2-8c1d-166be7238371	step12	completed	2026-02-03 11:52:15.739557+00	2026-02-03 11:52:16.280468+00	\N	\N	0
35bda64b-0f22-4f44-9b14-dd3b2d74d928	67c73686-f144-42a5-b52c-96e02c1e04e6	step10	completed	2026-02-03 11:51:47.874371+00	2026-02-03 11:55:07.42612+00	\N	\N	0
d109f711-2b8b-4c2d-8f81-00729c69e247	90dcfdc4-ebc1-4746-a09f-a9476d268565	step6_5	completed	2026-02-03 13:50:45.271135+00	2026-02-03 13:51:10.625544+00	\N	\N	0
766d8d05-62b7-4bb7-aa3e-79bcb2239cb0	40186126-cf83-4b8f-a524-d9ad733d4938	step1_5	completed	2026-02-03 13:24:35.347458+00	2026-02-03 13:24:35.452735+00	\N	\N	0
b5070283-c2a5-423d-b465-901f35cba1fb	ce77e4a2-9c91-44d9-aade-32054e4443fa	step6	completed	2026-02-03 23:24:42.261402+00	2026-02-03 23:25:48.313208+00	\N	\N	0
b4a221e4-cce5-4be1-bc4a-1786460e6ab3	f92d9d06-2bbb-404a-8cee-7f574d87c12b	step1	completed	2026-02-03 13:24:39.356047+00	2026-02-03 13:24:40.232868+00	\N	\N	0
e69a4b3d-7f97-44a1-805b-1800d793b130	90dcfdc4-ebc1-4746-a09f-a9476d268565	step7a	completed	2026-02-03 13:51:10.770078+00	2026-02-03 13:51:20.231336+00	\N	\N	0
26ef0c78-aabe-40b1-9965-f4528caa031c	90dcfdc4-ebc1-4746-a09f-a9476d268565	step1	completed	2026-02-03 13:24:54.511403+00	2026-02-03 13:24:59.502134+00	\N	\N	0
673b44ff-1211-4efe-a1fb-3e8fb95eefdd	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step1_5	completed	2026-02-03 13:24:59.583623+00	2026-02-03 13:24:59.765809+00	\N	\N	0
5ae759fc-5fa3-496d-9bca-cc2075cf7988	4d711f0b-58c6-4217-8325-cfd18b0d577b	step9	completed	2026-02-03 13:51:39.391568+00	2026-02-03 13:52:21.345195+00	\N	\N	0
36f65afa-ff92-4421-8740-ba0e099e1c40	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step6	completed	2026-02-03 23:25:17.649045+00	2026-02-03 23:26:24.609199+00	\N	\N	0
c8641b33-b8ee-4ed2-8dc4-5fecb9a9b9c9	9250e89e-ab21-419b-8b02-4d623b275c67	step10	completed	2026-02-03 13:52:35.974045+00	2026-02-03 13:56:44.661399+00	\N	\N	0
060174f2-6475-4f05-90cc-bac858d0cf05	b7005fcd-2bd4-4017-9e27-b8213ff93061	step7b	completed	2026-02-03 23:26:00.379091+00	2026-02-03 23:26:42.412947+00	\N	\N	0
9aabb024-2174-493f-8872-367378ede257	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step7b	completed	2026-02-03 22:41:24.335353+00	2026-02-03 22:41:51.303964+00	\N	\N	0
683ab62c-06f2-4782-8be5-ce2bee6db514	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step2	completed	2026-02-03 23:16:51.642684+00	2026-02-03 23:16:52.128355+00	\N	\N	0
b43db72c-1765-4c1d-896a-d1e37710db1d	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	step3a	completed	2026-02-04 02:40:31.373333+00	2026-02-04 02:41:14.239925+00	\N	\N	0
9f8eb0c8-cb50-4ec5-8d2c-9b1c96b8adb7	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	step0	completed	2026-02-04 03:01:29.001807+00	2026-02-04 03:02:06.394379+00	\N	\N	0
db91f4fe-2dfd-485b-b679-f971cc110262	b7005fcd-2bd4-4017-9e27-b8213ff93061	step2	completed	2026-02-03 23:16:52.582049+00	2026-02-03 23:16:53.051058+00	\N	\N	0
f41fda91-9872-4098-82aa-5f173fa69694	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	step1_5	completed	2026-02-04 03:02:14.089454+00	2026-02-04 03:02:14.179572+00	\N	\N	0
c0fb4296-8090-4c85-a2d0-b27cccf1bba2	ce77e4a2-9c91-44d9-aade-32054e4443fa	step3a	completed	2026-02-03 23:16:53.323024+00	2026-02-03 23:17:27.582444+00	\N	\N	0
d3973d80-0da1-40c0-a136-88e7230a8cb5	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step3a	completed	2026-02-03 23:16:52.8304+00	2026-02-03 23:17:30.835256+00	\N	\N	0
903a1f7b-c3a8-4633-b036-7c08f50566d3	b7005fcd-2bd4-4017-9e27-b8213ff93061	step3c	completed	2026-02-03 23:16:53.465355+00	2026-02-03 23:17:54.170611+00	\N	\N	0
0d05eaf6-c625-4f99-aad6-de459e0b0b46	b7005fcd-2bd4-4017-9e27-b8213ff93061	step3b	completed	2026-02-03 23:16:53.25+00	2026-02-03 23:18:32.632322+00	\N	\N	0
e8b78372-b89e-444d-8765-623f62377ec7	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step3b	completed	2026-02-03 23:16:52.91869+00	2026-02-03 23:18:38.661499+00	\N	\N	0
f5d1225e-6c0a-4ed1-9103-c80af9d83cba	736be378-e6ef-4450-afa8-be57caf8d1bc	step3b	completed	2026-02-03 23:16:53.465612+00	2026-02-03 23:18:42.791607+00	\N	\N	0
c2cc1da0-bc8f-4596-bf85-ac28b54d35b0	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step7a	completed	2026-02-03 23:27:09.495303+00	2026-02-03 23:27:55.346072+00	\N	\N	0
225146cd-06f8-4cf1-bd02-68d02fe74d64	736be378-e6ef-4450-afa8-be57caf8d1bc	step5	completed	2026-02-03 23:27:26.244491+00	2026-02-03 23:30:41.468498+00	\N	\N	0
ad78b877-64ca-45a0-a38b-31406ae2682a	736be378-e6ef-4450-afa8-be57caf8d1bc	step3_5	completed	2026-02-03 23:20:57.233308+00	2026-02-03 23:21:22.860392+00	\N	\N	0
60be8e7d-fbf6-47c9-a248-e387f059ce26	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step3_5	completed	2026-02-03 23:20:57.076942+00	2026-02-03 23:21:24.503317+00	\N	\N	0
16844350-7236-4850-b5b6-614b4bbe9c43	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step4	completed	2026-02-03 23:21:24.592379+00	2026-02-03 23:22:23.266082+00	\N	\N	0
77ec31f3-c4fa-46fa-8739-79775e8699ad	736be378-e6ef-4450-afa8-be57caf8d1bc	step6_5	completed	2026-02-03 23:31:46.754464+00	2026-02-03 23:32:29.196016+00	\N	\N	0
70129245-2390-40b7-a89c-f5a176ca9a45	fcb7741f-dd21-4ca3-98f6-1befc7c49129	step0	completed	2026-02-04 03:14:20.053236+00	2026-02-04 03:14:57.179757+00	\N	\N	0
86b32164-c92e-4617-b973-e55f305c31c4	b7005fcd-2bd4-4017-9e27-b8213ff93061	step8	completed	2026-02-03 23:33:08.879522+00	2026-02-03 23:35:12.354256+00	\N	\N	0
880c8c42-3d0d-4b53-af1f-23caf8867b81	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	step3b	completed	2026-02-04 03:14:44.476669+00	2026-02-04 03:15:48.485823+00	\N	\N	0
78cbd75c-b1ff-4466-8cdd-2bd3da36d317	2628769a-47a4-41bf-9666-44c43d8bda4d	step1	completed	2026-02-04 00:14:37.900093+00	2026-02-04 00:14:41.590739+00	\N	\N	0
7c9b0ea9-9a2a-44a3-ad3e-073f81a1491d	c4f11f16-312e-4634-abc7-1a83a5196cd1	step3b	failed	2026-02-04 03:40:50.403555+00	2026-02-04 03:40:50.49478+00	non_retryable	Failed to render prompt: Missing required variable: step2_data	0
b321aa00-18a0-4cd9-a7b0-bde1a259e903	2628769a-47a4-41bf-9666-44c43d8bda4d	step5	completed	2026-02-04 00:19:28.093645+00	2026-02-04 00:21:20.189206+00	\N	\N	0
adecf67b-664a-4837-a074-9d23ddf585a9	2628769a-47a4-41bf-9666-44c43d8bda4d	step10	completed	2026-02-04 00:27:38.055609+00	2026-02-04 00:34:57.136407+00	\N	\N	0
9c1994bf-51f6-417b-b071-82bd444a3a95	fcb7741f-dd21-4ca3-98f6-1befc7c49129	step3b	completed	2026-02-04 03:20:07.000158+00	2026-02-04 03:21:26.829079+00	\N	\N	0
d76852f9-84d5-463a-b665-732c0bec2050	fcb7741f-dd21-4ca3-98f6-1befc7c49129	step3c	completed	2026-02-04 03:20:06.999608+00	2026-02-04 03:21:32.88838+00	\N	\N	0
8169de05-ad57-43ab-8366-14862a314523	ba2e4594-2fde-472f-9548-01f281cbc05a	step1_5	completed	2026-02-04 03:35:23.31746+00	2026-02-04 03:35:23.396773+00	\N	\N	0
1c097b8b-899e-4d58-92ce-9510fb45b57f	ba2e4594-2fde-472f-9548-01f281cbc05a	step3b	failed	2026-02-04 03:41:53.881271+00	2026-02-04 03:41:53.973608+00	non_retryable	Failed to render prompt: Missing required variable: step2_data	0
fb0d719a-403d-495c-93b5-fc60f44e77e6	c4f11f16-312e-4634-abc7-1a83a5196cd1	step1	completed	2026-02-04 03:35:33.445824+00	2026-02-04 03:36:12.654654+00	\N	\N	0
ecc0ae9e-468a-4791-9c3f-54ba37c6d99d	2b0d02af-428d-4d33-ac92-bd35bb86b465	step0	completed	2026-02-04 03:42:53.554711+00	2026-02-04 03:43:38.402927+00	\N	\N	0
05643d3d-eb1a-48fc-8a48-20d770f1264b	c4f11f16-312e-4634-abc7-1a83a5196cd1	step1_5	completed	2026-02-04 03:36:12.746928+00	2026-02-04 03:36:12.830399+00	\N	\N	0
e1f477a3-efe5-4a65-a03d-50a0acd97f8b	fe080707-f401-4ceb-812e-4612e5293992	step3_5	completed	2026-02-04 03:45:53.783728+00	2026-02-04 03:46:18.595643+00	\N	\N	0
d7aaf348-da29-42f9-a8ee-af0456c13605	fe080707-f401-4ceb-812e-4612e5293992	step4	completed	2026-02-04 03:46:18.684821+00	2026-02-04 03:47:27.036117+00	\N	\N	0
93192bdd-95e2-4446-9b73-4cd46d2428a8	460ee6fe-60bb-4454-83f9-30be3232b345	step4	completed	2026-02-04 03:49:33.453583+00	2026-02-04 03:50:47.361384+00	\N	\N	0
68738676-05ca-44ad-8ef2-ac5f635b79d1	fe080707-f401-4ceb-812e-4612e5293992	step6	completed	2026-02-04 03:50:36.651486+00	2026-02-04 03:52:35.640904+00	\N	\N	0
e400df2a-dbaa-4edf-b234-84cbf3522eb5	c4f11f16-312e-4634-abc7-1a83a5196cd1	step2	completed	2026-02-04 03:37:01.550089+00	2026-02-04 03:37:01.682683+00	\N	\N	0
26107aaa-7f31-4292-ae6e-82816d32e382	460ee6fe-60bb-4454-83f9-30be3232b345	step10	failed	2026-02-04 04:13:55.753959+00	2026-02-04 04:13:55.91487+00	retryable	Client error: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_requests_per_model_per_day, limit: 0', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_requests_per_model_per_day', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel'}]}]}}	0
7f10cde1-803c-4bde-b5e9-e339963c7e6d	a1c79a6b-4c53-4837-8db9-c60b2a9219d4	step0	failed	2026-02-04 07:22:04.25864+00	2026-02-04 07:22:04.295103+00	retryable	Unknown LLM provider: google	0
7abcf8a7-7273-46be-8a33-b1d4202a93aa	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step10	completed	2026-02-03 11:48:03.882093+00	2026-02-03 11:51:15.738912+00	\N	\N	0
f4733766-f091-49c1-9397-97c31c6060a1	b7005fcd-2bd4-4017-9e27-b8213ff93061	step4	completed	2026-02-03 23:21:22.580357+00	2026-02-03 23:22:24.258869+00	\N	\N	0
f89569ee-6f34-46b0-8d90-f1d0c57c49be	c6445773-8f0c-4a5d-a5fe-fd229b3cc05f	step12	completed	2026-02-03 11:52:15.926283+00	2026-02-03 11:52:16.325602+00	\N	\N	0
5680e619-2817-4d6a-b0ec-ba2289375518	ca9bed12-f1fd-41a6-95b3-43e3fe74c238	step12	completed	2026-02-03 11:52:15.924932+00	2026-02-03 11:52:16.326056+00	\N	\N	0
32738fa0-d43b-45e8-89ef-29a897a2fc3a	b7005fcd-2bd4-4017-9e27-b8213ff93061	step5	completed	2026-02-03 23:22:24.353609+00	2026-02-03 23:23:29.360696+00	\N	\N	0
53f298a7-8093-48b9-89e8-31064eca1bfd	67c73686-f144-42a5-b52c-96e02c1e04e6	step12	completed	2026-02-03 11:57:02.196219+00	2026-02-03 11:57:02.367652+00	\N	\N	0
7fe0e28d-e12f-4d62-9d9b-5ca271f5b091	9250e89e-ab21-419b-8b02-4d623b275c67	step6_5	completed	2026-02-03 13:50:04.062332+00	2026-02-03 13:50:25.173886+00	\N	\N	0
59163321-a6f0-4795-9c72-9c352bda60d2	40186126-cf83-4b8f-a524-d9ad733d4938	step0	completed	2026-02-03 13:24:27.687596+00	2026-02-03 13:24:32.292576+00	\N	\N	0
959f8d69-90a4-41f8-8b52-fd6f3f38e742	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step6	completed	2026-02-03 13:50:09.95592+00	2026-02-03 13:50:35.37309+00	\N	\N	0
580831d8-f35e-4101-9215-ea0bc74e3248	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step5	completed	2026-02-03 23:22:23.352567+00	2026-02-03 23:25:17.559786+00	\N	\N	0
2183c8b4-8f9e-4811-adc4-004055b4e53c	9250e89e-ab21-419b-8b02-4d623b275c67	step0	completed	2026-02-03 13:24:51.306386+00	2026-02-03 13:24:54.536522+00	\N	\N	0
25dd1df1-db76-419e-87ea-5d1c769c9b56	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	step1	completed	2026-02-04 03:02:06.489872+00	2026-02-04 03:02:14.010175+00	\N	\N	0
f50c6b02-d6b5-44a1-b3ac-a3405a8a31e9	9250e89e-ab21-419b-8b02-4d623b275c67	step1	completed	2026-02-03 13:24:54.680432+00	2026-02-03 13:24:55.020034+00	\N	\N	0
0cac2230-e704-4143-85ca-e4ac36c0e178	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step6_5	completed	2026-02-03 23:26:24.699183+00	2026-02-03 23:27:09.410759+00	\N	\N	0
8f6d4e12-9944-4bb5-98b4-e77aeecfddb8	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step1	completed	2026-02-03 13:24:54.456785+00	2026-02-03 13:24:59.502858+00	\N	\N	0
f9d4f357-9a7a-4c39-97b4-32b32cd12ae3	4d711f0b-58c6-4217-8325-cfd18b0d577b	step1	completed	2026-02-03 13:24:55.273786+00	2026-02-03 13:24:59.441877+00	\N	\N	0
811e725d-de65-46bc-a1a7-1dd13de1b3cb	9250e89e-ab21-419b-8b02-4d623b275c67	step7b	completed	2026-02-03 13:50:50.182698+00	2026-02-03 13:51:13.411273+00	\N	\N	0
a3e6e7dd-3723-4ea4-98c6-f1ab5c89df90	90dcfdc4-ebc1-4746-a09f-a9476d268565	step7b	completed	2026-02-03 13:51:20.3208+00	2026-02-03 13:51:36.391889+00	\N	\N	0
7ddb5cf6-e7ff-43bb-a7dd-94e908380026	ce77e4a2-9c91-44d9-aade-32054e4443fa	step7b	completed	2026-02-03 23:27:47.920356+00	2026-02-03 23:28:23.904241+00	\N	\N	0
97e15c29-6b29-4c5d-aac0-fcb00b9b6595	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	step2	completed	2026-02-04 03:02:35.378929+00	2026-02-04 03:02:35.504514+00	\N	\N	0
76fdf270-4c1c-4dcc-86f4-57606eb50555	ce77e4a2-9c91-44d9-aade-32054e4443fa	step9	completed	2026-02-03 23:30:30.101148+00	2026-02-03 23:32:16.106516+00	\N	\N	0
4c2bdd0d-18f6-4ce8-8842-a78c16a1635d	4d711f0b-58c6-4217-8325-cfd18b0d577b	step10	completed	2026-02-03 13:52:21.489403+00	2026-02-03 13:56:01.912886+00	\N	\N	0
c89eb4c0-d918-401b-b1b1-0a3276053b35	736be378-e6ef-4450-afa8-be57caf8d1bc	step7a	completed	2026-02-03 23:32:29.282042+00	2026-02-03 23:33:13.974366+00	\N	\N	0
b331d904-a051-4d62-991e-f276828a7196	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step6_5	completed	2026-02-03 22:40:39.069526+00	2026-02-03 22:41:02.606085+00	\N	\N	0
302a1d72-4c5b-43b9-bb1f-acb5a0f063eb	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step10	completed	2026-02-03 22:43:27.63133+00	2026-02-03 22:45:57.469633+00	\N	\N	0
d3a8d835-d3db-4acb-8b49-ceb4e62da96b	736be378-e6ef-4450-afa8-be57caf8d1bc	step7b	completed	2026-02-03 23:33:14.060196+00	2026-02-03 23:33:55.450445+00	\N	\N	0
b79164ce-1795-47a4-ae28-6061b0d85a36	ce77e4a2-9c91-44d9-aade-32054e4443fa	step2	completed	2026-02-03 23:16:52.094254+00	2026-02-03 23:16:52.979934+00	\N	\N	0
b50c974e-f3f3-4e1d-b227-e7ec2cdfc66b	b7005fcd-2bd4-4017-9e27-b8213ff93061	step3a	completed	2026-02-03 23:16:53.161486+00	2026-02-03 23:17:46.765594+00	\N	\N	0
d7bf4e58-63f9-4cfb-ad58-701f37f1dd6b	ce77e4a2-9c91-44d9-aade-32054e4443fa	step3b	completed	2026-02-03 23:16:53.389255+00	2026-02-03 23:18:24.46427+00	\N	\N	0
acf26daa-de8d-4c31-97f6-1122f3995c7f	736be378-e6ef-4450-afa8-be57caf8d1bc	step8	completed	2026-02-03 23:33:55.540328+00	2026-02-03 23:35:48.37716+00	\N	\N	0
7ca2ce1d-8b09-4ed1-80b9-f693b9419364	b7005fcd-2bd4-4017-9e27-b8213ff93061	step3_5	completed	2026-02-03 23:20:57.232984+00	2026-02-03 23:21:22.486859+00	\N	\N	0
d1087150-7eb6-4bda-9606-fb436cc574f0	b7005fcd-2bd4-4017-9e27-b8213ff93061	step9	completed	2026-02-03 23:35:12.444288+00	2026-02-03 23:36:27.483053+00	\N	\N	0
0693b15d-c4fd-4138-9667-d10c8fb7f811	736be378-e6ef-4450-afa8-be57caf8d1bc	step9	completed	2026-02-03 23:35:48.46451+00	2026-02-03 23:37:20.437576+00	\N	\N	0
1c59b1e5-1bb6-440f-b6b4-bc7e77350d66	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step10	completed	2026-02-03 23:31:57.280645+00	2026-02-03 23:39:00.362316+00	\N	\N	0
50cdc5a1-9aec-4edf-b390-c32f013e00d4	ce77e4a2-9c91-44d9-aade-32054e4443fa	step12	completed	2026-02-03 23:44:34.468111+00	2026-02-03 23:44:34.644314+00	\N	\N	0
1162373c-16b4-4447-987e-00eefbd12ef0	b7005fcd-2bd4-4017-9e27-b8213ff93061	step12	completed	2026-02-03 23:44:57.117212+00	2026-02-03 23:44:57.304247+00	\N	\N	0
54788455-c12b-463e-acdd-74978b9c514d	736be378-e6ef-4450-afa8-be57caf8d1bc	step12	completed	2026-02-03 23:44:57.304621+00	2026-02-03 23:44:57.491165+00	\N	\N	0
47ef9ed3-7c42-45a7-a2b4-f1c2757e1379	2628769a-47a4-41bf-9666-44c43d8bda4d	step0	completed	2026-02-04 00:14:22.100255+00	2026-02-04 00:14:37.808833+00	\N	\N	0
365c3463-31f3-4809-826a-fecc459095e8	c4f11f16-312e-4634-abc7-1a83a5196cd1	step3a	failed	2026-02-04 03:40:50.404169+00	2026-02-04 03:40:50.494743+00	non_retryable	Failed to render prompt: Missing required variable: step2_data	0
5c6540d6-fff7-4ffc-bd38-aad12f201999	2628769a-47a4-41bf-9666-44c43d8bda4d	step3c	completed	2026-02-04 00:15:04.822066+00	2026-02-04 00:16:14.429868+00	\N	\N	0
12a782f0-f65f-43af-b65e-2f0a28fcf94f	2628769a-47a4-41bf-9666-44c43d8bda4d	step6	completed	2026-02-04 00:21:20.279065+00	2026-02-04 00:22:22.957006+00	\N	\N	0
e07a1c27-dfe8-49b8-b168-e4aa1eaab0fe	fcb7741f-dd21-4ca3-98f6-1befc7c49129	step1	completed	2026-02-04 03:14:57.261151+00	2026-02-04 03:15:00.742206+00	\N	\N	0
cf72d49a-0eea-4fc4-85a2-a6852f417c4f	2628769a-47a4-41bf-9666-44c43d8bda4d	step12	completed	2026-02-04 00:35:32.845621+00	2026-02-04 00:35:33.018028+00	\N	\N	0
6fbf26a3-bbe9-463d-b51a-9119d8755ddb	ba2e4594-2fde-472f-9548-01f281cbc05a	step3c	failed	2026-02-04 03:41:53.932881+00	2026-02-04 03:41:54.004342+00	non_retryable	Failed to render prompt: Missing required variable: step2_data	0
5dc83b91-7746-4049-9fd6-47201db254b7	fcb7741f-dd21-4ca3-98f6-1befc7c49129	step1_5	completed	2026-02-04 03:15:00.825678+00	2026-02-04 03:15:00.9037+00	\N	\N	0
6ae4f213-d0e1-4ad7-86af-cc11a0281f20	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	step3c	completed	2026-02-04 03:14:44.476902+00	2026-02-04 03:16:03.828205+00	\N	\N	0
1ba6e819-4a7f-4530-a8a1-3bf5bea4747d	fcb7741f-dd21-4ca3-98f6-1befc7c49129	step2	completed	2026-02-04 03:20:06.702293+00	2026-02-04 03:20:06.833654+00	\N	\N	0
d18381c8-4be4-48b4-96fa-cee6733866f4	fcb7741f-dd21-4ca3-98f6-1befc7c49129	step3a	completed	2026-02-04 03:20:06.935732+00	2026-02-04 03:20:48.041972+00	\N	\N	0
88f24e2f-d833-4d85-b6f6-0da6445793bf	fe080707-f401-4ceb-812e-4612e5293992	step0	completed	2026-02-04 03:43:23.40015+00	2026-02-04 03:43:40.534049+00	\N	\N	0
6ad2b166-80ea-482a-a611-ce4bfb4e1357	2b0d02af-428d-4d33-ac92-bd35bb86b465	step1	completed	2026-02-04 03:43:38.483913+00	2026-02-04 03:43:40.782821+00	\N	\N	0
eecb84a4-7a6d-44f3-a41e-4b98632c34b7	fe080707-f401-4ceb-812e-4612e5293992	step1_5	completed	2026-02-04 03:43:44.290852+00	2026-02-04 03:43:44.377418+00	\N	\N	0
5b6df1af-d244-444e-b123-e56656d6af9f	460ee6fe-60bb-4454-83f9-30be3232b345	step0	completed	2026-02-04 03:44:20.52171+00	2026-02-04 03:44:38.466771+00	\N	\N	0
59bbafbc-dd75-4310-83e8-886bce005171	460ee6fe-60bb-4454-83f9-30be3232b345	step1	completed	2026-02-04 03:44:38.547278+00	2026-02-04 03:44:42.017716+00	\N	\N	0
104a110f-eb0e-47a1-b2ab-15107561cbfd	fe080707-f401-4ceb-812e-4612e5293992	step3c	completed	2026-02-04 03:43:50.735959+00	2026-02-04 03:45:09.331356+00	\N	\N	0
2f483c2f-2884-4eee-ac23-8cf8058d51af	fe080707-f401-4ceb-812e-4612e5293992	step3b	completed	2026-02-04 03:43:50.762746+00	2026-02-04 03:45:47.150307+00	\N	\N	0
abe53eed-bd76-451b-b77e-939eb986baff	460ee6fe-60bb-4454-83f9-30be3232b345	step3a	completed	2026-02-04 03:45:28.047158+00	2026-02-04 03:46:10.248818+00	\N	\N	0
33b50023-8c96-4ce9-b9a4-b18240009899	460ee6fe-60bb-4454-83f9-30be3232b345	step3c	completed	2026-02-04 03:45:28.023218+00	2026-02-04 03:46:38.77801+00	\N	\N	0
65dfa9f8-2fe1-48e7-9fa8-18fcdf509b02	460ee6fe-60bb-4454-83f9-30be3232b345	step3b	completed	2026-02-04 03:45:28.02301+00	2026-02-04 03:47:34.677305+00	\N	\N	0
d5e19fae-aa0c-473a-a144-b31d622bdff4	460ee6fe-60bb-4454-83f9-30be3232b345	step3_5	completed	2026-02-04 03:49:08.11042+00	2026-02-04 03:49:33.376117+00	\N	\N	0
b9654692-e483-44a8-8150-f30a6643dd51	fe080707-f401-4ceb-812e-4612e5293992	step5	completed	2026-02-04 03:47:27.117316+00	2026-02-04 03:50:36.560017+00	\N	\N	0
27ed341b-d33c-4f8d-983e-97fa36a9726c	460ee6fe-60bb-4454-83f9-30be3232b345	step5	completed	2026-02-04 03:50:47.448921+00	2026-02-04 03:53:51.076591+00	\N	\N	0
f250d0b2-e6f5-4ba6-b877-06e04f2fe79f	fe080707-f401-4ceb-812e-4612e5293992	step6_5	failed	2026-02-04 03:54:29.727568+00	2026-02-04 03:55:25.448372+00	retryable	Failed to parse JSON response: format=unknown	0
a8e88ee6-4795-431e-9995-5dc5c2025777	460ee6fe-60bb-4454-83f9-30be3232b345	step6	completed	2026-02-04 03:53:51.156652+00	2026-02-04 03:55:41.759843+00	\N	\N	0
060501a2-db32-4359-b39f-9e2a7cdf2401	460ee6fe-60bb-4454-83f9-30be3232b345	step7a	completed	2026-02-04 04:01:43.064432+00	2026-02-04 04:02:41.901+00	\N	\N	0
8d673c79-1720-45e4-811c-9085a67c8ce1	460ee6fe-60bb-4454-83f9-30be3232b345	step6_5	completed	2026-02-04 04:00:56.656888+00	2026-02-04 04:01:42.975249+00	\N	\N	0
1bff5992-720b-41f2-8402-6a761d9638d2	460ee6fe-60bb-4454-83f9-30be3232b345	step7b	completed	2026-02-04 04:02:41.995914+00	2026-02-04 04:03:30.055885+00	\N	\N	0
98cbd98c-6c5b-4178-912c-9f9e5ba69c5d	460ee6fe-60bb-4454-83f9-30be3232b345	step8	completed	2026-02-04 04:03:30.143753+00	2026-02-04 04:05:39.616541+00	\N	\N	0
f6928eb8-6926-4dad-99a6-698b89c36207	460ee6fe-60bb-4454-83f9-30be3232b345	step9	completed	2026-02-04 04:05:39.709049+00	2026-02-04 04:07:20.674089+00	\N	\N	0
fe5ce7d2-e271-4fec-8b6c-381fecc9946c	40186126-cf83-4b8f-a524-d9ad733d4938	step1	completed	2026-02-03 13:24:32.394927+00	2026-02-03 13:24:35.256837+00	\N	\N	0
41d72718-d781-4062-8d1d-5f13db4878ea	f92d9d06-2bbb-404a-8cee-7f574d87c12b	step0	completed	2026-02-03 13:24:36.340575+00	2026-02-03 13:24:39.211091+00	\N	\N	0
869cad11-8430-452e-8eb5-91c2a21a29a3	02e16ff7-b095-429e-902c-dadc644bc252	step4	completed	2026-02-04 08:15:10.955627+00	2026-02-04 08:15:46.325993+00	\N	\N	0
ce0cdf99-190f-400b-ad44-de93bf2d9e8c	f92d9d06-2bbb-404a-8cee-7f574d87c12b	step1_5	completed	2026-02-03 13:24:40.305822+00	2026-02-03 13:24:40.393847+00	\N	\N	0
02d30e2e-7784-45fd-a210-1f51f2ead17a	4d711f0b-58c6-4217-8325-cfd18b0d577b	step7b	completed	2026-02-03 13:50:16.278505+00	2026-02-03 13:50:42.916119+00	\N	\N	0
c9092576-d5b4-466e-92e9-23aace3751d3	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step0	completed	2026-02-03 13:24:51.373113+00	2026-02-03 13:24:54.310132+00	\N	\N	0
c50af063-500e-4ad5-a78f-29e8ef35b6e7	4d711f0b-58c6-4217-8325-cfd18b0d577b	step0	completed	2026-02-03 13:24:51.432512+00	2026-02-03 13:24:55.201612+00	\N	\N	0
f8eff66d-0fd3-497e-b6f0-4c2ea0649ad2	b7005fcd-2bd4-4017-9e27-b8213ff93061	step6	completed	2026-02-03 23:23:29.449956+00	2026-02-03 23:24:33.827698+00	\N	\N	0
421dfbf7-f9bc-4b0b-ab60-ead1ac1b8c78	90dcfdc4-ebc1-4746-a09f-a9476d268565	step1_5	completed	2026-02-03 13:24:59.583145+00	2026-02-03 13:24:59.765443+00	\N	\N	0
0a6841f5-c3f0-4121-b7f9-57685c381c79	894a1783-f00d-431b-89fc-f3ed0984cc1a	step0	completed	2026-02-04 08:17:07.830042+00	2026-02-04 08:17:15.416851+00	\N	\N	0
7a8796a1-0da6-43ae-a751-b82132d56883	4d711f0b-58c6-4217-8325-cfd18b0d577b	step1_5	completed	2026-02-03 13:24:59.519125+00	2026-02-03 13:24:59.592901+00	\N	\N	0
9da8a3d9-a8b6-40aa-bb2b-5a158e160eea	4d711f0b-58c6-4217-8325-cfd18b0d577b	step8	completed	2026-02-03 13:50:43.018599+00	2026-02-03 13:51:39.243253+00	\N	\N	0
a3608d75-7d1f-4abd-b68c-222562500cb6	9250e89e-ab21-419b-8b02-4d623b275c67	step8	completed	2026-02-03 13:51:13.568835+00	2026-02-03 13:51:56.936161+00	\N	\N	0
a71ecdde-2d24-42e7-a1a9-9807c83b9cbe	ce77e4a2-9c91-44d9-aade-32054e4443fa	step7a	completed	2026-02-03 23:27:13.175258+00	2026-02-03 23:27:47.83134+00	\N	\N	0
0c190ef8-6de9-41c1-84e0-b73384457880	90dcfdc4-ebc1-4746-a09f-a9476d268565	step10	completed	2026-02-03 13:52:49.585725+00	2026-02-03 13:56:48.914142+00	\N	\N	0
5b531fb9-08b7-4d86-9d25-91f624eeb32a	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step7b	completed	2026-02-03 23:27:55.452355+00	2026-02-03 23:28:36.876061+00	\N	\N	0
4728a01d-0af6-49fe-85f6-a59d0310272a	0e87f430-0bda-4e81-9a38-aa67f402ac42	step0	completed	2026-02-03 23:14:05.683365+00	2026-02-03 23:14:18.770344+00	\N	\N	0
e2344543-1c43-41b3-9e0a-3947cbe4a766	3941a942-8c1a-4244-a34b-5005a080d96a	step0	completed	2026-02-03 23:14:05.771754+00	2026-02-03 23:14:18.770936+00	\N	\N	0
6bfd9421-c195-4592-8228-f8153fe0b37c	ce77e4a2-9c91-44d9-aade-32054e4443fa	step8	completed	2026-02-03 23:28:23.997207+00	2026-02-03 23:30:30.014655+00	\N	\N	0
c11d7ff6-487c-45b6-a139-7ca043487010	0e87f430-0bda-4e81-9a38-aa67f402ac42	step1_5	completed	2026-02-03 23:14:21.572595+00	2026-02-03 23:14:21.664165+00	\N	\N	0
9283f26f-d908-4385-8037-f393d13dcab6	67dc0b59-5ff5-4d35-8fcb-92de7bdadcb4	step1	completed	2026-02-03 23:14:18.203911+00	2026-02-03 23:14:24.231669+00	\N	\N	0
8f3192a9-9d7b-4d64-bd90-f9dd9de2acc6	736be378-e6ef-4450-afa8-be57caf8d1bc	step6	completed	2026-02-03 23:30:41.557239+00	2026-02-03 23:31:46.652585+00	\N	\N	0
4bf2189d-d89f-44fa-87b9-2cdbfb3adda5	67dc0b59-5ff5-4d35-8fcb-92de7bdadcb4	step1_5	completed	2026-02-03 23:14:24.312947+00	2026-02-03 23:14:24.40004+00	\N	\N	0
fb643a13-cc1e-4706-b259-ed44ef533498	3941a942-8c1a-4244-a34b-5005a080d96a	step1	completed	2026-02-03 23:14:18.917196+00	2026-02-03 23:14:29.66634+00	\N	\N	0
529d0211-e762-4e5c-9895-d64d869f743a	ce77e4a2-9c91-44d9-aade-32054e4443fa	step10	completed	2026-02-03 23:32:16.192053+00	2026-02-03 23:39:14.286027+00	\N	\N	0
9969b22c-49ea-46db-a8fa-ee26e76876be	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step0	completed	2026-02-03 23:14:37.160768+00	2026-02-03 23:14:51.531341+00	\N	\N	0
ca62ba56-42bd-4c0f-8f5a-51844bd561fe	b7005fcd-2bd4-4017-9e27-b8213ff93061	step10	completed	2026-02-03 23:36:27.574672+00	2026-02-03 23:44:05.506582+00	\N	\N	0
0b38a302-1181-45ea-85a0-8135468e7c8d	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step1_5	completed	2026-02-03 23:14:52.298547+00	2026-02-03 23:14:52.391593+00	\N	\N	0
3f9c216a-d6f6-4553-98fc-7b7636878da3	736be378-e6ef-4450-afa8-be57caf8d1bc	step0	completed	2026-02-03 23:14:48.465151+00	2026-02-03 23:15:03.534334+00	\N	\N	0
d8868a99-df70-4bf4-87f8-942c89a00bb2	736be378-e6ef-4450-afa8-be57caf8d1bc	step1_5	completed	2026-02-03 23:15:04.247304+00	2026-02-03 23:15:04.342202+00	\N	\N	0
ba2becbb-3616-41ea-991d-8d4d69d19515	2628769a-47a4-41bf-9666-44c43d8bda4d	step3a	completed	2026-02-04 00:15:04.865856+00	2026-02-04 00:15:45.018063+00	\N	\N	0
e1da0854-9b8a-47a0-90be-63dff3f1e92e	b7005fcd-2bd4-4017-9e27-b8213ff93061	step1_5	completed	2026-02-03 23:15:04.944136+00	2026-02-03 23:15:05.039188+00	\N	\N	0
d1bed3c2-7cb7-452a-80dc-a0cc1c109e41	ce77e4a2-9c91-44d9-aade-32054e4443fa	step0	completed	2026-02-03 23:14:48.365881+00	2026-02-03 23:15:07.76048+00	\N	\N	0
0e327e21-d176-447f-8f4d-c37fb5381593	ce77e4a2-9c91-44d9-aade-32054e4443fa	step1_5	completed	2026-02-03 23:15:08.655653+00	2026-02-03 23:15:08.751572+00	\N	\N	0
1b4d9fcd-b13d-440c-9b38-1ac67d3b6203	2628769a-47a4-41bf-9666-44c43d8bda4d	step7a	completed	2026-02-04 00:23:04.111893+00	2026-02-04 00:23:42.305862+00	\N	\N	0
60e60807-a9c8-45d8-bd6d-b92e433afc69	736be378-e6ef-4450-afa8-be57caf8d1bc	step2	completed	2026-02-03 23:16:52.622125+00	2026-02-03 23:16:53.051224+00	\N	\N	0
8ec0ea7f-9942-4fa2-812b-895e57d11a4a	736be378-e6ef-4450-afa8-be57caf8d1bc	step3c	completed	2026-02-03 23:16:53.335896+00	2026-02-03 23:18:02.185147+00	\N	\N	0
45af55d3-338e-496d-a356-bec6c7c4dde1	2628769a-47a4-41bf-9666-44c43d8bda4d	step9	completed	2026-02-04 00:26:28.666363+00	2026-02-04 00:27:37.9674+00	\N	\N	0
1c6f03af-97c5-46f4-a58e-0daa3f183310	ce77e4a2-9c91-44d9-aade-32054e4443fa	step3_5	completed	2026-02-03 23:20:57.149103+00	2026-02-03 23:21:21.928453+00	\N	\N	0
25bf9b27-4f2e-4643-a6e3-4c63f1ab14da	c4f11f16-312e-4634-abc7-1a83a5196cd1	step3c	failed	2026-02-04 03:40:50.403773+00	2026-02-04 03:40:50.49449+00	non_retryable	Failed to render prompt: Missing required variable: step2_data	0
f82427a2-b4ea-4f2e-8ed9-1dcf013adc68	0af170e5-6cff-40f4-8de4-b8e85f5c9912	step0	failed	2026-02-04 00:39:18.911186+00	2026-02-04 00:39:53.144416+00	retryable	'QualityResult' object has no attribute 'is_valid'	0
027434fc-88f3-4a8d-bbd1-e67d7092bd84	ba2e4594-2fde-472f-9548-01f281cbc05a	step3a	failed	2026-02-04 03:41:53.935352+00	2026-02-04 03:41:54.004595+00	non_retryable	Failed to render prompt: Missing required variable: step2_data	0
bb49316c-a7d5-4dfe-8f85-786bd58b5f3d	a5bcf4f3-d9e4-4ce2-b6d0-6deaf1194ac2	step0	completed	2026-02-04 00:44:00.073257+00	2026-02-04 00:44:34.041903+00	\N	\N	0
8e26ccbb-09c8-4975-9791-54e9b97490ff	a5bcf4f3-d9e4-4ce2-b6d0-6deaf1194ac2	step1	completed	2026-02-04 00:44:34.134286+00	2026-02-04 00:44:34.470073+00	\N	\N	0
66a028e7-dc70-4b5c-af9e-c94a08cf63be	a5bcf4f3-d9e4-4ce2-b6d0-6deaf1194ac2	step1_5	completed	2026-02-04 00:44:34.560922+00	2026-02-04 00:44:34.650249+00	\N	\N	0
c07a8194-8010-40e4-8e08-fb3748830d20	2b0d02af-428d-4d33-ac92-bd35bb86b465	step1_5	completed	2026-02-04 03:43:40.871313+00	2026-02-04 03:43:40.949691+00	\N	\N	0
e4ead386-f98d-4a6f-89d1-fd4cb426c155	fe080707-f401-4ceb-812e-4612e5293992	step1	completed	2026-02-04 03:43:40.76122+00	2026-02-04 03:43:44.204162+00	\N	\N	0
b298a576-fb55-4cbf-8085-19afdad9d865	fe080707-f401-4ceb-812e-4612e5293992	step2	completed	2026-02-04 03:43:50.476344+00	2026-02-04 03:43:50.621508+00	\N	\N	0
b24459f2-61bc-49cf-bf06-70a87435774f	a5bcf4f3-d9e4-4ce2-b6d0-6deaf1194ac2	step2	failed	2026-02-04 00:46:41.739485+00	2026-02-04 00:46:41.782808+00	retryable	'InputValidationResult' object has no attribute 'is_acceptable'	0
97e3546b-838a-40e9-ad37-fc44898ec128	fe080707-f401-4ceb-812e-4612e5293992	step3a	completed	2026-02-04 03:43:50.754942+00	2026-02-04 03:44:35.012811+00	\N	\N	0
98781604-ea67-48a9-b3e0-25f7491eb8ae	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	step0	completed	2026-02-04 00:47:57.725667+00	2026-02-04 00:48:27.659085+00	\N	\N	0
6d57713d-0215-4d94-8cfe-54e2856b9786	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	step1	completed	2026-02-04 00:48:27.750606+00	2026-02-04 00:48:28.589744+00	\N	\N	0
f2766c06-abff-45f5-b793-29efd962c42c	460ee6fe-60bb-4454-83f9-30be3232b345	step1_5	completed	2026-02-04 03:44:42.095582+00	2026-02-04 03:44:42.179748+00	\N	\N	0
1092c07e-0d4d-415a-b7be-2a78038a15e5	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	step1_5	completed	2026-02-04 00:48:28.681168+00	2026-02-04 00:48:28.772493+00	\N	\N	0
84a425b6-87fe-47d2-869b-ddb8223d1373	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	step3c	completed	2026-02-04 03:15:34.58279+00	2026-02-04 03:16:59.728044+00	\N	\N	0
fc50c999-0198-4181-af93-d9cdbbb86680	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	step2	completed	2026-02-04 00:48:35.054104+00	2026-02-04 00:48:35.199434+00	\N	\N	0
b070737c-85dc-4e97-99b5-6da4532e947e	fb98fa48-bfa5-4034-8d13-7ae6b6d9c1fc	step3b	completed	2026-02-04 03:15:34.581988+00	2026-02-04 03:17:03.04634+00	\N	\N	0
917088a2-e31c-4a86-8e68-f624eb83742c	460ee6fe-60bb-4454-83f9-30be3232b345	step2	completed	2026-02-04 03:45:27.770893+00	2026-02-04 03:45:27.901473+00	\N	\N	0
0e239a01-4801-46c7-a06f-389a1aecd51e	edda5f45-cc65-43e2-8030-837e22e237d4	step0	failed	2026-02-04 03:28:56.702621+00	2026-02-04 03:28:56.735625+00	retryable	Unknown LLM provider: google	0
885cb311-2847-4f1c-854b-c27dd497de41	83bb3054-6602-47a6-80f1-7b724c30fa69	step0	failed	2026-02-04 03:29:16.066021+00	2026-02-04 03:29:16.0948+00	retryable	Unknown LLM provider: blog	0
e323d071-05fe-4db5-bef7-aad3910ff02f	3022c25f-f16b-4816-877c-90cb9847bfb6	step0	failed	2026-02-04 03:29:33.469798+00	2026-02-04 03:29:33.522181+00	retryable	Unknown LLM provider: google	0
514176e2-4a1c-49bb-b0fb-70f43f62e8f7	c46548f7-2a8d-4370-a937-9090a5afce03	step0	failed	2026-02-04 03:30:44.925898+00	2026-02-04 03:31:16.567007+00	retryable	'QualityResult' object has no attribute 'is_valid'	0
a280d7fe-d124-4c3f-8900-393beef0f467	1e9fdb8e-bed1-4055-99aa-b0df904b2331	step0	running	2026-02-04 03:34:02.977096+00	\N	\N	\N	3
7e9236aa-0420-4e60-b16b-912aa2e53ddc	ba2e4594-2fde-472f-9548-01f281cbc05a	step0	completed	2026-02-04 03:34:46.358861+00	2026-02-04 03:35:17.852327+00	\N	\N	0
167c6825-270d-4a82-90f0-74590c4624f8	ba2e4594-2fde-472f-9548-01f281cbc05a	step1	completed	2026-02-04 03:35:17.939462+00	2026-02-04 03:35:23.231373+00	\N	\N	0
32ebb4c8-cfaa-4968-b6d4-9c999b85494e	c4f11f16-312e-4634-abc7-1a83a5196cd1	step0	completed	2026-02-04 03:35:00.045696+00	2026-02-04 03:35:33.350183+00	\N	\N	0
e330d988-3069-4ab3-afa1-0668fc8e7f5c	ba2e4594-2fde-472f-9548-01f281cbc05a	step2	completed	2026-02-04 03:36:24.56465+00	2026-02-04 03:36:24.725092+00	\N	\N	0
1addfdb3-6379-4347-b9c6-439e189c1c03	fe0702c5-d13e-47cd-a2d4-cf3e91e5f981	step3a	completed	2026-02-04 03:02:35.61882+00	2026-02-04 03:03:14.939193+00	\N	\N	0
4ec11ad1-4b00-486c-80e7-21a53d9c1b2e	90dcfdc4-ebc1-4746-a09f-a9476d268565	step0	completed	2026-02-03 13:24:51.512536+00	2026-02-03 13:24:54.379092+00	\N	\N	0
7acbae50-feb7-4170-a3f5-fb37a56d96f8	4d711f0b-58c6-4217-8325-cfd18b0d577b	step6	completed	2026-02-03 13:48:29.855811+00	2026-02-03 13:49:09.917205+00	\N	\N	0
4c950083-22d7-417a-a695-956a4aa7ed6d	9250e89e-ab21-419b-8b02-4d623b275c67	step1_5	completed	2026-02-03 13:24:55.093885+00	2026-02-03 13:24:55.200709+00	\N	\N	0
8937d5c4-3a65-4f28-82c8-4021d32f8a88	9250e89e-ab21-419b-8b02-4d623b275c67	step5	completed	2026-02-03 13:47:47.842571+00	2026-02-03 13:49:35.759558+00	\N	\N	0
48ff1dac-bd1d-44cc-8e4e-0a8de856fad4	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step5	completed	2026-02-03 13:47:48.58229+00	2026-02-03 13:50:09.802684+00	\N	\N	0
fefbf20d-de41-4fd0-8d61-807512c09776	90dcfdc4-ebc1-4746-a09f-a9476d268565	step5	completed	2026-02-03 13:47:42.022415+00	2026-02-03 13:50:18.542384+00	\N	\N	0
9e2d6c85-d84c-4e5d-a94e-9a5057c0e63c	9250e89e-ab21-419b-8b02-4d623b275c67	step2	completed	2026-02-03 13:25:48.55513+00	2026-02-03 13:25:48.837472+00	\N	\N	0
fd022cf7-61d5-472c-90b8-e8400647a38c	9250e89e-ab21-419b-8b02-4d623b275c67	step7a	completed	2026-02-03 13:50:25.326944+00	2026-02-03 13:50:50.022498+00	\N	\N	0
869d55dd-b902-44b3-a4b7-b85a7f3ff877	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step2	completed	2026-02-03 13:25:48.67981+00	2026-02-03 13:25:48.868895+00	\N	\N	0
4680cc5b-e782-452b-abe7-7cab537fcb76	90dcfdc4-ebc1-4746-a09f-a9476d268565	step2	completed	2026-02-03 13:25:48.836822+00	2026-02-03 13:25:49.174808+00	\N	\N	0
af5c7d98-257f-4b20-94e6-a4d824b003dd	b7005fcd-2bd4-4017-9e27-b8213ff93061	step6_5	completed	2026-02-03 23:24:33.92409+00	2026-02-03 23:25:20.051784+00	\N	\N	0
dbe8525d-f926-4f13-aed5-368cbf012876	4d711f0b-58c6-4217-8325-cfd18b0d577b	step2	completed	2026-02-03 13:25:48.835395+00	2026-02-03 13:25:49.238941+00	\N	\N	0
2d4a50f3-e58f-4338-b9eb-e8ac39931139	90dcfdc4-ebc1-4746-a09f-a9476d268565	step8	completed	2026-02-03 13:51:36.483842+00	2026-02-03 13:52:25.925849+00	\N	\N	0
18040bc5-f137-4aa3-969e-a77bbf13d38a	9250e89e-ab21-419b-8b02-4d623b275c67	step9	completed	2026-02-03 13:51:57.075667+00	2026-02-03 13:52:35.816986+00	\N	\N	0
37c5c0fa-360b-4d7c-bd3a-a155f5b95dcc	90dcfdc4-ebc1-4746-a09f-a9476d268565	step9	completed	2026-02-03 13:52:26.073625+00	2026-02-03 13:52:49.433939+00	\N	\N	0
de3daca6-2e0f-42d6-8323-1251e477e308	b7005fcd-2bd4-4017-9e27-b8213ff93061	step7a	completed	2026-02-03 23:25:20.140637+00	2026-02-03 23:26:00.293944+00	\N	\N	0
09eeaf61-a6f5-4298-a10e-4778a50635b1	9250e89e-ab21-419b-8b02-4d623b275c67	step12	completed	2026-02-03 22:40:27.454985+00	2026-02-03 22:40:27.975412+00	\N	\N	0
2190ef25-d36b-4a77-b526-3e18a02331f9	4d711f0b-58c6-4217-8325-cfd18b0d577b	step12	completed	2026-02-03 22:40:27.486846+00	2026-02-03 22:40:27.976047+00	\N	\N	0
128b7baf-51e0-4a5a-bf20-15adb3f4982e	90dcfdc4-ebc1-4746-a09f-a9476d268565	step12	completed	2026-02-03 22:40:27.490349+00	2026-02-03 22:40:27.994291+00	\N	\N	0
113b697b-f85d-48f7-a628-0b7ae6bab643	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step7a	completed	2026-02-03 22:41:02.693159+00	2026-02-03 22:41:24.244271+00	\N	\N	0
704b8e97-b571-4fdc-9ddd-caba8d8bb355	9250e89e-ab21-419b-8b02-4d623b275c67	step3a	completed	2026-02-03 13:25:49.260737+00	2026-02-03 13:25:58.171092+00	\N	\N	0
6f54df13-df67-4b38-b637-bdd6c485e417	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step3a	completed	2026-02-03 13:25:49.363305+00	2026-02-03 13:25:59.646054+00	\N	\N	0
3639691f-4c73-4199-ae2a-29f054c97bd3	90dcfdc4-ebc1-4746-a09f-a9476d268565	step3a	completed	2026-02-03 13:25:49.509119+00	2026-02-03 13:25:59.67747+00	\N	\N	0
4b8d0c86-cec9-4848-b559-97e3e4827111	4d711f0b-58c6-4217-8325-cfd18b0d577b	step3a	completed	2026-02-03 13:25:49.716013+00	2026-02-03 13:25:59.67812+00	\N	\N	0
54b61d88-a800-4086-9f83-bcaf812df6e0	90dcfdc4-ebc1-4746-a09f-a9476d268565	step3c	completed	2026-02-03 13:25:49.595624+00	2026-02-03 13:26:29.117319+00	\N	\N	0
1b6da590-4198-437d-87a8-bc53815bf956	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step3c	completed	2026-02-03 13:25:49.485523+00	2026-02-03 13:26:32.519605+00	\N	\N	0
753dadfa-a1f0-490e-b961-518ac4adcd28	9250e89e-ab21-419b-8b02-4d623b275c67	step3c	completed	2026-02-03 13:25:49.201063+00	2026-02-03 13:26:33.535834+00	\N	\N	0
393baf51-9433-4d9a-88cd-493d3fffb581	4d711f0b-58c6-4217-8325-cfd18b0d577b	step3c	completed	2026-02-03 13:25:49.63254+00	2026-02-03 13:26:33.677128+00	\N	\N	0
92a5d139-75cf-4428-85b7-cdd416a79d0c	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step3b	completed	2026-02-03 13:25:49.215041+00	2026-02-03 13:27:36.873015+00	\N	\N	0
fb58100b-ddd6-451d-8397-dc4667802134	4d711f0b-58c6-4217-8325-cfd18b0d577b	step3b	completed	2026-02-03 13:25:49.716191+00	2026-02-03 13:27:49.319184+00	\N	\N	0
a9d80308-6e72-444e-a499-16187c290e21	90dcfdc4-ebc1-4746-a09f-a9476d268565	step3b	completed	2026-02-03 13:25:49.61027+00	2026-02-03 13:28:34.637557+00	\N	\N	0
0a033218-84b0-4461-b621-bd87bce7493a	9250e89e-ab21-419b-8b02-4d623b275c67	step3b	completed	2026-02-03 13:25:49.381676+00	2026-02-03 13:28:35.693162+00	\N	\N	0
661174f7-534e-4df1-89cb-a2132dab2213	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step8	completed	2026-02-03 22:41:51.38801+00	2026-02-03 22:42:41.144935+00	\N	\N	0
fbb0b98a-bff7-4eb5-87d7-8e5f856124a6	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step12	completed	2026-02-03 22:46:27.891222+00	2026-02-03 22:46:26.530858+00	\N	\N	0
79ec05ac-7c96-4770-aaad-ae5ba1c1d0aa	9250e89e-ab21-419b-8b02-4d623b275c67	step3_5	completed	2026-02-03 13:47:14.392091+00	2026-02-03 13:47:22.942369+00	\N	\N	0
8e6c6818-eade-4aec-b759-dfc009ac3202	ce77e4a2-9c91-44d9-aade-32054e4443fa	step6_5	completed	2026-02-03 23:26:34.87992+00	2026-02-03 23:27:13.07233+00	\N	\N	0
742c36f3-a524-4de0-a5cc-dbd4aea5117c	4d711f0b-58c6-4217-8325-cfd18b0d577b	step3_5	completed	2026-02-03 13:47:14.664434+00	2026-02-03 13:47:23.827616+00	\N	\N	0
3c367b48-01b3-4940-a44c-dfeb894da311	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step3_5	completed	2026-02-03 13:47:14.518411+00	2026-02-03 13:47:24.862528+00	\N	\N	0
866f9816-37da-45de-881c-c141313354c5	90dcfdc4-ebc1-4746-a09f-a9476d268565	step3_5	completed	2026-02-03 13:47:14.761166+00	2026-02-03 13:47:24.898496+00	\N	\N	0
db913db4-0758-40fe-bb6e-5679318cd421	67dc0b59-5ff5-4d35-8fcb-92de7bdadcb4	step0	completed	2026-02-03 23:14:05.850315+00	2026-02-03 23:14:18.105987+00	\N	\N	0
420e7823-13cf-48f1-aa61-8f0348dbb476	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step8	completed	2026-02-03 23:28:36.981426+00	2026-02-03 23:30:43.881527+00	\N	\N	0
f3a74939-0b13-4611-a325-05a80b47f5c2	90dcfdc4-ebc1-4746-a09f-a9476d268565	step4	completed	2026-02-03 13:47:25.034895+00	2026-02-03 13:47:41.86343+00	\N	\N	0
1aff006b-20bf-459b-b25a-7da934f1b1db	4d711f0b-58c6-4217-8325-cfd18b0d577b	step4	completed	2026-02-03 13:47:23.971258+00	2026-02-03 13:47:43.510107+00	\N	\N	0
5578bfc9-7b39-46e8-ac87-ecece59ed178	29e2016a-8679-48f0-85c6-d237ecc8d30e	step0	completed	2026-02-03 23:14:05.772254+00	2026-02-03 23:14:19.589013+00	\N	\N	0
58821fdc-440d-4d58-96eb-e26c6be9546b	9250e89e-ab21-419b-8b02-4d623b275c67	step4	completed	2026-02-03 13:47:23.09155+00	2026-02-03 13:47:47.693314+00	\N	\N	0
1b3de6dd-ea4e-4a90-8037-5af613942914	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step9	completed	2026-02-03 23:30:43.968686+00	2026-02-03 23:31:57.190951+00	\N	\N	0
9e23f927-cd92-4156-a8d9-cfebab93be84	64133ae9-85fe-4e72-a3f4-4089044e4fc8	step4	completed	2026-02-03 13:47:24.953898+00	2026-02-03 13:47:48.435545+00	\N	\N	0
bae08248-efac-49fd-89d8-e326582fd90b	4d711f0b-58c6-4217-8325-cfd18b0d577b	step5	completed	2026-02-03 13:47:43.665734+00	2026-02-03 13:48:29.710538+00	\N	\N	0
7fe61641-d235-4ae6-8831-b2e7e2de0ce9	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step12	completed	2026-02-03 23:44:34.298989+00	2026-02-03 23:44:34.614782+00	\N	\N	0
fb8a92e0-6a9d-4b4f-9dd6-a8b4b8a0b3af	0e87f430-0bda-4e81-9a38-aa67f402ac42	step1	completed	2026-02-03 23:14:18.916962+00	2026-02-03 23:14:21.490231+00	\N	\N	0
a955d30d-b9ad-4fe4-a347-f5c28699b3f3	29e2016a-8679-48f0-85c6-d237ecc8d30e	step1	completed	2026-02-03 23:14:19.68158+00	2026-02-03 23:14:23.706556+00	\N	\N	0
3e2a68ca-f898-4606-bcc8-5a24c866949c	736be378-e6ef-4450-afa8-be57caf8d1bc	step10	completed	2026-02-03 23:37:20.522604+00	2026-02-03 23:44:54.188277+00	\N	\N	0
08248394-ad2b-4e0c-81b4-84a46a12d7c7	29e2016a-8679-48f0-85c6-d237ecc8d30e	step1_5	completed	2026-02-03 23:14:23.793803+00	2026-02-03 23:14:23.885198+00	\N	\N	0
e9266e61-b346-4f02-bf78-2c414eb762f7	3941a942-8c1a-4244-a34b-5005a080d96a	step1_5	completed	2026-02-03 23:14:29.757413+00	2026-02-03 23:14:29.856251+00	\N	\N	0
97ce97db-8fce-49d1-a341-9ff7355db664	2628769a-47a4-41bf-9666-44c43d8bda4d	step1_5	completed	2026-02-04 00:14:41.674582+00	2026-02-04 00:14:41.769101+00	\N	\N	0
850ab094-e1b8-4f79-b9ed-6ea9598d45bd	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step1	completed	2026-02-03 23:14:51.629438+00	2026-02-03 23:14:52.212524+00	\N	\N	0
b80e6f55-9457-42fc-9b6c-db445a9e4662	2628769a-47a4-41bf-9666-44c43d8bda4d	step2	completed	2026-02-04 00:15:04.555197+00	2026-02-04 00:15:04.70588+00	\N	\N	0
1ddc0178-e5c5-4dfa-9562-1f72151116c8	736be378-e6ef-4450-afa8-be57caf8d1bc	step1	completed	2026-02-03 23:15:03.623376+00	2026-02-03 23:15:04.160994+00	\N	\N	0
de71b5ea-60db-4ad1-b527-b2059f3713c9	b7005fcd-2bd4-4017-9e27-b8213ff93061	step0	completed	2026-02-03 23:14:48.415983+00	2026-02-03 23:15:04.447299+00	\N	\N	0
f4e6dc10-97e5-45cb-a7bc-66f502bd9def	b7005fcd-2bd4-4017-9e27-b8213ff93061	step1	completed	2026-02-03 23:15:04.557381+00	2026-02-03 23:15:04.849663+00	\N	\N	0
0a5cc7e2-9c04-470c-ac7a-4cf51e15c809	2628769a-47a4-41bf-9666-44c43d8bda4d	step3b	completed	2026-02-04 00:15:04.869012+00	2026-02-04 00:16:57.426918+00	\N	\N	0
c81f55f1-dfaa-4062-ad3e-6248b9664336	ce77e4a2-9c91-44d9-aade-32054e4443fa	step1	completed	2026-02-03 23:15:07.849026+00	2026-02-03 23:15:08.562625+00	\N	\N	0
f2bea2ce-3965-45cf-9c3d-558691c41f19	2628769a-47a4-41bf-9666-44c43d8bda4d	step3_5	completed	2026-02-04 00:18:05.998685+00	2026-02-04 00:18:29.313879+00	\N	\N	0
e273a1b9-b400-4ec7-97af-e7109b0a9f0b	736be378-e6ef-4450-afa8-be57caf8d1bc	step3a	completed	2026-02-03 23:16:53.465136+00	2026-02-03 23:17:34.497335+00	\N	\N	0
f90b4ed2-2527-40c8-937a-13dec619b784	efbb3c80-e3d6-4b8b-93f2-bb4a53915a30	step3c	completed	2026-02-03 23:16:52.948533+00	2026-02-03 23:17:52.87113+00	\N	\N	0
fece4965-4216-41f5-9ded-fb884028b95e	ce77e4a2-9c91-44d9-aade-32054e4443fa	step3c	completed	2026-02-03 23:16:53.212299+00	2026-02-03 23:17:58.535844+00	\N	\N	0
ba1b5bd1-0ae3-455b-8507-1a41895674b8	2628769a-47a4-41bf-9666-44c43d8bda4d	step4	completed	2026-02-04 00:18:29.40499+00	2026-02-04 00:19:28.00584+00	\N	\N	0
b95f0644-e048-4442-bf2f-ede59011cd43	ce77e4a2-9c91-44d9-aade-32054e4443fa	step4	completed	2026-02-03 23:21:22.010912+00	2026-02-03 23:22:20.10291+00	\N	\N	0
5110f213-196e-45fc-8cca-e4404bd83722	2628769a-47a4-41bf-9666-44c43d8bda4d	step6_5	completed	2026-02-04 00:22:23.04923+00	2026-02-04 00:23:04.020718+00	\N	\N	0
d0ea6d9f-60d8-4270-8030-957993298d05	2628769a-47a4-41bf-9666-44c43d8bda4d	step7b	completed	2026-02-04 00:23:42.404049+00	2026-02-04 00:24:22.888701+00	\N	\N	0
e707647c-7eca-4014-8d98-242a688c294e	2628769a-47a4-41bf-9666-44c43d8bda4d	step8	completed	2026-02-04 00:24:22.974351+00	2026-02-04 00:26:28.575326+00	\N	\N	0
daeffba6-0b7a-4552-ba63-aea0b7d6fa70	f8d40443-72e7-4705-afb6-09dc53a76743	step0	completed	2026-02-04 07:23:38.149749+00	2026-02-04 07:23:47.4641+00	\N	\N	0
d15c6202-ab4a-4436-a242-9f68953867c9	02e16ff7-b095-429e-902c-dadc644bc252	step3a	completed	2026-02-04 08:12:00.361239+00	2026-02-04 08:12:12.975763+00	\N	\N	0
f24c7261-5e44-4666-8977-27d679a633ab	f8d40443-72e7-4705-afb6-09dc53a76743	step1	completed	2026-02-04 07:23:47.551608+00	2026-02-04 07:24:30.534421+00	\N	\N	0
17005468-ccd1-4601-ab6e-3624b098197e	02e16ff7-b095-429e-902c-dadc644bc252	step3c	completed	2026-02-04 08:12:00.361513+00	2026-02-04 08:12:44.513121+00	\N	\N	0
87677f68-19de-4e5f-9e09-bb4780e4bd72	f8d40443-72e7-4705-afb6-09dc53a76743	step1_5	completed	2026-02-04 07:24:30.619756+00	2026-02-04 07:24:30.705014+00	\N	\N	0
ac866a58-5ac8-4511-bb7b-227ed3363947	02e16ff7-b095-429e-902c-dadc644bc252	step3b	completed	2026-02-04 08:12:00.361274+00	2026-02-04 08:14:41.565759+00	\N	\N	0
dc475488-bd5c-4a5b-bbb6-cd81df482df0	f8d40443-72e7-4705-afb6-09dc53a76743	step2	completed	2026-02-04 07:26:52.365547+00	2026-02-04 07:26:52.496288+00	\N	\N	0
1c8c4f4f-2109-4ca2-bf8b-6aaf70017331	f8d40443-72e7-4705-afb6-09dc53a76743	step3a	completed	2026-02-04 07:26:52.674161+00	2026-02-04 07:27:03.753416+00	\N	\N	0
930712af-907d-4132-baa0-7a75172fca9b	f8d40443-72e7-4705-afb6-09dc53a76743	step3c	completed	2026-02-04 07:26:52.722492+00	2026-02-04 07:27:27.148665+00	\N	\N	0
f6b6d136-2dd5-476b-bf9f-ab38a981bf1f	f8d40443-72e7-4705-afb6-09dc53a76743	step3b	completed	2026-02-04 07:26:52.720794+00	2026-02-04 07:29:33.732174+00	\N	\N	0
68b1ed93-bb1d-4257-89fb-b0f509fb9774	f8d40443-72e7-4705-afb6-09dc53a76743	step3_5	completed	2026-02-04 08:09:05.530636+00	2026-02-04 08:09:16.111335+00	\N	\N	0
ee82de17-6618-4a9d-9aad-20151838f21f	02e16ff7-b095-429e-902c-dadc644bc252	step5	failed	2026-02-04 08:15:54.343513+00	2026-02-04 08:15:54.38225+00	retryable	unhashable type: 'list'	0
97da929e-f27a-47fb-8e92-ace9af59b41e	f8d40443-72e7-4705-afb6-09dc53a76743	step4	completed	2026-02-04 08:09:16.195262+00	2026-02-04 08:09:51.637908+00	\N	\N	0
90d86cec-09cf-4f04-81df-26864d6c9d64	894a1783-f00d-431b-89fc-f3ed0984cc1a	step1	completed	2026-02-04 08:17:15.504316+00	2026-02-04 08:17:29.623677+00	\N	\N	0
41ef7722-b526-47e5-b7b7-fadd0afe1e51	894a1783-f00d-431b-89fc-f3ed0984cc1a	step1_5	completed	2026-02-04 08:17:29.70953+00	2026-02-04 08:17:29.790797+00	\N	\N	0
962fa5fe-0789-44ae-9336-67020c30ae2b	f8d40443-72e7-4705-afb6-09dc53a76743	step5	failed	2026-02-04 08:10:01.099231+00	2026-02-04 08:10:01.152448+00	retryable	unhashable type: 'slice'	0
4f5ecdaa-b65d-478a-944e-86f267ecb6e7	894a1783-f00d-431b-89fc-f3ed0984cc1a	step2	completed	2026-02-04 10:39:04.091678+00	2026-02-04 10:39:04.23402+00	\N	\N	0
6cd0fe2e-e156-4d33-abb1-cbcea9862638	02e16ff7-b095-429e-902c-dadc644bc252	step0	completed	2026-02-04 08:11:28.145085+00	2026-02-04 08:11:37.945721+00	\N	\N	0
f191a5ee-0776-42d7-8f7d-5a1369b12866	02e16ff7-b095-429e-902c-dadc644bc252	step1	completed	2026-02-04 08:11:38.034041+00	2026-02-04 08:11:52.077013+00	\N	\N	0
239a132c-f0ac-4af3-82bd-6aff6276b3ca	02e16ff7-b095-429e-902c-dadc644bc252	step1_5	completed	2026-02-04 08:11:52.163281+00	2026-02-04 08:11:52.244633+00	\N	\N	0
0aa42a92-1ade-4dfd-9113-5d9101a077ed	02e16ff7-b095-429e-902c-dadc644bc252	step2	completed	2026-02-04 08:12:00.095984+00	2026-02-04 08:12:00.239705+00	\N	\N	0
d7033dc1-7472-45c5-8dae-2a6c2dcbd5b6	894a1783-f00d-431b-89fc-f3ed0984cc1a	step3a	completed	2026-02-04 10:39:04.359885+00	2026-02-04 10:39:11.790816+00	\N	\N	0
880e8253-e499-4d46-90f4-372d4ab9afaa	894a1783-f00d-431b-89fc-f3ed0984cc1a	step3c	completed	2026-02-04 10:39:04.360256+00	2026-02-04 10:39:48.220107+00	\N	\N	0
7419baae-b8ec-48ba-ab51-fb087116df9a	894a1783-f00d-431b-89fc-f3ed0984cc1a	step3b	completed	2026-02-04 10:39:04.360356+00	2026-02-04 10:40:00.593495+00	\N	\N	0
db5d37dc-2826-48b1-a892-a35559dc1ef4	894a1783-f00d-431b-89fc-f3ed0984cc1a	step3_5	completed	2026-02-04 10:40:04.292131+00	2026-02-04 10:40:17.412726+00	\N	\N	0
12d562c9-19bd-4ef1-9a92-819447a2e9f1	894a1783-f00d-431b-89fc-f3ed0984cc1a	step4	completed	2026-02-04 10:40:17.514227+00	2026-02-04 10:40:55.827188+00	\N	\N	0
d1259300-1463-44f0-ab06-36ff3d297d23	894a1783-f00d-431b-89fc-f3ed0984cc1a	step5	failed	2026-02-04 10:41:08.870769+00	2026-02-04 10:41:13.931247+00	retryable	Failed to parse queries: format=json	0
8585ab01-d72a-40b0-be99-e50438b12bf3	34d18bb2-1742-43d7-82da-feec95f2294d	step0	completed	2026-02-04 10:43:03.816059+00	2026-02-04 10:43:11.301346+00	\N	\N	0
f2e630f8-fd1f-422d-b265-bd9017355aba	34d18bb2-1742-43d7-82da-feec95f2294d	step1	completed	2026-02-04 10:43:11.418192+00	2026-02-04 10:43:28.803027+00	\N	\N	0
f5794a84-8738-413b-bfd6-13682cfc1df0	34d18bb2-1742-43d7-82da-feec95f2294d	step1_5	completed	2026-02-04 10:43:28.907684+00	2026-02-04 10:43:29.005528+00	\N	\N	0
10fe5c5c-d888-46b2-9045-5ed1eac7cb92	34d18bb2-1742-43d7-82da-feec95f2294d	step2	completed	2026-02-04 10:45:22.206161+00	2026-02-04 10:45:22.372632+00	\N	\N	0
a25eef98-524e-4738-a12c-25e67753e71d	34d18bb2-1742-43d7-82da-feec95f2294d	step3a	completed	2026-02-04 10:45:22.509201+00	2026-02-04 10:45:29.994492+00	\N	\N	0
51c3e05b-04d2-4089-a63f-20e1f183b22c	34d18bb2-1742-43d7-82da-feec95f2294d	step3c	completed	2026-02-04 10:45:22.5087+00	2026-02-04 10:45:57.935139+00	\N	\N	0
1eabc598-266e-48aa-a0c7-d00da039d45b	34d18bb2-1742-43d7-82da-feec95f2294d	step3b	completed	2026-02-04 10:45:22.508406+00	2026-02-04 10:48:11.563698+00	\N	\N	0
18e7707c-f10b-4808-bf93-534bac3d132b	34d18bb2-1742-43d7-82da-feec95f2294d	step3_5	completed	2026-02-04 10:48:19.731943+00	2026-02-04 10:48:33.0497+00	\N	\N	0
11148837-96ce-4659-86cd-905b0b113d30	34d18bb2-1742-43d7-82da-feec95f2294d	step4	completed	2026-02-04 10:48:33.187297+00	2026-02-04 10:49:16.580742+00	\N	\N	0
7eefb6b1-8e34-468e-8058-deebd7eb304b	34d18bb2-1742-43d7-82da-feec95f2294d	step5	failed	2026-02-04 10:49:32.722003+00	2026-02-04 10:49:38.533274+00	retryable	Failed to parse queries: format=json	0
4dc48917-6cbe-4c26-ad92-3116eb407ef9	a87b2257-2fbf-4635-b21b-7f0779261103	step0	completed	2026-02-04 10:50:05.307229+00	2026-02-04 10:50:13.425106+00	\N	\N	0
59104252-036a-4ce4-bcd2-84612e2bc844	a87b2257-2fbf-4635-b21b-7f0779261103	step1	completed	2026-02-04 10:50:13.569685+00	2026-02-04 10:50:15.347142+00	\N	\N	0
22c45f53-e7d0-4835-b7bf-ce6da5030f30	a87b2257-2fbf-4635-b21b-7f0779261103	step1_5	completed	2026-02-04 10:50:15.449752+00	2026-02-04 10:50:15.541839+00	\N	\N	0
675893ab-cb1d-448b-8dd1-29bae79f6748	a87b2257-2fbf-4635-b21b-7f0779261103	step2	completed	2026-02-04 10:50:49.345651+00	2026-02-04 10:50:49.516567+00	\N	\N	0
db390bab-ea0b-4516-ac49-cf0a60e0c411	a87b2257-2fbf-4635-b21b-7f0779261103	step3a	completed	2026-02-04 10:50:49.663187+00	2026-02-04 10:51:08.845597+00	\N	\N	0
a79d3d86-c851-4a91-a44f-bb50a6884776	a87b2257-2fbf-4635-b21b-7f0779261103	step3c	completed	2026-02-04 10:50:49.667134+00	2026-02-04 10:51:24.333443+00	\N	\N	0
b4524e8a-de6b-497b-b0b5-ce18f7cb38a7	a87b2257-2fbf-4635-b21b-7f0779261103	step3b	completed	2026-02-04 10:50:49.666474+00	2026-02-04 10:53:34.468865+00	\N	\N	0
54145f5a-75a8-4636-b7ac-8fcf3d9d275b	a87b2257-2fbf-4635-b21b-7f0779261103	step3_5	completed	2026-02-04 10:53:44.036928+00	2026-02-04 10:53:54.277793+00	\N	\N	0
2a07b6d9-f042-4777-8cdd-c2067ed84866	a87b2257-2fbf-4635-b21b-7f0779261103	step4	completed	2026-02-04 10:53:54.429288+00	2026-02-04 10:54:34.948375+00	\N	\N	0
32ada4c1-af1a-492c-af46-3f9b88e471cb	a87b2257-2fbf-4635-b21b-7f0779261103	step5	completed	2026-02-04 10:54:35.084687+00	2026-02-04 10:56:53.115603+00	\N	\N	0
c66a74a6-ac50-45ef-8bf0-de88fc03d3cb	a87b2257-2fbf-4635-b21b-7f0779261103	step6	completed	2026-02-04 10:56:53.283563+00	2026-02-04 10:57:36.683876+00	\N	\N	0
46f2f642-91eb-426d-8202-1336bd2bfdae	a87b2257-2fbf-4635-b21b-7f0779261103	step6_5	completed	2026-02-04 10:57:36.828881+00	2026-02-04 10:57:57.068744+00	\N	\N	0
b3bc601e-0d55-479c-9c7f-9808324e56d5	7fefa4b1-e1db-4cb9-9812-6e87946f3aa8	step0	completed	2026-02-04 11:01:16.320123+00	2026-02-04 11:01:24.090632+00	\N	\N	0
e55153a4-2bcd-4483-8677-27ac96f163c5	7fefa4b1-e1db-4cb9-9812-6e87946f3aa8	step1	completed	2026-02-04 11:01:24.250354+00	2026-02-04 11:01:25.819245+00	\N	\N	0
5174129f-66e5-4731-9c0b-a606ea910803	7fefa4b1-e1db-4cb9-9812-6e87946f3aa8	step1_5	completed	2026-02-04 11:01:25.939815+00	2026-02-04 11:01:26.042605+00	\N	\N	0
1d326c1b-0938-49f9-90c0-ee3d5ca9f174	a87b2257-2fbf-4635-b21b-7f0779261103	step7b	completed	2026-02-04 11:06:43.014398+00	2026-02-04 11:07:17.818754+00	\N	\N	0
d00b3014-d25e-486a-8fb1-b428fbfd270d	a87b2257-2fbf-4635-b21b-7f0779261103	step7a	completed	2026-02-04 11:05:39.755976+00	2026-02-04 11:06:42.91104+00	\N	\N	0
34a8968c-a5ff-486c-bad3-e6dd4fd86942	a87b2257-2fbf-4635-b21b-7f0779261103	step8	completed	2026-02-04 11:07:17.973746+00	2026-02-04 11:08:01.425309+00	\N	\N	0
8b184c68-69b7-453d-ac65-f09ed481acee	a87b2257-2fbf-4635-b21b-7f0779261103	step9	completed	2026-02-04 11:12:56.698649+00	2026-02-04 11:13:52.023023+00	\N	\N	0
904acb82-371b-4e45-a65e-12341b970666	a87b2257-2fbf-4635-b21b-7f0779261103	step10	completed	2026-02-04 11:13:52.132701+00	2026-02-04 11:17:56.228806+00	\N	\N	0
fd3e6f6c-3f48-4103-942d-0013ab456566	a87b2257-2fbf-4635-b21b-7f0779261103	step12	completed	2026-02-04 11:18:40.005687+00	2026-02-04 11:18:40.189757+00	\N	\N	0
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: seo
--

COPY public.tenants (id, name, database_url, is_active, created_at, updated_at) FROM stdin;
dev-tenant-001	Development Tenant	postgresql+asyncpg://seo:seo_password@postgres:5432/seo_articles	t	2026-01-12 09:33:09.679176+00	2026-01-12 09:33:09.679176+00
\.


--
-- Name: api_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: seo
--

SELECT pg_catalog.setval('public.api_settings_id_seq', 2, true);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: seo
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 280, true);


--
-- Name: help_contents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: seo
--

SELECT pg_catalog.setval('public.help_contents_id_seq', 42, true);


--
-- Name: llm_models_id_seq; Type: SEQUENCE SET; Schema: public; Owner: seo
--

SELECT pg_catalog.setval('public.llm_models_id_seq', 17, true);


--
-- Name: api_settings api_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.api_settings
    ADD CONSTRAINT api_settings_pkey PRIMARY KEY (id);


--
-- Name: api_settings api_settings_tenant_id_service_key; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.api_settings
    ADD CONSTRAINT api_settings_tenant_id_service_key UNIQUE (tenant_id, service);


--
-- Name: artifacts artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_pkey PRIMARY KEY (id);


--
-- Name: attempts attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_pkey PRIMARY KEY (id);


--
-- Name: attempts attempts_step_id_attempt_num_key; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_step_id_attempt_num_key UNIQUE (step_id, attempt_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: diagnostic_reports diagnostic_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.diagnostic_reports
    ADD CONSTRAINT diagnostic_reports_pkey PRIMARY KEY (id);


--
-- Name: error_logs error_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_pkey PRIMARY KEY (id);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: github_sync_status github_sync_status_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.github_sync_status
    ADD CONSTRAINT github_sync_status_pkey PRIMARY KEY (id);


--
-- Name: hearing_templates hearing_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.hearing_templates
    ADD CONSTRAINT hearing_templates_pkey PRIMARY KEY (id);


--
-- Name: help_contents help_contents_help_key_key; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.help_contents
    ADD CONSTRAINT help_contents_help_key_key UNIQUE (help_key);


--
-- Name: help_contents help_contents_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.help_contents
    ADD CONSTRAINT help_contents_pkey PRIMARY KEY (id);


--
-- Name: llm_models llm_models_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_pkey PRIMARY KEY (id);


--
-- Name: llm_models llm_models_provider_id_model_name_key; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_provider_id_model_name_key UNIQUE (provider_id, model_name);


--
-- Name: llm_providers llm_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.llm_providers
    ADD CONSTRAINT llm_providers_pkey PRIMARY KEY (id);


--
-- Name: prompts prompts_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_pkey PRIMARY KEY (id);


--
-- Name: prompts prompts_step_name_version_key; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.prompts
    ADD CONSTRAINT prompts_step_name_version_key UNIQUE (step_name, version);


--
-- Name: review_requests review_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_pkey PRIMARY KEY (id);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (id);


--
-- Name: step_llm_defaults step_llm_defaults_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.step_llm_defaults
    ADD CONSTRAINT step_llm_defaults_pkey PRIMARY KEY (step);


--
-- Name: steps steps_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.steps
    ADD CONSTRAINT steps_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: github_sync_status uq_github_sync_run_step; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.github_sync_status
    ADD CONSTRAINT uq_github_sync_run_step UNIQUE (run_id, step);


--
-- Name: hearing_templates uq_hearing_template_tenant_name; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.hearing_templates
    ADD CONSTRAINT uq_hearing_template_tenant_name UNIQUE (tenant_id, name);


--
-- Name: review_requests uq_review_request_run_step_type; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT uq_review_request_run_step_type UNIQUE (run_id, step, review_type);


--
-- Name: steps uq_steps_run_step; Type: CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.steps
    ADD CONSTRAINT uq_steps_run_step UNIQUE (run_id, step_name);


--
-- Name: idx_artifacts_run_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_artifacts_run_id ON public.artifacts USING btree (run_id);


--
-- Name: idx_artifacts_step_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_artifacts_step_id ON public.artifacts USING btree (step_id);


--
-- Name: idx_attempts_step_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_attempts_step_id ON public.attempts USING btree (step_id);


--
-- Name: idx_diagnostic_reports_run_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_diagnostic_reports_run_id ON public.diagnostic_reports USING btree (run_id);


--
-- Name: idx_error_logs_created_at; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_error_logs_created_at ON public.error_logs USING btree (created_at DESC);


--
-- Name: idx_error_logs_run_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_error_logs_run_id ON public.error_logs USING btree (run_id);


--
-- Name: idx_error_logs_source; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_error_logs_source ON public.error_logs USING btree (source);


--
-- Name: idx_error_logs_step_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_error_logs_step_id ON public.error_logs USING btree (step_id);


--
-- Name: idx_events_created_at; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_events_created_at ON public.events USING btree (created_at DESC);


--
-- Name: idx_events_event_type; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_events_event_type ON public.events USING btree (event_type);


--
-- Name: idx_events_run_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_events_run_id ON public.events USING btree (run_id);


--
-- Name: idx_events_tenant_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_events_tenant_id ON public.events USING btree (tenant_id);


--
-- Name: idx_github_sync_status_run_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_github_sync_status_run_id ON public.github_sync_status USING btree (run_id);


--
-- Name: idx_github_sync_status_status; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_github_sync_status_status ON public.github_sync_status USING btree (status);


--
-- Name: idx_hearing_templates_name; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_hearing_templates_name ON public.hearing_templates USING btree (name);


--
-- Name: idx_hearing_templates_tenant_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_hearing_templates_tenant_id ON public.hearing_templates USING btree (tenant_id);


--
-- Name: idx_prompts_active; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_prompts_active ON public.prompts USING btree (step_name, is_active) WHERE (is_active = true);


--
-- Name: idx_prompts_step_name; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_prompts_step_name ON public.prompts USING btree (step_name);


--
-- Name: idx_review_requests_run_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_review_requests_run_id ON public.review_requests USING btree (run_id);


--
-- Name: idx_review_requests_status; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_review_requests_status ON public.review_requests USING btree (status);


--
-- Name: idx_runs_created_at; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_runs_created_at ON public.runs USING btree (created_at DESC);


--
-- Name: idx_runs_status; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_runs_status ON public.runs USING btree (status);


--
-- Name: idx_runs_tenant_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_runs_tenant_id ON public.runs USING btree (tenant_id);


--
-- Name: idx_steps_run_id; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_steps_run_id ON public.steps USING btree (run_id);


--
-- Name: idx_steps_status; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX idx_steps_status ON public.steps USING btree (status);


--
-- Name: ix_help_contents_category; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX ix_help_contents_category ON public.help_contents USING btree (category);


--
-- Name: ix_help_contents_help_key; Type: INDEX; Schema: public; Owner: seo
--

CREATE INDEX ix_help_contents_help_key ON public.help_contents USING btree (help_key);


--
-- Name: hearing_templates update_hearing_templates_updated_at; Type: TRIGGER; Schema: public; Owner: seo
--

CREATE TRIGGER update_hearing_templates_updated_at BEFORE UPDATE ON public.hearing_templates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: review_requests update_review_requests_updated_at; Type: TRIGGER; Schema: public; Owner: seo
--

CREATE TRIGGER update_review_requests_updated_at BEFORE UPDATE ON public.review_requests FOR EACH ROW EXECUTE FUNCTION public.update_review_requests_updated_at();


--
-- Name: runs update_runs_updated_at; Type: TRIGGER; Schema: public; Owner: seo
--

CREATE TRIGGER update_runs_updated_at BEFORE UPDATE ON public.runs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: artifacts artifacts_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: artifacts artifacts_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE SET NULL;


--
-- Name: attempts attempts_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.attempts
    ADD CONSTRAINT attempts_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE CASCADE;


--
-- Name: diagnostic_reports diagnostic_reports_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.diagnostic_reports
    ADD CONSTRAINT diagnostic_reports_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: error_logs error_logs_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: error_logs error_logs_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.error_logs
    ADD CONSTRAINT error_logs_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE SET NULL;


--
-- Name: events events_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: events events_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.steps(id) ON DELETE SET NULL;


--
-- Name: github_sync_status github_sync_status_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.github_sync_status
    ADD CONSTRAINT github_sync_status_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: llm_models llm_models_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.llm_models
    ADD CONSTRAINT llm_models_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.llm_providers(id);


--
-- Name: review_requests review_requests_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.review_requests
    ADD CONSTRAINT review_requests_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- Name: step_llm_defaults step_llm_defaults_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.step_llm_defaults
    ADD CONSTRAINT step_llm_defaults_provider_id_fkey FOREIGN KEY (provider_id) REFERENCES public.llm_providers(id);


--
-- Name: steps steps_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: seo
--

ALTER TABLE ONLY public.steps
    ADD CONSTRAINT steps_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.runs(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Cyoi0n7h3qMV8nEbeDOnhhlvSnDZr3SvND9E7uS2vgvbpbkerImIe81aMVSKsP3

