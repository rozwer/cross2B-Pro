# Database 仕様

## マルチテナント方針

**顧客別DB物理分離**を採用。

理由：

- 物理的なデータ分離保証
- 顧客単位のバックアップ/削除が容易
- オンプレ移行時に顧客DBを切り出し可能

---

## テナントDB運用ツール

### CLI コマンド

```bash
# テナント作成（DB作成 + マイグレーション + 接続情報登録）
seo-gen tenant create --name "customer-a"

# 全テナントに一括マイグレーション
seo-gen tenant migrate --all

# 特定テナントのみマイグレーション
seo-gen tenant migrate --tenant-id "xxx"

# バックアップ
seo-gen tenant backup --tenant-id "xxx" --output "/backups/"

# リストア（PITR対応）
seo-gen tenant restore --tenant-id "xxx" --backup-file "/backups/xxx.sql"

# テナント削除（GDPR対応、完全削除）
seo-gen tenant delete --tenant-id "xxx" --confirm
```

### 運用フロー

1. **新規テナント追加**
   - `tenant create` でDB作成
   - 接続情報が `tenants` テーブルに自動登録
   - 最新マイグレーションが自動適用

2. **スキーマ更新**
   - `tenant migrate --all` で全テナントに適用
   - 失敗したテナントはスキップせず**即座に停止**
   - 部分適用は許容しない

3. **テナント解約**
   - `tenant delete` で Storage + DB を完全削除
   - 監査ログは共通管理DBに残る（削除不可）

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
    cost_per_1k_input_tokens DECIMAL(10, 6),   -- コスト追跡用
    cost_per_1k_output_tokens DECIMAL(10, 6),  -- コスト追跡用
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

-- 監査ログ（改ざん防止）
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 監査ログ改ざん防止トリガー
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs table does not allow UPDATE or DELETE';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_audit_log_modification
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();

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

-- コスト追跡用ビュー（run単位）
CREATE VIEW run_costs AS
SELECT
    r.id AS run_id,
    SUM(
        (s.token_usage->>'input')::INTEGER * m.cost_per_1k_input_tokens / 1000 +
        (s.token_usage->>'output')::INTEGER * m.cost_per_1k_output_tokens / 1000
    ) AS total_llm_cost,
    SUM((s.token_usage->>'input')::INTEGER) AS total_input_tokens,
    SUM((s.token_usage->>'output')::INTEGER) AS total_output_tokens
FROM runs r
JOIN steps s ON r.id = s.run_id
LEFT JOIN llm_models m ON s.llm_model = m.model_name
GROUP BY r.id;
```

---

## Storage {#storage}

### パス規約

```
storage/{tenant_id}/{run_id}/{step}/output.json
storage/{tenant_id}/{run_id}/{step}/artifacts/
```

### 成果物契約

| フィールド      | 説明                 |
| --------------- | -------------------- |
| `output_path`   | storage上のパス      |
| `output_digest` | sha256               |
| `summary`       | UI/ログ用の短い要約  |
| `metrics`       | token usage / 文字数 |

### 禁止事項

- Temporal履歴やLangGraph stateに大きいJSON/本文を持たない
- 必ず `path/digest` 参照にする
