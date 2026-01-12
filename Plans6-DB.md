# DB/Storage層 修正計画（Plans-DB.md）

> **作成日**: 2026-01-12
> **対象**: apps/api/db/, apps/api/storage/, apps/api/schemas/
> **ステータス**: 計画中
> **並列実行**: Plans-API, Plans-Worker, Plans-LangGraph, Plans-Frontend, Plans-LLM と競合なし

---

## 概要

| 優先度 | 件数 |
|--------|------|
| CRITICAL | 2件 |
| HIGH | 6件 |
| MEDIUM | 3件 |

---

## 🔴 CRITICAL `cc:TODO`

### C-1. WebSocket接続メモリリーク `cc:TODO`
**ファイル**: `apps/api/routers/websocket.py:26-182`
**問題**:
- `active_connections`と`_legacy_connections`辞書に上限がない
- 接続数が無制限に成長
- 不正切断時にWebSocketオブジェクトへの参照が残る可能性
- 長時間運用でOOM
**修正方針**:
1. 接続数の上限設定（per tenant, per run）
2. 自動タイムアウト機構（e.g., 30分無操作で接続を強制閉じる）
3. `disconnect()`時の参照カウント確認
**工数**: 60分

### C-2. List型フィールドのdict/Pydantic混在 `cc:TODO`
**ファイル**: `apps/api/routers/step11.py:799, 881, 946-947, 1041, 1128-1129`
**問題**:
- `Step11State.positions`が`List[ImagePosition]` | `List[dict]`の混在
- model_dump()後、再度Step11State(**state_data)でロードするとnested modelがdictに変換
- 毎回`isinstance()`チェックが必要で検証が脆弱
**修正方針**:
- `Step11State`のnested fieldsに`model_config = ConfigDict(from_attributes=True)`設定
- または明示的にtype=dictで保存・復元時にPydanticモデルに再構築
**工数**: 45分

---

## 🟠 HIGH `cc:TODO`

### H-1. 外部キー制約の不整合 - Artifact の step_id 参照 `cc:TODO`
**ファイル**: `apps/api/db/models.py:178`
**問題**:
- Step削除時に`SET NULL`が指定
- Run削除時のカスケード処理と二重になる
- Artifactテーブルにorphanな`step_id = NULL`レコードが残る可能性
**修正方針**:
- ondeleteを`CASCADE`に変更
**工数**: 20分

### H-2. TenantDBManager エンジンキャッシュのメモリリーク `cc:TODO`
**ファイル**: `apps/api/db/tenant.py:104-182`
**問題**:
- `_engines`と`_session_factories`辞書が無限に成長
- テナント削除時にエンジンが解放されない
**修正方針**:
- LRUキャッシュまたはTTL付きキャッシュを導入
- テナント削除時に`_engines`エントリ削除
**工数**: 45分

### H-3. PromptPackLoader のメモリリーク `cc:TODO`
**ファイル**: `apps/api/prompts/loader.py:140-182`
**問題**:
- `_cache: dict[str, PromptPack] = {}`が無制限に成長
- 削除機構がない
**修正方針**:
- キャッシュサイズの上限設定（functools.lru_cache）
- 定期的なキャッシュクリア戦略
**工数**: 30分

### H-4. ストリーミング処理でメモリリーク `cc:TODO`
**ファイル**: `apps/api/tools/fetch.py:294-330`
**問題**:
- `chunks = []`にストリーミング中のデータをすべて蓄積
- MAX_CONTENT_LENGTH(10MB)に近いファイルで一度に大量メモリ消費
**修正方針**:
- チャンクバッファサイズの制限
- サイズ超過時の即座なストリーム中断
**工数**: 25分

### H-5. CreateRunInput Union型判別不能 `cc:TODO`
**ファイル**: `apps/api/schemas/runs.py:114`
**問題**:
- `input: LegacyRunInput | ArticleHearingInput`でどちらか判別不可
- isinstance()チェックなしでattributeアクセスすると失敗
**修正方針**:
- Discriminator（判別フィールド）を追加
```python
input: Annotated[
    LegacyRunInput | ArticleHearingInput,
    Field(discriminator='format')
]
```
**工数**: 25分

### H-6. run_ids UUID検証漏れ `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:1391-1400`
**問題**:
- `BulkDeleteRequest.run_ids`が`list[str]`、UUID形式か未検証
- 無効なIDで無駄なDB操作
**修正方針**:
- `run_ids: list[UUID]`で型制約
**工数**: 15分

---

## 🟡 MEDIUM `cc:TODO`

### M-1. パストラバーサル検証の二重エンコーディング対策不足 `cc:TODO`
**ファイル**: `apps/api/storage/artifact_store.py:29`
**問題**:
- `%252e%252e`（二重エンコード）を検出していない
**修正方針**:
```python
PATH_TRAVERSAL_PATTERN = re.compile(
    r"\.\./|\.\.\\|"
    r"%2e%2e|%252e%252e|"
    r"%2e%2e%2f|%2e%2e%5c|"
    r"\.%2e|%2e\.",
    re.IGNORECASE
)
```
**工数**: 20分

### M-2. ArticleMetadata構築時の型検証漏れ `cc:TODO`
**ファイル**: `apps/api/routers/step12.py:414-425`
**問題**:
- metadataフィールドがない場合{}が渡され、全デフォルト値で構築
**修正方針**:
- ArticleMetadataのコンストラクタでmetadataの必須フィールドを検証
**工数**: 20分

### M-3. clone時のoriginal_config検証漏れ `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:1060-1127`
**問題**:
- `step_configs`, `tool_config`, `options`がNoneの可能性
- Workflow側で予期しない型エラー
**修正方針**:
- configフィールドをPydanticスキーマで検証
**工数**: 25分

---

## 完了基準

- [ ] 全CRITICAL/HIGH項目の修正完了
- [ ] Python lint/type エラーがない
- [ ] DBマイグレーションが必要な場合は作成・適用
- [ ] 関連するユニットテスト追加・通過
