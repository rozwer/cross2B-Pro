# 共通ヘルパー設計書

> Step改善案から抽出した共通パターンをヘルパーとして設計

## 概要

15のステップ改善ドキュメントを分析した結果、以下の**7つの共通ヘルパー**を特定しました。

| ヘルパー | 説明 | 対象ステップ |
|---------|------|-------------|
| `OutputParser` | JSON/Markdown パース・整形 | 全ステップ |
| `InputValidator` | 入力データ品質チェック | Step3-10 |
| `QualityValidator` | 出力品質検証 | 全ステップ |
| `ContentMetrics` | コンテンツメトリクス計算 | Step2,3b,7a-10 |
| `CheckpointManager` | チェックポイント管理 | 全ステップ |
| `QualityRetryLoop` | 品質ループ制御 | Step0,3a-c,4,7a,10 |
| Shared Schemas | 共通Pydanticモデル | 全ステップ |

---

## 1. OutputParser

### 目的
LLM出力のJSON/Markdownパースを堅牢化する。

### 背景
- 全ステップでJSONコードブロック除去が必要
- 長文生成（Step6.5, 7a, 8）でJSON形式が崩れやすい
- 決定的な修正（末尾カンマ除去等）は許容

### インターフェース

```python
# apps/worker/helpers/output_parser.py

from typing import Any
import json
import re
from pydantic import BaseModel

class ParseResult(BaseModel):
    """パース結果"""
    success: bool
    data: dict[str, Any] | None = None
    raw: str = ""
    format_detected: str = ""  # "json", "markdown", "unknown"
    fixes_applied: list[str] = []


class OutputParser:
    """LLM出力のパーサー"""

    def parse_json(self, content: str) -> ParseResult:
        """JSONをパース（コードブロック対応）"""
        content = content.strip()
        fixes = []

        # 1. コードブロック除去
        extracted = self._extract_json_block(content)
        if extracted != content:
            fixes.append("code_block_removed")
        content = extracted

        # 2. JSONパース試行
        try:
            data = json.loads(content)
            return ParseResult(
                success=True,
                data=data,
                raw=content,
                format_detected="json",
                fixes_applied=fixes,
            )
        except json.JSONDecodeError:
            pass

        # 3. 決定的修正を試みる
        fixed, fix_names = self._apply_deterministic_fixes(content)
        if fixed:
            fixes.extend(fix_names)
            try:
                data = json.loads(fixed)
                return ParseResult(
                    success=True,
                    data=data,
                    raw=fixed,
                    format_detected="json",
                    fixes_applied=fixes,
                )
            except json.JSONDecodeError:
                pass

        return ParseResult(
            success=False,
            raw=content,
            format_detected="unknown",
            fixes_applied=fixes,
        )

    def _extract_json_block(self, content: str) -> str:
        """JSONコードブロックを抽出"""
        # ```json ... ``` パターン
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()

        # ``` ... ``` パターン
        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                extracted = content[start:end].strip()
                # JSONらしければ返す
                if extracted.startswith("{") or extracted.startswith("["):
                    return extracted

        # コードブロックなし、そのまま返す
        return content

    def _apply_deterministic_fixes(
        self,
        content: str,
    ) -> tuple[str | None, list[str]]:
        """決定的な修正を適用（ログ必須）"""
        fixes = []
        fixed = content

        # 末尾カンマ除去
        new_fixed = re.sub(r',\s*}', '}', fixed)
        new_fixed = re.sub(r',\s*]', ']', new_fixed)
        if new_fixed != fixed:
            fixes.append("trailing_comma_removed")
            fixed = new_fixed

        # 修正があった場合のみ返す
        if fixes:
            return fixed, fixes

        return None, []

    def looks_like_markdown(self, content: str) -> bool:
        """Markdown形式かどうか判定"""
        md_indicators = [
            r'^#\s',       # H1
            r'^##\s',      # H2
            r'^###\s',     # H3
            r'^\*\s',      # リスト
            r'^\-\s',      # リスト
            r'^\d+\.\s',   # 番号付きリスト
        ]
        return any(re.search(p, content, re.M) for p in md_indicators)

    def looks_like_json(self, content: str) -> bool:
        """JSON形式かどうか判定"""
        stripped = content.strip()
        return (
            (stripped.startswith("{") and stripped.endswith("}")) or
            (stripped.startswith("[") and stripped.endswith("]"))
        )
```

