# Batch 3: 収集・検証ステップ - ヘルパー統合

> **対象**: Step0（キーワード選択）、Step1（競合取得）、Step2（CSV検証）

---

## Step0: Keyword Selection

### 対象ファイル
- `apps/worker/activities/step0.py`

### 統合するヘルパー

```python
from apps.worker.helpers import (
    OutputParser,
    QualityValidator,
    ContentMetrics,
    QualityRetryLoop,
)
from apps.worker.helpers.quality_validator import (
    MinLengthValidator,
    KeywordPresenceValidator,
    CompositeValidator,
)

class Step0KeywordSelection(BaseActivity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.metrics = ContentMetrics()

        # 出力品質検証
        self.output_validator = CompositeValidator([
            MinLengthValidator(field="analysis", min_length=200, issue_code="analysis_too_short"),
        ])

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        # 入力検証（キーワードは必須）
        keyword = state.get("keyword", "")
        if not keyword or not keyword.strip():
            raise ActivityError(
                "Keyword is required",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # 品質リトライループ
        retry_loop = QualityRetryLoop(
            validator=self._validate_output_quality,
            max_retries=1,
        )

        result = await retry_loop.execute(
            generate_fn=self._generate,
            enhance_prompt_fn=self._enhance_prompt,
        )

        # 出力パース
        parse_result = self.parser.parse_json(result.content)

        if parse_result.success:
            data = parse_result.data
        else:
            # JSONパース失敗時はテキストとして保存
            data = {"raw_analysis": result.content}

        return self._structure_output(data, keyword)

    def _validate_output_quality(self, content: str) -> QualityResult:
        """出力品質をチェック"""
        required_elements = {
            "search_intent": ["検索意図", "intent", "目的"],
            "difficulty": ["難易度", "difficulty", "競合度"],
            "recommendation": ["推奨", "recommend", "提案"],
        }

        issues = []
        content_lower = content.lower()

        for element, keywords in required_elements.items():
            if not any(kw in content_lower for kw in keywords):
                issues.append(f"missing_{element}")

        # 長さチェック
        if len(content) < 200:
            issues.append("content_too_short")

        return QualityResult(
            is_acceptable=len(issues) <= 1,
            issues=issues,
        )
```

### 構造化出力スキーマ

```python
# apps/worker/activities/schemas/step0.py
from pydantic import BaseModel, Field
from typing import Literal

class Step0Output(BaseModel):
    keyword: str
    search_intent: str = ""
    difficulty_score: int = Field(default=5, ge=1, le=10)
    recommended_angles: list[str] = Field(default_factory=list)
    target_audience: str = ""
    content_type_suggestion: str = ""
    raw_analysis: str
```

---

## Step1: Competitor Fetch

### 対象ファイル
- `apps/worker/activities/step1.py`

### 統合するヘルパー

