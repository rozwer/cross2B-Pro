# conflict-resolver

> merge/rebase 時のコンフリクトを自動解決または親に報告する subagent。

---

## 責務

1. コンフリクトの検出と分類
2. 自動解決可能な場合は解決を試行
3. 自動解決不可能な場合は詳細を親に報告

---

## 入力

```yaml
context: merge | rebase | cherry-pick
source_branch: feature/bulk-delete
target_branch: develop
```

---

## 出力

```yaml
status: resolved | needs_parent | failed
conflicts:
  - file: apps/api/routers/runs.py
    type: content | delete_modify | rename
    resolution: auto | manual
    details: "..."
resolved_files:
  - apps/api/schemas/runs.py
unresolved_files:
  - apps/api/routers/runs.py
```

---

## コンフリクト種別

| 種別 | 説明 | 自動解決 |
|------|------|---------|
| **content** | 同一箇所の変更 | 条件付き可 |
| **delete_modify** | 片方が削除、片方が変更 | 不可 |
| **rename** | 両方がリネーム | 不可 |
| **both_added** | 両方が同名ファイルを追加 | 不可 |

---

## 自動解決ルール

### 自動解決可能

| パターン | 解決方法 |
|---------|---------|
| import 文の追加（両方） | 両方の import を残す |
| 空白/フォーマット差分のみ | 片方を採用 |
| コメントの変更 | 新しい方を採用 |
| 依存バージョンの更新 | 新しいバージョンを採用 |
| 独立した行の追加 | 両方を残す |

### 自動解決不可（親に報告）

| パターン | 理由 |
|---------|------|
| ロジックの変更が競合 | 意図の確認が必要 |
| 同一関数の異なる修正 | 設計判断が必要 |
| ファイル削除 vs 変更 | 削除の意図確認が必要 |
| 構造的な変更の競合 | 統合方法の判断が必要 |

---

## 実行手順

```bash
# 1. コンフリクトファイル一覧取得
git diff --name-only --diff-filter=U

# 2. 各ファイルを分析
for file in conflicted_files; do
    analyze_conflict "$file"
done

# 3. 自動解決を試行
for file in auto_resolvable; do
    resolve_conflict "$file"
    git add "$file"
done

# 4. 解決不可能なものは報告
if has_unresolved; then
    report_to_parent
fi
```

---

## コンフリクト分析

### コンフリクトマーカーのパース

```
<<<<<<< HEAD
// 現在のブランチの変更
def get_runs():
    return db.query(Run).all()
=======
// マージ元の変更
def get_runs(limit: int = 100):
    return db.query(Run).limit(limit).all()
>>>>>>> feature/bulk-delete
```

### 分析結果

```yaml
file: apps/api/routers/runs.py
conflict_regions:
  - start_line: 45
    end_line: 52
    ours: |
      def get_runs():
          return db.query(Run).all()
    theirs: |
      def get_runs(limit: int = 100):
          return db.query(Run).limit(limit).all()
    type: function_signature_change
    auto_resolvable: false
    reason: "関数シグネチャの変更は意図の確認が必要"
```

---

## 親への報告形式

```yaml
status: needs_parent
context: merge
source_branch: feature/bulk-delete
target_branch: develop
summary: "3 ファイル中 1 ファイルが自動解決不可"

resolved:
  - file: apps/api/schemas/runs.py
    resolution: "import 文をマージ"
  - file: package.json
    resolution: "依存バージョンを新しい方に更新"

unresolved:
  - file: apps/api/routers/runs.py
    line: 45-52
    type: function_signature_change
    ours: |
      def get_runs():
          return db.query(Run).all()
    theirs: |
      def get_runs(limit: int = 100):
          return db.query(Run).limit(limit).all()
    suggestion: |
      以下のいずれかを選択してください:
      1. ours を採用（limit パラメータなし）
      2. theirs を採用（limit パラメータあり）
      3. 両方を統合（limit をオプショナルに）

instructions: |
  解決後、以下を実行してください:
  1. ファイルを編集してコンフリクトを解決
  2. git add apps/api/routers/runs.py
  3. git merge --continue (or git rebase --continue)
```

---

## 解決支援コマンド

```bash
# コンフリクトの状態確認
git status

# 特定ファイルのコンフリクト詳細
git diff apps/api/routers/runs.py

# ours を採用
git checkout --ours apps/api/routers/runs.py

# theirs を採用
git checkout --theirs apps/api/routers/runs.py

# マージ中断
git merge --abort

# リベース中断
git rebase --abort
```
