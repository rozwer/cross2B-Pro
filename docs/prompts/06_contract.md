# Session 6: Contract + Store基盤

## Phase 3（Phase 2完了後）

---

## 作業開始手順

```bash
cd /home/rozwer/案件
git fetch origin
git pull origin develop

# Phase 2 のマージ確認
git log --oneline develop | head -10
# feat/tools, feat/validation がマージ済みであること

# Worktree作成
TOPIC="contract"
mkdir -p .worktrees
git worktree add -b "feat/$TOPIC" ".worktrees/$TOPIC" develop

# 作業ディレクトリへ移動
cd ".worktrees/$TOPIC"
```

---

## 前提確認

Phase 1, 2 が完了済みであること:

```bash
ls apps/api/llm/base.py
ls apps/api/tools/base.py
ls apps/api/validation/schemas.py
```

---

## 実装指示

あなたはSEO記事自動生成システムのバックエンド実装者です。

### 実装対象

契約基盤 + 成果物ストア + 観測基盤 + DBスキーマ

### 前提

- 仕様書/ROADMAP.md の Step 4, Step 5 を参照
- 仕様書/backend/database.md を参照
- 仕様書/backend/temporal.md を参照

### 成果物

```
apps/api/
├── core/                    # Part A: 契約基盤
│   ├── __init__.py
│   ├── state.py             # GraphState スキーマ
│   ├── context.py           # ExecutionContext
│   └── errors.py            # エラー分類
├── storage/                 # Part B: 成果物ストア
│   ├── __init__.py
│   ├── artifact_store.py    # MinIO連携
│   └── schemas.py           # ArtifactRef型
├── db/                      # Part C: DBスキーマ
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy モデル
│   ├── tenant.py            # テナントDB接続管理
│   └── migrations/          # Alembic マイグレーション
├── observability/           # Part D: 観測基盤
│   ├── __init__.py
│   ├── events.py            # イベント発行
│   └── logger.py            # 構造化ログ
└── prompts/                 # Part E: Prompt Pack
    ├── __init__.py
    └── loader.py            # PromptPackLoader

tests/unit/
├── core/
├── storage/
├── db/
├── observability/
└── prompts/
```

---

## Part A: 契約基盤（core/）

### state.py

```python
from typing import TypedDict
from .errors import StepError
from ..storage.schemas import ArtifactRef
from ..validation.schemas import ValidationReport

class GraphState(TypedDict):
    run_id: str
    tenant_id: str
    current_step: str
    step_outputs: dict[str, ArtifactRef]
    validation_reports: list[ValidationReport]
    errors: list[StepError]
    config: dict  # 実行時設定
    metadata: dict  # 追加メタデータ
```

### context.py

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ExecutionContext:
    run_id: str
    step_id: str
    attempt: int
    tenant_id: str
    started_at: datetime
    timeout_seconds: int

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "attempt": self.attempt,
            "tenant_id": self.tenant_id,
            "started_at": self.started_at.isoformat(),
        }
```

### errors.py

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class ErrorCategory(str, Enum):
    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    VALIDATION_FAIL = "validation_fail"

class StepError(BaseModel):
    step_id: str
    category: ErrorCategory
    message: str
    details: dict | None = None
    occurred_at: datetime
    attempt: int

    def is_retryable(self) -> bool:
        return self.category == ErrorCategory.RETRYABLE
```

---

## Part B: 成果物ストア（storage/）

### schemas.py

```python
from pydantic import BaseModel
from datetime import datetime

class ArtifactRef(BaseModel):
    path: str  # storage/{tenant_id}/{run_id}/{step}/output.json
    digest: str  # sha256
    content_type: str  # application/json, text/markdown, etc.
    size_bytes: int
    created_at: datetime
```

### artifact_store.py

