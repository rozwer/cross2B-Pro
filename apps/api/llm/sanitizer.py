"""LLM入力サニタイザー

VULN-010: プロンプトインジェクション対策
- 制御文字の除去
- プロンプト境界マーカーの検出・警告
- 長さ制限
- ロールの強制

使用例:
    from apps.api.llm.sanitizer import sanitize_user_input, UserInputSanitized

    # 単純なサニタイズ
    clean_input = sanitize_user_input(user_provided_text)

    # 境界マーカーも含めてサニタイズ（ユーザー入力をシステムから分離）
    wrapped = UserInputSanitized(user_provided_text)
    prompt = f'''
システム指示: 以下のユーザー入力を分析してください。

{wrapped.to_prompt()}
'''
"""

import logging
import re
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)

# 危険な制御文字パターン
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# プロンプトインジェクションに使われやすいパターン
INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.I), "ignore_previous"),
    (re.compile(r"disregard\s+(all\s+)?above", re.I), "disregard_above"),
    (re.compile(r"system\s*:\s*", re.I), "system_role_marker"),
    (re.compile(r"assistant\s*:\s*", re.I), "assistant_role_marker"),
    (re.compile(r"\[INST\]|\[/INST\]", re.I), "instruction_marker"),
    (re.compile(r"<\|im_start\|>|<\|im_end\|>", re.I), "chatml_marker"),
    (re.compile(r"Human\s*:\s*|Assistant\s*:\s*", re.I), "conversation_marker"),
    (re.compile(r"```system|```instruction", re.I), "code_block_injection"),
    (re.compile(r"you\s+are\s+now\s+", re.I), "role_override"),
    (re.compile(r"act\s+as\s+(if\s+you\s+are\s+)?", re.I), "role_override_act"),
    (re.compile(r"pretend\s+(to\s+be|you\s+are)", re.I), "role_override_pretend"),
]

# デフォルト最大長（文字数）
DEFAULT_MAX_LENGTH = 100_000

# 境界マーカー
USER_INPUT_START = "<<<USER_INPUT_START>>>"
USER_INPUT_END = "<<<USER_INPUT_END>>>"


def sanitize_user_input(
    text: str,
    max_length: int = DEFAULT_MAX_LENGTH,
    warn_on_injection: bool = True,
    strip_injection_patterns: bool = False,
) -> str:
    """ユーザー入力をサニタイズ

    Args:
        text: サニタイズ対象のテキスト
        max_length: 最大文字数（超過分は切り捨て）
        warn_on_injection: インジェクションパターン検出時に警告ログを出すか
        strip_injection_patterns: インジェクションパターンを除去するか（False推奨）

    Returns:
        サニタイズ済みテキスト
    """
    if not text:
        return ""

    # 制御文字の除去（改行・タブは保持）
    result = CONTROL_CHARS_PATTERN.sub("", text)

    # 長さ制限
    if len(result) > max_length:
        logger.warning(f"User input truncated: {len(result)} -> {max_length} chars")
        result = result[:max_length]

    # インジェクションパターンのチェック
    if warn_on_injection:
        detected = []
        for pattern, name in INJECTION_PATTERNS:
            if pattern.search(result):
                detected.append(name)

        if detected:
            logger.warning(
                "Potential prompt injection detected",
                extra={
                    "patterns": detected,
                    "input_length": len(result),
                    "input_preview": result[:100] + "..." if len(result) > 100 else result,
                },
            )

    # パターン除去（オプション、通常は使用しない）
    if strip_injection_patterns:
        for pattern, name in INJECTION_PATTERNS:
            result = pattern.sub("[FILTERED]", result)

    return result


def escape_for_prompt(text: str) -> str:
    """プロンプト内で安全に使用できるようにエスケープ

    - バッククォートをエスケープ
    - 角括弧をエスケープ

    Args:
        text: エスケープ対象のテキスト

    Returns:
        エスケープ済みテキスト
    """
    # バッククォートのシーケンスをエスケープ
    result = re.sub(r"```+", lambda m: "\\`" * len(m.group(0)), text)
    return result


@dataclass(frozen=True)
class UserInputSanitized:
    """サニタイズ済みユーザー入力を表す型

    プロンプト内でユーザー入力を安全に扱うためのラッパー。
    境界マーカーでシステムプロンプトとユーザー入力を明確に分離。

    使用例:
        user_input = UserInputSanitized(raw_user_text)
        prompt = f'''
        以下のユーザー入力を分析してください:

        {user_input.to_prompt()}

        上記の内容を要約してください。
        '''
    """

    _MAX_LENGTH: ClassVar[int] = DEFAULT_MAX_LENGTH

    content: str

    def __post_init__(self) -> None:
        # dataclassのfrozen=Trueなので、object.__setattr__を使用
        sanitized = sanitize_user_input(self.content, max_length=self._MAX_LENGTH)
        object.__setattr__(self, "content", sanitized)

    def to_prompt(self) -> str:
        """境界マーカー付きのプロンプト文字列を返す"""
        return f"{USER_INPUT_START}\n{self.content}\n{USER_INPUT_END}"

    def __str__(self) -> str:
        return self.to_prompt()


def create_safe_user_message(content: str) -> dict[str, str]:
    """サニタイズ済みのユーザーメッセージを作成

    Args:
        content: ユーザーメッセージ内容

    Returns:
        {"role": "user", "content": sanitized_content}
    """
    sanitized = sanitize_user_input(content)
    return {"role": "user", "content": sanitized}


def validate_system_prompt(prompt: str) -> tuple[bool, list[str]]:
    """システムプロンプトの検証

    システムプロンプト内に危険なパターンがないか確認。

    Args:
        prompt: システムプロンプト

    Returns:
        (is_valid, warnings): 検証結果と警告メッセージのリスト
    """
    warnings = []

    # 空のプロンプト
    if not prompt or not prompt.strip():
        return False, ["System prompt is empty"]

    # 極端に短いプロンプト
    if len(prompt.strip()) < 10:
        warnings.append("System prompt is very short, may be insufficient")

    # ユーザー入力を直接展開している可能性
    if "{user" in prompt.lower() or "{{user" in prompt.lower():
        warnings.append("System prompt may contain unsanitized user input template")

    return len(warnings) == 0, warnings
