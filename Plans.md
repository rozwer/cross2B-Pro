# 全体コードレビュー修正計画（Plans.md）

> **作成日**: 2026-01-12
> **目的**: プロジェクト全体のバグ温床となる問題の特定と修正（Plans7を超える包括的レビュー）
> **ステータス**: 計画中
> **除外項目**: モデル名設定、セキュリティ（developでの認証スキップ等）
> **最終更新**: 2026-01-12（2回目の深掘り調査完了）

---

## 概要

12回の並列調査（初回6回＋深掘り6回）により、Plans7で発見されていない新たな問題を多数検出しました。

| フェーズ | 内容 | 件数 |
|---------|------|------|
| 0 | CRITICAL（即時対応） | **25件** |
| 1 | HIGH（早期対応） | **58件** |
| 2 | MEDIUM（中期対応） | 28件 |
| 3 | LOW（改善） | 8件 |
| 4 | テスト・検証 | - |

**調査カバー範囲**:
- API Routers (runs.py, step11.py, step12.py, artifacts.py, hearing.py)
- Worker Activities/Graphs (全16ステップ, pre_approval.py, post_approval.py)
- Worker Workflows (article_workflow.py, parallel.py)
- Frontend Hooks/Components (useRunProgress, useRun, ImageGenerationWizard等)
- DB Models/Storage (models.py, tenant.py, artifact_store.py)
- LLM Clients (gemini.py, openai.py, anthropic.py)

---

## 🔴 フェーズ0: CRITICAL（即時対応）`cc:TODO`

### 0-1. [CRITICAL] LLMクライアント接続リーク `cc:TODO`
**ファイル**: `apps/worker/activities/step*.py` (全16ファイル)
**行番号**: 例) step0.py:166, step3a.py:286, step4.py:237 他
**問題**:
- 毎回のActivity実行時に`get_llm_client()`で新規インスタンス化
- リソース回収（コネクションクローズ）が実装されていない
- GeminiClient、AsyncOpenAI、AsyncAnthropic全てで同じ問題
- 長時間実行のワークフローでコネクション枯渇
**修正方針**:
1. `get_llm_client()`をシングルトン/キャッシュに変更
2. LLMInterfaceに`async def close()`メソッド追加
3. context manager パターン導入
**工数**: 90分

---

### 0-2. [CRITICAL] Temporal決定性違反: datetime.now() の不適切な使用 `cc:TODO`
**ファイル**:
- `apps/worker/activities/base.py:623`
- `apps/worker/activities/step3_5.py:11-12`
- `apps/worker/activities/step12.py:12`
- `apps/worker/graphs/pre_approval.py:274`
- `apps/worker/graphs/post_approval.py:433,545`
**問題**:
- Activity/LangGraphノード内で`datetime.now()`/`datetime.utcnow()`を使用
- メタデータのタイムスタンプがTemporal履歴に記録される
- 同じActivityを同じ入力で再実行するとタイムスタンプが異なる
- Temporal Replayテストが失敗
**修正方針**:
- メタデータのタイムスタンプはAPI層で記録
- または、Workflowレベルで一度だけ時刻を取得してActivityに渡す
**工数**: 60分

---

### 0-3. [CRITICAL] ImageAdditionWorkflow での unsafe imports `cc:TODO`
**ファイル**: `apps/worker/workflows/article_workflow.py:994-1001`
**問題**:
```python
with workflow.unsafe.imports_passed_through():
    from apps.worker.activities import (...)
```
- ワークフロー内部で非決定的なimportを許容
- Temporalのリプレイで失敗する可能性が高い
**修正方針**:
- `unsafe.imports_passed_through()`ブロックを削除
- ワークフロー外（`__init__`など）でimportを行う
**工数**: 30分

---

### 0-4. [CRITICAL] Temporal signal 送信後の session context 不整合 `cc:TODO`
**ファイル**: `apps/api/routers/step11.py:1198-1227, 1275-1300`
**問題**:
- DB commit後にTemporal signalが失敗すると、新規セッションでロールバックを試みる
- ロールバック実行中に別スレッドが同じrun_idを操作する可能性
- commit自体が成功しているため、ロールバック完了前にAPI側が503を返す
- クライアント側は失敗と認識してリトライ → 重複操作
**修正方針**:
- signal送信をコミット前に実行（失敗時は全ロールバック）
- または signal失敗時に明示的にlong-running taskで非同期ロールバック
**工数**: 45分

