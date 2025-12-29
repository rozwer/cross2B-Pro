#!/usr/bin/env python3
"""PreToolUse(Bash:git commit): Conventional Commits 形式を検証"""

import json
import re
import sys

CONVENTIONAL_PATTERN = r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .+"

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

# --no-verify がある場合はスキップ
if "--no-verify" in command:
    sys.exit(0)

# HEREDOC パターン（$(cat <<'EOF' ... EOF) など）はスキップ
# これは複雑なメッセージ形式で、別途検証が困難なため
if "<<" in command and "EOF" in command:
    sys.exit(0)

# git commit -m "message" から最初の message を抽出
# 複数の -m がある場合、最初のものがタイトル行
patterns = [
    r'git\s+commit\s+.*?-m\s+"([^"]+)"',  # ダブルクォート
    r"git\s+commit\s+.*?-m\s+'([^']+)'",  # シングルクォート
]

message = None
for pattern in patterns:
    match = re.search(pattern, command)
    if match:
        message = match.group(1)
        break

if message:
    if not re.match(CONVENTIONAL_PATTERN, message):
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": f"Conventional Commits 形式ではありません: {message}",
                }
            )
        )
        sys.exit(2)

sys.exit(0)
