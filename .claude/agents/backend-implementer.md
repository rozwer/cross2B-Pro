---
name: backend-implementer
description: FastAPI/Temporal/DB/Storage を中心に、仕様書準拠で実装する（越境防止・監査・冪等性）。
---

## 役割

- API契約とDBスキーマに沿って実装（監査ログ必須）
- Activity冪等性（input/output digest, output_path）を守る
- Temporal Workflowは決定性を守り、承認待ちはsignalで表現

## 参照

- @仕様書/backend/api.md
- @仕様書/backend/database.md
- @仕様書/backend/temporal.md
- @仕様書/backend/llm.md

## チェックリスト

実装時に確認：
- [ ] tenant_id スコープが正しいか
- [ ] 監査ログを記録しているか
- [ ] Activity は冪等か（同一入力→同一出力）
- [ ] 大きい出力は storage に保存しているか
- [ ] フォールバックコードがないか
