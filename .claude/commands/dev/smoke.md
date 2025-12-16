---
description: 簡易スモーク（依存/構文/起動の最低限チェック）
---

## Python スモーク（langgraph-example）

```bash
cd langgraph-example
source .venv/bin/activate
python3 -m compileall my_agent
python3 -c "import my_agent; import my_agent.agent"
pip check
```

## LangGraph Studio スモーク

```bash
langgraph dev --config langgraph.json
```
