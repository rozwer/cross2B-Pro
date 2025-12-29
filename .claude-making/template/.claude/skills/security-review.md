---
name: security-review
description: OWASP Top 10・認証認可・秘密情報のセキュリティレビューを実行する
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
| `--focus <categories>` | 観点を絞る（owasp, auth, secrets） | 全て |
| `--no-report` | レポートを保存しない | false |

---

## 使用例

### 基本的な使い方

```bash
# 未コミット変更をレビュー（デフォルト）
/security-review

# 特定ファイルをレビュー
/security-review --files src/api/auth.py

# 複数ファイルをレビュー
/security-review --files "src/api/*.py"

# PR をレビュー
/security-review --pr 123

# 観点を絞る（認証のみ）
/security-review --focus auth

# 複数観点を指定
/security-review --focus owasp,secrets

# レポートを保存しない
/security-review --no-report
```

### 組み合わせ例

```bash
# PR の認証部分をセキュリティ観点でレビュー
/security-review --pr 123 --focus owasp

# 特定ファイルの秘密情報チェック（レポートなし）
/security-review --files src/config.py --focus secrets --no-report
```

---

## 実行フロー

```
1. オプション解析
   |-- mode 判定（uncommitted / files / pr）
   |-- focus 判定（owasp / auth / secrets / 全て）
   +-- save_report 判定

2. @security-reviewer を呼び出し
   入力:
     mode: {mode}
     files: {files}
     pr_number: {pr_number}
     focus: {focus}
     save_report: {save_report}

3. 結果を表示
   |-- status: pass / warn / fail
   |-- findings: 問題一覧
   |-- summary: 重要度別カウント
   +-- recommendation: 推奨アクション

4. レポート保存（save_report: true の場合）
   +-- reports/security-review-{YYYY-MM-DD}.md
```

---

## 出力形式

### 成功時（pass）

```
[OK] セキュリティレビュー完了

[SUMMARY] サマリー:
  Critical: 0
  High: 0
  Medium: 0
  Low: 0

[OK] セキュリティ問題は見つかりませんでした。
```

### 警告時（warn）

```
[WARN] セキュリティレビュー完了

[SUMMARY] サマリー:
  Critical: 0
  High: 0
  Medium: 2
  Low: 3

[FINDINGS] 問題一覧:

[MEDIUM] Debug mode enabled
  ファイル: src/main.py:10
  カテゴリ: OWASP A05
  説明: デバッグモードが有効になっています
  修正案:
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

[MEDIUM] Missing authorization check
  ファイル: src/api/admin.py:45
  カテゴリ: Auth
  説明: 管理者権限チェックが漏れています
  修正案:
    @require_admin
    def delete_user(user_id):

[INFO] 推奨: Medium の問題を確認してください。

[FILE] レポート保存: reports/security-review-2025-01-15.md
```

### 失敗時（fail）

```
[NG] セキュリティレビュー完了

[SUMMARY] サマリー:
  Critical: 1
  High: 1
  Medium: 0
  Low: 0

[FINDINGS] 問題一覧:

[CRITICAL] Hardcoded API key
  ファイル: src/config.py:15
  カテゴリ: Secrets
  説明: APIキーがソースコードにハードコードされています
  修正案:
    API_KEY = os.environ["API_KEY"]
  参照: https://owasp.org/Top10/A02_2021-Cryptographic_Failures/

[HIGH] SQL Injection vulnerability
  ファイル: src/db/queries.py:30
  カテゴリ: OWASP A03
  説明: ユーザー入力がクエリに直接埋め込まれています
  修正案:
    query = "SELECT * FROM users WHERE id = :id"
    db.execute(query, {"id": user_id})
  参照: https://owasp.org/Top10/A03_2021-Injection/

[NG] Critical/High の問題を必ず修正してからマージしてください。

[FILE] レポート保存: reports/security-review-2025-01-15.md
```

---

## focus オプション詳細

| 値 | チェック内容 |
|----|-------------|
| `owasp` | OWASP Top 10（A01-A10） |
| `auth` | 認証・認可（権限チェック/セッション管理） |
| `secrets` | 秘密情報（APIキー/パスワード/トークン） |

### 観点の選び方

| 変更内容 | 推奨 focus |
|---------|-----------|
| 認証/認可関連 | `owasp,auth` |
| DBクエリ変更 | `owasp` |
| API エンドポイント追加 | 全て |
| 外部サービス連携 | `secrets` |
| 設定ファイル変更 | `secrets` |
| ログ出力変更 | `secrets` |

---

## OWASP Top 10 チェック項目

| ID | 脆弱性 | 主なチェック内容 |
|----|--------|-----------------|
| A01 | アクセス制御の不備 | 権限チェック漏れ |
| A02 | 暗号化の失敗 | 平文保存、弱い暗号化 |
| A03 | インジェクション | SQL/NoSQL/OS/LDAP インジェクション |
| A04 | 安全でない設計 | セキュリティ設計の欠陥 |
| A05 | セキュリティ設定ミス | デバッグモード、デフォルト設定 |
| A06 | 脆弱なコンポーネント | 既知の脆弱性を持つ依存 |
| A07 | 認証の失敗 | セッション管理、パスワードポリシー |
| A08 | データ整合性の失敗 | 署名なしデータ、信頼できないソース |
| A09 | ログと監視の失敗 | 不十分なログ、監視欠如 |
| A10 | SSRF | サーバーサイドリクエストフォージェリ |

---

## 関連

- **@security-reviewer**: このスキルが呼び出す agent
- **@code-reviewer**: 一般的なコードレビュー
- **/pr**: PR マージ前の最終チェック

---

## 推奨ワークフロー

```
1. コード変更を作成

2. /review で一般レビュー
   |-- 正確性
   |-- 保守性
   +-- 可読性

3. /security-review でセキュリティレビュー
   |-- OWASP Top 10
   |-- 認証・認可
   +-- 秘密情報

4. 問題があれば修正

5. git add && git commit

6. git push && PR作成
```
