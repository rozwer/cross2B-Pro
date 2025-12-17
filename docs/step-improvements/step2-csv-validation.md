# Step2: CSV Validation - 改善案

## 概要

| 項目 | 内容 |
|------|------|
| ファイル | `apps/worker/activities/step2.py` |
| Activity名 | `step2_csv_validation` |
| 使用ツール | なし（純粋なバリデーション） |
| 目的 | 競合データの品質検証・正規化 |

---

## 現状分析

### リトライ戦略

**現状**:
- バリデーション失敗 → `VALIDATION_FAIL` で終了
- Temporal のリトライ対象外（NON_RETRYABLE扱い）

**問題点**:
1. **自己修復機能なし**: バリデーション失敗したらそこで終了
2. **部分的な修復不可**: 1件でもエラーがあると全体が失敗
3. **閾値設定なし**: エラー許容度がゼロ（厳しすぎる場合がある）

### フォーマット整形機構

**現状**:
- `url`, `title`, `content` の存在チェック
- `content` の長さチェック（100文字以上）
- WARNING/ERROR の severity 分類

**問題点**:
1. **整形ロジックなし**: 検証はするが修正しない
2. **正規化なし**: 空白、改行、エンコーディング問題を放置
3. **バリデーションルールが固定**: 設定で変更できない
4. **詳細な品質メトリクス不足**: 何がどの程度悪いのか不明

### 中途開始機構

**現状**:
- ステップ全体の冪等性のみ
- 部分検証結果の保存なし

**問題点**:
1. **再開不可**: 大量データの検証途中で失敗しても最初から
2. **進捗把握困難**: 何件中何件目を処理中か不明

---

## 改善案

### 1. リトライ戦略の強化

#### 1.1 自動修復機能の追加

```python
class Step2CSVValidation(BaseActivity):
    """バリデーション + 自動修復"""

    # エラー許容閾値
    MAX_ERROR_RATE = 0.3  # 30%までならエラー許容
    MIN_VALID_RECORDS = 2  # 最低2件は必要

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # ... step1データ読み込み ...

        validated_records = []
        validation_issues = []
        auto_fixed_count = 0

        for idx, competitor in enumerate(competitors):
            # 1. 自動修復を試みる
            fixed_record, fixes = self._auto_fix(competitor)

            if fixes:
                auto_fixed_count += 1
                activity.logger.info(f"Auto-fixed record {idx}: {fixes}")

            # 2. 修復後のバリデーション
            issues = self._validate_record(fixed_record, idx)

            if self._has_critical_errors(issues):
                validation_issues.append({
                    "index": idx,
                    "url": competitor.get("url", "unknown"),
                    "issues": issues,
                    "auto_fixes_attempted": fixes,
                })
            else:
                validated_records.append(fixed_record)
                if issues:  # WARNING のみ
                    validation_issues.append({
                        "index": idx,
                        "url": fixed_record.get("url"),
                        "issues": issues,
                        "status": "accepted_with_warnings",
                    })

        # 3. 閾値チェック
        error_rate = 1 - (len(validated_records) / len(competitors))

        if len(validated_records) < self.MIN_VALID_RECORDS:
            raise ActivityError(
                f"Too few valid records: {len(validated_records)} "
                f"(minimum: {self.MIN_VALID_RECORDS})",
                category=ErrorCategory.NON_RETRYABLE,
                details={"validation_issues": validation_issues},
            )

        if error_rate > self.MAX_ERROR_RATE:
            raise ActivityError(
                f"Error rate too high: {error_rate:.1%} "
                f"(maximum: {self.MAX_ERROR_RATE:.1%})",
                category=ErrorCategory.RETRYABLE,  # step1から再取得の余地
                details={"validation_issues": validation_issues},
            )

        return {
            "step": self.step_id,
            "is_valid": True,
            "total_records": len(competitors),
            "valid_records": len(validated_records),
            "auto_fixed_count": auto_fixed_count,
            "validation_issues": validation_issues,
            "validated_data": validated_records,
        }
```

