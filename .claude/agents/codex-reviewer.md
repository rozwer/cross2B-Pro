---
name: codex-reviewer
description: Codex CLI を呼び出してセカンドオピニオンのコードレビューを実行する。
---

## 役割

Claude が書いた変更や既存コードを、別AI（Codex）に独立レビューさせる。

## 実行方法

### 未コミット変更をレビュー

```bash
codex review --uncommitted
```

### 特定ブランチとの差分をレビュー

```bash
codex review --base develop
```

### 特定コミットをレビュー

```bash
codex review --commit <SHA>
```

**注意:** `--uncommitted`/`--base`/`--commit` とカスタムプロンプトは同時に使えない。

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