---

### 0-5. [CRITICAL] RunStatus enum/string 型混在 `cc:TODO`
**ファイル**: `apps/api/routers/step11.py:1458, 1469, 1640, 1663, 1755`
**問題**:
```python
run.status = RunStatus.RUNNING  # ❌ Enumオブジェクト
# 正しくは:
run.status = RunStatus.RUNNING.value  # ✅ 文字列値
```
- runs.py全体では`.value`を使用
- step11.pyでは`.value`なしで混在
- DBにEnumオブジェクトが格納 → SQLクエリで不一致
**修正方針**: 全箇所に`.value`を追加
**工数**: 30分

---

### 0-6. [CRITICAL] Session commit漏れ（全endpoint共通） `cc:TODO`
**ファイル**: 複数（runs.py, artifacts.py, step11.py など）
**問題**:
- 全endpointで`await session.commit()`が明示的に呼ばれていない
- コンテキスト終了時の自動コミットに依存
- explicit commitがないため、transaction boundaryが不明確
- エラーハンドリングが不確実
**修正方針**:
- db/tenant.pyの挙動をドキュメント化
- 重要なエンドポイントで`await session.commit()`を明示化
**工数**: 60分

---

### 0-7. [CRITICAL] useRunProgress: 無限ループリスク `cc:TODO`
**ファイル**: `apps/ui/src/hooks/useRunProgress.ts:60-123`
**行番号**: 91（connect）、108-123（useEffect）
**問題**:
- `connect`関数が依存配列に`connectionState`を含む
- `useEffect`が`connect`を依存配列に含む
- 状態遷移: connectionState変更 → connect再生成 → useEffect再実行 → 無限ループ
- runId切り替え時に複数回WebSocket接続
**修正方針**:
- connectionStateをuseRefで管理
- useEffect依存配列: `[autoConnect, runId]`のみに
**工数**: 30分

---

### 0-8. [CRITICAL] useRun: stopOnComplete の stale closure `cc:TODO`
**ファイル**: `apps/ui/src/hooks/useRun.ts:144-163`
**行番号**: 152-162（startPolling内のsetInterval）
**問題**:
- `startPolling`内の`setInterval`で`stopOnCompleteRef.current`を参照
- pollingInterval変更 → startPolling再生成 → 新しいinterval作成 → 古いintervalは残存
- 複数のintervalが同時実行
**修正方針**:
- `pollingInterval`をuseRef化
- interval resetで古いintervalクリアを確実に
**工数**: 25分

---

### 0-9. [CRITICAL] Step11 multi-phase Signal リセット競合 `cc:TODO`
**ファイル**: `apps/worker/workflows/article_workflow.py:712-891`
**問題**:
```python
while True:
    self.step11_phase = "waiting_11B"
    self.step11_positions_confirmed = None  # リセット!
    await workflow.wait_condition(...)
```
- Signal値をNoneにリセットするが、その直前にAPIからsignalが来た場合は値が失われる
- async raceが存在（wait_conditionの評価タイミングとsignal handlerの実行タイミング）
**修正方針**:
- Signal handlerで状態遷移を厳密に検証
- Signalをリセットしない方式に変更（Flag別途管理）
**工数**: 60分

---

### 0-10. [CRITICAL] delete_run で cascade 削除が確実でない `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:1341`
**問題**:
- `session.flush()`はORMオブジェクトをメモリから削除しているだけ
- 外部キー制約エラーの詳細が不明
- Delete failed時の処理がない（logのみ）
- 孤立したアーティファクトレコードが残る可能性
**修正方針**:
```python
try:
    await session.delete(run)
    await session.flush()
except IntegrityError as e:
    raise HTTPException(status_code=400, detail="Cannot delete run with dependent records")
```
**工数**: 20分

---

### 0-11. [CRITICAL] bulk_delete_runs commit 漏れ `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:1440`
**問題**:
- `await session.flush()`のみで`await session.commit()`を実行していない
- delete実行後に例外が発生すると、一部削除・一部残存のチェッカーボード状態
- 監査ログのみコミットされ、Run削除はロールバック → DB不整合
**修正方針**: `await session.commit()`を追加
**工数**: 10分

