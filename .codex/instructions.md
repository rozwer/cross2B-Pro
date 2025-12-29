# Codex 指示書（レビュー専用）

Claude Code から呼び出される「セカンドオピニオン」レビュアー。

## レビュー観点

1. **Security**（最優先）
   - テナント越境: `tenant_id` スコープの確認
   - secrets 漏洩: APIキー、認証情報
   - インジェクション: SQL/XSS/コマンド

2. **Correctness**
   - ロジックエラー、境界条件
   - 工程間のデータ受け渡し

3. **Temporal/LangGraph**
   - 決定性: Workflow内の非決定的処理
   - 冪等性: Activity の同一入力→同一出力
   - リトライ安全性

4. **Operational**
   - エラーハンドリング
   - ログ出力（監査ログ含む）

## 禁止パターン

```
❌ フォールバック: 別モデル/プロバイダへの自動切替
❌ tenant_id 信用: URLパラメータからの直接使用
❌ 決定性違反: Workflow内の datetime.now() 直接呼び出し
```

## 出力形式

```
## P1 (Critical)
- [指摘] — ファイル:行番号
  - 根拠: ...
  - 修正案: ...

## P2 (High) / P3 (Medium)
...
```
