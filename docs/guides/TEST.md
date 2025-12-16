# テストガイド

SEO記事自動生成システムのテスト戦略とテスト実行方法を説明します。

## テスト戦略

### テストレベル

| レベル | LLM | 頻度 | 目的 | コマンド |
|--------|-----|------|------|----------|
| smoke | モック | 毎commit | 依存/構文/起動確認 | `/dev:smoke` |
| unit | モック | 毎push | ロジック検証 | `pytest tests/unit/` |
| integration | モック | 毎PR | ワークフロー構造検証 | `pytest tests/integration/` |
| e2e | モック | 毎PR | 起動・疎通確認 | `pytest tests/e2e/` |
| e2e（本番） | 実LLM | 毎週 | 実運用相当の検証 | `USE_MOCK_LLM=false pytest tests/e2e/` |

### カバレッジ目標

| 対象 | 目標 |
|------|------|
| クリティカルパス | 100% |
| 全体 | 80%以上 |

## ディレクトリ構成

```
tests/
├── conftest.py           # 共通フィクスチャ
├── unit/                 # ユニットテスト
│   ├── core/             # State, Context, Error
│   ├── db/               # データベースモデル
│   ├── llm/              # LLMクライアント
│   ├── observability/    # ログ・イベント
│   ├── prompts/          # プロンプト管理
│   ├── storage/          # Artifact Store
│   ├── tools/            # 外部ツール
│   ├── validation/       # JSON/CSV検証
│   └── worker/           # Workflow/Activity
├── integration/          # 統合テスト
│   └── workflow/         # ワークフロー統合
└── e2e/                  # E2Eテスト
    └── test_workflow_e2e.py
```

## テスト実行

### 全テスト実行

```bash
# venv有効化
source .venv/bin/activate

# 全テスト
pytest

# 詳細出力
pytest -v

# カバレッジ付き
pytest --cov=apps --cov-report=html
```

### レベル別実行

```bash
# ユニットテスト
pytest tests/unit/

# 統合テスト
pytest tests/integration/

# E2Eテスト
pytest tests/e2e/

# 特定モジュール
pytest tests/unit/llm/
pytest tests/unit/validation/
```

### マーカー指定

```bash
# smokeテストのみ
pytest -m smoke

# 遅いテストを除外
pytest -m "not slow"
```

## smoke テスト

commit前に実行する最低限のチェック。

### 内容

1. **依存チェック**: パッケージの整合性
2. **型チェック**: mypy による静的解析
3. **構文チェック**: ruff によるリント
4. **起動チェック**: インポートエラーの検出

### 実行方法

```bash
# スラッシュコマンド
/dev:smoke

# 手動実行
pip check
mypy apps/
ruff check apps/
python -c "from apps.api import *; from apps.worker import *"
```

## 特殊テスト

### 冪等性テスト

同一入力で同一出力を返すことを検証。

```python
def test_activity_idempotency():
    """Activity の冪等性テスト"""
    result1 = activity(input_data)
    result2 = activity(input_data)
    assert result1.output_digest == result2.output_digest
```

### 決定性テスト

同一入力で複数回実行し、digest一致を確認。

```python
def test_determinism():
    """同一入力 → 同一出力"""
    digests = [process(input_data).digest for _ in range(3)]
    assert len(set(digests)) == 1
```

### フォールバック不在テスト

コードにフォールバック経路がないことを静的検証。

```bash
# fallback 文字列の検出
grep -r "fallback" apps/ --include="*.py" && exit 1 || exit 0
```

### マルチテナント分離テスト

tenant_id 越境が発生しないことを確認。

```python
def test_tenant_isolation():
    """異なる tenant のデータにアクセスできないこと"""
    tenant_a_data = get_data(tenant_id="tenant_a", run_id="run_1")

    with pytest.raises(PermissionError):
        get_data(tenant_id="tenant_b", run_id="run_1")  # 越境
```

### APIスキーマ整合性テスト

BE-UI間のAPIスキーマが一致することを確認。

```python
def test_run_response_matches_ui_type():
    """RunResponse が UI の Run 型と一致すること"""
    response = client.get("/api/runs/test-run", headers={"X-Tenant-ID": "test"})
    data = response.json()

    # UI型の必須フィールド
    assert "id" in data
    assert "tenant_id" in data
    assert "status" in data
    assert "current_step" in data
    assert "input" in data  # input_data ではなく input
    assert "model_config" in data
    assert "steps" in data
    assert "created_at" in data
    assert "updated_at" in data

def test_create_run_request_schema():
    """Run作成リクエストがUI形式で受け付けられること"""
    request_body = {
        "input": {
            "keyword": "テストキーワード",
            "target_audience": "初心者"
        },
        "model_config": {
            "platform": "gemini",
            "model": "gemini-2.0-flash",
            "options": {"grounding": True}
        },
        "tool_config": {
            "serp_fetch": True,
            "page_fetch": True,
            "url_verify": True,
            "pdf_extract": False
        }
    }
    response = client.post(
        "/api/runs",
        json=request_body,
        headers={"X-Tenant-ID": "test"}
    )
    assert response.status_code == 201
```

### WebSocketイベント形式テスト

WebSocketイベントがUI期待形式で送信されることを確認。

