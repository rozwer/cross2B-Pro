---
description: Codex にセカンドオピニオンのコードレビューを依頼する
---

## 概要

このコマンドは `@codex-reviewer` subagent を呼び出し、Codex CLI で自動的にコードレビューを実行します。

## 実行

Claude は以下の subagent を呼び出してください：

```
@codex-reviewer
```

## subagent の動作

1. `git diff HEAD` で現在の差分を取得
2. Codex CLI を非対話モードで実行
3. レビュー結果を整形して返却

## レビュー観点

- **Correctness**: ロジック、境界条件、エッジケース
- **Security**: secrets漏洩、インジェクション、認可
- **Maintainability**: 命名、構造、テスト可能性
- **Operational safety**: エラーハンドリング、リトライ、ログ

## 注意

- `git push` などの **リモート操作はしない**
- `.env` や APIキー等が差分に混ざらないよう確認