---

### 0-12. [CRITICAL] retry_step の Step レコード削除時のリレーション破損 `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:899-907`
**問題**:
- SQL DELETEで直接Stepを削除
- Artifactの`step_id`が参照していた場合、FK制約エラー OR SET NULLでorphanになる
- 削除前に関連Artifactを確認していない
**修正方針**:
- Step削除前に関連Artifactを削除またはstep_idをクリア
**工数**: 30分

---

## 🟠 フェーズ1: HIGH（早期対応）`cc:TODO`

### 1-1. [HIGH] Signal 競合: approve/reject のタイムウィンドウ問題 `cc:TODO`
**ファイル**:
- `apps/worker/workflows/article_workflow.py:343-368`
- `apps/api/routers/runs.py:369-461, 473-575`
**問題**:
- APIはsignal送信直後にDBステータスを更新
- しかしWorkflowがまだsignalを受け取っていない可能性
- 二重状態更新が発生
**修正方針**:
- API層での`run.status`更新を削除
- Workflowのsync_run_status Activity結果を待つ方式に変更
**工数**: 60分

---

### 1-2. [HIGH] Sync Status Activity の重複実行問題 `cc:TODO`
**ファイル**:
- `apps/worker/workflows/article_workflow.py:619-624`
- `apps/api/routers/runs.py:550-556`
**問題**:
- Reject signal後、Workflowは`sync_run_status`でDB更新を試みる
- 同時にAPI層もDBを更新
- `completed_at`が複数回セットされ、タイムスタンプが不正確
**修正方針**:
- Reject APIエンドポイントではsignal送信のみ行い、DB更新はWorkflow内に委ねる
**工数**: 45分

---

### 1-3. [HIGH] Anthropicクライアントのリトライにバックオフなし `cc:TODO`
**ファイル**: `apps/api/llm/anthropic.py:173-262`
**問題**:
- RateLimitError検出時に即座にリトライ → API側がさらに拒否
- Geminiの実装（指数バックオフ実装済み）と動作が異なる
**修正方針**:
- `asyncio.sleep(delay)`でバックオフを導入（Geminiと同じロジック）
**工数**: 30分

---

### 1-4. [HIGH] OpenAIリトライにsleep実装がない `cc:TODO`
**ファイル**: `apps/api/llm/openai.py:160-265`
**問題**:
- RateLimitError時にバックオフなし → API側で更にペナルティ
- Gemini実装との矛盾（保守性低下）
**修正方針**:
- Geminiと同じ指数バックオフロジックを導入
**工数**: 30分

---

### 1-5. [HIGH] JSON パース失敗時の情報喪失 `cc:TODO`
**ファイル**: `apps/api/llm/openai.py:324-339`
**問題**:
- JSONパース失敗時に`raw_output`をカット（`content[:500]`）
- 大きい出力の情報が大幅に失われる
**修正方針**:
- フル内容を保存するが、ログには最初500文字＋「... (全XXX文字)」で表示
- エラー出力を`error_output.json`としてartifactに保存
**工数**: 25分

---

### 1-6. [HIGH] Gemini APIエラー分類が不完全 `cc:TODO`
**ファイル**: `apps/api/llm/gemini.py:855-911`
**問題**:
- エラー分類が文字列パターンマッチングのみ（脆弱）
- Google Genai SDKの例外型を全キャッチしていない
- SDKアップデート時にエラーメッセージフォーマットが変わると動作がずれる
**修正方針**:
- Google Genai SDK例外型をインポートし、`isinstance()`でチェック
- 例外型マッピングテーブルを作成
**工数**: 45分

---

### 1-7. [HIGH] 出力トークン比率の警告ロジックが不正確 `cc:TODO`
**ファイル**:
- `apps/api/llm/gemini.py:840-853`
- `apps/api/llm/anthropic.py:432-446`
**問題**:
- `if ratio < 0.1`で警告（「10%未満は期待より大幅に少ない」と判定）
- 実際には多くの工程が短い出力を期待（JSON パースなら100トークン）
- 誤報告が頻繁に発生 → ログが信頼できなくなる
**修正方針**:
- `finish_reason`で`MAX_TOKENS`を先に確認
- 基準値を工程ごとに設定
**工数**: 30分