### 使用例

```python
from apps.worker.helpers import OutputParser

parser = OutputParser()

# JSONパース
result = parser.parse_json(llm_response.content)
if result.success:
    data = result.data
    if result.fixes_applied:
        activity.logger.info(f"JSON fixes applied: {result.fixes_applied}")
else:
    # Markdownとして扱う判断
    if parser.looks_like_markdown(llm_response.content):
        activity.logger.info("Treating as markdown")
        # ... markdown処理 ...
    else:
        raise ActivityError("Failed to parse LLM output", ...)
```

---

## 2. InputValidator

### 目的
前ステップのデータ品質を検証し、早期にエラーを検出する。

### 背景
- Step4以降で前ステップデータの欠落が問題
- 必須 vs 推奨の区別が必要
- 最低件数/最低文字数のチェックが共通

### インターフェース

```python
# apps/worker/helpers/input_validator.py

from pydantic import BaseModel

class InputValidationResult(BaseModel):
    """入力検証結果"""
    is_valid: bool
    missing_required: list[str] = []
    missing_recommended: list[str] = []
    quality_issues: list[str] = []


class InputValidator:
    """入力データの検証"""

    def validate(
        self,
        data: dict,
        required: list[str] | None = None,
        recommended: list[str] | None = None,
        min_lengths: dict[str, int] | None = None,
        min_counts: dict[str, int] | None = None,
    ) -> InputValidationResult:
        """入力データを検証"""
        missing_required = []
        missing_recommended = []
        quality_issues = []

        # 必須フィールドチェック
        for field in (required or []):
            if not self._get_nested(data, field):
                missing_required.append(field)

        # 推奨フィールドチェック
        for field in (recommended or []):
            if not self._get_nested(data, field):
                missing_recommended.append(field)

        # 最低文字数チェック
        for field, min_len in (min_lengths or {}).items():
            value = self._get_nested(data, field)
            if isinstance(value, str) and len(value) < min_len:
                quality_issues.append(
                    f"{field}_too_short: {len(value)} < {min_len}"
                )

        # 最低件数チェック
        for field, min_count in (min_counts or {}).items():
            value = self._get_nested(data, field)
            if isinstance(value, list) and len(value) < min_count:
                quality_issues.append(
                    f"{field}_count_low: {len(value)} < {min_count}"
                )

        is_valid = len(missing_required) == 0
        return InputValidationResult(
            is_valid=is_valid,
            missing_required=missing_required,
            missing_recommended=missing_recommended,
            quality_issues=quality_issues,
        )

    def _get_nested(self, data: dict, path: str) -> Any:
        """ネストしたフィールドを取得（dot notation対応）"""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
```

### 使用例

```python
from apps.worker.helpers import InputValidator

validator = InputValidator()

# Step4での検証
result = validator.validate(
    data={
        "step3a": step3a_data,
        "step3b": step3b_data,
        "step3c": step3c_data,
    },
    required=["step3a.query_analysis", "step3b.cooccurrence_analysis"],
    recommended=["step3c.competitor_analysis"],
    min_lengths={"step3a.query_analysis": 100},
)

if not result.is_valid:
    raise ActivityError(
        f"Required inputs missing: {result.missing_required}",
        category=ErrorCategory.NON_RETRYABLE,
    )

if result.missing_recommended:
    activity.logger.warning(f"Recommended missing: {result.missing_recommended}")
```

---

## 3. QualityValidator

### 目的
LLM出力の品質を統一的に検証する。

