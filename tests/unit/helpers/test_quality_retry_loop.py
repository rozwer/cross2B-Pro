"""Tests for QualityRetryLoop class."""

import pytest

from apps.worker.helpers import QualityRetryLoop
from apps.worker.helpers.schemas import QualityResult


class MockValidator:
    """Test validator."""

    def __init__(self, results: list[QualityResult]):
        self.results = results
        self.call_count = 0

    def validate(self, content: str, **kwargs) -> QualityResult:
        result = self.results[min(self.call_count, len(self.results) - 1)]
        self.call_count += 1
        return result


class TestQualityRetryLoop:
    """QualityRetryLoop tests."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Success on first attempt."""
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
        """Success on retry."""
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
        """Accept on final attempt."""
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
        """Reject on final attempt."""
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
        """Content extraction function."""
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
        """Retry without enhance_prompt."""
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
            # No enhance_prompt
        )

        assert result.success is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """Zero retries (single attempt)."""
        loop = QualityRetryLoop(max_retries=0, accept_on_final=False)

        async def llm_call(prompt: str):
            return "content"

        validator = MockValidator([
            QualityResult(is_acceptable=False, issues=["issue"]),
        ])

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test prompt",
            validator=validator,
        )

        assert result.success is False
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_final_prompt_tracked(self):
        """Final prompt is tracked."""
        loop = QualityRetryLoop(max_retries=1)

        async def llm_call(prompt: str):
            return "content"

        validator = MockValidator([
            QualityResult(is_acceptable=False, issues=["issue"]),
            QualityResult(is_acceptable=True),
        ])

        def enhance(prompt: str, issues: list[str]) -> str:
            return "enhanced prompt"

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="initial prompt",
            validator=validator,
            enhance_prompt=enhance,
        )

        assert result.final_prompt == "enhanced prompt"

    @pytest.mark.asyncio
    async def test_result_preserved(self):
        """LLM result is preserved."""
        loop = QualityRetryLoop(max_retries=0)

        async def llm_call(prompt: str):
            return {"key": "value", "data": [1, 2, 3]}

        validator = MockValidator([
            QualityResult(is_acceptable=True),
        ])

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test",
            validator=validator,
        )

        assert result.result == {"key": "value", "data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_quality_result_preserved(self):
        """Quality result is preserved."""
        loop = QualityRetryLoop(max_retries=0)

        async def llm_call(prompt: str):
            return "content"

        expected_quality = QualityResult(
            is_acceptable=True,
            issues=[],
            warnings=["minor_warning"],
            scores={"quality": 0.95},
        )
        validator = MockValidator([expected_quality])

        result = await loop.execute(
            llm_call=llm_call,
            initial_prompt="test",
            validator=validator,
        )

        assert result.quality == expected_quality
        assert result.quality.warnings == ["minor_warning"]
        assert result.quality.scores["quality"] == 0.95
