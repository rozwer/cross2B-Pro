# Git Hooks ルール

> pre-commit / pre-push hook の期待動作と、エラー時の対処方針を定義する。

---

## Hook 設定

### pre-commit

**実行内容：**
1. `ruff check --fix` - Python lint（自動修正）
2. `ruff format` - Python フォーマット
3. `mypy apps/` - 型チェック
4. `npm run lint` - TypeScript/JS lint（apps/ui）
5. `npx tsc --noEmit` - TypeScript 型チェック

**エラー時の対処：**

| エラー種別 | 対処 | 担当 |
|-----------|------|------|
| lint 警告（自動修正可） | `--fix` で修正 → 再 stage | subagent |
| format 差分 | 自動修正 → 再 stage | subagent |
| 型エラー（軽微） | 修正 → 再 commit | subagent |
| 型エラー（複雑） | 親に報告 | 親 |
| import エラー | 親に報告 | 親 |
| ロジックエラー | 親に報告 | 親 |

### pre-push

**実行内容：**
1. `pytest tests/smoke/ -v` - smoke テスト
2. `pytest tests/unit/ -v --tb=short` - ユニットテスト（簡易）

**エラー時の対処：**

| エラー種別 | 対処 | 担当 |
|-----------|------|------|
| テスト失敗 | 親に報告（修正は親が判断） | 親 |
| 環境エラー | 親に報告 | 親 |

---

## 判断基準：subagent で修正 vs 親に戻す

### subagent で修正可能

```
- ruff/prettier 自動修正
- 未使用 import の削除
- 型アノテーション追加（明らかなもの）
- フォーマット修正
- 軽微な型エラー（Optional 追加等）
```

### 親に戻す（修正不可）

```
- ロジック変更を伴う修正
- 複数ファイルに跨る型エラー
- テスト失敗（意図的な変更かもしれない）
- import 解決不能（依存追加が必要）
- 設計判断が必要なエラー
```

---

## Hook スクリプト例

```bash
#!/bin/bash
# .githooks/pre-commit

set -e

echo "=== Pre-commit checks ==="

# Python
if git diff --cached --name-only | grep -q '\.py$'; then
    echo "[Python] Running ruff..."
    uv run ruff check --fix apps/
    uv run ruff format apps/

    echo "[Python] Running mypy..."
    uv run mypy apps/ --ignore-missing-imports
fi

# TypeScript/JS
if git diff --cached --name-only | grep -qE '\.(ts|tsx|js|jsx)$'; then
    echo "[TypeScript] Running lint..."
    cd apps/ui && npm run lint

    echo "[TypeScript] Running type check..."
    npx tsc --noEmit
    cd ../..
fi

echo "=== Pre-commit passed ==="
```

---

## 設定方法

```bash
# hooks ディレクトリ設定
git config core.hooksPath .githooks

# または setup スクリプト
./scripts/setup-githooks.sh
```
