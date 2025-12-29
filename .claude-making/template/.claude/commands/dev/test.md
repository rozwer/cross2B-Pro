---
description: テスト実行（scope に応じて適切な skill を呼び出し）
allowed-tools: Bash, Skill
---

## 実行フロー

1. 引数を解析
2. scope に応じて分岐:
   - なし / `all` → `flow_test` skill 実行
   - `step0` - `step12` → `endpoint_test` skill --step $SCOPE
   - `api` / `worker` → `uv run pytest apps/$SCOPE/tests/ -v`
   - `smoke` → smoke テスト実行
   - `unit` → ユニットテストのみ
   - `integration` → 統合テストのみ

## 使用例

```
/dev:test             # flow_test（全体）
/dev:test step5       # step5 のエンドポイントテスト
/dev:test api         # API ユニットテスト
/dev:test worker      # Worker ユニットテスト
/dev:test smoke       # smoke テスト
/dev:test unit        # 全ユニットテスト
/dev:test integration # 統合テスト
```

---

## scope 別コマンド

### `all` / 引数なし

```bash
# flow_test skill を実行
# 全工程の統合テスト
```

### `step0` - `step12`

```bash
# endpoint_test skill を --step オプション付きで実行
# 該当 step のエンドポイントテスト
```

### `api`

```bash
uv run pytest apps/api/tests/ -v --tb=short
```

### `worker`

```bash
uv run pytest apps/worker/tests/ -v --tb=short
```

### `smoke`

```bash
./scripts/check-env.sh --quick && uv run pytest tests/smoke/ -v --tb=short
```

### `unit`

```bash
uv run pytest tests/unit/ -v --tb=short
```

### `integration`

```bash
uv run pytest tests/integration/ -v --tb=short
```

---

## クイックリファレンス

### 関連 skills

| Skill | 説明 |
|-------|------|
| `flow_test` | 全工程の統合テスト |
| `endpoint_test` | Step 別エンドポイントテスト |
| `fe_be_test` | フロントエンド・バックエンド結合テスト |

### pytest マーカー

```bash
# slow テストを除外
uv run pytest -m "not slow" -v

# Docker 必須テストのみ
uv run pytest -m docker -v

# 特定ファイル
uv run pytest tests/unit/test_step5.py -v
```

### カバレッジ

```bash
uv run pytest --cov=apps --cov-report=html
```
