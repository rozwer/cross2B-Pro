# 品質チェックでワークフローが止まる問題の修正

## 問題

step9の品質スコアチェックが厳しすぎて、リトライを繰り返しても基準を満たせずワークフローが停止することがあった。

## 原因

step9は品質スコア（0.90しきい値）を満たさない場合、`ApplicationError`を投げてTemporalのアクティビティリトライに依存していた。しかしリトライ上限がなく、スコアが改善しない場合は永遠にリトライを続ける可能性があった。

## 修正内容

### apps/worker/activities/step9.py

#### 定数の追加

```python
# Constants
MIN_POLISHED_LENGTH = 500
META_DESCRIPTION_PATTERN = re.compile(r"<!--\s*META_DESCRIPTION:\s*(.+?)\s*-->", re.DOTALL)
HEADING_CLEANUP_PATTERN = re.compile(r"^(#+)\s*H\d+-\d+[:\s]*", re.MULTILINE)
QUALITY_SCORE_THRESHOLD = 0.90
QUALITY_RETRY_MAX_ATTEMPTS = 3  # 追加
```

#### 品質チェックロジックの修正

```python
# P2 Critical: Enforce quality gate - fail if score below threshold
# BUT: If we've exhausted retries, accept the current result to avoid blocking
current_attempt = activity.info().attempt
if total_score < QUALITY_SCORE_THRESHOLD:
    low_scores = []
    if qs_data.get("accuracy", 0.0) < 0.85:
        low_scores.append(f"accuracy={qs_data.get('accuracy', 0.0):.2f}")
    if qs_data.get("seo_optimization", 0.0) < 0.85:
        low_scores.append(f"seo={qs_data.get('seo_optimization', 0.0):.2f}")
    if qs_data.get("cta_effectiveness", 0.0) < 0.80:
        low_scores.append(f"cta={qs_data.get('cta_effectiveness', 0.0):.2f}")

    if current_attempt >= QUALITY_RETRY_MAX_ATTEMPTS:
        # Exhausted retries - proceed with current result and add warning
        activity.logger.warning(
            f"Quality score {total_score:.2f} below threshold {QUALITY_SCORE_THRESHOLD}, "
            f"but max attempts ({QUALITY_RETRY_MAX_ATTEMPTS}) exhausted. "
            f"Proceeding with current result. Low scores: {', '.join(low_scores) if low_scores else 'none'}"
        )
        quality_warnings.append(
            f"Quality score {total_score:.2f} below threshold {QUALITY_SCORE_THRESHOLD} "
            f"(accepted after {current_attempt} attempts)"
        )
    else:
        # Retry
        activity.logger.warning(
            f"Quality score below threshold: {total_score:.2f} < {QUALITY_SCORE_THRESHOLD}. "
            f"Attempt {current_attempt}/{QUALITY_RETRY_MAX_ATTEMPTS}. "
            f"Low scores: {', '.join(low_scores) if low_scores else 'none identified'}"
        )
        raise ApplicationError(
            f"Quality score {total_score:.2f} below threshold {QUALITY_SCORE_THRESHOLD}. "
            f"Issues: {', '.join(low_scores) if low_scores else 'general quality'}",
            type="QUALITY_BELOW_THRESHOLD",
            non_retryable=False,
        )
```

## 動作

| 試行回数 | 品質スコア | 動作 |
|---------|-----------|------|
| 1回目 | 0.85 | リトライ |
| 2回目 | 0.88 | リトライ |
| 3回目 | 0.87 | **警告付きで採用、続行** |

## 他のステップとの違い

| ステップ | 品質チェック方式 | 上限到達時の動作 |
|---------|----------------|-----------------|
| step3a, step3b, step3c, step3_5, step4, step6 | `QualityRetryLoop` + `accept_on_final=True` | 内部リトライ後、結果を受け入れて続行 |
| step9 | Temporalアクティビティリトライ | **修正後**: 3回で警告付き続行 |

## 関連コミット

- `4cbfe65 feat(worker): add quality gate retry limit to step9`

## 確認方法

1. 品質スコアが低い記事を生成
2. step9が3回リトライ後、警告付きで続行することを確認
3. 出力の`quality_warnings`に警告メッセージが含まれていることを確認

## 備考

- 他のステップ（step3a等）は`QualityRetryLoop`を使用しており、`accept_on_final=True`で内部リトライ後に結果を受け入れる設計
- step9のみがTemporalリトライに依存していたため、この修正が必要だった