---

### 1-8. [HIGH] トークン計算フォーマット不統一 `cc:TODO`
**ファイル**: `apps/worker/activities/step*.py` (各227等)
**問題**:
- 出力結果に入力＋出力の両方が必要（課金追跡用）
- 現状では`input_tokens`/`output_tokens`を個別記録しているが、コスト計算が一貫性なし
**修正方針**:
- 全Activityで統一フォーマット（`"token_usage": {"input": x, "output": y}`）を採用
- Runレベルのコスト追跡スキーマを定義
**工数**: 60分

---

### 1-9. [HIGH] Step11 signal validation 欠落 `cc:TODO`
**ファイル**: `apps/worker/workflows/article_workflow.py:157-179`
**問題**:
- `modified_positions`が指定された場合、スキーマ検証がない
- 不正なpositionオブジェクト（必須フィールド欠落）がworkflowに流入
- 後続のActivityで未予測のエラーが発生
**修正方針**:
- Signal handler内でPydantic modelでバリデーション
- 不正なペイロードはApplicationErrorで非可逆失敗
**工数**: 30分

---

### 1-10. [HIGH] Step11 位置情報の境界チェック欠落 `cc:TODO`
**ファイル**: `apps/worker/workflows/article_workflow.py:810-838`
**問題**:
- シグナル送信時に`num_positions`と`num_images`の不整合がある場合、エラーが静かに無視される
- ユーザーが「画像3を再生成」と指示しても、その指示が無視される可能性
**修正方針**:
- シグナル到着時に`step11_confirm_positions()`で位置情報を事前検証
- 境界エラーはworkflow-levelの非可逆エラーとして処理
**工数**: 25分

---

### 1-11. [HIGH] LangGraph asyncio.gather の例外処理不足 `cc:TODO`
**ファイル**: `apps/worker/graphs/pre_approval.py:420-433`
**問題**:
- Exceptionを含む辞書がreturnされる
- 下流のノードが`{"error": "..."}`を有効な出力として扱う
- 失敗モードが明確でない
**修正方針**:
- 例外をそのままraiseしてstep_wrapper側で適切に処理
- または、LangGraphレベルで失敗を明示的に処理
**工数**: 30分

---

### 1-12. [HIGH] LLMクライアントインスタンスの永続化による副作用 `cc:TODO`
**ファイル**: `apps/worker/activities/step11.py:295-305`
**問題**:
- Activity インスタンスが同一run内で複数回再利用される場合、同じGemini接続を使いまわす
- Timeout/接続エラーが発生した場合、キャッシュされた不健全なクライアントで再試行される
**修正方針**:
- クライアント毎回作成するか、接続ヘルスチェックを実装
**工数**: 25分

---

### 1-13. [HIGH] Pre-approval graph: step1_5 の例外処理 `cc:TODO`
**ファイル**: `apps/worker/graphs/pre_approval.py:154-277`
**問題**:
- 全エラーが`continue`で黙って無視される
- `total_articles`が0になる可能性
- LangGraph step_wrapperがこの結果を受け取っても、警告レベルの情報しかない
**修正方針**:
- 複数キーワードのフェッチ失敗時は非可逆エラーとして処理
- または、`total_articles == 0`の場合のみエラーを投げる
**工数**: 25分

---

### 1-14. [HIGH] LangGraph state update: 不完全な状態遷移 `cc:TODO`
**ファイル**: `apps/worker/graphs/wrapper.py:159-166`
**問題**:
- すべてのノード完了後、`status`が`"running"`のまま
- Event emitterがこのstateを基にeventをemitする場合、状態が不整合
**修正方針**:
- ノード完了後は`status`を`"waiting_approval"`または`"completed"`に更新
**工数**: 20分

---

### 1-15. [HIGH] Post-approval step8 (Fact Check): 検出ロジックの脆弱性 `cc:TODO`
**ファイル**: `apps/worker/graphs/post_approval.py:347-356`
**問題**:
- LLM出力を単純な文字列マッチで判定
- 英語: "contradiction"でも日本語では"矛盾"で検出失敗
- 「矛盾がないことを確認した」と含む場合、誤検出
**修正方針**:
- JSONスキーマでLLMに構造化判定を要求
- または、複数の検出キーワード（矛盾、不整合、誤り等）を使用
**工数**: 30分