```python
from minio import Minio
import hashlib
import os
from .schemas import ArtifactRef

class ArtifactStore:
    def __init__(self):
        self.client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.getenv("MINIO_USE_SSL", "false").lower() == "true",
        )
        self.bucket = os.getenv("MINIO_BUCKET", "seo-gen-artifacts")

    async def put(
        self,
        content: bytes,
        path: str,
        content_type: str = "application/json"
    ) -> ArtifactRef:
        """成果物を保存し、参照を返す"""
        pass

    async def get(self, ref: ArtifactRef) -> bytes:
        """成果物を取得"""
        pass

    async def exists(self, ref: ArtifactRef) -> bool:
        """成果物の存在確認（digest検証含む）"""
        pass
```

---

## Part C: DBスキーマ（db/）

### models.py

仕様書/backend/database.md に従って実装:
- 共通管理DB: tenants, llm_providers, llm_models, step_llm_defaults
- 顧客別DB: runs, steps, artifacts, audit_logs, prompts

### tenant.py

```python
class TenantDBManager:
    """テナント別DB接続管理"""

    async def get_connection(self, tenant_id: str) -> AsyncSession:
        """テナントDBへの接続を取得"""
        pass

    async def create_tenant_db(self, tenant_id: str, name: str) -> str:
        """新規テナントDB作成"""
        pass
```

### migrations/

Alembic を使用。共通管理DB用と顧客別DB用のマイグレーションを分離。

---

## Part D: 観測基盤（observability/）

### events.py

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class EventType(str, Enum):
    STEP_STARTED = "step.started"
    STEP_SUCCEEDED = "step.succeeded"
    STEP_FAILED = "step.failed"
    STEP_RETRYING = "step.retrying"
    REPAIR_APPLIED = "repair.applied"

class Event(BaseModel):
    event_type: EventType
    run_id: str
    step_id: str | None
    tenant_id: str
    payload: dict
    timestamp: datetime

class EventEmitter:
    async def emit(self, event: Event) -> None:
        """イベントをDBに永続化"""
        pass
```

---

## Part E: Prompt Pack（prompts/）

### loader.py

```python
class PromptPackLoader:
    def load(self, pack_id: str | None) -> "PromptPack":
        if pack_id is None:
            raise ValueError("pack_id is required. Auto-execution without explicit pack_id is forbidden.")

        if pack_id == "mock_pack":
            return self._load_mock_pack()

        return self._load_from_db(pack_id)
```

---

## DoD（完了条件）

- [ ] Session 1-5 の出力がすべて同一契約（GraphState）に載る
- [ ] 失敗時に「再試行可能か」が機械判定できる（ErrorCategory）
- [ ] フォールバック経路が設計上存在しない
- [ ] 型チェック（mypy）が通る
- [ ] 出力が保存され ref で参照でき、run/step と紐づけて追跡できる
- [ ] prompt pack 未設定で自動実行されない（例外発生）
- [ ] イベントが DB に永続化され、後から追跡可能
- [ ] マルチテナント分離が storage / DB 両方で機能
- [ ] pytest が通過
- [ ] Alembic マイグレーションが適用できる

### 禁止事項

- Temporal履歴やLangGraph stateに大きいJSON/本文を持たない（path/digest参照のみ）
- prompt pack 未設定での自動実行

---

## 完了後

```bash
# smokeテスト
pytest tests/unit/core/ tests/unit/storage/ tests/unit/db/ tests/unit/observability/ tests/unit/prompts/ -v

# 型チェック
mypy apps/api/core/ apps/api/storage/ apps/api/db/ apps/api/observability/ apps/api/prompts/

# マイグレーション確認
alembic upgrade head

# コミット
git add .
git commit -m "feat(core): 契約基盤 + Store + 観測 + DB"

# push & PR作成
git push -u origin feat/contract
gh pr create --base develop --title "feat(core): 契約・Store・観測・DB基盤" --body "## 概要
- GraphState, ExecutionContext, ErrorCategory
- ArtifactStore (MinIO)
- DB models + migrations (Alembic)
- EventEmitter
- PromptPackLoader

## 依存
- Phase 1, 2 完了済み

## テスト
- [x] pytest通過
- [x] mypy通過
- [x] Alembic migrate成功"
```
