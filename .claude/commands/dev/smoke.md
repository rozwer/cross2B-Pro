---
description: 簡易スモーク（依存/構文/起動の最低限チェック）
---

> commit 前に必ず実行。詳細は @rules/implementation.md#テスト戦略

## 1. 依存チェック

```bash
# Python
cd langgraph-example && source .venv/bin/activate
pip check

# Node（apps/frontend がある場合）
cd apps/frontend && npm audit --audit-level=high
```

## 2. 型・構文チェック

```bash
# Python
python3 -m compileall my_agent
mypy apps/ --ignore-missing-imports
ruff check apps/

# TypeScript（apps/frontend がある場合）
cd apps/frontend && npx tsc --noEmit
```

## 3. インポートテスト

```bash
cd langgraph-example && source .venv/bin/activate
python3 -c "import my_agent; import my_agent.agent"
```

## 4. 起動確認（オプション）

```bash
# LangGraph Studio
langgraph dev --config langgraph.json

# Docker Compose（apps/ が揃った後）
docker compose up -d --wait && docker compose ps
```

## 失敗時

- 依存エラー → `pip install -e .` / `npm install`
- 型エラー → 該当ファイルを修正
- 構文エラー → `ruff check --fix` で自動修正可能なものは修正
