"""Quality-checked retry loop for LLM operations.

QualityRetryLoop provides a structured way to execute LLM calls with:
- Automatic quality validation after each attempt
- Prompt enhancement based on validation issues
- Configurable retry behavior
- Option to accept final result even if quality check fails
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from apps.worker.helpers.quality_validator import QualityValidator
from apps.worker.helpers.schemas import QualityResult

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryLoopResult(BaseModel):
    """Retry loop result."""

    success: bool
    result: Any | None = None
    quality: QualityResult | None = None
    attempts: int = 0
    final_prompt: str | None = None


class QualityRetryLoop:
    """Quality-checked retry loop."""

    def __init__(
        self,
        max_retries: int = 1,
        accept_on_final: bool = True,
    ):
        """
        Args:
            max_retries: Maximum retry count (0 for initial attempt only)
            accept_on_final: Accept result even if quality check fails on final attempt
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
        Execute LLM call with quality checking.

        Args:
            llm_call: LLM call function (receives prompt, returns response)
            initial_prompt: Initial prompt
            validator: Quality validator
            enhance_prompt: Function to improve prompt based on quality issues
                - Args: (current prompt, detected issues list)
                - Returns: Improved prompt
            extract_content: Function to extract content from LLM result
                - Default: str(result)

        Returns:
            RetryLoopResult:
                - success: Quality check passed or accept_on_final=True on final attempt
                - result: LLM call result
                - quality: Final quality result
                - attempts: Number of attempts
                - final_prompt: Final prompt used

        Loop behavior:
            1. Call LLM
            2. Extract content
            3. Quality check
            4. If acceptable, exit with success
            5. If retryable, enhance prompt with enhance_prompt
            6. Repeat until max attempts
            7. If accept_on_final, return success=True with final result
        """
        current_prompt = initial_prompt
        last_result: T | None = None
        last_quality: QualityResult | None = None

        max_attempts = 1 + self.max_retries

        for attempt in range(max_attempts):
            is_final_attempt = attempt == max_attempts - 1

            # Call LLM
            result = await llm_call(current_prompt)
            last_result = result

            # Extract content
            if extract_content is not None:
                content = extract_content(result)
            else:
                content = str(result)

            # Validate quality
            quality = validator.validate(content)
            last_quality = quality

            if quality.is_acceptable:
                return RetryLoopResult(
                    success=True,
                    result=result,
                    quality=quality,
                    attempts=attempt + 1,
                    final_prompt=current_prompt,
                )

            # Log retry attempt
            if not is_final_attempt:
                logger.warning(
                    f"Quality retry {attempt + 1}/{self.max_retries}: {quality.issues}"
                )

                # Enhance prompt for next attempt
                if enhance_prompt is not None:
                    current_prompt = enhance_prompt(current_prompt, quality.issues)
                # If no enhance_prompt, retry with same prompt

        # All attempts exhausted
        if self.accept_on_final:
            return RetryLoopResult(
                success=True,
                result=last_result,
                quality=last_quality,
                attempts=max_attempts,
                final_prompt=current_prompt,
            )

        return RetryLoopResult(
            success=False,
            result=last_result,
            quality=last_quality,
            attempts=max_attempts,
            final_prompt=current_prompt,
        )
