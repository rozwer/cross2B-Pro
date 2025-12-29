---
name: deploy
description: VPS へのデプロイを安全に実行し、ロールバック機能を提供する
---

# deploy

> VPS デプロイのワークフロー自動化スキル

---

## 使用方法

```bash
/deploy <target> [options]
```

---

## オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `<target>` | デプロイ先（staging / production） | 必須 |
| `--version <tag>` | デプロイするバージョン/タグ | 最新コミット |
| `--dry-run` | 実際にはデプロイせず確認のみ | false |
| `--skip-backup` | バックアップをスキップ | false |
| `--force` | 確認プロンプトをスキップ（staging のみ） | false |

---

## 使用例

### 基本的な使い方

```bash
# staging にデプロイ
/deploy staging

# production にデプロイ
/deploy production

# 特定バージョンをデプロイ
/deploy staging --version v1.2.3

# Git タグを指定
/deploy production --version release-2025-01-15

# ドライラン（実際にはデプロイしない）
/deploy production --dry-run

# staging に即座にデプロイ（確認スキップ）
/deploy staging --force
```

### 組み合わせ例

```bash
# 本番デプロイ前の確認
/deploy production --version v1.2.3 --dry-run

# staging で特定バージョンをテスト
/deploy staging --version v1.2.3 --force

# 緊急時のデプロイ（バックアップスキップ）※ staging のみ
/deploy staging --skip-backup --force
```

---

## 実行フロー

```
1. オプション解析
   ├─ target 判定（staging / production）
   ├─ version 判定（タグ / コミットハッシュ / 最新）
   └─ dry_run 判定

2. 事前チェック
   ├─ SSH 接続確認
   ├─ 現在のデプロイ状態取得
   ├─ ディスク容量確認
   └─ 依存サービス状態確認

3. 確認プロンプト（production は必須）
   ├─ 現在のバージョン表示
   ├─ デプロイ対象バージョン表示
   ├─ 変更差分サマリー表示
   └─ 確認入力待ち

4. @deployer を呼び出し
   入力:
     target: {target}
     version: {version}
     dry_run: {dry_run}
     skip_backup: {skip_backup}

5. デプロイ実行（dry_run: false の場合）
   ├─ バックアップ作成
   ├─ コード同期（rsync / git pull）
   ├─ 依存インストール
   ├─ マイグレーション実行
   ├─ サービス再起動
   └─ ヘルスチェック

6. 結果を表示
   ├─ status: success / failed / dry_run_complete
   ├─ deployed_version: デプロイしたバージョン
   ├─ rollback_point: ロールバック用の情報
   ├─ changes: 変更サマリー
   └─ health_check: ヘルスチェック結果
```

---

## 出力形式

### ドライラン時

```
🔍 ドライラン実行

📋 デプロイ計画:
  ターゲット: production
  現在のバージョン: v1.2.2 (abc1234)
  デプロイバージョン: v1.2.3 (def5678)

📊 変更内容:
  コミット数: 5
  変更ファイル: 12
  マイグレーション: あり（2件）

📦 実行されるステップ:
  1. バックアップ作成
  2. コード同期
  3. 依存インストール（uv sync）
  4. マイグレーション実行
  5. サービス再起動（api, worker）
  6. ヘルスチェック

⚠️ これはドライランです。実際のデプロイは行われていません。
```

### 成功時

```
✅ デプロイ成功

📋 デプロイ結果:
  ターゲット: staging
  バージョン: v1.2.3 (def5678)
  所要時間: 2分15秒

📦 実行されたステップ:
  ✅ バックアップ作成 → backup-2025-12-29-143000.tar.gz
  ✅ コード同期 → 12 files changed
  ✅ 依存インストール → 0 packages added
  ✅ マイグレーション → 2 migrations applied
  ✅ サービス再起動 → api, worker
  ✅ ヘルスチェック → all services healthy

🔄 ロールバックポイント:
  コマンド: /rollback staging --to v1.2.2
  バックアップ: backup-2025-12-29-143000.tar.gz

📊 ヘルスチェック:
  API: ✅ 200 OK (45ms)
  Worker: ✅ connected to Temporal
  DB: ✅ connections: 5/100
```

### 失敗時

