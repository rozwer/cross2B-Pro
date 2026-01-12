# Step11/Temporal/WebSocket レビュー指摘修正計画

> **作成日**: 2026-01-12
> **目的**: コードレビューで発見されたP1/P2/P3の問題を修正し、統合テストを追加
> **ステータス**: 完了

---

## 完了済みフェーズ

| フェーズ | 内容 | コミット |
|---------|------|---------|
| 1 | [P1-1] Step11 Temporalシグナル送信 | 7a1653f |
| 2 | [P1-2] Step11ストレージパス統一 | 7a1653f |
| 3 | [P1-3] Worker tenant_id必須化 | 7a1653f |
| 4 | [P2] WebSocket認証追加 | 7a1653f |
| 5 | [P3] 冪等キャッシュ改善 | 7a1653f |
| 6 | 統合テスト追加 | 未コミット |

### 変更サマリー

**P1 (Critical)**
- Step11 API 5エンドポイントにTemporalシグナル送信追加
- ストレージパスを`storage/{tenant}/{run}/step11/output.json`に統一
- Worker→内部APIでtenant_id必須送信

**P2 (High)**
- WebSocket接続時にJWT認証・テナント検証追加
- 開発モードでは認証スキップ

**P3 (Medium)**
- `depends_on_steps`プロパティで依存ステップを定義可能に
- 依存artifactのdigestを冪等キャッシュに含める

**フェーズ6: 統合テスト**
- `tests/integration/test_step11_temporal.py` - Temporalシグナル送信テスト（17テスト）
- `tests/integration/test_step11_step12_integration.py` - Step11→Step12連携テスト（13テスト）
- `tests/integration/test_websocket_auth.py` - WebSocket認証テスト（16テスト）

---

## 完了基準

- [x] P1: Step11の各フェーズがAPIからTemporalシグナルで正しく進行する
- [x] P1: Step11出力がStep12で正しく読み込まれる
- [x] P1: Worker内部APIがtenant_id必須で動作する
- [x] P2: WebSocketが認証・テナント検証を行う
- [x] P3: 冪等キャッシュが依存artifact変更を検知する
- [x] 統合テストがすべてパスする（46テスト成功）
- [x] lint/型チェックがパスする

---

## 参考情報

### 関連ファイル

- [step11.py](apps/api/routers/step11.py) - Temporalシグナル送信追加
- [websocket.py](apps/api/routers/websocket.py) - JWT認証追加
- [internal.py](apps/api/routers/internal.py) - tenant_id必須化
- [base.py](apps/worker/activities/base.py) - 冪等キャッシュ改善
- [test_step11_temporal.py](tests/integration/test_step11_temporal.py) - Temporalシグナルテスト
- [test_step11_step12_integration.py](tests/integration/test_step11_step12_integration.py) - 連携テスト
- [test_websocket_auth.py](tests/integration/test_websocket_auth.py) - WebSocket認証テスト

---

## 次のアクション

- 他のタスクに移る場合は「`/work`」または新しい指示を
