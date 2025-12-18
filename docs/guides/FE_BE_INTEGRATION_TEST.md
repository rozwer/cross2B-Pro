# フロントエンド/バックエンド整合性テストガイド

> FE/BE 間の不整合を発見・修正するための実践的なガイド

## 概要

フロントエンド（Next.js）とバックエンド（FastAPI）間の整合性問題は、以下の原因で発生しやすい：

1. **型定義の乖離** - TypeScript と Pydantic の型が同期されていない
2. **フィールド名の不一致** - DB/API/FE でフィールド名が異なる
3. **API 実装漏れ** - FE が呼び出す API が BE で未実装
4. **レスポンス形式の不一致** - BE が返すフィールドと FE が期待するフィールドが異なる

---

## 調査手順

### Step 1: 静的コード分析

#### 1.1 型定義の比較

```bash
# FE の型定義
cat apps/ui/src/lib/types.ts

# BE の Pydantic モデル
grep -n "class.*BaseModel" apps/api/main.py
```

**チェックポイント：**
- フィールド名が一致しているか
- オプショナル/必須の違いがないか
- 型（string/number/boolean）が一致しているか

#### 1.2 API エンドポイントの比較

```bash
# FE の API クライアント
cat apps/ui/src/lib/api.ts

# BE のエンドポイント一覧
grep -n "@app\.\(get\|post\|put\|delete\)" apps/api/main.py
```

**チェックポイント：**
- FE が呼び出す全エンドポイントが BE に存在するか
- パスパラメータ、クエリパラメータが一致しているか
- HTTP メソッドが一致しているか

#### 1.3 DB スキーマと ORM モデルの比較

```bash
# 実際の DB スキーマ
docker compose exec postgres psql -U seo -d seo_articles -c "\d テーブル名"

# SQLAlchemy モデル
cat apps/api/db/models.py
```

**チェックポイント：**
- カラム名が一致しているか
- カラムの型が一致しているか
- NOT NULL 制約が一致しているか

---

### Step 2: 実動作テスト

#### 2.1 API エンドポイントテスト

FE と同じリクエスト形式で curl を使用してテスト：

```bash
# Run 作成（FE 形式）
curl -s -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{
    "input": {"keyword": "テスト"},
    "model_config": {
      "platform": "gemini",
      "model": "gemini-2.0-flash",
      "options": {}
    }
  }'

# Run 一覧（ページネーション）
curl -s "http://localhost:8000/api/runs?page=1&limit=10" \
  -H "X-Tenant-ID: dev-tenant-001"

# Run 詳細
curl -s "http://localhost:8000/api/runs/${RUN_ID}" \
  -H "X-Tenant-ID: dev-tenant-001"

# 承認
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/approve" \
  -H "X-Tenant-ID: dev-tenant-001"

# 却下
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/reject" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{"reason": "テスト却下"}'

# リトライ
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/retry/step0" \
  -H "X-Tenant-ID: dev-tenant-001"

# クローン
curl -s -X POST "http://localhost:8000/api/runs/${RUN_ID}/clone" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: dev-tenant-001" \
  -d '{}'

# 成果物一覧
curl -s "http://localhost:8000/api/runs/${RUN_ID}/files" \
  -H "X-Tenant-ID: dev-tenant-001"

# プロンプト一覧
curl -s "http://localhost:8000/api/prompts?pack_id=default" \
  -H "X-Tenant-ID: dev-tenant-001"
```

#### 2.2 WebSocket テスト

```python
import asyncio
import websockets
import json

async def test_websocket(run_id):
    uri = f"ws://localhost:8000/ws/runs/{run_id}?tenant_id=dev-tenant-001"
    async with websockets.connect(uri) as ws:
        print(f"Connected to {uri}")
        try:
            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(message)
            print(json.dumps(data, indent=2))
            # フィールド確認
            print(f"type: {data.get('type')}")
            print(f"step: {data.get('step')}")  # FE が期待
            print(f"step_id: {data.get('step_id')}")  # BE が送信（旧）
        except asyncio.TimeoutError:
            print("No message received")

asyncio.run(test_websocket("RUN_ID"))
```

