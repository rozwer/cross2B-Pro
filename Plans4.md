# 設定・テスト・インフラ統合修正計画（Plans4）

> **作成日**: 2026-01-12
> **目的**: 設定ファイル、テスト品質、スクリプト、LLMプロバイダー統合の問題修正
> **ステータス**: 計画中
> **並列作業**: Plans1 (Backend), Plans2 (Worker), Plans3 (Frontend) と競合なし

---

## 概要

Plans1〜3でカバーされていない領域の問題を修正します。

| フェーズ | 内容 | 件数 |
|---------|------|------|
| 0 | CRITICAL（即時対応） | 1件 |
| 1 | HIGH（早期対応） | 5件 |
| 2 | MEDIUM（中期対応） | 8件 |
| 3 | LOW（改善） | 2件 |
| 4 | テスト・検証 | - |

**除外項目（別途対応）:**
- モデル名関連の問題
- セキュリティ（developでの認証スキップなど）

---

## 🔴 フェーズ0: CRITICAL `cc:TODO`

### 0-1. [CRITICAL] uv.lock ファイル不在による再現性問題 `cc:TODO`
**ファイル**: プロジェクトルート（不在: `uv.lock`）
**問題**:
- Dockerfile が `uv.lock` をコピーしようとするが、ファイルが存在しない
- `COPY uv.lock* ./` で無言でスキップされる
- 本番環境で依存関係の再現性が保証されない
- 開発環境と本番環境の依存バージョンが異なる可能性
**修正方針**:
1. `uv sync` を実行して `uv.lock` を生成
2. バージョン管理に含める（推奨）
3. CI で lock ファイル検証を追加
**工数**: 30分

---

## 🟠 フェーズ1: HIGH `cc:TODO`

