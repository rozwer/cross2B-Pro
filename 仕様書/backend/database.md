# Database 仕様

## マルチテナント方針

**顧客別DB物理分離**を採用。

理由：
- 物理的なデータ分離保証
- 顧客単位のバックアップ/削除が容易
- オンプレ移行時に顧客DBを切り出し可能

## 共通管理DB

```sql
-- テナント管理
CREATE TABLE tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    database_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- LLMプロバイダー設定
CREATE TABLE llm_providers (
    id TEXT PRIMARY KEY,  -- 'claude', 'gemini', 'openai'
    display_name TEXT NOT NULL,
    api_base_url TEXT,
    is_active BOOLEAN DEFAULT true
);

-- LLMモデル設定
CREATE TABLE llm_models (
    id SERIAL PRIMARY KEY,
    provider_id TEXT REFERENCES llm_providers(id),
    model_name TEXT NOT NULL,
    model_class TEXT NOT NULL,  -- 'pro', 'standard'
    is_active BOOLEAN DEFAULT true
);

-- 工程別デフォルトLLM設定
CREATE TABLE step_llm_defaults (
    step TEXT PRIMARY KEY,
    provider_id TEXT REFERENCES llm_providers(id),
    model_class TEXT NOT NULL
);
```

## 顧客別DB

```sql
-- ワークフロー実行
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL,  -- pending/running/paused/completed/failed
    current_step TEXT,
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 工程別実行ログ
CREATE TABLE steps (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id),
    step TEXT NOT NULL,
    status TEXT NOT NULL,
    llm_model TEXT,
    token_usage JSONB,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- 生成ファイル
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id),
    step TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    digest TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 監査ログ
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- プロンプト
CREATE TABLE prompts (
    id SERIAL PRIMARY KEY,
    step TEXT NOT NULL,
    version INT NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    is_active BOOLEAN DEFAULT true,
    UNIQUE (step, version)
);
```

---

## Storage {#storage}

### パス規約

```
storage/{tenant_id}/{run_id}/{step}/output.json
storage/{tenant_id}/{run_id}/{step}/artifacts/
```

### 成果物契約

| フィールド | 説明 |
|------------|------|
| `output_path` | storage上のパス |
| `output_digest` | sha256 |
| `summary` | UI/ログ用の短い要約 |
| `metrics` | token usage / 文字数 |

### 禁止事項

- Temporal履歴やLangGraph stateに大きいJSON/本文を持たない
- 必ず `path/digest` 参照にする
