#!/usr/bin/env python3
"""PreToolUse hook: 重要ファイルの保護"""

import json
import sys

# 保護対象ファイルパターン
PROTECTED_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
    "credentials",
    "secrets",
    ".git/",
]


def main():
    # 標準入力からツール情報を読み取り
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # パースエラーは無視

    # ファイルパスを取得
    file_path = data.get("tool_input", {}).get("file_path", "")

    # 保護対象かチェック
    for pattern in PROTECTED_PATTERNS:
        if pattern in file_path:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": f"Protected file pattern: {pattern}",
                    }
                )
            )
            sys.exit(0)

    # 許可
    sys.exit(0)


if __name__ == "__main__":
    main()
