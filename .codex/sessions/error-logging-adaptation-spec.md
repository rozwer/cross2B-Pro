# Error Logging & LLM Diagnostics 適応仕様書

## 概要

`claude/error-logging-llm-diagnostics-ICYzz`ブランチの機能を現行develop（スキーマ違い）に適応して導入する。

## 元ブランチからの主な変更点

1. **DBスキーマ適応**: Integer ID → UUID, `step` → `step_name`
2. **tenant.py便利関数**: グローバルマネージャーパターンの追加
3. **エンドポイント分離**: main.pyへの直接追加ではなく、routers/diagnostics.pyに分離

## 作成するファイル

### 1. apps/api/observability/error_collector.py

エラーログ収集サービス。run/step単位でエラーを収集し、LLM診断用のコンテキストを構築。

**主な機能:**
- `ErrorCollector.log_error()` - エラーをDBに記録
- `ErrorCollector.log_exception()` - 例外を自動的に記録
- `ErrorCollector.log_llm_error()` - LLMエラー専用
- `ErrorCollector.log_tool_error()` - ツールエラー専用
- `ErrorCollector.get_errors_for_run()` - run単位でエラー取得
- `ErrorCollector.build_diagnostic_context()` - LLM診断用コンテキスト構築

**LogSource enum:**
- llm, tool, validation, storage, activity, api

### 2. apps/api/observability/diagnostics.py

LLMベースの障害診断サービス。エラーログを分析して根本原因と復旧手順を提案。

**主な機能:**
- `DiagnosticsService.analyze_failure()` - 失敗runを分析
- `DiagnosticsService.get_latest_diagnosis()` - 最新の診断レポート取得

**出力:**
- root_cause_analysis: 根本原因
- recommended_actions: 推奨アクション（優先度付き）
- resume_step: 再開推奨ステップ
- confidence_score: 信頼度

### 3. apps/api/routers/diagnostics.py

診断関連のAPIエンドポイント。

**エンドポイント:**
- `GET /api/runs/{run_id}/errors` - エラーログ一覧
- `GET /api/runs/{run_id}/errors/summary` - エラーサマリー
- `POST /api/runs/{run_id}/diagnose` - LLM診断を実行
- `GET /api/runs/{run_id}/diagnostics` - 診断レポート一覧

## 修正するファイル

### 1. apps/api/db/models.py

**追加するモデル:**

```python
class ErrorLog(Base):
    """Detailed error log for diagnostics."""
    __tablename__ = "error_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False, index=True)
    step_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("steps.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="activity", index=True)
    error_category: Mapped[str] = mapped_column(String(32), nullable=False)
    error_type: Mapped[str] = mapped_column(String(128), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)

    run: Mapped["Run"] = relationship(back_populates="error_logs")


class DiagnosticReport(Base):
    """LLM-generated failure diagnosis."""
    __tablename__ = "diagnostic_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False, index=True)
    root_cause_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    resume_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    llm_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="diagnostic_reports")
```

**Runモデルに追加:**
```python
error_logs: Mapped[list["ErrorLog"]] = relationship(back_populates="run", cascade="all, delete-orphan")
diagnostic_reports: Mapped[list["DiagnosticReport"]] = relationship(back_populates="run", cascade="all, delete-orphan")
```

### 2. apps/api/db/tenant.py

**追加する関数:**

```python
async def get_engine(self, tenant_id: str) -> AsyncEngine:
    """Get or create engine for tenant."""
    if not validate_tenant_id(tenant_id):
        raise TenantIdValidationError(...)
    db_url = await self._get_tenant_db_url(tenant_id)
    return self._get_or_create_engine(tenant_id, db_url)


# Module-level convenience functions
_tenant_manager: TenantDBManager | None = None

def get_tenant_manager() -> TenantDBManager:
    """Get the global TenantDBManager instance."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantDBManager()
    return _tenant_manager

async def get_tenant_engine(tenant_id: str) -> AsyncEngine:
    """Get engine for a tenant (convenience function)."""
    manager = get_tenant_manager()
    return await manager.get_engine(tenant_id)
```

### 3. scripts/init-db.sql

**追加するテーブル:**

```sql
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_error_logs_run_id ON error_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_step_id ON error_logs(step_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_source ON error_logs(source);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_diagnostic_reports_run_id ON diagnostic_reports(run_id);
```

### 4. apps/worker/activities/base.py

**追加するメソッド:**

```python
async def _collect_error(
    self,
    ctx: ExecutionContext,
    error: Exception,
    category: ErrorCategory,
    source: str = "activity",
    context: dict[str, Any] | None = None,
) -> None:
    """Collect error for LLM-based diagnostics."""
    # Implementation...
```

### 5. apps/api/main.py

**追加するimportとルーター登録:**

```python
from apps.api.routers import diagnostics
app.include_router(diagnostics.router)
```

## DBクエリの適応ポイント

元コードの`build_diagnostic_context()`内のクエリ:
- `steps.step` → `steps.step_name`
- `steps.llm_model` → 削除（現行スキーマにない）
- Integer ID → UUID

## 注意事項

1. **フォールバック禁止**: DiagnosticsServiceでLLM呼び出しが失敗した場合、fallback_diagnosisを使うがこれは「別モデルへの切替」ではなくパターンマッチングによる基本診断
2. **テナント分離**: すべてのエラーログ/診断レポートはrun_id経由でテナントスコープ
3. **監査**: エラーログ自体が監査証跡となる
