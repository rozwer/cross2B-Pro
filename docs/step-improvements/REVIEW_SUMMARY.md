# Step改善案 - レビューサマリー

> このドキュメントはCodexレビュー用のサマリーです

## 作成日

2025-12-17

## 対象

- `docs/step-improvements/step*.md` (15ファイル)
- `apps/worker/activities/step*.py` (15ファイル)

---

## 主要な発見事項

### 1. フォールバック禁止ルール違反

#### Step5: Primary Collection (重大)

**ファイル**: `apps/worker/activities/step5.py:92-98`

```python
except Exception:
    # Fall back to basic queries if parsing fails  ← 違反
    search_queries = [
        f"{keyword} research statistics",
        f"{keyword} official data",
        f"{keyword} academic study",
    ]
```

**問題**: LLMパース失敗時に固定クエリへフォールバックしている

#### Step10: Final Output (潜在的違反)

**ファイル**: `apps/worker/activities/step10.py:125-127`

```python
except Exception:
    # Checklist is nice-to-have, continue if fails
    checklist = "Publication checklist generation failed."
```

**問題**: ダミー文字列での置換はフォールバックに該当する可能性

---

### 2. 冪等性キャッシュの無効化

**ファイル**: `apps/worker/activities/base.py:337`

```python
return None  # Always re-run for now; enable caching later
```

**影響**: 全ステップで既存結果の再利用ができない

---

### 3. 共通の問題パターン

| パターン                 | 該当ステップ | 説明                                    |
| ------------------------ | ------------ | --------------------------------------- |
| 入力品質チェック不十分   | 全ステップ   | 前ステップデータの欠落/不良を検出しない |
| 構造化出力スキーマなし   | Step0-10     | LLM出力が自由形式でパース不安定         |
| 品質リトライなし         | Step0-10     | 出力品質が低くても成功扱い              |
| 中間チェックポイントなし | Step5,7a,8   | 長時間処理の途中失敗で全ロスト          |
| JSON切れ対応なし         | Step7a,7b,8  | 長文生成でJSONが途中で切れる            |

---

## ステップ別優先度まとめ

### 最高優先度（フォールバック違反修正）

- **Step5**: パース失敗時のフォールバック削除
- **Step10**: チェックリスト失敗時の処理見直し

### 高優先度（品質保証基盤）

- **Step4**: 構造化出力スキーマ導入（後続全ステップに影響）
- **base.py**: 冪等性キャッシュの有効化

### 中優先度（安定性向上）

- **Step3b**: 「ワークフローの心臓」として品質検証強化
- **Step7a**: セクション単位処理による長文対応
- **Step8**: 3つのLLM呼び出しのチェックポイント化

---

## アーキテクチャ上の懸念

### 1. エラー分類の曖昧さ

- `RETRYABLE` と `NON_RETRYABLE` の境界が不明確
- Rate Limit対応が固定的

### 2. 品質検証の欠如

- LLMレスポンスの品質を評価する仕組みがない
- 「成功」の定義が「例外が発生しない」のみ

### 3. 可観測性の不足

- 処理進捗の可視化が不十分
- メトリクス収集が限定的

---

## 推奨される実装順序

1. **Phase 1: 緊急修正** (即座に対応)
   - Step5のフォールバック削除
   - Step10のチェックリスト処理修正

2. **Phase 2: 基盤整備** (1-2週間)
   - base.pyの冪等性有効化
   - Step4の構造化出力スキーマ

3. **Phase 3: 品質向上** (2-4週間)
   - 各ステップの入力品質チェック
   - 出力品質検証の導入

4. **Phase 4: 堅牢化** (1-2ヶ月)
   - 中間チェックポイントの実装
   - セクション単位処理の導入

---

## レビュー依頼観点

1. **Correctness**: フォールバック禁止違反の判定は正確か
2. **Security**: 越境・注入のリスクは考慮されているか
3. **Maintainability**: 提案された改善は保守性を向上させるか
4. **Operational Safety**: リトライ・冪等性・ログの提案は適切か

---

## 関連ドキュメント

- `仕様書/ROADMAP.md` - 実装計画
- `仕様書/workflow.md` - ワークフロー定義
- `.claude/CLAUDE.md` - プロジェクト指示書
- `.claude/rules/workflow-contract.md` - ワークフロー契約
