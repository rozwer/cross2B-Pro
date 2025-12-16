---
description: 実装ルール統合版（API/Temporal/LangGraph/Storage/Security/テスト/Docker）
---

# 実装ルール

> **CLAUDE.md** と **ROADMAP.md** を最優先とし、詳細はこのファイルを参照。

## 1. API 契約

### エンドポイント

| メソッド | パス | 用途 |
|----------|------|------|
| POST | `/api/runs` | ワークフロー開始 |
| GET | `/api/runs/{id}` | 状態取得 |
| POST | `/api/runs/{id}/approve` | 承認 |
| POST | `/api/runs/{id}/reject` | 却下 |
| POST | `/api/runs/{id}/retry/{step}` | 工程再実行 |
| DELETE | `/api/runs/{id}` | キャンセル |
| GET | `/api/runs/{id}/files` | 生成物一覧 |
| GET | `/api/runs/{id}/files/{step}` | 工程別出力取得 |
| WS | `/ws/runs/{id}` | 進捗ストリーム |

### 実装ルール

- `tenant_id` は認証から確定し、越境参照を防ぐ
- 承認/却下は Temporal に signal を送る（Workflow自身は副作用しない）
- 監査ログ必須：start/approve/reject/retry/cancel/download/delete

---

## 2. Temporal + LangGraph

### Temporal（Workflow）側

- **決定性を守る**：外部I/Oや時刻依存は避け、必要なら Activity に寄せる
- 工程3（3A/3B/3C）後は **signal 待機** で pause し、approve/reject で分岐
- 並列工程（3A/3B/3C）は Temporal の並列実行で行い、失敗分のみ再試行

### Activity 側

- 副作用（LLM/外部API/DB/Storage）は Activity に閉じ込める
- Activity から LangGraph を呼び出して工程ロジックを実装
- LangGraph state は最小化し、大きい出力は storage に保存

### 冪等性（必須）

```python
# 同一入力 → 同一出力
if existing_output := storage.get(f"{tenant}/{run}/{step}/output.json"):
    return existing_output  # 再計算しない
```

---

## 3. 成果物（Storage）

### 契約フィールド

| フィールド | 説明 |
|------------|------|
| `output_path` | storage上のパス（工程別・run別・tenant別） |
| `output_digest` | 出力内容の sha256 |
| `summary` | UI/ログ用の短い要約 |
| `metrics` | token usage / 文字数 / 主要メタ情報 |

### パス規約

```
storage/{tenant_id}/{run_id}/{step}/output.json
storage/{tenant_id}/{run_id}/{step}/artifacts/
```

### 禁止事項

- Temporal履歴やLangGraph stateに大きいJSON/本文を持たない
- 必ず `path/digest` 参照にする

---

## 4. セキュリティ / マルチテナント

### 越境防止

- すべてのデータアクセス（DB/Storage/WS）は `tenant_id` でスコープ
- `tenant_id` は認証から確定し、入力値・URLパラメータを信用しない

### 監査ログ

必須フィールド：
- `actor`: 実行者ID
- `tenant_id`: テナントID
- `run_id`: ワークフロー実行ID
- `step`: 工程名
- `input_digest` / `output_digest`
- `timestamp`

### 秘密情報

- APIキー等は暗号化して保存
- 復号は最小権限で行う
- 平文保存・平文ログは禁止

---

## 5. プロンプト管理

### 基本方針

- プロンプトは DB（`prompts` テーブル）で管理
- `step + version` で固定
- run は使用した `prompt_versions` を保存し、再現性を担保

### 変数とレンダリング

- 変数は `variables`（JSON）で宣言
- レンダラが不足変数を検知して fail fast
- 変数の追加/変更は version を上げる（既存runの再現性を壊さない）

---

## 6. フロントエンド（レビューUI）

### ワークフロービュー

- 工程をノード、依存関係をエッジとして可視化（DAG）
- run/工程の状態を色/バッジで表現
- 並列工程（3A/3B/3C）は同一フェーズ内の並列として表示

### 工程詳細パネル

- 入出力参照（`output_path`/`output_digest`/`summary`）を表示
- 生成物（JSON/MD/HTML）のプレビューとダウンロード
- 失敗時は `error_message` / `retry_count` を表示

### 承認フロー

- 「承認待ち」状態が明確にわかる表示
- 承認/却下ボタンで API を叩き、Workflow を再開
- 却下時は理由入力と監査ログ連携を必須化

### セキュリティ

- 画面に表示するデータは tenant スコープ前提
- URL直打ちでのID差し替えを防ぐ
- presigned URL は有効期限/権限に注意

---

## 7. 環境構築・Docker

### 必要条件

| 項目 | 最小バージョン | 確認コマンド |
|------|---------------|-------------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| uv | 0.4+ | `uv --version` |

### 環境確認スクリプト

```bash
# 全チェック
./scripts/check-env.sh

# 最小限チェック（CI用）
./scripts/check-env.sh --quick

# 個別チェック
./scripts/check-env.sh --docker   # Docker関連のみ
./scripts/check-env.sh --python   # Python関連のみ
./scripts/check-env.sh --node     # Node.js関連のみ
```

