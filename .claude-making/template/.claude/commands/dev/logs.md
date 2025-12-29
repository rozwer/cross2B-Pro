---
description: サービスログを表示
allowed-tools: Bash
---

## 実行

```bash
docker compose logs -f --tail=100
```

## 特定サービスのみ

```bash
docker compose logs -f <service-name>
```