#### 1.2 自動修復ロジック

```python
def _auto_fix(self, record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """レコードの自動修復を試みる"""
    fixed = record.copy()
    fixes = []

    # URL正規化
    if "url" in fixed:
        original_url = fixed["url"]
        fixed["url"] = self._normalize_url(original_url)
        if fixed["url"] != original_url:
            fixes.append(f"url_normalized")

    # タイトル修復
    if not fixed.get("title") or len(fixed.get("title", "").strip()) == 0:
        # URLからタイトルを推測
        if "url" in fixed:
            fixed["title"] = self._extract_title_from_url(fixed["url"])
            fixes.append("title_extracted_from_url")

    # コンテンツ正規化
    if "content" in fixed:
        original_len = len(fixed["content"])
        fixed["content"] = self._normalize_content(fixed["content"])
        if len(fixed["content"]) != original_len:
            fixes.append(f"content_normalized:{original_len}->{len(fixed['content'])}")

    # 空白トリム
    for key in ["title", "content"]:
        if key in fixed and isinstance(fixed[key], str):
            stripped = fixed[key].strip()
            if stripped != fixed[key]:
                fixed[key] = stripped
                fixes.append(f"{key}_trimmed")

    return fixed, fixes

def _normalize_content(self, content: str) -> str:
    """コンテンツの正規化"""
    # 連続空白を単一スペースに
    content = re.sub(r'[ \t]+', ' ', content)
    # 連続改行を2つまでに
    content = re.sub(r'\n{3,}', '\n\n', content)
    # 制御文字除去（改行・タブ以外）
    content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', content)
    # BOM除去
    content = content.lstrip('\ufeff')
    return content.strip()

def _normalize_url(self, url: str) -> str:
    """URLの正規化"""
    url = url.strip()
    # プロトコル補完
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    # 末尾スラッシュの統一
    return url.rstrip('/')

def _extract_title_from_url(self, url: str) -> str:
    """URLからタイトルを推測"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    if path:
        # 最後のパスセグメントをタイトル化
        segment = path.split('/')[-1]
        # ハイフン・アンダースコアをスペースに
        title = re.sub(r'[-_]', ' ', segment)
        # 拡張子除去
        title = re.sub(r'\.\w+$', '', title)
        return title.title()
    return parsed.netloc
```

### 2. フォーマット整形機構の導入

#### 2.1 バリデーション設定の外部化

```python
from pydantic import BaseModel
from typing import Optional

class ValidationConfig(BaseModel):
    """バリデーション設定"""
    min_content_length: int = 100
    max_content_length: int = 50000
    min_title_length: int = 5
    max_title_length: int = 200
    required_fields: list[str] = ["url", "title", "content"]
    allow_empty_title: bool = False
    allow_short_content: bool = False
    error_rate_threshold: float = 0.3
    min_valid_records: int = 2

class Step2CSVValidation(BaseActivity):
    def __init__(self, config: ValidationConfig | None = None, **kwargs):
        super().__init__(**kwargs)
        self.validation_config = config or ValidationConfig()
```

#### 2.2 詳細な品質メトリクス

```python
class ContentQualityMetrics(BaseModel):
    """コンテンツ品質メトリクス"""
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    unique_word_ratio: float
    heading_count: int
    has_lists: bool
    has_code_blocks: bool
    language_detected: Optional[str]
    readability_score: Optional[float]

class ValidationResult(BaseModel):
    """バリデーション結果"""
    index: int
    url: str
    status: str  # "valid", "fixed", "warning", "error"
    issues: list[dict]
    auto_fixes: list[str]
    quality_metrics: ContentQualityMetrics

def _compute_quality_metrics(self, content: str) -> ContentQualityMetrics:
    """コンテンツ品質メトリクスを計算"""
    words = content.split()
    sentences = re.split(r'[.!?。！？]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]

    return ContentQualityMetrics(
        word_count=len(words),
        sentence_count=len(sentences),
        avg_sentence_length=len(words) / max(len(sentences), 1),
        unique_word_ratio=len(set(words)) / max(len(words), 1),
        heading_count=content.count('\n#') + content.count('\n##'),
        has_lists=bool(re.search(r'^[-*•]\s', content, re.MULTILINE)),
        has_code_blocks='```' in content or '    ' in content,
        language_detected=self._detect_language(content),
        readability_score=None,  # 将来拡張
    )
