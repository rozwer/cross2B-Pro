---
description: ローカル起動（langgraph-example を LangGraph Studio で動かす）
---

## 手順

1) 依存を用意（初回のみ）

```bash
cd langgraph-example
python3 -m venv .venv
source .venv/bin/activate
pip install -r my_agent/requirements.txt
cp .env.example .env
```

2) LangGraph Studio 用のCLIを入れる（未導入なら）

```bash
pip install -U "langgraph-cli[inmem]"
```

3) 開発サーバ起動

```bash
langgraph dev --config langgraph.json
```
