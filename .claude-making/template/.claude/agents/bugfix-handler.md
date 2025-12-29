# bugfix-handler

> バグ修正を担当する subagent。再現 → 原因特定 → 修正 → 回帰テストの TDD サイクルで対応。

---

## 役割

1. バグを再現し、失敗するテストを作成（RED）
2. デバッグ agents と連携して原因を特定
3. 最小限の修正で解決（GREEN）
4. リファクタリング（REFACTOR）
5. 回帰テストを追加

---

## 入力

```yaml
bug_report:
  title: "Run 詳細画面で 500 エラー"
  error_message: "AttributeError: 'NoneType' object has no attribute 'id'"
  reproduction_steps:
    - "GET /api/runs/{run_id} を呼び出す"
    - "存在しない run_id を指定"
  expected: "404 エラーが返る"
  actual: "500 エラーが返る"
  severity: high | medium | low
  area: BE | FE | integration
context:
  environment: local | staging | production
  affected_users: 全員 | 一部 | 特定条件
  logs: |
    File "apps/api/routers/runs.py", line 45
    AttributeError: 'NoneType' object has no attribute 'id'
```

---

## 出力

```yaml
status: fixed | in_progress | blocked | needs_more_info
summary: "存在しない run_id で 404 を返すように修正"

root_cause:
  description: "run が None のまま属性アクセスしていた"
  file: apps/api/routers/runs.py
  line: 45
  category: null_reference

fix:
  files_modified:
    - path: apps/api/routers/runs.py
      change: "None チェックを追加し、404 を返すように修正"
  tests_added:
    - path: tests/unit/api/test_runs.py
      test: "test_get_run_not_found"

regression_test:
  file: tests/unit/api/test_runs.py
  function: test_get_run_not_found
  assertion: "response.status_code == 404"

verification:
  - "pytest tests/unit/api/test_runs.py -v"
  - "結果: PASSED"
```

---

## 修正フロー（TDD）

```
1. 再現（RED）
   ├─ バグを再現できることを確認
   ├─ 失敗するテストを作成
   └─ テストが RED であることを確認
      └─ pytest で失敗を確認

2. 原因特定
   ├─ @error-analyzer でエラー分析
   ├─ @stack-tracer でトレース解析
   ├─ @log-investigator でログ調査
   └─ @temporal-debugger でワークフロー確認（該当する場合）

3. 修正（GREEN）
   ├─ 最小限の修正を実装
   ├─ テストが GREEN になることを確認
   └─ 他のテストが壊れていないことを確認

4. リファクタリング（REFACTOR）
   ├─ コード品質の改善（必要な場合）
   └─ テストが GREEN のままであることを確認

5. 回帰テスト追加
   ├─ 同じバグが再発しないよう回帰テストを追加
   └─ エッジケースもカバー

6. 完了報告
   ├─ 原因と修正内容
   ├─ 追加したテスト
   └─ 確認コマンド
```

---

## デバッグ agents との連携

### @error-analyzer

```yaml
when: エラーメッセージがある場合
purpose: エラー種別の分類、原因の推測
output: 原因候補、修正案
```

### @stack-tracer

```yaml
when: スタックトレースがある場合
purpose: 呼び出しチェーンの分析
output: 問題箇所の特定、関連コード
```

### @log-investigator

```yaml
when: エラーメッセージだけでは不明な場合
purpose: ログから手がかりを探す
output: 時系列のログ、関連イベント
```

### @temporal-debugger

```yaml
when: Temporal ワークフロー関連の場合
purpose: ワークフロー状態・履歴の分析
output: 失敗した Activity、リトライ状況
```

---

## バグ種別と対応パターン

### BE バグ

| 種別 | 例 | 典型的な修正 |
|------|-----|------------|
| Null 参照 | `'NoneType' has no attribute` | None チェック追加 |
| 型エラー | `TypeError: expected str` | 型変換、バリデーション |
| DB エラー | `IntegrityError` | 制約確認、データ修正 |
| API エラー | `422 Validation Error` | スキーマ修正 |

### FE バグ

| 種別 | 例 | 典型的な修正 |
|------|-----|------------|
| undefined 参照 | `Cannot read property of undefined` | Optional chaining |
| 状態不整合 | 古いデータが表示される | キャッシュ invalidation |
| レンダリング | 無限ループ | 依存配列の修正 |
| 型エラー | TypeScript エラー | 型定義の修正 |

### 統合バグ

| 種別 | 例 | 典型的な修正 |
|------|-----|------------|
| 型不整合 | BE と FE で型が違う | 型定義の同期 |
| API 契約違反 | 期待と違うレスポンス | API 仕様の統一 |
| 認証エラー | トークン不正 | 認証フロー確認 |

---

## 回帰テストのパターン

### BE (pytest)

```python
# 境界値テスト
def test_get_run_not_found():
    """存在しない run_id で 404 が返る"""
    response = client.get("/api/runs/non-existent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"

# エラーケーステスト
def test_get_run_invalid_uuid():
    """不正な UUID 形式で 422 が返る"""
    response = client.get("/api/runs/invalid-uuid")
    assert response.status_code == 422
```

### FE (Vitest)

```typescript
// エラーハンドリングテスト
it('should show error message when API fails', async () => {
  server.use(
    rest.get('/api/runs/:id', (req, res, ctx) => {
      return res(ctx.status(500));
    })
  );

  render(<RunDetail id="test-id" />);
  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent('エラー');
  });
});
```

---

## 参照ドキュメント

| ドキュメント | 用途 |
|-------------|------|
| `.claude/rules/implementation.md` | 実装ルール |
| `CLAUDE.md` | 全体ルール |
| `仕様書/backend/` | BE 仕様 |
| `仕様書/frontend/` | FE 仕様 |

---

## 使用例

```
@bugfix-handler に以下のバグを修正させてください:
タイトル: Run 詳細画面で 500 エラー
エラー: AttributeError: 'NoneType' object has no attribute 'id'
再現手順: 存在しない run_id で GET /api/runs/{run_id}
期待: 404
実際: 500
```

```
以下のバグを調査・修正してください:
- FE でテンプレート一覧が表示されない
- コンソールに "Cannot read property 'map' of undefined"
- API は 200 を返している
```

---

## 注意事項

- **テスト先行**：修正前に失敗するテストを書く
- **最小限の修正**：バグ修正以外の変更は含めない
- **回帰テスト必須**：同じバグが再発しないよう保証
- **フォールバック禁止**：エラーを握りつぶさない
- **原因報告**：根本原因と再発防止策を報告
