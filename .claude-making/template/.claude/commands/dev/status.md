---
description: 現在の開発状態を一覧表示
allowed-tools: Bash
---

## 実行

```bash
echo "=== Git Status ==="
git status --short

echo ""
echo "=== Docker Status ==="
docker compose ps 2>/dev/null || echo "Not running"

echo ""
echo "=== Recent Commits ==="
git log --oneline -5
```