#### 2.3 エラーログの確認

```bash
# API コンテナのログ
docker compose logs api --tail=50 | grep -E "(ERROR|Exception|Traceback)"

# SQL エラーの確認
docker compose logs api --tail=100 | grep -E "SELECT|INSERT|UPDATE|DELETE"
```

---

### Step 3: よくある問題パターン

#### 3.1 SQLAlchemy モデルと DB スキーマの不整合

**症状：**
```
sqlalchemy.exc.ProgrammingError: column "xxx" does not exist
```

**原因：**
- models.py のカラム名と実際の DB テーブルのカラム名が異なる
- コンテナが古いモデルをキャッシュしている

**解決：**
```bash
# 1. スキーマ確認
docker compose exec postgres psql -U seo -d seo_articles -c "\d steps"

# 2. models.py を修正

# 3. コンテナ再起動
docker compose restart api
```

#### 3.2 Pydantic フィールドエイリアス

**症状：**
- FE が送信するフィールド名と BE が受け取るフィールド名が異なる

**例：**
```python
# BE: model_config は Python の予約語なので別名を使用
model_config_data: ModelConfig = Field(alias="model_config")
```

**確認：**
```python
class Config:
    populate_by_name = True  # これがあれば両方の名前で受け取れる
```

#### 3.3 501 Not Implemented

**症状：**
- API が `{"detail": "Not implemented"}` を返す

**原因：**
- エンドポイントは定義されているが実装が未完了

**確認：**
```bash
grep -n "501\|Not implemented" apps/api/main.py
```

#### 3.4 ページネーションの不一致

**症状：**
- FE は `page` パラメータを送信、BE は `offset` を返す

**解決：**
- FE 側で変換処理を実装
```typescript
const page = Math.floor(offset / limit) + 1;
const has_more = runs.length === limit && (offset + runs.length) < total;
```

#### 3.5 WebSocket メッセージ形式の不一致

**症状：**
- FE が期待するフィールドと BE が送信するフィールドが異なる

**確認：**
```bash
# BE の送信形式
grep -A10 "broadcast_step_event\|broadcast_run_update" apps/api/main.py

# FE の期待形式
grep -A10 "interface ProgressEvent" apps/ui/src/lib/types.ts
```

---

## チェックリスト

### 新機能追加時

- [ ] BE に新しい Pydantic モデルを追加したら、FE の types.ts も更新
- [ ] 新しいエンドポイントを追加したら、FE の api.ts も更新
- [ ] DB スキーマを変更したら、models.py も更新しコンテナ再起動
- [ ] WebSocket メッセージ形式を変更したら、FE の ProgressEvent 型も更新

### デバッグ時

- [ ] curl でリクエストを再現できるか確認
- [ ] docker compose logs でエラーログを確認
- [ ] DB スキーマと models.py の整合性を確認
- [ ] コンテナを再起動して古いキャッシュをクリア

### リリース前

- [ ] 全エンドポイントの動作確認（curl テスト）
- [ ] WebSocket 接続の確認
- [ ] エラーケースの確認（認証なし、不正なパラメータ等）

---

## 関連ファイル

| ファイル | 役割 |
|----------|------|
| `apps/ui/src/lib/types.ts` | FE 型定義 |
| `apps/ui/src/lib/api.ts` | FE API クライアント |
| `apps/ui/src/lib/websocket.ts` | FE WebSocket クライアント |
| `apps/api/main.py` | BE エンドポイント・Pydantic モデル |
| `apps/api/db/models.py` | SQLAlchemy モデル |
| `scripts/init-db.sql` | DB スキーマ定義 |

---

## 分析結果ファイル

| ファイル | 内容 |
|----------|------|
| `frontend_backend_behavior_diff_analysis.json` | 初期分析（修正済み） |
| `frontend_backend_behavior_diff_analysis_v2.json` | 詳細分析 |
| `frontend_backend_behavior_diff_analysis_v3.json` | 再テスト結果 |