### 背景
- 各ステップで「必須要素の存在チェック」が必要
- 出力の完全性（切れていないか）チェックが必要
- 構造的な品質（セクション数、見出し階層等）チェックが必要

### インターフェース

```python
# apps/worker/helpers/quality_validator.py

from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Protocol


class QualityResult(BaseModel):
    """品質検証結果"""
    is_acceptable: bool
    issues: list[str] = []
    warnings: list[str] = []
    scores: dict[str, float] = {}  # 任意のスコア


class QualityValidator(Protocol):
    """品質検証のプロトコル"""

    def validate(self, content: str, **kwargs) -> QualityResult:
        """コンテンツを検証"""
        ...


class RequiredElementsValidator:
    """必須要素の存在チェック"""

    def __init__(
        self,
        required_patterns: dict[str, list[str]],
        max_missing: int = 0,
    ):
        """
        Args:
            required_patterns: {element_name: [keyword_patterns]}
            max_missing: 許容する欠落数
        """
        self.required_patterns = required_patterns
        self.max_missing = max_missing

    def validate(self, content: str, **kwargs) -> QualityResult:
        """必須要素の存在をチェック"""
        content_lower = content.lower()
        missing = []

        for element, patterns in self.required_patterns.items():
            found = any(p.lower() in content_lower for p in patterns)
            if not found:
                missing.append(element)

        return QualityResult(
            is_acceptable=len(missing) <= self.max_missing,
            issues=[f"missing_{e}" for e in missing],
        )


class StructureValidator:
    """構造的な品質チェック"""

    def __init__(
        self,
        min_h2_sections: int = 3,
        require_h3: bool = False,
        min_word_count: int = 0,
    ):
        self.min_h2_sections = min_h2_sections
        self.require_h3 = require_h3
        self.min_word_count = min_word_count

    def validate(self, content: str, **kwargs) -> QualityResult:
        """構造をチェック"""
        import re
        issues = []
        warnings = []

        # H2セクション数
        h2_count = len(re.findall(r'^##\s', content, re.M))
        if h2_count < self.min_h2_sections:
            issues.append(f"h2_count_low: {h2_count} < {self.min_h2_sections}")

        # H3の存在
        if self.require_h3:
            h3_count = len(re.findall(r'^###\s', content, re.M))
            if h3_count == 0:
                warnings.append("no_h3_subsections")

        # 単語数
        word_count = len(content.split())
        if self.min_word_count > 0 and word_count < self.min_word_count:
            issues.append(f"word_count_low: {word_count} < {self.min_word_count}")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores={"h2_count": h2_count, "word_count": word_count},
        )


class CompletenessValidator:
    """完全性チェック（切れていないか）"""

    def __init__(
        self,
        conclusion_patterns: list[str] | None = None,
    ):
        self.conclusion_patterns = conclusion_patterns or [
            "まとめ", "結論", "おわり", "conclusion",
        ]

    def validate(self, content: str, **kwargs) -> QualityResult:
        """完全性をチェック"""
        issues = []
        content_lower = content.lower()

        # 結論セクションの存在
        has_conclusion = any(
            p in content_lower for p in self.conclusion_patterns
        )
        if not has_conclusion:
            issues.append("no_conclusion_section")

        # 文末チェック（切れている兆候）
        content_stripped = content.rstrip()
        if content_stripped.endswith(("...", "…", "、")):
            issues.append("appears_truncated")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
        )


class CompositeValidator:
    """複数のバリデータを組み合わせる"""

    def __init__(self, validators: list[QualityValidator]):
        self.validators = validators

    def validate(self, content: str, **kwargs) -> QualityResult:
        """全バリデータを実行して統合"""
        all_issues = []
        all_warnings = []
        all_scores = {}

        for validator in self.validators:
            result = validator.validate(content, **kwargs)
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
            all_scores.update(result.scores)

        return QualityResult(
            is_acceptable=len(all_issues) == 0,
            issues=all_issues,
            warnings=all_warnings,
            scores=all_scores,
        )
```

