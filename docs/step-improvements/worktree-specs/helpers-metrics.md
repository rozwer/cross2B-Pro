# Worktree: helpers-metrics 要件定義書

> **ブランチ名**: `feat/helpers-metrics`
> **担当**: ContentMetrics + CheckpointManager + QualityRetryLoop
> **優先度**: 高/中（メトリクス・効率化・品質ループ）

---

## 目的

コンテンツのメトリクス計算、チェックポイント管理、品質リトライループの共通ヘルパーを実装する。
Step7a-10の長文処理と再実行効率化に特に重要。

---

## 成果物

### ファイル構成

```
apps/worker/helpers/
├── content_metrics.py    # ContentMetrics クラス
├── checkpoint_manager.py # CheckpointManager クラス
├── quality_retry_loop.py # QualityRetryLoop クラス
tests/unit/helpers/
├── test_content_metrics.py
├── test_checkpoint_manager.py
├── test_quality_retry_loop.py
```

---

## 前提条件

**`helpers-parsing` worktree で以下が実装済みであること:**
- `schemas.py` の `TextMetrics`, `MarkdownMetrics`, `CheckpointMetadata`

**`helpers-validation` worktree で以下が実装済みであること:**
- `quality_validator.py` の `QualityValidator` プロトコル, `QualityResult`

```python
# インポート例
from apps.worker.helpers.schemas import TextMetrics, MarkdownMetrics, CheckpointMetadata
from apps.worker.helpers.quality_validator import QualityValidator, QualityResult
```

---

## 1. ContentMetrics (`content_metrics.py`)

### 1.1 クラス定義

