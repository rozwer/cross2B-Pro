# データ移行手順

## 含まれるファイル

| ファイル | 内容 | サイズ |
|---------|------|--------|
| `migration-backup.zip` | 下記2つをまとめた zip | 22MB |
| `db_dump.sql` | PostgreSQL 全データダンプ | 313KB |
| `artifacts-backup/` | MinIO オブジェクトストレージのバックアップ | 85MB (1,442ファイル) |

## 復元手順

### 1. リポジトリのクローン

```bash
git clone <repo-url>
cd 案件
git checkout migration/data
```

### 2. zip を使う場合（推奨）

`migration-backup.zip` を解凍すれば `db_dump.sql` と `artifacts-backup/` が得られます。

```bash
cd migration
unzip migration-backup.zip
```

### 3. インフラ起動

```bash
docker compose up -d postgres minio temporal temporal-ui
```

### 4. PostgreSQL 復元

```bash
cat migration/db_dump.sql | docker compose exec -T postgres psql -U seo -d seo_articles
```

### 5. MinIO 復元

```bash
# バックアップをコンテナにコピー
docker compose cp migration/artifacts-backup seo-minio:/tmp/artifacts-backup

# MinIO クライアント設定
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin

# ミラー（復元）
docker compose exec minio mc mirror /tmp/artifacts-backup/ local/seo-gen-artifacts/
```

### 6. 確認

```bash
# DB 確認
docker compose exec postgres psql -U seo -d seo_articles -c "SELECT count(*) FROM runs;"

# MinIO 確認
docker compose exec minio mc ls local/seo-gen-artifacts/storage/
```

## 環境変数

`.env` ファイルに API キーを設定してください。
別途 `api_keys.txt` を参照（このブランチには含まれていません）。