### 使用例

```python
from apps.worker.helpers import (
    RequiredElementsValidator,
    StructureValidator,
    CompletenessValidator,
    CompositeValidator,
)

# Step4用のバリデータ
step4_validator = CompositeValidator([
    RequiredElementsValidator(
        required_patterns={
            "keyword": [keyword],  # キーワードが含まれているか
        },
        max_missing=0,
    ),
    StructureValidator(
        min_h2_sections=3,
        require_h3=True,
    ),
])

result = step4_validator.validate(outline_content, keyword=keyword)
if not result.is_acceptable:
    activity.logger.warning(f"Quality issues: {result.issues}")
```

---

## 4. ContentMetrics

### 目的
コンテンツのメトリクスを統一的に計算する。

### 背景
- 日本語対応の単語数カウントが必要
- セクション数、見出し階層のカウントが共通
- キーワード密度計算が複数ステップで必要

### インターフェース

```python
# apps/worker/helpers/content_metrics.py

from pydantic import BaseModel
import re


class TextMetrics(BaseModel):
    """テキストメトリクス"""
    char_count: int
    word_count: int
    paragraph_count: int
    sentence_count: int


class MarkdownMetrics(BaseModel):
    """Markdownメトリクス"""
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    h4_count: int = 0
    list_count: int = 0
    code_block_count: int = 0
    link_count: int = 0
    image_count: int = 0


class ContentMetrics:
    """コンテンツメトリクス計算"""

    def text_metrics(self, text: str, lang: str = "ja") -> TextMetrics:
        """テキストメトリクスを計算"""
        # 文字数
        char_count = len(text)

        # 単語数（日本語対応）
        if lang == "ja":
            # 日本語文字数 + 英単語数
            ja_chars = len(re.findall(
                r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text
            ))
            en_words = len(re.findall(r'[a-zA-Z]+', text))
            word_count = ja_chars + en_words
        else:
            word_count = len(text.split())

        # 段落数
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)

        # 文数
        sentences = re.split(r'[.!?。！？]+', text)
        sentence_count = len([s for s in sentences if s.strip()])

        return TextMetrics(
            char_count=char_count,
            word_count=word_count,
            paragraph_count=paragraph_count,
            sentence_count=sentence_count,
        )

    def markdown_metrics(self, content: str) -> MarkdownMetrics:
        """Markdownメトリクスを計算"""
        return MarkdownMetrics(
            h1_count=len(re.findall(r'^#\s', content, re.M)),
            h2_count=len(re.findall(r'^##\s', content, re.M)),
            h3_count=len(re.findall(r'^###\s', content, re.M)),
            h4_count=len(re.findall(r'^####\s', content, re.M)),
            list_count=len(re.findall(r'^[\-\*]\s', content, re.M)),
            code_block_count=len(re.findall(r'```', content)) // 2,
            link_count=len(re.findall(r'\[([^\]]+)\]\([^\)]+\)', content)),
            image_count=len(re.findall(r'!\[', content)),
        )

    def keyword_density(
        self,
        text: str,
        keyword: str,
        lang: str = "ja",
    ) -> float:
        """キーワード密度を計算（%）"""
        text_lower = text.lower()
        keyword_lower = keyword.lower()

        keyword_count = text_lower.count(keyword_lower)
        text_metrics = self.text_metrics(text, lang)

        if text_metrics.word_count == 0:
            return 0.0

        return (keyword_count / text_metrics.word_count) * 100

    def compare_content(
        self,
        original: str,
        modified: str,
        lang: str = "ja",
    ) -> dict[str, float]:
        """2つのコンテンツを比較"""
        orig_metrics = self.text_metrics(original, lang)
        mod_metrics = self.text_metrics(modified, lang)

        word_diff = mod_metrics.word_count - orig_metrics.word_count
        word_ratio = mod_metrics.word_count / max(orig_metrics.word_count, 1)

        orig_md = self.markdown_metrics(original)
        mod_md = self.markdown_metrics(modified)

        return {
            "word_diff": word_diff,
            "word_ratio": word_ratio,
            "h2_diff": mod_md.h2_count - orig_md.h2_count,
            "h3_diff": mod_md.h3_count - orig_md.h3_count,
        }
