---
description: ローカル起動（langgraph-example を LangGraph Studio で動かす）
---

## 手順

1) 依存を用意（初回のみ）

```bash
# ルートディレクトリで実行（uv が .venv を自動作成）
uv sync

# 環境変数ファイルをコピー
cp langgraph-example/.env.example langgraph-example/.env
```

2) LangGraph Studio 用のCLIを入れる（未導入なら）

```bash
uv add --dev "langgraph-cli[inmem]"
```

3) 開発サーバ起動

```bash
cd langgraph-example
uv run langgraph dev --config langgraph.json
```
