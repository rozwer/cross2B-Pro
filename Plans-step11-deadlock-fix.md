# Plans.md — Step11 Skip デッドロック修正

## 概要
`ArticleWorkflow.step11_skip` シグナルが `step11_phase = "skipped"` をセットするが、
11B〜11Eフェーズの `wait_condition` がそれを検知しないためデッドロックが発生する。
`ImageAdditionWorkflow` には既に対策済みのコードが存在するため、それに合わせて修正する。

## 根本原因
- `wait_condition(lambda: seq > seen)` は skip 状態を観測しない
- skip 後は全シグナルハンドラが `phase == "skipped"` で拒否するため外部解除も不可
- 結果: ワークフローが7日間タイムアウトまで永久にスタック

## 影響を受けたRun
| 項目 | 値 |
|------|-----|
| run ID | `4ed82987-e9c4-4f48-8771-0e316fd83603` |
| 再開Workflow ID | `019c9016` |
| 状態 | ~~強制終了済み / DB status = `waiting_image_input` のまま~~ → **修正済み (completed)** |

## Temporal patched() について
Codex検証結果: **不要**。wait_conditionの呼び出し順序・数は変わらず、
lambdaの述語変更のみのため決定論を壊さない。
むしろ patched() を使うと既存スタックワークフローが修正パスを通れなくなり逆効果。

---

## Phase 1: Worker コード修正 [bugfix:reproduce-first]

- [x] **B1-1**: 4箇所の wait_condition に `or self.step11_phase == "skipped"` を追加 `cc:done`
  - L1131 (11B): `step11_positions_confirmed_seq > seen`
  - L1183 (11C): `step11_instructions_seq > seen`
  - L1223 (11D): `step11_image_reviews_seq > seen`
  - L1325 (11E): `step11_finalized_seq > seen`
  - 各 wait 直後に `if self.step11_phase == "skipped": return skip_result` を追加

- [x] **B1-2**: `step11_skip` ハンドラのフェーズバリデーション拡張 `cc:done`
  - L281: `waiting_11C`, `waiting_11D`, `waiting_11E` を許可リストに追加
  - 全 waiting フェーズからスキップ可能にする

- [x] **B1-3**: skip 時の early return ロジック実装 `cc:done`
  - `step11_mark_skipped` activity を呼んで正常終了させる
  - `ImageAdditionWorkflow` の `return {"artifact_ref": {}, "skipped": True}` パターンに合わせる

---

## Phase 2: テスト [feature:tdd]

- [x] **B2-1**: デッドロック再現テスト作成 `cc:done`
  - 10テスト作成 (AST 4 + Unit 6): `tests/unit/worker/test_step11_skip_deadlock.py`
  - 全テスト通過 (10/10)

- [x] **B2-2**: 既存 step11 テストの回帰確認 `cc:done`
  - 1143 passed, 6 failed (pre-existing), 12 errors (pre-existing fixtures)
  - 今回の修正による回帰なし

---

## Phase 3: DB 修正 + デプロイ

- [x] **B3-1**: DB status 修正 `cc:done`
  ```sql
  UPDATE runs SET status = 'completed', current_step = 'step12'
  WHERE id = '4ed82987-e9c4-4f48-8771-0e316fd83603';
  ```

- [x] **B3-2**: Worker コンテナリビルド + デプロイ `cc:done`
  - `docker compose build worker && docker compose up -d worker`
  - Worker正常起動確認済み

---

## Phase 4: E2E 検証

- [x] **B4-1**: step11 → Skip フロー確認 (11B phase) `cc:done`
  - Run `a87b2257` を step11 から再開
  - `waiting_image_input` / `step11_position_review` (11B) でskip
  - 即座に `completed` に遷移 — **デッドロック解消確認**

- [x] **B4-2**: step11 → 11C phase からの Skip 確認 `cc:done`
  - Run `2628769a` を step11 から再開
  - positions 承認 → phase 11C (`step11_image_instructions`) に遷移
  - 11C でskip → 即座に `completed` — **新規追加フェーズも動作確認**

---

## 優先度マトリクス

| 分類 | Phase | 結果 |
|------|-------|------|
| **Required** | Phase 1 | DONE |
| **Required** | Phase 2 | DONE |
| **Required** | Phase 3 | DONE |
| **Recommended** | Phase 4 | DONE |

## 技術メモ
- 対象ファイル: `apps/worker/workflows/article_workflow.py`
- テストファイル: `tests/unit/worker/test_step11_skip_deadlock.py`
- 参考実装: 同ファイル内 `ImageAdditionWorkflow` (L1340〜) の `or self.skipped` パターン
- DB接続: `docker exec seo-postgres psql -U seo -d seo_articles`