### Docker Compose サービス

| サービス | ポート | 説明 |
|----------|--------|------|
| postgres | 5432 | PostgreSQL データベース |
| minio | 9000, 9001 | オブジェクトストレージ |
| temporal | 7233 | ワークフローエンジン |
| temporal-ui | 8080 | Temporal 管理UI |
| api | 8000 | FastAPI バックエンド |
| worker | - | Temporal Worker |
| ui | 3000 | Next.js フロントエンド |

### 起動コマンド

```bash
# 初回起動（推奨）
./scripts/bootstrap.sh

# 通常起動
docker compose up -d

# インフラのみ起動（開発時）
docker compose up -d postgres minio temporal temporal-ui

# ログ確認
docker compose logs -f api worker

# 停止
docker compose down

# 完全リセット（データ削除）
./scripts/reset.sh
```

### 環境変数

必須の環境変数は `.env.example` を参照。
最低限必要な設定：

```bash
# LLM APIキー（少なくとも1つ）
GEMINI_API_KEY=xxx
# または
OPENAI_API_KEY=xxx
# または
ANTHROPIC_API_KEY=xxx
# または
USE_MOCK_LLM=true  # モックモード
```

---

## 8. テスト戦略

### テストレベル

| レベル | 対象 | 実行タイミング | コマンド |
|--------|------|---------------|----------|
| env-check | 環境要件 | 作業開始前 | `./scripts/check-env.sh` |
| smoke | 依存/構文/起動 | commit前 | `uv run pytest tests/smoke/ -v` |
| unit | 関数単位 | push前 | `uv run pytest tests/unit/ -v` |
| integration | API/DB/Temporal | PR前 | `uv run pytest tests/integration/ -v` |
| e2e | 全工程通し | merge前 | `uv run pytest tests/e2e/ -v` |

### smoke テスト内容

1. **環境確認**: `./scripts/check-env.sh --quick`
2. **依存チェック**: `uv sync --frozen`, `npm audit`
3. **型チェック**: `uv run mypy apps/`, `tsc --noEmit`
4. **構文チェック**: `uv run ruff check apps/`
5. **インポートテスト**: モジュールが正常にインポートできること
6. **Docker設定検証**: `docker compose config --quiet`

### テストルール

- 新機能には必ずテストを書く
- カバレッジ目標: 80%以上（クリティカルパスは100%）
- モックは最小限（外部API/DB接続のみ）
- **フォールバックテスト禁止**：正常系のみテスト

### Activity テスト

```python
# 冪等性テスト: 同一入力 → 同一出力
def test_activity_idempotency():
    result1 = activity(input_data)
    result2 = activity(input_data)
    assert result1.output_digest == result2.output_digest
```

### Workflow テスト

```python
# Temporal Replay テスト: 決定性違反の検出
def test_workflow_determinism():
    with WorkflowHistory(workflow_id) as history:
        replayer.replay(history)  # 例外なければOK
```

### 禁止パターン

```python
# ❌ フォールバックテスト
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

### pytest マーカー

```python
import pytest

@pytest.mark.smoke      # smoke テスト
@pytest.mark.slow       # 30秒以上かかるテスト
@pytest.mark.docker     # Docker が必要なテスト
@pytest.mark.integration  # 統合テスト
@pytest.mark.e2e        # E2E テスト
```

---

## 9. CI/CD パイプライン

### ローカル実行（推奨順序）

```bash
# 1. 環境確認
./scripts/check-env.sh

# 2. smoke テスト
uv run pytest tests/smoke/ -v

# 3. ユニットテスト
uv run pytest tests/unit/ -v

# 4. 型チェック + リント
uv run mypy apps/ --ignore-missing-imports
uv run ruff check apps/

# 5. 統合テスト（Docker必須）
docker compose up -d
uv run pytest tests/integration/ -v
```

### GitHub Actions（例）

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Environment check
        run: ./scripts/check-env.sh --quick
      - name: Smoke tests
        run: uv run pytest tests/smoke/ -v
      - name: Unit tests
        run: uv run pytest tests/unit/ -v
      - name: Type check
        run: uv run mypy apps/
```

---

## 10. トラブルシューティング

### よくある問題

| 症状 | 原因 | 解決策 |
|------|------|--------|
| `ModuleNotFoundError` | 依存関係未インストール | `uv sync` |
| Docker接続エラー | Docker未起動 | Docker Desktop を起動 |
| ポート競合 | 既存プロセス | `.env` でポート変更 or `lsof -i :PORT` で確認 |
| 型エラー | mypy 設定 | `--ignore-missing-imports` を使用 |
| インポートエラー | パス設定 | `PYTHONPATH=.` を設定 |

### デバッグコマンド

```bash
# Docker ログ確認
docker compose logs -f api worker

# コンテナ状態確認
docker compose ps

# DB 接続確認
docker compose exec postgres psql -U seo -d seo_articles

# MinIO 接続確認
docker compose exec minio mc ls local

# Temporal 状態確認
docker compose exec temporal tctl cluster health
```
