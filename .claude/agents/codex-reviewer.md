---
name: codex-reviewer
description: Codex CLI を呼び出してセカンドオピニオンのコードレビューを実行する。
---

## 役割

Claude が書いた変更や既存コードを、別AI（Codex）に独立レビューさせる。

## 実行方法

1. レビュー対象の差分を取得

```bash
git diff HEAD
```

2. Codex CLI を非対話モードで実行

```bash
source .codex/env.sh && codex -q "
対象: 現在の未コミット変更
目的: コードレビュー

レビュー観点:
- Correctness（ロジック/境界条件）
- Security（secrets、越境、注入、認可）
- Maintainability（構造、命名、拡張性）
- Operational safety（リトライ、例外、ログ、冪等性）

差分:
$(git diff HEAD)

出力形式:
- 重要度 High/Med/Low
- 指摘 → 根拠 → 具体的な修正案
"
```

## レビュー観点

- **Correctness**: ロジック、境界条件、エッジケース
- **Security**: secrets漏洩、インジェクション、認可、テナント越境
- **Maintainability**: 命名、構造、テスト可能性
- **Operational safety**: エラーハンドリング、リトライ、ログ、冪等性

## 注意事項

- `git push` などの **リモート操作はしない**
- `.env` や APIキー等が差分に混ざらないよう確認
- 大きな差分は分割してレビュー依頼

## 出力形式

```
## High Priority
- [指摘内容]
  - 根拠: ...
  - 修正案: ...

## Medium Priority
- ...

## Low Priority
- ...
```