```

#### 2.3 出力スキーマの定義

```python
class ValidatedCompetitor(BaseModel):
    """検証済み競合データ"""
    url: str
    title: str
    content: str
    content_hash: str  # 重複検出用
    word_count: int
    quality_score: float  # 0.0-1.0
    validation_status: str
    auto_fixes_applied: list[str]

class Step2Output(BaseModel):
    """Step2出力スキーマ"""
    step: str = "step2"
    is_valid: bool
    total_records: int
    valid_records: int
    rejected_records: int
    auto_fixed_count: int
    avg_quality_score: float
    validation_summary: dict[str, int]  # {"error": 2, "warning": 5, "ok": 8}
    validated_data: list[ValidatedCompetitor]
    rejected_data: list[dict]  # 拒否理由付き
    validation_issues: list[ValidationResult]
```

### 3. 中途開始機構の実装

#### 3.1 バッチ処理と進捗保存

```python
BATCH_SIZE = 10  # 10件ごとにチェックポイント

async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    # チェックポイントの復元
    checkpoint = await self._load_checkpoint(ctx, "validation_progress")

    if checkpoint:
        start_index = checkpoint["last_processed_index"] + 1
        validated_records = checkpoint["validated_records"]
        validation_issues = checkpoint["validation_issues"]
        activity.logger.info(f"Resuming from index {start_index}")
    else:
        start_index = 0
        validated_records = []
        validation_issues = []

    # バッチ処理
    for batch_start in range(start_index, len(competitors), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(competitors))
        batch = competitors[batch_start:batch_end]

        for idx, competitor in enumerate(batch, start=batch_start):
            fixed_record, fixes = self._auto_fix(competitor)
            issues = self._validate_record(fixed_record, idx)

            if self._has_critical_errors(issues):
                validation_issues.append({...})
            else:
                validated_records.append(fixed_record)

        # バッチ完了後にチェックポイント保存
        await self._save_checkpoint(ctx, "validation_progress", {
            "last_processed_index": batch_end - 1,
            "validated_records": validated_records,
            "validation_issues": validation_issues,
        })
        activity.logger.info(f"Checkpoint saved: {batch_end}/{len(competitors)}")

    return self._build_output(validated_records, validation_issues)
```

#### 3.2 Heartbeat による進捗報告

```python
async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
    total = len(competitors)

    for idx, competitor in enumerate(competitors):
        # Temporal Heartbeat で進捗を報告
        activity.heartbeat(f"Validating {idx + 1}/{total}")

        # ... バリデーション処理 ...

    return result
```

---

## 優先度と実装順序

| 優先度 | 改善項目 | 工数見積 | 理由 |
|--------|----------|----------|------|
| **高** | 自動修復機能 | 3h | データ品質向上 |
| **高** | エラー閾値設定 | 1h | 柔軟性向上 |
| **中** | 品質メトリクス | 2h | 可観測性向上 |
| **中** | 設定の外部化 | 2h | 運用性向上 |
| **低** | バッチ処理 | 2h | 大量データ対応 |
| **低** | Heartbeat | 30m | 進捗可視化 |

---

## テスト観点

1. **正常系**: 全件バリデーション通過
2. **自動修復**: 軽微な問題が自動修復される
3. **閾値**: エラー率超過で適切に失敗
4. **最小件数**: 有効件数不足で失敗
5. **チェックポイント**: 途中から再開できる
6. **メトリクス**: 品質スコアが正しく計算される