```

### 使用例

```python
from apps.worker.helpers import ContentMetrics

metrics = ContentMetrics()

# テキストメトリクス
text_m = metrics.text_metrics(draft_content)
activity.logger.info(f"Word count: {text_m.word_count}")

# Markdownメトリクス
md_m = metrics.markdown_metrics(draft_content)
activity.logger.info(f"H2 sections: {md_m.h2_count}")

# キーワード密度
density = metrics.keyword_density(draft_content, keyword)
if density > 3.0:
    activity.logger.warning(f"Keyword density too high: {density:.1f}%")

# 変更比較（Step7b, Step9）
comparison = metrics.compare_content(original, polished)
if comparison["word_ratio"] < 0.7:
    activity.logger.warning("Content significantly reduced")
```

---

## 5. CheckpointManager

### 目的
Activity内のチェックポイントを統一的に管理する。

### 背景
- 複数ステップでチェックポイント保存/ロードが必要
- storage APIの呼び出しパターンが共通
- 失敗時の部分結果保存が重要

### インターフェース

```python
# apps/worker/helpers/checkpoint_manager.py

from typing import Any
from datetime import datetime
import json
import hashlib
from pydantic import BaseModel

from apps.worker.storage import ArtifactStore


class CheckpointMetadata(BaseModel):
    """チェックポイントメタデータ"""
    phase: str
    created_at: datetime
    input_digest: str | None = None


class CheckpointManager:
    """Activity内チェックポイント管理"""

    def __init__(self, store: ArtifactStore):
        self.store = store

    async def save(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
        data: dict[str, Any],
        input_digest: str | None = None,
    ) -> str:
        """チェックポイントを保存"""
        path = self._build_path(tenant_id, run_id, step_id, phase)

        checkpoint = {
            "_metadata": {
                "phase": phase,
                "created_at": datetime.utcnow().isoformat(),
                "input_digest": input_digest,
            },
            "data": data,
        }

        content = json.dumps(checkpoint, ensure_ascii=False, default=str)
        await self.store.put(
            content.encode("utf-8"),
            path,
            content_type="application/json",
        )
        return path

    async def load(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
        input_digest: str | None = None,
    ) -> dict[str, Any] | None:
        """チェックポイントをロード"""
        path = self._build_path(tenant_id, run_id, step_id, phase)

        try:
            content_bytes = await self.store.get_raw(path)
            if not content_bytes:
                return None

            checkpoint = json.loads(content_bytes.decode("utf-8"))

            # input_digestが指定されていて一致しない場合は無効
            if input_digest:
                stored_digest = checkpoint.get("_metadata", {}).get("input_digest")
                if stored_digest and stored_digest != input_digest:
                    return None

            return checkpoint.get("data")

        except Exception:
            return None

    async def clear(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
    ) -> None:
        """ステップのチェックポイントをクリア"""
        # 実装はstoreのAPIに依存
        pass

    def _build_path(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
    ) -> str:
        """チェックポイントパスを構築"""
        return f"{tenant_id}/{run_id}/{step_id}/checkpoint/{phase}.json"
```

### 使用例

```python
from apps.worker.helpers import CheckpointManager

checkpoint_mgr = CheckpointManager(self.store)

# ロード試行
cached = await checkpoint_mgr.load(
    ctx.tenant_id, ctx.run_id, self.step_id, "queries_generated",
    input_digest=input_digest,
)

if cached:
    search_queries = cached["queries"]