```python
import re
from apps.worker.helpers.schemas import TextMetrics, MarkdownMetrics


class ContentMetrics:
    """コンテンツメトリクス計算"""

    def text_metrics(self, text: str, lang: str = "ja") -> TextMetrics:
        """
        テキストメトリクスを計算

        Args:
            text: 対象テキスト
            lang: 言語（"ja" で日本語対応）

        Returns:
            TextMetrics: 文字数、単語数、段落数、文数

        日本語対応:
            - 日本語文字（ひらがな、カタカナ、漢字）は1文字=1単語としてカウント
            - 英単語は通常通りカウント
            - 合計を word_count とする
        """

    def markdown_metrics(self, content: str) -> MarkdownMetrics:
        """
        Markdownメトリクスを計算

        Returns:
            MarkdownMetrics: 見出し数、リスト数、コードブロック数、リンク数、画像数

        パターン:
            - H1: ^#\s
            - H2: ^##\s
            - H3: ^###\s
            - H4: ^####\s
            - リスト: ^[\-\*]\s
            - コードブロック: ``` のペア
            - リンク: \[text\](url)
            - 画像: !\[
        """

    def keyword_density(
        self,
        text: str,
        keyword: str,
        lang: str = "ja",
    ) -> float:
        """
        キーワード密度を計算（%）

        Args:
            text: 対象テキスト
            keyword: 検索キーワード
            lang: 言語

        Returns:
            float: キーワード密度（0.0〜100.0）

        計算式:
            (キーワード出現回数 / 総単語数) * 100
        """

    def compare_content(
        self,
        original: str,
        modified: str,
        lang: str = "ja",
    ) -> dict[str, float]:
        """
        2つのコンテンツを比較

        Args:
            original: 元のコンテンツ
            modified: 変更後のコンテンツ

        Returns:
            dict: 比較メトリクス
                - word_diff: 単語数の差
                - word_ratio: 変更後/元の比率
                - h2_diff: H2セクション数の差
                - h3_diff: H3セクション数の差

        用途:
            - Step7b: ポリッシング前後の比較
            - Step9: リライト前後の比較
        """

    def estimate_reading_time(
        self,
        text: str,
        lang: str = "ja",
        wpm: int = 400,
    ) -> int:
        """
        読了時間を推定（分）

        Args:
            text: 対象テキスト
            lang: 言語
            wpm: 分あたり単語数（日本語デフォルト400）

        Returns:
            int: 推定読了時間（分、切り上げ）
        """
```

### 1.2 使用例

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

## 2. CheckpointManager (`checkpoint_manager.py`)

### 2.1 クラス定義

```python
from typing import Any
from datetime import datetime
import json
import hashlib

from apps.worker.storage import ArtifactStore
from apps.worker.helpers.schemas import CheckpointMetadata


class CheckpointManager:
    """Activity内チェックポイント管理"""

    def __init__(self, store: ArtifactStore):
        """
        Args:
            store: ストレージインスタンス
        """
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
        """
        チェックポイントを保存

        Args:
            tenant_id: テナントID
            run_id: 実行ID
            step_id: ステップID
            phase: フェーズ名（例: "queries_generated", "html_generated"）
            data: 保存するデータ
            input_digest: 入力のダイジェスト（冪等性チェック用）

        Returns:
            str: 保存先パス

        保存形式:
            {
                "_metadata": {
                    "phase": "...",
                    "created_at": "...",
                    "input_digest": "...",
                    "step_id": "..."
                },
                "data": { ... }
            }
        """

    async def load(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
        input_digest: str | None = None,
    ) -> dict[str, Any] | None:
        """
        チェックポイントをロード

        Args:
            tenant_id: テナントID
            run_id: 実行ID
            step_id: ステップID
            phase: フェーズ名
            input_digest: 入力のダイジェスト（指定時は一致チェック）

        Returns:
            dict | None: 保存されたデータ、存在しないか不一致ならNone

        冪等性ロジック:
            1. チェックポイントが存在するか確認
            2. input_digest が指定されていて、保存時と異なる場合は None
            3. 一致または未指定なら data を返す
        """

    async def exists(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
    ) -> bool:
        """
        チェックポイントが存在するか確認

        Returns:
            bool: 存在すれば True
        """

    async def clear(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str | None = None,
    ) -> None:
        """
        チェックポイントをクリア

        Args:
            phase: 指定時はそのフェーズのみ、Noneなら全フェーズ
        """

    def build_path(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
    ) -> str:
        """
        チェックポイントパスを構築

        Returns:
            str: "{tenant_id}/{run_id}/{step_id}/checkpoint/{phase}.json"
        """

    @staticmethod
    def compute_digest(data: Any) -> str:
        """
        データのダイジェストを計算

        Args:
            data: JSON化可能なデータ

        Returns:
            str: SHA256ダイジェスト（hex）
        """
```

### 2.2 使用例

```python
from apps.worker.helpers import CheckpointManager

checkpoint_mgr = CheckpointManager(self.store)

# 入力のダイジェストを計算
input_digest = CheckpointManager.compute_digest({"keyword": keyword})

# ロード試行
cached = await checkpoint_mgr.load(
    ctx.tenant_id, ctx.run_id, self.step_id, "queries_generated",
    input_digest=input_digest,
)

if cached:
    search_queries = cached["queries"]
    activity.logger.info("Loaded from checkpoint")
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

## 3. QualityRetryLoop (`quality_retry_loop.py`)

### 3.1 クラス定義

```python
from typing import Callable, Any, Awaitable, TypeVar
from temporalio import activity
from pydantic import BaseModel

from apps.worker.helpers.schemas import QualityResult
from apps.worker.helpers.quality_validator import QualityValidator

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
        accept_on_final: bool = True,
    ):
        """
        Args:
            max_retries: 最大リトライ回数（0で初回のみ）
            accept_on_final: 最終試行は品質不足でも受け入れるか
        """
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
            llm_call: LLM呼び出し関数（プロンプトを受け取りレスポンスを返す）
            initial_prompt: 初期プロンプト
            validator: 品質検証器
            enhance_prompt: 品質問題に基づいてプロンプトを改善する関数
                - 引数: (現在のプロンプト, 検出された問題リスト)
                - 戻り値: 改善されたプロンプト
            extract_content: LLM結果からコンテンツを抽出する関数
                - デフォルト: str(result)

        Returns:
            RetryLoopResult:
                - success: 品質チェック通過 or accept_on_final=True で最終試行完了
                - result: LLM呼び出し結果
                - quality: 最終的な品質結果
                - attempts: 試行回数
                - final_prompt: 最終的に使用したプロンプト

        ループ動作:
            1. LLM呼び出し
            2. コンテンツ抽出
            3. 品質チェック
            4. acceptable なら成功で終了
            5. リトライ可能なら enhance_prompt でプロンプト改善
            6. 最大試行数まで繰り返し
            7. accept_on_final なら最終結果を success=True で返す
        """
```

### 3.2 使用例

```python
from apps.worker.helpers import QualityRetryLoop
from apps.worker.helpers import StructureValidator

retry_loop = QualityRetryLoop(max_retries=1)

# プロンプト改善関数
def enhance_outline_prompt(prompt: str, issues: list[str]) -> str:
    additions = []
    if any("h2_count" in i for i in issues):
        additions.append("- 必ず3つ以上のH2セクションを含めてください")
    if any("h3" in i for i in issues):
        additions.append("- 各H2セクションにH3サブセクションを追加してください")

    if additions:
        return prompt + "\n\n追加指示:\n" + "\n".join(additions)
    return prompt

# 実行
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
    raise ActivityError("Outline generation failed quality check")
```

---

## テスト要件

### test_content_metrics.py

```python
import pytest
from apps.worker.helpers import ContentMetrics


class TestTextMetrics:
    """text_metrics のテスト"""

    def test_japanese_text(self):
        """日本語テキスト"""
        metrics = ContentMetrics()
        result = metrics.text_metrics("これはテストです。", lang="ja")

        # 日本語8文字 + 。= char_count
        assert result.char_count == 10
        # 日本語は1文字=1単語
        assert result.word_count == 8

    def test_english_text(self):
        """英語テキスト"""
        metrics = ContentMetrics()
        result = metrics.text_metrics("This is a test.", lang="en")

        assert result.word_count == 4

    def test_mixed_text(self):
        """日英混在テキスト"""
        metrics = ContentMetrics()
        result = metrics.text_metrics("SEO対策について解説", lang="ja")

        # SEO(1単語) + 日本語7文字 = 8
        assert result.word_count == 8

    def test_paragraph_count(self):
        """段落数"""
        metrics = ContentMetrics()
        content = "段落1\n\n段落2\n\n段落3"
        result = metrics.text_metrics(content)

        assert result.paragraph_count == 3

    def test_sentence_count_japanese(self):
        """文数（日本語）"""
        metrics = ContentMetrics()
        content = "文1です。文2です。文3です。"
        result = metrics.text_metrics(content)

        assert result.sentence_count == 3

    def test_sentence_count_english(self):
        """文数（英語）"""
        metrics = ContentMetrics()
        content = "Sentence one. Sentence two! Sentence three?"
        result = metrics.text_metrics(content, lang="en")

        assert result.sentence_count == 3


class TestMarkdownMetrics:
    """markdown_metrics のテスト"""

    def test_heading_counts(self):
        """見出し数"""
        metrics = ContentMetrics()
        content = """
# Title
## Section 1
### Subsection 1.1
## Section 2
### Subsection 2.1
#### Deep section
"""
        result = metrics.markdown_metrics(content)

        assert result.h1_count == 1
        assert result.h2_count == 2
        assert result.h3_count == 2
        assert result.h4_count == 1

    def test_list_count(self):
        """リスト数"""
        metrics = ContentMetrics()
        content = """
- item 1
- item 2
* item 3
"""
        result = metrics.markdown_metrics(content)

        assert result.list_count == 3

    def test_code_block_count(self):
        """コードブロック数"""
        metrics = ContentMetrics()
        content = """
```python
code here
```

```
more code
```
"""
        result = metrics.markdown_metrics(content)

        assert result.code_block_count == 2

    def test_link_count(self):
        """リンク数"""
        metrics = ContentMetrics()
        content = "[link1](url1) and [link2](url2)"
        result = metrics.markdown_metrics(content)

        assert result.link_count == 2

    def test_image_count(self):
        """画像数"""
        metrics = ContentMetrics()
        content = "![alt1](img1.png) and ![alt2](img2.png)"
        result = metrics.markdown_metrics(content)

        assert result.image_count == 2


class TestKeywordDensity:
    """keyword_density のテスト"""

    def test_basic_density(self):
        """基本的な密度計算"""
        metrics = ContentMetrics()
        # 10単語中1回 = 10%
        content = "SEO word word word word word word word word word"
        density = metrics.keyword_density(content, "SEO", lang="en")

        assert 9.0 <= density <= 11.0  # 約10%

    def test_zero_density(self):
        """キーワードなし"""
        metrics = ContentMetrics()
        content = "no keyword here"
        density = metrics.keyword_density(content, "SEO", lang="en")

        assert density == 0.0

    def test_case_insensitive(self):
        """大文字小文字を区別しない"""
        metrics = ContentMetrics()
        content = "seo SEO Seo"
        density = metrics.keyword_density(content, "SEO", lang="en")

        assert density > 0


class TestCompareContent:
    """compare_content のテスト"""

    def test_word_diff(self):
        """単語数の差"""
        metrics = ContentMetrics()
        original = "one two three"
        modified = "one two three four five"
        result = metrics.compare_content(original, modified, lang="en")

        assert result["word_diff"] == 2

    def test_word_ratio(self):
        """単語数の比率"""
        metrics = ContentMetrics()
        original = "one two"
        modified = "one two three four"
        result = metrics.compare_content(original, modified, lang="en")

        assert result["word_ratio"] == 2.0

    def test_h2_diff(self):
        """H2セクション数の差"""
        metrics = ContentMetrics()
        original = "## Section 1"
        modified = "## Section 1\n## Section 2"
        result = metrics.compare_content(original, modified)

        assert result["h2_diff"] == 1
```

### test_checkpoint_manager.py

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from apps.worker.helpers import CheckpointManager


class TestCheckpointManager:
    """CheckpointManager のテスト"""

    @pytest.fixture
    def mock_store(self):
        """モックストア"""
        store = MagicMock()
        store.put = AsyncMock()
        store.get_raw = AsyncMock(return_value=None)
        return store

    @pytest.fixture
    def manager(self, mock_store):
        """CheckpointManager インスタンス"""
        return CheckpointManager(mock_store)

    @pytest.mark.asyncio
    async def test_save(self, manager, mock_store):
        """保存"""
        path = await manager.save(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            data={"queries": ["q1", "q2"]},
        )

        assert "checkpoint" in path
        assert mock_store.put.called

    @pytest.mark.asyncio
    async def test_load_not_found(self, manager, mock_store):
        """存在しないチェックポイント"""
        mock_store.get_raw.return_value = None

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_load_found(self, manager, mock_store):
        """存在するチェックポイント"""
        import json
        checkpoint = {
            "_metadata": {"phase": "queries_generated"},
            "data": {"queries": ["q1"]},
        }
        mock_store.get_raw.return_value = json.dumps(checkpoint).encode()

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
        )

        assert result == {"queries": ["q1"]}

    @pytest.mark.asyncio
    async def test_load_digest_mismatch(self, manager, mock_store):
        """ダイジェスト不一致"""
        import json
        checkpoint = {
            "_metadata": {
                "phase": "queries_generated",
                "input_digest": "old_digest",
            },
            "data": {"queries": ["q1"]},
        }
        mock_store.get_raw.return_value = json.dumps(checkpoint).encode()

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            input_digest="new_digest",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_load_digest_match(self, manager, mock_store):
        """ダイジェスト一致"""
        import json
        checkpoint = {
            "_metadata": {
                "phase": "queries_generated",
                "input_digest": "same_digest",
            },
            "data": {"queries": ["q1"]},
        }
        mock_store.get_raw.return_value = json.dumps(checkpoint).encode()

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            input_digest="same_digest",
        )

        assert result == {"queries": ["q1"]}

    def test_build_path(self, manager):
        """パス構築"""
        path = manager.build_path("t1", "r1", "step5", "queries_generated")

        assert path == "t1/r1/step5/checkpoint/queries_generated.json"

    def test_compute_digest(self):
        """ダイジェスト計算"""
        digest1 = CheckpointManager.compute_digest({"key": "value"})
        digest2 = CheckpointManager.compute_digest({"key": "value"})
        digest3 = CheckpointManager.compute_digest({"key": "different"})

        assert digest1 == digest2
        assert digest1 != digest3
```

### test_quality_retry_loop.py

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from apps.worker.helpers import QualityRetryLoop
from apps.worker.helpers.schemas import QualityResult


class MockValidator:
    """テスト用バリデータ"""

    def __init__(self, results: list[QualityResult]):
        self.results = results
        self.call_count = 0

    def validate(self, content: str, **kwargs) -> QualityResult:
        result = self.results[min(self.call_count, len(self.results) - 1)]
        self.call_count += 1
        return result


class TestQualityRetryLoop:
    """QualityRetryLoop のテスト"""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """初回で成功"""
        loop = QualityRetryLoop(max_retries=1)

        async def llm_call(prompt: str):
            return "good content"

        validator = MockValidator([
            QualityResult(is_acceptable=True),
        ])

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test prompt",
            validator=validator,
        )

        assert result.success is True
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_success_on_retry(self):
        """リトライで成功"""
        loop = QualityRetryLoop(max_retries=1)

        call_count = 0

        async def llm_call(prompt: str):
            nonlocal call_count
            call_count += 1
            return f"content {call_count}"

        validator = MockValidator([
            QualityResult(is_acceptable=False, issues=["issue1"]),
            QualityResult(is_acceptable=True),
        ])

        def enhance(prompt: str, issues: list[str]) -> str:
            return prompt + "\nFix: " + str(issues)

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test prompt",
            validator=validator,
            enhance_prompt=enhance,
        )

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_accept_on_final(self):
        """最終試行で受け入れ"""
        loop = QualityRetryLoop(max_retries=1, accept_on_final=True)

        async def llm_call(prompt: str):
            return "content"

        validator = MockValidator([
            QualityResult(is_acceptable=False, issues=["issue"]),
            QualityResult(is_acceptable=False, issues=["issue"]),
        ])

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test prompt",
            validator=validator,
        )

        assert result.success is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_reject_on_final(self):
        """最終試行で拒否"""
        loop = QualityRetryLoop(max_retries=1, accept_on_final=False)

        async def llm_call(prompt: str):
            return "content"

        validator = MockValidator([
            QualityResult(is_acceptable=False, issues=["issue"]),
            QualityResult(is_acceptable=False, issues=["issue"]),
        ])

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test prompt",
            validator=validator,
        )

        assert result.success is False
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_extract_content(self):
        """コンテンツ抽出関数"""
        loop = QualityRetryLoop(max_retries=0)

        class Response:
            content = "extracted content"

        async def llm_call(prompt: str):
            return Response()

        validated_content = None

        class CaptureValidator:
            def validate(self, content: str, **kwargs) -> QualityResult:
                nonlocal validated_content
                validated_content = content
                return QualityResult(is_acceptable=True)

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test",
            validator=CaptureValidator(),
            extract_content=lambda r: r.content,
        )

        assert validated_content == "extracted content"

    @pytest.mark.asyncio
    async def test_no_enhance_prompt(self):
        """enhance_prompt なしでもリトライ"""
        loop = QualityRetryLoop(max_retries=1)

        call_count = 0

        async def llm_call(prompt: str):
            nonlocal call_count
            call_count += 1
            return "content"

        validator = MockValidator([
            QualityResult(is_acceptable=False, issues=["issue"]),
            QualityResult(is_acceptable=True),
        ])

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test prompt",
            validator=validator,
            # enhance_prompt なし
        )

        assert result.success is True
        assert call_count == 2