---

### 1-16. [HIGH] BaseActivity._get_dependency_digests の失敗ハンドリング `cc:TODO`
**ファイル**: `apps/worker/activities/base.py:414-440`
**問題**:
- metadataファイルが破損している場合、例外が無視される
- Storageレイヤーの問題（MinIO接続エラーなど）も同じく無視される
- 本当のエラー（Storage障害）とファイル不在の区別ができない
**修正方針**:
- Exception typeを区別（S3Error NoSuchKey vs その他）
- Storage関連エラーはRETRYABLE, ファイル不在はNON_RETRYABLE
**工数**: 25分

---

### 1-17. [HIGH] Wrapper._extract_render_vars: 不完全なデータ参照 `cc:TODO`
**ファイル**: `apps/worker/graphs/wrapper.py:201-214`
**問題**:
- `step_outputs`に`ArtifactRef`が保存されていると仮定
- しかし実装を見ると、後続のnodeでは辞書アクセスしている
- 型の不整合が生じている
**修正方針**:
- GraphStateスキーマを明確化
- `step_outputs: Dict[str, ArtifactRef]`と統一
**工数**: 30分

---

### 1-18. [HIGH] Activity冪等性違反: 外部I/O呼び出しの不確定性 `cc:TODO`
**ファイル**: `apps/worker/activities/step1.py:246-271`
**問題**:
- 同じURLをフェッチするたびに異なるコンテンツが返される可能性（Webサイト更新）
- コンテンツハッシュが異なるため、入力ダイジェストは同じでも出力が異なる
- idempotency checkは入力ハッシュのみに基づいている
**修正方針**:
- ページ取得結果にタイムスタンプを含める
- キャッシュ戦略を検討（24時間キャッシュなど）
**工数**: 45分

---

### 1-19. [HIGH] step11.py の step11_state 破損時の回復戦略がない `cc:TODO`
**ファイル**: `apps/api/routers/step11.py:250, 712-744, 878-912`
**問題**:
- `step11_state`が不完全だとPydantic ValidationError
- Rollback時に`previous_step11_state`を保存しているが、保存前に部分的な更新があるとデータ喪失
- エラーハンドリングがない
**修正方針**:
- ValidationError時にデフォルト状態にリセット
- audit.logで記録
**工数**: 25分

---

### 1-20. [HIGH] step11.py status check が不正確 `cc:TODO`
**ファイル**: `apps/api/routers/step11.py:1421-1426`
**問題**:
- `RunStatus`はenum、`run.status`は文字列
- 名前が同じでも型が異なると`not in`は常にTrue
**修正方針**:
```python
allowed_statuses = [RunStatus.WAITING_APPROVAL.value, RunStatus.WAITING_IMAGE_INPUT.value]
```
**工数**: 15分

---

### 1-21. [HIGH] clone_run でワークフロー開始前の session flush 不足 `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:1166`
**問題**:
- flush()でORMには登録されるが、次のコンテキストから見える保証がない
- リトライ時に旧run_idで開始される可能性
**修正方針**: `await session.commit()`に変更
**工数**: 10分

---

### 1-22. [HIGH] step12 JSON decode 失敗時のエラーハンドリング `cc:TODO`
**ファイル**: `apps/api/routers/step12.py:195-198`
**問題**:
- 呼び出し元で step12_dataをNoneチェックしているが、明確なエラーメッセージがない
- ユーザーは「Step12 not completed」と表示されるが、実はJSON破損
**修正方針**:
- 呼び出し側で詳細チェック
- HTTPException(status_code=500, detail="Step12 data corrupted")
**工数**: 15分

---

### 1-23. [HIGH] step12 と step11 の artifact 参照不整合 `cc:TODO`
**ファイル**: `apps/api/routers/step12.py:225, 235`
**問題**:
- step11 skipのパスが異なる可能性
- step11 output pathの統一が必要
**修正方針**: step11 output pathを統一・文書化
**工数**: 20分

---