```python
def test_websocket_event_format():
    """WebSocketイベントが UI の ProgressEvent 型と一致すること"""
    # BE内部形式: step.started → UI形式: step_started
    from apps.api.main import convert_event_type

    assert convert_event_type("step.started") == "step_started"
    assert convert_event_type("step.completed") == "step_completed"
    assert convert_event_type("step.failed") == "step_failed"
    assert convert_event_type("run.completed") == "run_completed"

@pytest.mark.asyncio
async def test_websocket_broadcast():
    """WebSocket経由でイベントが正しく配信されること"""
    async with websockets.connect(f"ws://localhost:8000/ws/runs/{run_id}") as ws:
        # テストイベントを発行
        event = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(event)

        # UI ProgressEvent 型の必須フィールド
        assert "type" in data
        assert "run_id" in data
        assert "progress" in data
        assert "message" in data
        assert "timestamp" in data
        assert "_" in data["type"]  # step_started 形式
```

### エンドポイント整合性テスト

UI api.ts が期待するエンドポイントが存在することを確認。

```python
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/runs"),
    ("POST", "/api/runs"),
    ("GET", "/api/runs/{id}"),
    ("DELETE", "/api/runs/{id}"),  # cancel: POST → DELETE
    ("POST", "/api/runs/{id}/approve"),
    ("POST", "/api/runs/{id}/reject"),
    ("POST", "/api/runs/{id}/resume/{step}"),
    ("POST", "/api/runs/{id}/clone"),
    ("GET", "/api/runs/{id}/files"),
    ("GET", "/api/runs/{id}/files/{artifact_id}/content"),
    ("GET", "/api/runs/{id}/preview"),
    ("GET", "/api/runs/{id}/events"),
])
def test_endpoint_exists(method, path):
    """UI が期待するエンドポイントが存在すること"""
    # FastAPI の routes から確認
    from apps.api.main import app
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    normalized_path = path.replace("{id}", "{run_id}").replace("{artifact_id}", "{artifact_id}")
    assert any(normalized_path in r for r in routes), f"{method} {path} not found"
```

### Temporal Replay テスト

Workflow の決定性違反を検出。

```python
def test_workflow_determinism():
    """Temporal Replay テスト"""
    with WorkflowHistory(workflow_id) as history:
        replayer.replay(history)  # 例外なければOK
```

## フィクスチャ

### 共通フィクスチャ（conftest.py）

| フィクスチャ | 説明 |
|--------------|------|
| `tenant_id` | テスト用テナントID |
| `run_id` | テスト用ランID |
| `mock_pack_id` | モックプロンプトパックID |
| `base_config` | 基本設定辞書 |
| `mock_llm_response` | モックLLMレスポンス |
| `mock_artifact_store` | モックArtifact Store |
| `mock_event_emitter` | モックイベントエミッター |

### 使用例

```python
def test_workflow_step(tenant_id, run_id, mock_artifact_store):
    """フィクスチャを使用したテスト"""
    context = ExecutionContext(
        tenant_id=tenant_id,
        run_id=run_id,
        step_id="step0",
    )
    result = process_step(context, mock_artifact_store)
    assert result.status == "success"
```

## モックLLM

### 有効化

```bash
# 環境変数で制御
export USE_MOCK_LLM=true
export MOCK_PACK_ID=mock_pack

# または pytest 設定（自動適用）
# conftest.py で USE_MOCK_LLM=true が設定済み
```

### モックレスポンス配置

```
mocks/
├── llm_responses/
│   ├── step0_keyword.json
│   ├── step3a_query.json
│   └── ...
└── llm_variants/
    ├── step0_keyword_v1.json
    └── ...
```

## 禁止パターン

### フォールバックテスト（禁止）

```python
# ❌ 禁止
def test_fallback_to_mock():
    with patch("llm.call", side_effect=Exception):
        result = activity(input)  # モックにフォールバック
        assert result.success  # これは禁止

# ✅ 正しいテスト
def test_llm_failure_raises():
    with patch("llm.call", side_effect=Exception):
        with pytest.raises(ActivityError):
            activity(input)  # 失敗が正しい挙動
```

### 黙った採用（禁止）

```python
# ❌ 禁止
def test_silent_repair():
    broken_json = '{"key": "value",}'  # 末尾カンマ
    result = process(broken_json)
    assert result.success  # 修正してログなし

# ✅ 正しいテスト
def test_repair_with_log():
    broken_json = '{"key": "value",}'
    result = process(broken_json)
    assert result.success
    assert result.repair_log is not None  # 修正ログ必須
```

## CI/CD 統合

### GitHub Actions 例

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check apps/

      - name: Type check
        run: mypy apps/

      - name: Unit tests
        run: pytest tests/unit/ -v

      - name: Integration tests
        run: pytest tests/integration/ -v
```

## トラブルシューティング

### インポートエラー

```bash
# PYTHONPATH を確認
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# または pytest.ini で設定済み
# pythonpath = ["."]
```

### 非同期テストエラー

```bash
# pytest-asyncio が必要
pip install pytest-asyncio

# pyproject.toml で設定済み
# asyncio_mode = "auto"
```

### モックが効かない

```python
# パッチ対象を確認
# ❌ 間違い
with patch("apps.api.llm.gemini.GeminiClient"):
    ...

# ✅ 正しい（使用箇所でパッチ）
with patch("apps.worker.activities.step0.GeminiClient"):
    ...
```

## 参考リンク

- [pytest ドキュメント](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [仕様書/ROADMAP.md](仕様書/ROADMAP.md) - テスト戦略詳細
- [.claude/rules/implementation.md](.claude/rules/implementation.md) - 実装ルール
