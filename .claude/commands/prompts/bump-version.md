---
description: プロンプトのバージョン更新（DBの新規 row 追加＋切替）
---

## 手順（推奨）

1) 既存の `step` の最新 `version` を確認  
2) 新しい `version` を INSERT（`variables` も更新）  
3) `is_active` の切替（運用ポリシーに従う）  
4) 影響範囲（工程/文字数/出力フォーマット）をレビュー用にまとめる  
5) `prompt_versions` を run に保存できることを確認（再現性）
