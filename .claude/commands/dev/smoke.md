---
description: 簡易スモーク（環境/依存/構文/起動の最低限チェック）
---

> commit 前に必ず実行。詳細は @rules/implementation.md#テスト戦略

## クイック実行（推奨）

```bash
# 環境確認 + smoke テスト一括実行
./scripts/check-env.sh --quick && uv run pytest tests/smoke/ -v --tb=short
```

---

## 0. 環境確認（必須）

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

### 確認項目

| 項目 | 最小バージョン | 確認コマンド |
|------|---------------|-------------|
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| uv | 0.4+ | `uv --version` |

---

## 1. 依存チェック

```bash
# Python（ルートディレクトリで実行）
uv sync --frozen  # lockファイルと一致するか確認

# Node（apps/ui）
cd apps/ui && npm audit --audit-level=high
```

---

## 2. 型・構文チェック

```bash
# Python
uv run python3 -m compileall apps/
uv run mypy apps/ --ignore-missing-imports
uv run ruff check apps/

# TypeScript（apps/ui）
cd apps/ui && npx tsc --noEmit
```

---

## 3. インポートテスト

```bash
# API モジュール
uv run python3 -c "from apps.api.main import app; print('API OK')"

# Worker モジュール
uv run python3 -c "from apps.worker.main import main; print('Worker OK')"

# LangGraph サンプル
cd langgraph-example && source .venv/bin/activate
python3 -c "import my_agent; import my_agent.agent; print('LangGraph OK')"
```

---

## 4. Docker 検証

```bash
# 設定ファイルの検証
docker compose config --quiet

# サービス一覧
docker compose config --services

# ビルド確認（オプション、時間がかかる）
docker compose build --dry-run
```

---

## 5. 起動確認（オプション）

```bash
# 全サービス起動
./scripts/bootstrap.sh

# または個別起動
docker compose up -d postgres minio temporal temporal-ui

# ヘルスチェック
curl -s http://localhost:8000/health | jq .

# サービス状態確認
docker compose ps
```

---

## 6. pytest smoke テスト

```bash
# smoke テストスイート実行
uv run pytest tests/smoke/ -v --tb=short

# 特定テストのみ
uv run pytest tests/smoke/test_docker_compose.py -v
```

---

## 失敗時の対処

| 症状 | 原因 | 解決策 |
|------|------|--------|
| 環境チェック失敗 | 必要ツール未インストール | `./scripts/check-env.sh` の出力を確認 |
| 依存エラー | パッケージ不足 | `uv sync` / `npm install` |
| 型エラー | 型定義の問題 | 該当ファイルを修正 |
| 構文エラー | リント違反 | `uv run ruff check --fix apps/` |
| Docker エラー | Docker未起動 | Docker Desktop を起動 |
| ポート競合 | 既存プロセス | `.env` でポート変更 or `lsof -i :PORT` |
| インポートエラー | パス設定 | `PYTHONPATH=.` を設定 |

---

## チェックリスト

commit 前に以下を確認：

- [ ] `./scripts/check-env.sh --quick` が成功
- [ ] `uv run pytest tests/smoke/ -v` が成功
- [ ] `uv run ruff check apps/` がエラーなし
- [ ] `uv run mypy apps/ --ignore-missing-imports` がエラーなし