else:
    # 処理実行
    search_queries = await self._generate_queries(...)

    # 保存
    await checkpoint_mgr.save(
        ctx.tenant_id, ctx.run_id, self.step_id, "queries_generated",
        data={"queries": search_queries},
        input_digest=input_digest,
    )
```

---

## 6. QualityRetryLoop

### 目的
品質チェック付きリトライを統一的に実行する。

### 背景
- 複数ステップで「LLM呼び出し → 品質チェック → 必要ならリトライ」のパターン
- リトライ時のプロンプト補強が共通

### インターフェース

```python
# apps/worker/helpers/quality_retry_loop.py

from typing import Callable, Any, Awaitable, TypeVar
from temporalio import activity
from pydantic import BaseModel

from apps.worker.helpers.quality_validator import QualityResult, QualityValidator

T = TypeVar("T")


class RetryLoopResult(BaseModel):
    """リトライループの結果"""
    success: bool
    result: Any | None = None
    quality: QualityResult | None = None
    attempts: int = 0
    final_prompt: str | None = None


class QualityRetryLoop:
    """品質チェック付きリトライループ"""

    def __init__(
        self,
        max_retries: int = 1,
        accept_on_final: bool = True,  # 最終試行は品質不足でも受け入れる
    ):
        self.max_retries = max_retries
        self.accept_on_final = accept_on_final

    async def execute(
        self,
        llm_call: Callable[[str], Awaitable[T]],
        initial_prompt: str,
        validator: QualityValidator,
        enhance_prompt: Callable[[str, list[str]], str] | None = None,
        extract_content: Callable[[T], str] | None = None,
    ) -> RetryLoopResult:
        """
        品質チェック付きでLLM呼び出しを実行

        Args:
            llm_call: LLM呼び出し関数（プロンプトを受け取る）
            initial_prompt: 初期プロンプト
            validator: 品質検証器
            enhance_prompt: 品質問題に基づいてプロンプトを改善する関数
            extract_content: LLM結果からコンテンツを抽出する関数
        """
        prompt = initial_prompt
        last_result = None
        last_quality = None

        for attempt in range(self.max_retries + 1):
            # LLM呼び出し
            result = await llm_call(prompt)
            last_result = result

            # コンテンツ抽出
            if extract_content:
                content = extract_content(result)
            else:
                content = str(result)

            # 品質チェック
            quality = validator.validate(content)
            last_quality = quality

            if quality.is_acceptable:
                return RetryLoopResult(
                    success=True,
                    result=result,
                    quality=quality,
                    attempts=attempt + 1,
                    final_prompt=prompt,
                )

            # リトライ可能か
            if attempt < self.max_retries:
                if enhance_prompt:
                    prompt = enhance_prompt(prompt, quality.issues)
                    activity.logger.warning(
                        f"Quality retry {attempt + 1}: {quality.issues}"
                    )
                else:
                    activity.logger.warning(
                        f"Quality issues but no enhance_prompt: {quality.issues}"
                    )

        # 最終試行
        if self.accept_on_final:
            activity.logger.warning(
                f"Accepting sub-optimal quality: {last_quality.issues}"
            )
            return RetryLoopResult(
                success=True,
                result=last_result,
                quality=last_quality,
                attempts=self.max_retries + 1,
                final_prompt=prompt,
            )

        return RetryLoopResult(
            success=False,
            result=last_result,
            quality=last_quality,
            attempts=self.max_retries + 1,
            final_prompt=prompt,
        )
```

### 使用例

```python
from apps.worker.helpers import QualityRetryLoop, StructureValidator

retry_loop = QualityRetryLoop(max_retries=1)

def enhance_outline_prompt(prompt: str, issues: list[str]) -> str:
    """品質問題に基づいてプロンプトを補強"""
    additions = []
    if "h2_count_low" in str(issues):
        additions.append("- 必ず3つ以上のH2セクションを含めてください")
    if "no_h3_subsections" in str(issues):
        additions.append("- 各H2セクションにH3サブセクションを追加してください")

    if additions:
        return prompt + "\n\n追加指示:\n" + "\n".join(additions)
    return prompt

