---
description: Codex にセカンドオピニオンのコードレビューを依頼する（.codex の codex-reviewer skill を使う）
---

## 目的

- Claude が書いた変更や既存PRを、別AI（Codex）に独立レビューさせる。

## 前提

- `codex`（Codex CLI）がローカルで使えること
- このリポジトリの `.codex/` を使う（skills/config を揃える）

## 手順（推奨：TUI）

1) レビュー対象の差分を作る（秘密情報が混ざっていないか確認）

```bash
git diff
```

2) project-local Codex を起動

```bash
source .codex/env.sh
codex
```

3) Codex の入力欄で `$` を押してスキルピッカーを開き、`codex-reviewer` を選ぶ

4) 依頼文テンプレ（そのまま貼って編集）

```
対象: <branch/PR/コミット/ファイル>
目的: <何を達成した変更か>
前提: <仕様書リンクや制約>

レビュー観点:
- Correctness（ロジック/境界条件）
- Security（secrets、越境、注入、認可）
- Maintainability（構造、命名、拡張性）
- Operational safety（リトライ、例外、ログ、冪等性）

差分:
<git diff を貼る / または変更ファイル一覧と重要箇所>

出力形式:
- 重要度 High/Med/Low
- 指摘 → 根拠 → 具体的な修正案
```

## 注意

- `git push` などの **リモート操作はしない**（必要なら人間が実施）。
- `.env` や APIキー等が差分/ログに混ざらないようにする。
