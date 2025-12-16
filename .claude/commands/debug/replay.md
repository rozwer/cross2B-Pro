---
description: Temporal リプレイ（決定性違反/履歴起因バグの切り分け）
---

## 目的

- Workflow の決定性違反や、履歴に依存する不具合を安全に再現する。

## 手順（導入後に確定）

1) Workflow history を取得（Temporal CLI/API）  
2) Python SDK の replayer でローカル replay  
3) 例外の最初の差分（非決定な分岐/時刻/乱数/外部I/O）を特定して修正
