---
description: プロンプトのレンダリング結果をプレビュー（変数解決/差分確認）
---

## 目的

- DB管理のプロンプト（`step + version`）を、想定変数でレンダリングして確認する。

## 手順（推奨）

1) 対象 `step` と `version` を決める  
2) 変数（JSON）を用意する（不足は fail fast）  
3) レンダリングして `ref/` に保存する（例：`ref/prompts/<step>/v<version>.txt`）

※ レンダラ実装（Jinja2 等）が追加されたら、ここに実コマンドを確定してください。