### 1-24. [HIGH] 外部キー制約の不整合 - Artifact の step_id 参照 `cc:TODO`
**ファイル**: `apps/api/db/models.py:178`
**問題**:
- Step削除時に`SET NULL`が指定
- しかしRun削除時のカスケード処理と二重になる
- Artifactテーブルにorphanな`step_id = NULL`レコードが残る可能性
**修正方針**:
- ondeleteを`CASCADE`に変更
**工数**: 20分

---

### 1-25. [HIGH] N+1 クエリ問題 - list_run_artifacts `cc:TODO`
**ファイル**: `apps/api/routers/artifacts.py:121-124`
**問題**:
- Stepをすべて取得してからArtifactをページング取得
- 毎回2つのクエリが実行される
**修正方針**:
- Runをselectinload(Run.steps)で一度に取得
**工数**: 30分

---

### 1-26. [HIGH] delete_run flush のみ（commit 漏れ） `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:1341-1343`
**問題**:
- flush()のみでcommitしていない
- セッション管理の暗黙的な依存
**修正方針**: `await session.commit()`を追加
**工数**: 10分

---

### 1-27. [HIGH] Parallel Steps の二重リトライロジック `cc:TODO`
**ファイル**: `apps/worker/workflows/parallel.py:83-136`
**問題**:
- Activity側の`retry_policy`（max 3 attempts）
- `run_parallel_steps`関数自体が最大3ラウンドのリトライ
- 最大3×3=9回のリトライが可能
**修正方針**:
- Activity側の`retry_policy`を削除し、Workflow側のloopでのみリトライを管理
**工数**: 30分

---

### 1-28. [HIGH] ApplicationError の non_retryable 設定の矛盾 `cc:TODO`
**ファイル**: `apps/worker/activities/sync_status.py:112-116`
**問題**:
- sync_run_statusが`non_retryable=False`（リトライ可能）
- 他のActivityでは`non_retryable=True`
- DB接続エラーなど一時的障害で何度リトライしても失敗
**修正方針**:
- `non_retryable=True`に統一
- リトライはWorkflow層で管理
**工数**: 15分

---

### 1-29. [HIGH] ImageGenerationWizard: 状態更新キューイング問題 `cc:TODO`
**ファイル**: `apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx:124-180`
**問題**:
- `setState`が複数回呼ばれ、batchingの影響を受ける
- phase遷移時に中間状態でAPIが複数実行される可能性
- 高速でphase切り替えした場合、古いfetch結果が新しいstateに混入
**修正方針**:
- `abortController`で既存リクエストをキャンセル前にabort flagチェック
- state updateをbatch処理
**工数**: 30分

---

### 1-30. [HIGH] WorkflowProgressView: localStorage 同期ズレ `cc:TODO`
**ファイル**: `apps/ui/src/components/workflow/WorkflowProgressView.tsx:61-76`
**問題**:
- SSR / hydrationミスマッチで、サーバー側のデフォルト値とクライアント側のlocalStorage値がズレる
- 初回レンダリング時にpatternが異なる値で初期化される可能性
**修正方針**:
- useEffect + useStateの分離（hydration対応）
**工数**: 20分

---

### 1-31. [HIGH] ArtifactViewer: useMemo 依存配列問題 `cc:TODO`
**ファイル**: `apps/ui/src/components/artifacts/ArtifactViewer.tsx:88-125`
**問題**:
- `groupedArtifacts`の`useMemo`が`[artifacts]`に依存
- 親コンポーネントから`artifacts`が毎回新しい配列参照で渡される場合、毎回再計算
- 大規模ファイルセット（>100ファイル）で顕著なパフォーマンス低下
**修正方針**:
- artifactsをJSON.stringifyでdepthチェック
- または親でartifactsをメモ化して渡す
**工数**: 20分

---

### 1-32. [HIGH] useArtifactContent: artifactId 変更時の race condition `cc:TODO`
**ファイル**: `apps/ui/src/hooks/useArtifact.ts:78-111`
**問題**:
- artifactIdがnull → 有効なID → nullと高速で変更された場合
- 古いartifactのcontentが残存
- ファイルリストの高速切り替え時に前の内容が一瞬表示される
**修正方針**:
- useEffect前にnullチェック追加
- またはuseCallback内でnullチェック後、即座にsetContent(null)
**工数**: 20分

---

