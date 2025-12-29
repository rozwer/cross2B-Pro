---
name: security-review
description: OWASP Top 10・テナント分離・認証認可のセキュリティレビューを実行する
---

# security-review

> セキュリティ専門のコードレビューを実行するスキル

---

## 使用方法

```bash
/security-review [options]
```

---

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--files <path>` | 特定ファイルをレビュー | - |
| `--pr <number>` | PR をレビュー | - |
| `--focus <categories>` | 観点を絞る（owasp, tenant, secrets） | 全て |
| `--no-report` | レポートを保存しない | false |

---

## 使用例

### 基本的な使い方

```bash
# 未コミット変更をレビュー（デフォルト）
/security-review

# 特定ファイルをレビュー
/security-review --files apps/api/routers/runs.py

# 複数ファイルをレビュー
/security-review --files "apps/api/routers/*.py"

# PR をレビュー
/security-review --pr 123

# 観点を絞る（テナント越境のみ）
/security-review --focus tenant

# 複数観点を指定
/security-review --focus owasp,tenant

# レポートを保存しない
/security-review --no-report
```

### 組み合わせ例

```bash
# PR の認証部分をセキュリティ観点でレビュー
/security-review --pr 123 --focus owasp

# 特定ファイルのテナント越境チェック（レポートなし）
/security-review --files apps/api/routers/runs.py --focus tenant --no-report
```

---

## 実行フロー

```
1. オプション解析
   ├─ mode 判定（uncommitted / files / pr）
   ├─ focus 判定（owasp / tenant / secrets / 全て）
   └─ save_report 判定

2. @security-reviewer を呼び出し
   入力:
     mode: {mode}
     files: {files}
     pr_number: {pr_number}
     focus: {focus}
     save_report: {save_report}

3. 結果を表示
   ├─ status: pass / warn / fail
   ├─ findings: 問題一覧
   ├─ summary: 重要度別カウント
   └─ recommendation: 推奨アクション

4. レポート保存（save_report: true の場合）
   └─ reports/security-review-{YYYY-MM-DD}.md
```

---

## 出力形式

### 成功時（pass）

```
✅ セキュリティレビュー完了

📊 サマリー:
  Critical: 0
  High: 0
  Medium: 0
  Low: 0

✅ セキュリティ問題は見つかりませんでした。
```

### 警告時（warn）

```
⚠️ セキュリティレビュー完了

📊 サマリー:
  Critical: 0
  High: 0
  Medium: 2
  Low: 3

📋 問題一覧:

[MEDIUM] Debug mode enabled
  ファイル: apps/api/main.py:10
  カテゴリ: OWASP A05
  説明: デバッグモードが有効になっています
  修正案:
    app = FastAPI(debug=os.environ.get("DEBUG", "false").lower() == "true")

[MEDIUM] Missing tenant_id scope
  ファイル: apps/api/routers/runs.py:45
  カテゴリ: Tenant
  説明: DBクエリでtenant_idフィルタが漏れています
  修正案:
    run = db.query(Run).filter(Run.id == run_id, Run.tenant_id == tenant_id).first()

💡 推奨: Medium の問題を確認してください。

📄 レポート保存: reports/security-review-2025-12-29.md
```

### 失敗時（fail）

```
❌ セキュリティレビュー完了

📊 サマリー:
  Critical: 1
  High: 1
  Medium: 0
  Low: 0

📋 問題一覧:

[CRITICAL] Hardcoded API key
  ファイル: apps/api/config.py:15
  カテゴリ: Secrets
  説明: APIキーがソースコードにハードコードされています
  修正案:
    API_KEY = os.environ["API_KEY"]
  参照: https://owasp.org/Top10/A02_2021-Cryptographic_Failures/

[HIGH] SQL Injection vulnerability
  ファイル: apps/api/routers/runs.py:30
  カテゴリ: OWASP A03
  説明: ユーザー入力がクエリに直接埋め込まれています
  修正案:
    query = "SELECT * FROM runs WHERE id = :id"
    db.execute(query, {"id": run_id})
  参照: https://owasp.org/Top10/A03_2021-Injection/

🚨 Critical/High の問題を必ず修正してからマージしてください。

📄 レポート保存: reports/security-review-2025-12-29.md
```

---

## focus オプション詳細

| 値 | チェック内容 |
|----|-------------|
| `owasp` | OWASP Top 10（A01-A10） |
| `tenant` | テナント越境（DB/Storage/WS/URL） |
| `secrets` | 秘密情報（APIキー/パスワード/トークン） |

### 観点の選び方

| 変更内容 | 推奨 focus |
|---------|-----------|
| 認証/認可関連 | `owasp` |
| DBクエリ変更 | `owasp,tenant` |
| API エンドポイント追加 | 全て |
| Storage アクセス変更 | `tenant,secrets` |
| 設定ファイル変更 | `secrets` |
| ログ出力変更 | `secrets` |

---

## 関連

- **@security-reviewer**: このスキルが呼び出す agent
- **@codex-reviewer**: 一般的なコードレビュー
- **@pr-reviewer**: PR マージ前の最終チェック

---

## 推奨ワークフロー

```
1. コード変更を作成

2. @codex-reviewer で一般レビュー
   ├─ 正確性
   ├─ 保守性
   └─ 運用安全性

3. /security-review でセキュリティレビュー
   ├─ OWASP Top 10
   ├─ テナント越境
   └─ 秘密情報

4. 問題があれば修正

5. git add && git commit

6. git push && PR作成
```
