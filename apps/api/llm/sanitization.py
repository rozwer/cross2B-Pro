"""Prompt injection defense module.

This module provides sanitization and detection for prompt injection attacks.
It should be used before sending any user-provided content to LLMs.

Key protections:
- Detection of common injection patterns
- Input length limits
- Character filtering for dangerous sequences
- Logging of suspicious inputs
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class InjectionRisk(str, Enum):
    """Risk level for prompt injection detection."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SanitizationResult:
    """Result of input sanitization."""

    sanitized_text: str
    original_text: str
    risk_level: InjectionRisk
    detected_patterns: list[str]
    was_modified: bool


# Common prompt injection patterns to detect
INJECTION_PATTERNS = [
    # System prompt override attempts
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", "system_override"),
    (r"(?i)disregard\s+(all\s+)?(previous|prior|above)", "system_override"),
    (r"(?i)forget\s+(everything|all|your)\s+(you|instructions?|training)", "system_override"),
    (r"(?i)you\s+are\s+now\s+(a|an|the)", "role_override"),
    (r"(?i)new\s+instructions?:", "new_instructions"),
    (r"(?i)system\s*:\s*", "system_block"),
    (r"(?i)<\s*system\s*>", "system_tag"),

    # Jailbreak attempts
    (r"(?i)pretend\s+(you\s+are|to\s+be|you're)", "jailbreak"),
    (r"(?i)act\s+as\s+(if|though)", "jailbreak"),
    (r"(?i)roleplay\s+(as|like)", "jailbreak"),
    (r"(?i)dan\s+mode", "jailbreak"),
    (r"(?i)developer\s+mode", "jailbreak"),

    # Data exfiltration attempts
    (r"(?i)show\s+me\s+(your|the)\s+(system|initial)\s+prompt", "data_exfil"),
    (r"(?i)what\s+(are|is)\s+your\s+(instructions?|rules?|constraints?)", "data_exfil"),
    (r"(?i)reveal\s+(your|the)\s+prompt", "data_exfil"),

    # Code execution attempts
    (r"(?i)execute\s+(this|the\s+following)\s+code", "code_exec"),
    (r"(?i)run\s+(this|the)\s+(command|script)", "code_exec"),
    (r"(?i)```(python|bash|sh|javascript|js)\s*\n.*?\n```", "code_block"),
]

# Maximum input length (characters)
MAX_INPUT_LENGTH = 100000

# Characters/sequences to escape or remove
DANGEROUS_SEQUENCES = [
    ("\x00", ""),  # Null byte
    ("\r\n\r\n", "\n\n"),  # Multiple newlines (boundary confusion)
]


def detect_injection_patterns(text: str) -> tuple[InjectionRisk, list[str]]:
    """Detect potential prompt injection patterns in text.

    Args:
        text: Input text to analyze

    Returns:
        Tuple of (risk_level, list of detected pattern names)
    """
    detected = []

    for pattern, pattern_name in INJECTION_PATTERNS:
        if re.search(pattern, text):
            detected.append(pattern_name)

    # Determine risk level based on detections
    if not detected:
        return InjectionRisk.NONE, detected

    # High-risk patterns
    high_risk = {"system_override", "system_block", "system_tag", "jailbreak"}
    if any(p in high_risk for p in detected):
        return InjectionRisk.HIGH, detected

    # Medium-risk patterns
    medium_risk = {"role_override", "data_exfil", "code_exec"}
    if any(p in medium_risk for p in detected):
        return InjectionRisk.MEDIUM, detected

    return InjectionRisk.LOW, detected


def sanitize_input(
    text: str,
    max_length: int = MAX_INPUT_LENGTH,
    log_suspicious: bool = True,
    run_id: str | None = None,
    step_id: str | None = None,
) -> SanitizationResult:
    """Sanitize user input for safe use in LLM prompts.

    Performs:
    1. Length limiting
    2. Dangerous sequence removal
    3. Pattern detection (but not blocking - that's up to the caller)
    4. Logging of suspicious inputs

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        log_suspicious: Whether to log suspicious patterns
        run_id: Run ID for logging context
        step_id: Step ID for logging context

    Returns:
        SanitizationResult with sanitized text and risk assessment
    """
    original = text
    was_modified = False

    # 1. Length limiting
    if len(text) > max_length:
        text = text[:max_length]
        was_modified = True
        logger.warning(
            f"Input truncated from {len(original)} to {max_length} chars",
            extra={"run_id": run_id, "step_id": step_id},
        )

    # 2. Remove dangerous sequences
    for dangerous, replacement in DANGEROUS_SEQUENCES:
        if dangerous in text:
            text = text.replace(dangerous, replacement)
            was_modified = True

    # 3. Detect injection patterns
    risk_level, detected_patterns = detect_injection_patterns(text)

    # 4. Log suspicious inputs
    if log_suspicious and risk_level != InjectionRisk.NONE:
        logger.warning(
            f"Prompt injection detected: risk={risk_level.value}, patterns={detected_patterns}",
            extra={
                "run_id": run_id,
                "step_id": step_id,
                "risk_level": risk_level.value,
                "detected_patterns": detected_patterns,
                "input_preview": text[:100] if len(text) > 100 else text,
            },
        )

    return SanitizationResult(
        sanitized_text=text,
        original_text=original,
        risk_level=risk_level,
        detected_patterns=detected_patterns,
        was_modified=was_modified,
    )


def wrap_user_content(text: str, delimiter: str = "---") -> str:
    """Wrap user content with delimiters to separate from system instructions.

    This helps prevent injection attacks by clearly delimiting user content.

    Args:
        text: User content to wrap
        delimiter: Delimiter string to use

    Returns:
        Wrapped content
    """
    return f"\n{delimiter} USER CONTENT START {delimiter}\n{text}\n{delimiter} USER CONTENT END {delimiter}\n"


def create_safe_prompt(
    template: str,
    user_input: str,
    run_id: str | None = None,
    step_id: str | None = None,
    block_high_risk: bool = True,
) -> tuple[str, SanitizationResult]:
    """Create a safe prompt by sanitizing user input and combining with template.

    Args:
        template: System prompt template (trusted)
        user_input: User-provided input (untrusted)
        run_id: Run ID for logging
        step_id: Step ID for logging
        block_high_risk: If True, raise exception for high-risk inputs

    Returns:
        Tuple of (combined prompt, sanitization result)

    Raises:
        ValueError: If high-risk input is detected and block_high_risk is True
    """
    # Sanitize the user input
    result = sanitize_input(
        user_input,
        log_suspicious=True,
        run_id=run_id,
        step_id=step_id,
    )

    # Block high-risk inputs if configured
    if block_high_risk and result.risk_level == InjectionRisk.HIGH:
        raise ValueError(
            f"Input contains high-risk injection patterns: {result.detected_patterns}"
        )

    # Wrap user content with delimiters
    safe_content = wrap_user_content(result.sanitized_text)

    # Combine with template
    # Note: Template should contain {{user_input}} placeholder
    if "{{user_input}}" in template:
        combined = template.replace("{{user_input}}", safe_content)
    else:
        combined = template + safe_content

    return combined, result