### 1-33. [HIGH] RunDetailPage: handleOpenPreview の stale closure `cc:TODO`
**ファイル**: `apps/ui/src/app/runs/[id]/page.tsx:134-152`
**問題**:
- `handleOpenPreview`が`previewArticle`を依存配列から意図的に除外
- ただし`articleNumber ?? previewArticle`でpreviewArticleを参照
- 記事の高速クリックで内部状態がズレる
**修正方針**:
- `previewArticle`をuseRefで管理
**工数**: 20分

---

### 1-34. [HIGH] RunList: selectedIds の Set 参照透過性 `cc:TODO`
**ファイル**: `apps/ui/src/components/runs/RunList.tsx:84-92`
**問題**:
- `selectedIds`を`new Set(...)`で更新
- Setの内容変更後に同じ参照でsetState（エッジケース）
- UI更新が漏れる場合がある
**修正方針**:
- `setSelectedIds(new Set([...newSelected]))`とする
**工数**: 10分

---

### 1-35. [HIGH] Resume From Step でのアーティファクト検証不足 `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:840-847`
**問題**:
- 読み込んだ`artifact_data`と`artifact_path`が以後使われていない
- Activity側でartifact不在時の挙動が明記されていない
**修正方針**:
- 不要なartifact読み込みを削除
- またはActivity側でartifact不在時の挙動を明記
**工数**: 20分

---

## 🟡 フェーズ2: MEDIUM（中期対応）`cc:TODO`

### 2-1. [MEDIUM] delete_run と bulk_delete_runs で audit log の順序が逆 `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:1325-1341 vs 1417-1424`
**工数**: 15分

### 2-2. [MEDIUM] step11 finalize でロールバック対象が限定的 `cc:TODO`
**ファイル**: `apps/api/routers/step11.py:1195-1227`
**工数**: 25分

### 2-3. [MEDIUM] useRuns: page/status 変更時の race condition `cc:TODO`
**ファイル**: `apps/ui/src/hooks/useRuns.ts:77-84`
**工数**: 25分

### 2-4. [MEDIUM] ErrorBoundary: 再試行ボタンで状態が完全リセットされない `cc:TODO`
**ファイル**: `apps/ui/src/components/common/ErrorBoundary.tsx:30-32`
**工数**: 15分

### 2-5. [MEDIUM] ArtifactViewer: expandedSteps が Set のまま参照保持 `cc:TODO`
**ファイル**: `apps/ui/src/components/artifacts/ArtifactViewer.tsx:127-135`
**工数**: 15分

### 2-6. [MEDIUM] ImageGenerationWizard: currentPhase prop 変更時の状態不整合 `cc:TODO`
**ファイル**: `apps/ui/src/components/imageGeneration/ImageGenerationWizard.tsx:93-98`
**工数**: 20分

### 2-7. [MEDIUM] Gemini generation_config 設定矛盾 `cc:TODO`
**ファイル**: `apps/api/llm/gemini.py:556-618`
**工数**: 20分

### 2-8. [MEDIUM] Anthropic 予期しないエラーの分類が甘い `cc:TODO`
**ファイル**: `apps/api/llm/anthropic.py:256-259`
**工数**: 15分

### 2-9. [MEDIUM] Gemini タイムアウト設定が硬直 `cc:TODO`
**ファイル**: `apps/api/llm/gemini.py:90, 678`
**工数**: 20分

### 2-10. [MEDIUM] Step11 タイムアウト一貫性 `cc:TODO`
**ファイル**: `apps/worker/workflows/article_workflow.py:1020`
**工数**: 25分

### 2-11. [MEDIUM] hearing.py delete template 後の orphan `cc:TODO`
**ファイル**: `apps/api/routers/hearing.py:310-311`
**工数**: 20分

### 2-12. [MEDIUM] Parallel steps の Activity / Workflow リトライ衝突 `cc:TODO`
**ファイル**: `apps/worker/workflows/parallel.py:83-136`
**工数**: 30分

### 2-13. [MEDIUM] Step11 Phase State 非アトミック性 `cc:TODO`
**ファイル**: `apps/worker/workflows/article_workflow.py:757-891`
**工数**: 45分

### 2-14. [MEDIUM] websocket.py broadcast() が tenant_id なしでも silent 成功 `cc:TODO`
**ファイル**: `apps/api/routers/websocket.py:77-92`
**工数**: 10分