```python
from apps.worker.helpers import (
    InputValidator,
    QualityValidator,
    ContentMetrics,
    CheckpointManager,
)
from apps.worker.helpers.quality_validator import (
    MinCountValidator,
    CompositeValidator,
)

class Step1CompetitorFetch(BaseActivity):
    MIN_SUCCESSFUL_FETCHES = 3
    PAGE_FETCH_MAX_RETRIES = 2
    PAGE_FETCH_TIMEOUT = 30

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()

        # 収集結果の品質検証
        self.result_validator = CompositeValidator([
            MinCountValidator(field="competitors", min_count=3, issue_code="too_few_competitors"),
        ])

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        keyword = state.get("keyword", "")

        # SERP結果のチェックポイント
        serp_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "serp_completed"
        )

        if serp_checkpoint:
            urls = serp_checkpoint["urls"]
        else:
            # SERP取得
            serp_result = await self._fetch_serp(keyword, config)
            urls = serp_result.get("urls", [])

            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "serp_completed",
                {"urls": urls, "serp_data": serp_result}
            )

        # 部分収集のチェックポイント
        pages_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "pages_partial"
        )

        if pages_checkpoint:
            already_fetched = set(pages_checkpoint.get("fetched_urls", []))
            partial_results = pages_checkpoint.get("results", [])
        else:
            already_fetched = set()
            partial_results = []

        # 残りを取得
        remaining_urls = [u for u in urls if u not in already_fetched]

        if remaining_urls:
            new_results = await self._fetch_pages_parallel(remaining_urls, page_fetch_tool)

            # 部分結果を更新保存
            all_results = partial_results + new_results
            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "pages_partial",
                {
                    "fetched_urls": list(already_fetched | set(remaining_urls)),
                    "results": all_results,
                }
            )
        else:
            all_results = partial_results

        # 成功率チェック
        success_count = len([r for r in all_results if r.get("success")])

        if success_count < self.MIN_SUCCESSFUL_FETCHES:
            raise ActivityError(
                f"Insufficient data: only {success_count} pages fetched "
                f"(minimum: {self.MIN_SUCCESSFUL_FETCHES})",
                category=ErrorCategory.RETRYABLE,
            )

        return self._structure_output(all_results, keyword)

    async def _fetch_page_with_retry(
        self,
        page_fetch_tool,
        url: str,
    ) -> tuple[dict | None, str | None]:
        """個別ページを最大2回リトライで取得"""
        last_error = None

        for attempt in range(self.PAGE_FETCH_MAX_RETRIES):
            try:
                fetch_result = await asyncio.wait_for(
                    page_fetch_tool.execute(url=url),
                    timeout=self.PAGE_FETCH_TIMEOUT,
                )

                if fetch_result.success and fetch_result.data:
                    content = fetch_result.data.get("body_text", "")

                    # コンテンツ品質チェック
                    if self._is_valid_content(content):
                        return self._extract_page_data(fetch_result.data, url), None

                    last_error = "invalid_content"
                else:
                    last_error = fetch_result.error_message

            except asyncio.TimeoutError:
                last_error = f"timeout_{self.PAGE_FETCH_TIMEOUT}s"
            except Exception as e:
                last_error = str(e)

            if attempt < self.PAGE_FETCH_MAX_RETRIES - 1:
                await asyncio.sleep(1 * (attempt + 1))

        return None, last_error

    def _is_valid_content(self, content: str) -> bool:
        """コンテンツが有効かチェック"""
        if not content or len(content) < 100:
            return False

        # エラーページの検出
        error_indicators = [
            "404", "403", "access denied", "not found",
            "cloudflare", "captcha", "robot check",
        ]
        content_lower = content.lower()
        for indicator in error_indicators:
            if indicator in content_lower and len(content) < 500:
                return False

        return True
```

### 構造化出力スキーマ

```python
# apps/worker/activities/schemas/step1.py
from pydantic import BaseModel, Field
from datetime import datetime

class CompetitorPage(BaseModel):
    url: str
    title: str
    content: str = Field(..., max_length=15000)
    word_count: int = 0
    headings: list[str] = Field(default_factory=list)
    fetched_at: datetime

class FetchStats(BaseModel):
    total_urls: int
    successful: int
    failed: int
    success_rate: float

class Step1Output(BaseModel):
    keyword: str
    serp_query: str
    competitors: list[CompetitorPage]
    failed_urls: list[dict]
    fetch_stats: FetchStats
```

---

## Step2: CSV Validation

### 対象ファイル
- `apps/worker/activities/step2.py`

### 統合するヘルパー

