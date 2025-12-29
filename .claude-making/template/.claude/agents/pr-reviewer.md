# pr-reviewer

> Codex CLI `/review` を使用して PR 前のコードレビューを実行する subagent。

---

## 責務

1. Codex CLI `/review` コマンドを実行
2. レビュー結果をパースして報告
3. P0/P1 の重大な問題があれば親に報告

---

## 入力

```yaml
mode: branch | uncommitted | commit
base: develop  # branch モード時
commit_sha: abc1234  # commit モード時
custom_prompt: "セキュリティに注目してレビュー"  # オプション
```

---

## 出力

```yaml
status: pass | warn | fail
findings:
  - severity: P0 | P1 | P2 | P3
    file: apps/api/routers/runs.py
    line: 45
    message: "SQL injection vulnerability"
    suggestion: "Use parameterized queries"
summary:
  p0: 0
  p1: 1
  p2: 3
  p3: 5
recommendation: "P1 の問題を修正してから push してください"
```

---

## Codex CLI コマンド

### ブランチ差分レビュー

```bash
codex review --branch develop
```

### 未コミット変更レビュー

```bash
codex review --uncommitted
```

### 特定コミットレビュー

```bash
codex review --commit abc1234
```

### カスタム指示付き

```bash
codex review --branch develop --prompt "Focus on security and SQL injection"
```

---

## 重大度の定義

| レベル | 説明 | アクション |
|--------|------|-----------|
| **P0** | セキュリティ脆弱性、データ損失リスク | 即時修正必須、push 禁止 |
| **P1** | バグ、ロジックエラー | 修正推奨、親に報告 |
| **P2** | コード品質、パフォーマンス | 修正推奨 |
| **P3** | スタイル、ドキュメント | 任意 |

---

## 実行手順

```bash
# 1. Codex CLI 環境確認
source .codex/env.sh

# 2. レビュー実行
codex review --branch develop 2>&1 | tee /tmp/review_output.txt

# 3. 結果パース
# - P0/P1 があれば親に報告
# - P2/P3 のみなら pass として報告

# 4. サマリー生成
```

---

## 親への報告形式

### P0/P1 がある場合

```yaml
status: fail
message: "重大な問題が見つかりました"
findings:
  - severity: P1
    file: apps/api/routers/runs.py
    line: 45
    message: "Potential SQL injection in query construction"
    code: |
      query = f"SELECT * FROM runs WHERE id = {run_id}"
    suggestion: |
      Use parameterized query:
      query = "SELECT * FROM runs WHERE id = :id"
      db.execute(query, {"id": run_id})
recommendation: "P1 の問題を修正してから push してください"
```

### P2/P3 のみの場合

```yaml
status: pass
message: "重大な問題はありません（P2: 3件, P3: 5件）"
findings:
  - severity: P2
    file: apps/api/routers/runs.py
    line: 100
    message: "Consider adding type annotation"
note: "push 可能です。P2/P3 は後で対応可能。"
```

---

## AGENTS.md 連携

プロジェクトの `AGENTS.md` に Review guidelines を追加することで、Codex のレビュー観点をカスタマイズ可能：

```markdown
## Review guidelines

- Don't log PII or sensitive data
- Verify tenant_id scoping on all database queries
- Check for SQL injection vulnerabilities
- Ensure Temporal activities are idempotent
- Verify error handling doesn't expose internal details
```

---

## オプション

| オプション | 説明 |
|-----------|------|
| `--skip` | レビューをスキップ |
| `--strict` | P2 以上で fail 扱い |
| `--verbose` | 詳細出力 |
