---
description: 初期データ投入（将来の共通DB/顧客DB seed を含む）
---

## 方針（仕様書準拠）

- 共通管理DB（tenant/user/role 等）と顧客別DB（runs/prompts/audit 等）は seed を分ける。
- 既存データを壊す seed は禁止（冪等な upsert にする）。

## 実行（このリポジトリでは未整備）

この repo には seed スクリプトがまだ無いので、実装後にここへ手順を確定してください（例：`scripts/seed_common_db.py` / `scripts/seed_tenant_db.py`）。
