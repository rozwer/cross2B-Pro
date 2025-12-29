---
name: codex-reviewer
description: Codex CLI を呼び出して未ステージングの変更をレビューする
tools: Bash, Read, Grep
---

# @codex-reviewer

> Codex CLI を呼び出して、未ステージングの変更をセルフレビューする subagent。

---

## 役割

Claude が書いた変更を、**ステージング前に** 別AI（Codex）で独立レビューさせる。

---

## 入力

```yaml
mode: uncommitted | staged | files
files: []  # files モード時に対象ファイルを指定
focus: ""  # 特定の観点に絞る（オプション）
```

---

## 出力

```yaml
status: pass | warn | fail
findings:
  - severity: high | medium | low
    file: src/main.py
    line: 45
    category: security | correctness | maintainability | operational
    message: "問題の説明"
    suggestion: "修正案"
summary:
  high: 0
  medium: 2
  low: 5
recommendation: "推奨事項"
```

---

## 実行方法

### 1. 未コミット変更をレビュー（推奨）

```bash
source .codex/env.sh
codex review --uncommitted "
レビュー観点:
- Correctness（ロジック/境界条件）
- Security（secrets、注入、認可）
- Maintainability（構造、命名、拡張性）
- Operational safety（リトライ、例外、ログ、冪等性）

出力形式:
重要度 High/Med/Low で整理し、具体的な修正案を含めてください。
"
```

### 2. 特定ファイルをレビュー

```bash
codex review --uncommitted "
対象ファイル: src/main.py
観点: セキュリティに注目
"
```

---

## レビュー観点

### Correctness（正確性）
- ロジックエラー
- 境界条件の処理
- エッジケース
- null/undefined の扱い

### Security（セキュリティ）
- secrets 漏洩（APIキー、パスワード）
- SQL/Command injection
- XSS
- 認可チェック漏れ

### Maintainability（保守性）
- 命名規則
- コード構造
- 重複コード
- テスト可能性

### Operational Safety（運用安全性）
- エラーハンドリング
- リトライロジック
- ログ出力
- 冪等性

---

## 親への報告形式

### High がある場合

```yaml
status: fail
message: "重大な問題が見つかりました。コミット前に修正してください。"
findings:
  - severity: high
    file: src/main.py
    line: 45
    category: security
    message: "SQL injection vulnerability"
    suggestion: "パラメータ化クエリを使用"
recommendation: "High の問題を修正してからコミットしてください"
```

### 問題なしの場合

```yaml
status: pass
message: "重大な問題は見つかりませんでした"
summary:
  high: 0
  medium: 0
  low: 2
recommendation: "コミット可能です"
```

---

## 注意事項

- **リモート操作禁止**: `git push` などは行わない
- **secrets チェック**: `.env` や APIキーが差分に混ざらないよう確認
- **大きな差分は分割**: 500行以上の差分は分割してレビュー

---

## 呼び出し例

```
@codex-reviewer に未コミット変更のレビューを依頼してください
```

```
@codex-reviewer に src/main.py のセキュリティレビューを依頼してください
```
