---
name: codex-reviewer
description: SEO記事自動生成システム向けコードレビュー。マルチテナント、Temporal、LangGraph、FastAPI、Next.jsの観点を含む。
---

## プロジェクト固有の観点

このプロジェクトは以下の技術スタックを使用：
- **Backend**: FastAPI + Temporal + LangGraph + PostgreSQL + MinIO
- **Frontend**: Next.js (App Router) + TypeScript + MUI
- **アーキテクチャ**: マルチテナント、工程ベースワークフロー

## レビューチェックリスト

### 1. Correctness（ロジック/境界条件）
- 工程間のデータ受け渡しは正しいか
- LangGraph state のスキーマは一貫しているか
- Activity の入出力型は正しいか

### 2. Security（最重要）
- **テナント越境**: 全てのDB/Storage/APIアクセスに `tenant_id` スコープがあるか
- **secrets漏洩**: APIキー、認証情報がログ/レスポンスに含まれていないか
- **インジェクション**: SQL/XSS/コマンドインジェクションの脆弱性はないか
- **認可**: エンドポイントに適切な認証/認可があるか

### 3. Temporal/LangGraph 固有
- **決定性**: Workflow内で非決定的な処理（時刻、乱数、外部I/O）はないか
- **冪等性**: Activity は同一入力で同一出力を返すか
- **リトライ安全**: リトライ時に副作用が重複しないか
- **Signal待機**: 承認フローは正しく実装されているか

### 4. Maintainability（構造、命名）
- 関数/変数名は意図を表しているか
- 重複コードはないか
- 適切な抽象化レベルか

### 5. Operational safety（運用安全性）
- エラーハンドリングは適切か
- ログは十分か（デバッグ可能か）
- 監査ログ（audit_logs）に必要な情報が記録されているか

## 禁止パターン（このプロジェクト固有）

```
❌ フォールバック: 別モデル/別プロバイダへの自動切替
❌ storage直書き: path/digest参照なしの大きなJSON保存
❌ tenant_id信用: URLパラメータからの直接使用
❌ 決定性違反: Workflow内でのdatetime.now()直接呼び出し
```

## 出力形式

```
## P1 (Critical)
- [指摘] — ファイル:行番号
  - 根拠: ...
  - 修正案: ...

## P2 (High)
- ...

## P3 (Medium)
- ...
```