result = await retry_loop.execute(
    llm_call=lambda p: llm.generate(messages=[{"role": "user", "content": p}]),
    initial_prompt=outline_prompt,
    validator=StructureValidator(min_h2_sections=3, require_h3=True),
    enhance_prompt=enhance_outline_prompt,
    extract_content=lambda r: r.content,
)

if result.success:
    outline = result.result.content
    if result.attempts > 1:
        activity.logger.info(f"Required {result.attempts} attempts")
else:
    raise ActivityError("Outline generation failed quality check", ...)
```

---

## 7. Shared Schemas

### 目的
全ステップで共通して使える型定義を提供する。

```python
# apps/worker/helpers/schemas.py

from pydantic import BaseModel, Field
from typing import Literal, Any
from datetime import datetime


# === 品質関連 ===

class QualityResult(BaseModel):
    """品質検証結果"""
    is_acceptable: bool
    issues: list[str] = []
    warnings: list[str] = []
    scores: dict[str, float] = {}


class InputValidationResult(BaseModel):
    """入力検証結果"""
    is_valid: bool
    missing_required: list[str] = []
    missing_recommended: list[str] = []
    quality_issues: list[str] = []


class CompletenessResult(BaseModel):
    """完全性チェック結果"""
    is_complete: bool
    is_truncated: bool = False
    issues: list[str] = []


# === パース関連 ===

class ParseResult(BaseModel):
    """パース結果"""
    success: bool
    data: dict[str, Any] | None = None
    raw: str = ""
    format_detected: str = ""
    fixes_applied: list[str] = []


# === メトリクス関連 ===

class TextMetrics(BaseModel):
    """テキストメトリクス"""
    char_count: int
    word_count: int
    paragraph_count: int
    sentence_count: int


class MarkdownMetrics(BaseModel):
    """Markdownメトリクス"""
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    h4_count: int = 0
    list_count: int = 0
    code_block_count: int = 0
    link_count: int = 0
    image_count: int = 0


# === チェックポイント関連 ===

class CheckpointMetadata(BaseModel):
    """チェックポイントメタデータ"""
    phase: str
    created_at: datetime
    input_digest: str | None = None
    step_id: str = ""


# === Activity出力の共通フィールド ===

class StepOutputBase(BaseModel):
    """ステップ出力の基底クラス"""
    step: str
    keyword: str
    execution_time_ms: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
```

---

## 実装優先度

| 優先度 | ヘルパー | 理由 | 工数見積 |
|--------|---------|------|----------|
| **最高** | `OutputParser` | 全ステップのJSONパースに必須 | 2h |
| **最高** | `InputValidator` | 入力品質保証の基盤 | 2h |
| **最高** | Shared Schemas | 型定義の統一 | 1h |
| **高** | `QualityValidator` | 出力品質検証の統一 | 3h |
| **高** | `ContentMetrics` | メトリクス計算の統一 | 2h |
| **中** | `CheckpointManager` | 再実行効率化 | 2h |
| **中** | `QualityRetryLoop` | 品質ループの統一 | 2h |

**合計工数見積: 14h**

---

## ファイル構成

```
apps/worker/helpers/
├── __init__.py
├── output_parser.py      # OutputParser
├── input_validator.py    # InputValidator
├── quality_validator.py  # QualityValidator + 派生クラス
├── content_metrics.py    # ContentMetrics
├── checkpoint_manager.py # CheckpointManager
├── quality_retry_loop.py # QualityRetryLoop
└── schemas.py            # Shared Schemas
```

---

## 次のステップ

1. **Phase 1**: `OutputParser`, `InputValidator`, `Shared Schemas` を実装
2. **Phase 2**: `QualityValidator`, `ContentMetrics` を実装
3. **Phase 3**: `CheckpointManager`, `QualityRetryLoop` を実装
4. **Phase 4**: 各ステップを共通ヘルパーを使って書き換え