### 1-1. [HIGH] Temporal データベース分離の設定不足 `cc:TODO`
**ファイル**: [docker-compose.yml:60-80](docker-compose.yml#L60)
**問題**:
- Temporal が seo_articles データベースを使用している
- ビジネスデータとワークフロー管理データが混在
- スキーマバージョン管理が複雑化
- Temporal アップグレード時の影響が大きい
**修正方針**:
1. Temporal 用の別データベースを作成（`temporal` または `temporal_db`）
2. docker-compose.yml で環境変数として分離
3. init-db.sql にデータベース初期化ロジックを追加
**工数**: 60分

---

### 1-2. [HIGH] bootstrap.sh エラーハンドリング不足 `cc:TODO`
**ファイル**: [scripts/bootstrap.sh:70-94](scripts/bootstrap.sh#L70)
**問題**:
- Temporal ヘルスチェックが 30秒でタイムアウト（ログなし）
- エラーメッセージが曖昧：「continuing anyway」で無視
- `docker compose build` 失敗時のリトライロジックがない
- 実行途中でのクリーンアップ処理がない
**修正方針**:
1. Temporal チェックにタイムアウト時の詳細エラーログを追加
2. 失敗時に `docker compose logs temporal` を自動出力
3. `trap` で cleanup を設定
4. リトライロジックを追加
**工数**: 45分

---

### 1-3. [HIGH] LLMプロバイダー選択ロジックの曖昧さ `cc:TODO`
**ファイル**: `apps/api/llm/gemini.py`, `apps/api/llm/openai.py`, `apps/api/llm/anthropic.py`
**問題**:
- 複数の LLM API キーが設定されている場合、プロバイダー選択ロジックが曖昧
- デフォルトプロバイダーがハードコード化（Gemini が優先）
- API キーがない場合のエラーメッセージが非親切
- `USE_MOCK_LLM=false` かつキー未設定時の挙動が未定義
**修正方針**:
1. `LLM_DEFAULT_PROVIDER` 環境変数を追加
2. 各プロバイダーの初期化時に詳細なエラーログを出力
3. Mock モードの判定ロジックを一元化
4. `LLMProviderFactory` クラスで初期化処理を統一
**工数**: 60分

---

### 1-4. [HIGH] テスト環境変数の不完全性 `cc:TODO`
**ファイル**: [tests/conftest.py:101-107](tests/conftest.py#L101)
**問題**:
- `USE_MOCK_LLM` をハードコード（テスト中の実 API 呼び出し防止は OK）
- `GEMINI_API_KEY` などの API キーが設定されていない
- `DATABASE_URL` がテスト用に明示的に設定されていない
- MinIO/Temporal の設定がない
**修正方針**:
1. テスト用の DATABASE_URL を明示的に設定（in-memory DB or test DB）
2. MinIO のテスト用バケットを設定
3. pytest フックで環境変数をスコープ管理
**工数**: 30分

---

### 1-5. [HIGH] check-env.sh の包括性不足 `cc:TODO`
**ファイル**: [scripts/check-env.sh](scripts/check-env.sh)
**問題**:
- Python/Node バージョンチェックはあるが、必須環境変数の検証がない
- Docker サービスのヘルスチェックがない
- `.env` ファイルの必須値検証がない
**修正方針**:
1. 必須環境変数のチェックロジック追加
2. Docker サービスの接続確認追加
3. `.env` ファイルの必須フィールド検証
**工数**: 40分

---

## 🟡 フェーズ2: MEDIUM `cc:TODO`

### 2-1. [MEDIUM] DEV_TENANT_ID のハードコード `cc:TODO`
**ファイル**: [docker-compose.yml:128, 154-177](docker-compose.yml#L128)
**問題**:
- 環境変数で上書き可能だが、デフォルトが `dev-tenant-001` にハードコード
- 複数の開発者が同じテナントで開発するリスク
- Docker Compose が異なる環境での実行時に衝突
**修正方針**:
1. `DEV_TENANT_ID` のデフォルト値を環境変数で動的に生成（例：`dev-${USER}` または UUID）
2. `.env.example` に明確な説明を追加
**工数**: 20分

---

### 2-2. [MEDIUM] bootstrap.sh 依存関係の検証不足 `cc:TODO`
**ファイル**: [scripts/bootstrap.sh:50-57](scripts/bootstrap.sh#L50)
**問題**:
- `uv sync` の実行確認がない
- npm dependencies の確認がない
- `.env` ファイルチェックはあるが、必須値の検証がない
- Docker イメージビルド前の依存確認がない
**修正方針**:
1. `check-env.sh` を bootstrap 内で実行
2. 失敗時に明確なエラーメッセージとヒントを提示
**工数**: 25分

---

### 2-3. [MEDIUM] .env.example の整理 `cc:TODO`
**ファイル**: [.env.example](.env.example)
**問題**:
- 73個の環境変数（多すぎて管理不可）
- 必須 vs オプション の区別が不明確
- Google Ads API 関連が複数行を占める（ほとんど未実装）
- デフォルト値がコメントで説明されているのみ
**修正方針**:
1. `.env.example` を `必須`, `推奨`, `オプション`, `内部用` にセクション分割
2. 各セクションに詳細なコメントを追加
3. 不要な環境変数を削除またはコメント化
**工数**: 30分

---

### 2-4. [MEDIUM] Logger の datetime.now() 一貫性問題 `cc:TODO`
**ファイル**: [apps/api/observability/logger.py:46](apps/api/observability/logger.py#L46)
**問題**:
- `datetime.now()` を使用（timezone aware ではない）
- DB の `CURRENT_TIMESTAMP` は timezone aware
- ログとDB のタイムスタンプがズレる可能性
**修正方針**:
1. `datetime.now(timezone.utc)` に統一
2. Models, Schemas と同期
**工数**: 20分

---

### 2-5. [MEDIUM] Dockerfile の uv pip install 警告 `cc:TODO`
**ファイル**: [docker/Dockerfile.api:24](docker/Dockerfile.api#L24), [docker/Dockerfile.worker:22](docker/Dockerfile.worker#L22)
**問題**:
- `uv pip install --system` で仮想環境を作成しない
- コンテナ内での依存関係の追跡が困難
- multiarch ビルド時にバイナリの互換性問題の可能性
**修正方針**:
1. `uv sync` を代わりに使用（推奨）
2. または明示的なドキュメントを追加
**工数**: 25分

---

### 2-6. [MEDIUM] Alembic マイグレーション運用手順の不明確さ `cc:TODO`
**ファイル**: [apps/api/db/migrations/env.py:20-40](apps/api/db/migrations/env.py#L20)
**問題**:
- `MIGRATION_MODE` 環境変数で common/tenant を切り替え
- 本番環境での運用手順が不明
- ロールバック手順がない
**修正方針**:
1. マイグレーション手順ドキュメント作成（docs/migrations.md）
2. ロールバックテストを追加
**工数**: 45分

---

### 2-7. [MEDIUM] 共通 Constants ファイルの欠落 `cc:TODO`
**ファイル**: 該当ファイルなし（新規作成）
**問題**:
- Step names が複数ファイルで重複定義
- Status enum が models/schemas/routers に分散
- マジックナンバー・ハードコードが散在
**修正方針**:
1. `apps/api/core/constants.py` を新規作成
2. Step names, Statuses, エラーコード を集約
3. 使用箇所を更新
**工数**: 60分

---

### 2-8. [MEDIUM] 仕様書と実装コードの乖離 `cc:TODO`
**ファイル**: `仕様書/workflow.md` vs `apps/worker/workflows/article_workflow.py`
**問題**:
- 仕様書で step11 の待機状態が 7種類とされるが、実装は異なる
- API エンドポイントと実装の parameter 名が異なる
**修正方針**:
1. 仕様書を実装コードに基づいて更新
2. 定期的な同期プロセス構築
**工数**: 75分

---

## 🟢 フェーズ3: LOW `cc:TODO`

### 3-1. [LOW] test_docker_compose.py 検証項目が限定的 `cc:TODO`
**ファイル**: [tests/smoke/test_docker_compose.py](tests/smoke/test_docker_compose.py)
**問題**:
- Docker Compose の config 検証のみ
- 実際のコンテナ起動テストがない
- ネットワーク接続テストがない
**修正方針**:
1. ヘルスチェックエンドポイント呼び出しテストを追加
2. ポート疎通確認を追加
**工数**: 30分

---

### 3-2. [LOW] ステップ定義のハードコード `cc:TODO`
**ファイル**: [apps/api/routers/config.py:59-](apps/api/routers/config.py#L59)
**問題**:
- ステップ定義がハードコードで、DB から取得していない
- `step_id` が不規則な命名規則（step-1, step0, step1_5 など混在）
- UI との同期が手動
**修正方針**:
1. ステップ定義を DB テーブルで管理
2. API エンドポイント `/api/config/steps` を新規作成
**工数**: 90分

---

## 🔵 フェーズ4: テスト・検証 `cc:TODO`

### 4-1. 修正箇所の検証 `cc:TODO`
- [ ] `uv.lock` が正しく生成されること
- [ ] Docker ビルドが成功すること
- [ ] Temporal が別 DB で起動すること
- [ ] LLM プロバイダー選択が正しく動作すること

### 4-2. smoke テスト実行 `cc:TODO`
```bash
# 環境チェック
./scripts/check-env.sh

# Bootstrap 実行
./scripts/bootstrap.sh

# smoke テスト
uv run pytest tests/smoke/ -v
```

### 4-3. 統合テスト実行 `cc:TODO`
```bash
# Docker 起動
docker compose up -d

# ヘルスチェック
curl http://localhost:8000/health
curl http://localhost:3000

# 統合テスト
uv run pytest tests/integration/ -v
```

---

## 完了基準

- [ ] 全フェーズの修正完了
- [ ] `./scripts/bootstrap.sh` がエラーなしで完了
- [ ] smoke テストパス
- [ ] Docker イメージの再現性確認
- [ ] ドキュメント更新完了

---

## 推奨実装順序

1. **即時実行** (Day 1)
   - 0-1: uv.lock 生成
   - 1-1: Temporal DB 分離
   - 1-2: Bootstrap スクリプト改善

2. **早期対応** (Day 2-3)
   - 1-3: LLM プロバイダー factory 化
   - 1-4: テスト環境変数完全化
   - 1-5: check-env.sh 強化

3. **中期対応** (Week 2)
   - 2-1 〜 2-8: 設定統一とドキュメント整備

4. **改善** (Week 3)
   - 3-1 〜 3-2: テスト拡充とリファクタリング

---

## 次のアクション

- 「`/work Plans4.md`」でフェーズ0から実装開始
