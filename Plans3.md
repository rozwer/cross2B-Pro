# 工程出力トークン不足検出・修復計画

> **作成日**: 2026-01-12
> **目的**: LLM出力が途中で切れる問題を検出・修復し、将来の同様の問題を防止する

---

## 背景・問題

### 発見された問題

1. **古いrun（2026-01-02作成）**: step3c出力が1011バイト、119トークンと極端に小さい
2. **最新のrun（2026-01-09作成）**: step3c出力が15828バイトと正常
3. **UIでの表示**: 品質警告として「出力が切れている」と表示される

### 根本原因の推定

- LLM APIからのレスポンスが途中で切れている（finish_reasonが`MAX_TOKENS`または`STOP`以外）
- プロンプトが長すぎて出力トークンの余地が少ない
- ネットワークタイムアウトや接続断

### 影響を受けるrun

| run_id | キーワード | 状態 | step3c サイズ |
|--------|-----------|------|--------------|
| `9a47b511-e12c-46c6-95ef-045231b3f372` | 派遣社員 業務遂行能力 向上 | waiting_approval | 1011 bytes |
| `d0d028f3-7c5f-4543-a025-c50e4f0ba0a4` | SEO対策 初心者 | completed | 1053 bytes |
| `9bef840c-2ff7-41d3-80a5-cb8d0ee84f04` | コンテンツマーケティング 始め方 | completed | 1175 bytes |

---

## フェーズ 1: 検出機能の強化 `cc:完了`

### 1.1 finish_reasonの検証追加（Gemini）

**ファイル**: `apps/api/llm/gemini.py`

- [x] `_parse_response`で`finish_reason`を確認
- [x] `MAX_TOKENS`の場合は警告ログを出力
- [x] `SAFETY`や`RECITATION`の場合はエラーとして処理

```python
# 追加する検証ロジック
if finish_reason == "MAX_TOKENS":
    logger.warning(
        "Output was truncated due to max_tokens limit",
        extra={"model": self._model, "output_tokens": output_tokens}
    )
elif finish_reason in ("SAFETY", "RECITATION", "OTHER"):
    logger.error(
        f"Unexpected finish_reason: {finish_reason}",
        extra={"model": self._model}
    )
```

### 1.2 出力トークン比率チェック

- [x] `output_tokens / max_tokens`比率が低すぎる場合（例: < 10%）は警告
- [x] Anthropicクライアントにも同様の検証を追加

---

## フェーズ 2: 工程別出力検証の強化 `cc:完了`

### 2.1 step3c出力の最小サイズチェック

**ファイル**: `apps/worker/activities/step3c.py`

- [x] 出力バイト数が閾値（3000バイト）未満の場合は品質問題として検出
- [x] `parsed_data`がnullの場合は警告ログを出力

### 2.2 step3c QualityValidatorの改善

**ファイル**: `apps/worker/activities/step3c.py`

- [x] 切れの兆候（truncation indicators）チェックを追加
- [x] Critical issuesがある場合はis_acceptable=Falseにする

---

## フェーズ 3: 古いデータの修復オプション `cc:TODO`

### 3.1 手動再実行の手順書

影響を受けるrunを再実行する方法：

1. run詳細ページから「工程を再実行」ボタン
2. step3cを選択して再実行
3. 工程3（3A/3B/3C）全体の再実行も可能

### 3.2 データクリーンアップスクリプト（オプション）

- [ ] 不完全な出力を持つrunを検出するクエリ
- [ ] 対象runのstep3cデータを削除してpending状態に戻す
- [ ] ユーザーが手動で再実行できる状態にする

```sql
-- 不完全なstep3c出力を持つrunを検出
SELECT r.id, r.input_data->>'keyword', s.status
FROM runs r
JOIN steps s ON s.run_id = r.id
WHERE s.step_name = 'step3c'
  AND s.status = 'completed'
  -- 追加条件: output.jsonのサイズが小さい（要実装）
```

---

## フェーズ 4: UIでの表示改善 `cc:TODO`

### 4.1 品質警告の詳細化

**ファイル**: `apps/ui/src/components/artifacts/StepContentViewer.tsx`

- [ ] 「出力が切れている」警告に詳細情報を追加
- [ ] 出力トークン数/期待トークン数を表示
- [ ] 再実行を促すボタンを追加

### 4.2 runリストでの警告表示

- [ ] 不完全な出力を持つrunにはアイコンを表示
- [ ] ツールチップで詳細を説明

---

## フェーズ 5: テスト・確認 `cc:TODO`

- [ ] `npm run lint` でエラーがないことを確認
- [ ] `npx tsc --noEmit` で型エラーがないことを確認
- [ ] 新規runで工程3Cが正常に完了することを確認
- [ ] 出力トークンが十分に多いことを確認

---

## 完了基準

- [ ] finish_reasonの検証がログに出力される
- [ ] 出力トークン比率が低い場合に警告が出る
- [ ] step3cの出力最小サイズチェックが機能する
- [ ] UIで品質警告がわかりやすく表示される
- [ ] TypeScript エラーがない
- [ ] lint エラーがない

---

## 技術詳細

### 関連ファイル

| ファイル | 役割 |
|---------|------|
| `apps/api/llm/gemini.py` | Gemini APIクライアント |
| `apps/api/llm/anthropic.py` | Claude APIクライアント |
| `apps/worker/activities/step3c.py` | 工程3C Activity |
| `apps/worker/helpers/quality_validator.py` | 品質検証 |
| `apps/ui/src/components/artifacts/StepContentViewer.tsx` | 出力ビューア |

### Gemini finish_reason 一覧

| 値 | 説明 | 対応 |
|----|------|------|
| `STOP` | 正常終了 | OK |
| `MAX_TOKENS` | トークン上限到達 | 警告、再試行検討 |
| `SAFETY` | 安全性フィルター | エラー |
| `RECITATION` | 引用問題 | エラー |
| `OTHER` | その他 | エラー |

---

## 優先度

1. **高**: フェーズ1（検出機能強化）- 将来の問題を防止
2. **中**: フェーズ2（工程別検証）- 品質保証
3. **低**: フェーズ3（データ修復）- 既存データの対応
4. **低**: フェーズ4（UI改善）- ユーザー体験

---

## 次のアクション

- 「`/work`」で実装を開始
- または「フェーズ1から始めて」