```python
from apps.worker.helpers import (
    InputValidator,
    QualityValidator,
    ContentMetrics,
    CheckpointManager,
)
from apps.worker.helpers.quality_validator import (
    MinCountValidator,
    CompositeValidator,
)
from apps.worker.helpers.schemas import QualityResult

class Step2CSVValidation(BaseActivity):
    MAX_ERROR_RATE = 0.3
    MIN_VALID_RECORDS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()

        self.input_validator = InputValidator(
            required_fields=["step1.competitors"],
        )

    async def execute(self, ctx: ExecutionContext, state: GraphState) -> dict[str, Any]:
        step1_data = await load_step_data(...) or {}

        # 入力検証
        validation = self.input_validator.validate({"step1": step1_data})

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        competitors = step1_data.get("competitors", [])

        # バッチ処理チェックポイント
        progress_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "validation_progress"
        )

        if progress_checkpoint:
            start_index = progress_checkpoint["last_processed_index"] + 1
            validated_records = progress_checkpoint["validated_records"]
            validation_issues = progress_checkpoint["validation_issues"]
        else:
            start_index = 0
            validated_records = []
            validation_issues = []

        # バッチ処理
        BATCH_SIZE = 10
        for batch_start in range(start_index, len(competitors), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(competitors))
            batch = competitors[batch_start:batch_end]

            for idx, competitor in enumerate(batch, start=batch_start):
                # 自動修復
                fixed_record, fixes = self._auto_fix(competitor)

                if fixes:
                    activity.logger.info(f"Auto-fixed record {idx}: {fixes}")

                # 修復後のバリデーション
                issues = self._validate_record(fixed_record, idx)

                if self._has_critical_errors(issues):
                    validation_issues.append({
                        "index": idx,
                        "url": competitor.get("url", "unknown"),
                        "issues": issues,
                    })
                else:
                    validated_records.append(fixed_record)

            # バッチ完了後にチェックポイント保存
            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "validation_progress",
                {
                    "last_processed_index": batch_end - 1,
                    "validated_records": validated_records,
                    "validation_issues": validation_issues,
                }
            )

            activity.heartbeat(f"Validated {batch_end}/{len(competitors)}")

        # 閾値チェック
        error_rate = 1 - (len(validated_records) / max(len(competitors), 1))

        if len(validated_records) < self.MIN_VALID_RECORDS:
            raise ActivityError(
                f"Too few valid records: {len(validated_records)}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if error_rate > self.MAX_ERROR_RATE:
            raise ActivityError(
                f"Error rate too high: {error_rate:.1%}",
                category=ErrorCategory.RETRYABLE,
            )

        return self._structure_output(validated_records, validation_issues)

    def _auto_fix(self, record: dict) -> tuple[dict, list[str]]:
        """レコードの自動修復"""
        fixed = record.copy()
        fixes = []

        # URL正規化
        if "url" in fixed:
            original_url = fixed["url"]
            fixed["url"] = self._normalize_url(original_url)
            if fixed["url"] != original_url:
                fixes.append("url_normalized")

        # コンテンツ正規化
        if "content" in fixed:
            original_len = len(fixed["content"])
            fixed["content"] = self._normalize_content(fixed["content"])
            if len(fixed["content"]) != original_len:
                fixes.append(f"content_normalized")

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
        import re
        # 連続空白を単一スペースに
        content = re.sub(r'[ \t]+', ' ', content)
        # 連続改行を2つまでに
        content = re.sub(r'\n{3,}', '\n\n', content)
        # 制御文字除去
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', content)
        return content.strip()
```

### 構造化出力スキーマ

```python
# apps/worker/activities/schemas/step2.py
from pydantic import BaseModel, Field

class ValidatedCompetitor(BaseModel):
    url: str
    title: str
    content: str
    content_hash: str
    word_count: int
    quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    auto_fixes_applied: list[str] = Field(default_factory=list)

class ValidationSummary(BaseModel):
    total_records: int
    valid_records: int
    rejected_records: int
    auto_fixed_count: int
    error_rate: float

class Step2Output(BaseModel):
    is_valid: bool
    validation_summary: ValidationSummary
    validated_data: list[ValidatedCompetitor]
    rejected_data: list[dict]
    validation_issues: list[dict]
```

---

## 完了条件

### Step0
- [ ] OutputParser 統合
- [ ] QualityRetryLoop 統合
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過

### Step1
- [ ] CheckpointManager 統合（SERP、ページ取得）
- [ ] 個別ページリトライ実装
- [ ] コンテンツ品質チェック
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過

### Step2
- [ ] InputValidator 統合
- [ ] CheckpointManager 統合（バッチ処理）
- [ ] 自動修復機能実装
- [ ] 閾値チェック実装
- [ ] 構造化出力スキーマ追加
- [ ] テスト追加・通過