```

---

## 実装上の注意

### 日本語単語カウント

```python
def text_metrics(self, text: str, lang: str = "ja") -> TextMetrics:
    if lang == "ja":
        # 日本語文字を個別にカウント
        ja_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'
        ja_chars = len(re.findall(ja_pattern, text))

        # 英単語をカウント
        en_words = len(re.findall(r'[a-zA-Z]+', text))

        word_count = ja_chars + en_words
    else:
        word_count = len(text.split())
```

### チェックポイントのJSON化

```python
# datetime は ISO形式で保存
checkpoint = {
    "_metadata": {
        "created_at": datetime.utcnow().isoformat(),
    },
    "data": data,
}
content = json.dumps(checkpoint, ensure_ascii=False, default=str)
```

### リトライループのログ

```python
# リトライ時は必ずログ出力
if attempt < self.max_retries:
    activity.logger.warning(
        f"Quality retry {attempt + 1}/{self.max_retries}: {quality.issues}"
    )
```

---

## 完了条件

- [ ] `apps/worker/helpers/content_metrics.py` 全メソッド実装
- [ ] `apps/worker/helpers/checkpoint_manager.py` 全メソッド実装
- [ ] `apps/worker/helpers/quality_retry_loop.py` 全メソッド実装
- [ ] `apps/worker/helpers/__init__.py` にエクスポート追加
- [ ] `tests/unit/helpers/test_content_metrics.py` 全テスト通過
- [ ] `tests/unit/helpers/test_checkpoint_manager.py` 全テスト通過
- [ ] `tests/unit/helpers/test_quality_retry_loop.py` 全テスト通過
- [ ] `uv run mypy apps/worker/helpers/` 型エラーなし
- [ ] `uv run ruff check apps/worker/helpers/` リントエラーなし

---

## 依存関係

### このworktreeが依存するもの
- `helpers-parsing` の `schemas.py` (TextMetrics, MarkdownMetrics, CheckpointMetadata)
- `helpers-validation` の `quality_validator.py` (QualityValidator, QualityResult)
- `apps/worker/storage` の `ArtifactStore`

### このworktreeに依存するもの
- 全ステップ（特にStep5, 7a, 8, 10でチェックポイントを活用）
