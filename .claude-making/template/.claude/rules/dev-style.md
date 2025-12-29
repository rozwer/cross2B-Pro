---
description: 開発スタイル（パッケージ管理・コミット方針）
---

## パッケージ管理

### Python: `uv` を使用

pip/poetry ではなく uv を使用する。

```bash
uv sync              # 依存インストール
uv add <package>     # パッケージ追加
uv run pytest        # コマンド実行
```

### Node.js: `npm` を使用

```bash
npm install          # 依存インストール
npm run dev          # 開発サーバー起動
```

---

## コミット方針

### 基本ルール

- **細かく頻繁にコミット**する（大きな変更を一括コミットしない）
- カテゴリ別に分割：UI / API / Worker / docs / chore など
- 1コミット = 1つの論理的な変更単位
- コミットメッセージは **Conventional Commits** 形式

### Conventional Commits 形式

```
<type>(<scope>): <description>

例:
feat(ui): add dark mode toggle
fix(api): handle null response from LLM
docs: update workflow specification
refactor(worker): extract activity helpers
test(api): add unit tests for runs endpoint
chore: update dependencies
```

### type 一覧

| type | 用途 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメント |
| `refactor` | リファクタリング |
| `test` | テスト追加・修正 |
| `chore` | ビルド・設定変更 |
| `perf` | パフォーマンス改善 |
| `style` | コードスタイル変更（動作に影響なし） |

### 良い例・悪い例

```bash
# ✅ 良い例
git commit -m "feat(ui): add dark mode toggle"
git commit -m "fix(api): handle null response from LLM"
git commit -m "docs: update workflow specification"

# ❌ 悪い例（大きすぎる）
git commit -m "feat: implement entire feature with tests and docs"
```

---

## ブランチ戦略

```
main (master) ← 本番相当
  └── develop ← 開発統合ブランチ
        ├── feat/xxx ← 機能ブランチ
        ├── fix/xxx  ← バグ修正
        └── hotfix/xxx ← 緊急修正（mainから分岐）
```

### ルール

- **main への直接 push 禁止**（Git hooks で強制、develop は許可）
- **PR必須**（main へのマージ時）
- マージ前に smoke テスト通過