### 2-15. [MEDIUM] pre_approval.py asyncio.gather エラーハンドリング（再掲・詳細） `cc:TODO`
**ファイル**: `apps/worker/graphs/pre_approval.py:420-425`
**工数**: 20分

---

## 🟢 フェーズ3: LOW（改善）`cc:TODO`

### 3-1. [LOW] error_message のログ記録でメッセージが重複 `cc:TODO`
**ファイル**: `apps/api/routers/runs.py:245-246, 752-753`
**工数**: 10分

### 3-2. [LOW] ContentRenderer: decodedContent の再計算不要 `cc:TODO`
**ファイル**: `apps/ui/src/components/artifacts/ArtifactViewer.tsx:379`
**工数**: 15分

### 3-3. [LOW] NetworkDebugPanel: ログ配列の SET vs REF 混在 `cc:TODO`
**ファイル**: `apps/ui/src/app/runs/[id]/page.tsx:815-831`
**工数**: 10分

### 3-4. [LOW] API client の重複したエラーハンドリング（Plans7より） `cc:TODO`
**ファイル**: `apps/ui/src/lib/api.ts:102-113`
**工数**: 15分

### 3-5. [LOW] workflow_logger の import 位置（Plans7より） `cc:TODO`
**ファイル**: `apps/worker/workflows/parallel.py:19`
**工数**: 10分

---

## 🔵 フェーズ4: テスト・検証 `cc:TODO`

### 4-1. 修正箇所のユニットテスト追加 `cc:TODO`
- [ ] LLMクライアント接続管理テスト
- [ ] Temporal決定性テスト（datetime.now使用箇所）
- [ ] Signal競合テスト（approve/reject同時送信）
- [ ] Session commit/rollbackテスト
- [ ] RunStatus enum/string比較テスト
- [ ] WebSocket tenant isolationテスト
- [ ] LangGraph例外処理テスト

### 4-2. 統合テスト実行 `cc:TODO`
```bash
# Backend テスト
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# Frontend テスト
npm run lint --prefix apps/ui
npx tsc --noEmit --project apps/ui/tsconfig.json
```

### 4-3. Temporal Replay テスト `cc:TODO`
```bash
# 決定性違反の検出
uv run pytest tests/temporal/ -v --replay
```

---

## 完了基準

- [ ] 全フェーズの修正完了
- [ ] TypeScript エラーがない
- [ ] Python lint/type エラーがない
- [ ] ユニットテスト追加・通過
- [ ] 統合テスト通過
- [ ] Temporal Replay テスト通過

---

## Plans7との関係

Plans7にあり、本計画で重複している項目:
- 0-3 (useRunProgress) = Plans7 0-3
- WebSocket tenant_id問題 = Plans7 0-1, 0-2, 1-1

Plans7にある追加項目（本計画に含まれていない）:
- 0-4: Temporal approve/rejectシグナル競合（本計画1-1で詳細化）
- 0-5: sync_run_statusのステータス上書き競合（本計画1-2で詳細化）
- 1-2: TenantDBManagerエンジンキャッシュのメモリリーク
- 1-3: Activity heartbeatの欠如
- 1-4: retry_step/resume_from_stepの楽観的ロック欠如
- 1-5: clone_runのワークフロー開始失敗時の孤立Run（本計画1-21で関連）
- 1-6: Step11 signalsのフェーズ検証不足（本計画1-9, 1-10で詳細化）
- 2-1〜2-7: MEDIUM項目
- 3-1〜3-4: LOW項目

**重要**: 本計画（Plans.md）はPlans7の上位互換として運用します。Plans7の項目も本計画に含まれています。

---

## 次のアクション

1. 「`/work Plans.md`」でフェーズ0から実装開始
2. 各修正後にテスト実行
3. コミットは機能単位で細かく

---

## 関連ドキュメント

- [Plans7.md](Plans7.md) - 前回コードレビュー修正計画
- [Plans1.md](Plans1.md) - Backend 統合修正計画（API/DB/Storage）
- [Plans2.md](Plans2.md) - Worker 統合修正計画 ✅完了
- [Plans3.md](Plans3.md) - Frontend 統合修正計画 ✅完了
- [Plans4.md](Plans4.md) - 設定・テスト・インフラ統合修正計画 ✅完了
