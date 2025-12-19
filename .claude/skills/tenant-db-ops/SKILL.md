---
name: tenant-db-ops
description: マルチテナント（顧客別DB分離）のDB運用・マイグレーション・調査に使う。
---

## 使いどころ（トリガー例）

- 「顧客DBを追加」「schema 変更」「マイグレーション」「越境バグ調査」

## 運用原則

- 顧客別DBは越境させない（接続解決は tenant_id 起点で一元化）。
- 破壊的変更は段階導入（add column → backfill → switch → drop）。
- 監査ログ/実行履歴は消さない（保持要件に従う）。

## 追加するもの

- 新テーブル/列は `仕様書/backend/database.md` のスキーマと整合させる。
- 初期化SQLは `scripts/init-db.sql` を参照。