```
❌ デプロイ失敗

📋 デプロイ結果:
  ターゲット: production
  バージョン: v1.2.3 (def5678)
  失敗ステップ: マイグレーション実行

📦 実行されたステップ:
  ✅ バックアップ作成 → backup-2025-12-29-143000.tar.gz
  ✅ コード同期 → 12 files changed
  ✅ 依存インストール → 0 packages added
  ❌ マイグレーション → ERROR: relation "new_table" already exists

🚨 エラー詳細:
  コマンド: alembic upgrade head
  終了コード: 1
  エラー出力:
    sqlalchemy.exc.ProgrammingError: relation "new_table" already exists

🔄 自動ロールバック実行中...
  ✅ サービス復旧完了
  現在のバージョン: v1.2.2

💡 推奨アクション:
  1. マイグレーションスクリプトを確認
  2. 開発環境でマイグレーションをテスト
  3. 問題解決後に再デプロイ
```

### 確認プロンプト（production）

```
⚠️ 本番環境へのデプロイ確認

📋 デプロイ情報:
  ターゲット: production
  現在のバージョン: v1.2.2 (abc1234)
  デプロイバージョン: v1.2.3 (def5678)

📊 変更サマリー:
  - feat(api): add bulk delete endpoint
  - fix(worker): handle timeout in step3
  - docs: update API documentation

⚠️ 注意事項:
  - 本番環境へのデプロイです
  - デプロイ中はサービスが一時停止します
  - ロールバックポイントが自動作成されます

続行しますか？ [y/N]:
```

---

## セキュリティ考慮事項

### 認証

| 項目 | 要件 |
|------|------|
| SSH 認証 | 鍵認証のみ（パスワード認証禁止） |
| 鍵の場所 | `~/.ssh/deploy_key` |
| 権限 | デプロイ専用ユーザー（sudo 制限あり） |

### 確認プロンプト

| ターゲット | 確認プロンプト | --force オプション |
|-----------|---------------|-------------------|
| staging | あり | スキップ可能 |
| production | 必須 | スキップ不可 |

### 監査ログ

デプロイ操作は自動的に記録されます：

```
{
  "timestamp": "2025-12-29T14:30:00Z",
  "actor": "user@example.com",
  "action": "deploy",
  "target": "production",
  "version": "v1.2.3",
  "commit": "def5678",
  "result": "success",
  "rollback_point": "backup-2025-12-29-143000.tar.gz"
}
```

---

## target オプション詳細

| 値 | 説明 | URL |
|----|------|-----|
| `staging` | ステージング環境 | staging.example.com |
| `production` | 本番環境 | example.com |

### 環境ごとの違い

| 項目 | staging | production |
|------|---------|------------|
| 確認プロンプト | スキップ可能 | 必須 |
| バックアップ | 任意 | 必須 |
| ロールバック | 手動 | 自動（失敗時） |
| ダウンタイム | 許容 | 最小化（ローリング） |

---

## 関連

- **@deployer**: このスキルが呼び出す agent
- **@security-reviewer**: デプロイ前のセキュリティチェック
- **/rollback**: ロールバック実行スキル

---

## 推奨ワークフロー

```
1. コード変更を作成・マージ

2. /security-review でセキュリティチェック
   └─ Critical/High があれば修正

3. /deploy staging でステージング確認
   ├─ 動作確認
   ├─ 統合テスト
   └─ パフォーマンス確認

4. /deploy production --dry-run で本番確認
   └─ 変更内容・マイグレーション確認

5. /deploy production で本番デプロイ
   ├─ 確認プロンプトに応答
   ├─ デプロイ完了待ち
   └─ ヘルスチェック確認

6. 問題発生時
   └─ /rollback production --to <version>
```

---

## トラブルシューティング

| 症状 | 原因 | 解決策 |
|------|------|--------|
| SSH 接続失敗 | 鍵認証エラー | `ssh-add ~/.ssh/deploy_key` |
| 権限エラー | sudo 権限不足 | デプロイユーザーの権限確認 |
| マイグレーション失敗 | DB スキーマ不整合 | 開発環境で事前テスト |
| ヘルスチェック失敗 | サービス起動失敗 | ログ確認 `/var/log/app/` |
| ディスク容量不足 | バックアップ蓄積 | 古いバックアップを削除 |

### デバッグコマンド

```bash
# SSH 接続テスト
ssh -i ~/.ssh/deploy_key deploy@staging.example.com "echo ok"

# 現在のデプロイ状態確認
ssh deploy@staging.example.com "cat /app/version.txt"

# サービスログ確認
ssh deploy@staging.example.com "journalctl -u app -n 100"

# ディスク容量確認
ssh deploy@staging.example.com "df -h"
```
