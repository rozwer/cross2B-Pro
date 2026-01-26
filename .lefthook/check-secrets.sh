#!/bin/bash
# 秘密情報検出スクリプト
# Migrated from .githooks/pre-commit

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# 引数からファイルリストを取得
FILES="$@"

if [ -z "$FILES" ]; then
    exit 0
fi

HAS_ERROR=0

# 秘密情報パターン
SECRET_PATTERNS=(
    'OPENAI_API_KEY\s*=\s*["\x27]?sk-[a-zA-Z0-9]+'
    'ANTHROPIC_API_KEY\s*=\s*["\x27]?sk-ant-[a-zA-Z0-9]+'
    'GEMINI_API_KEY\s*=\s*["\x27]?[a-zA-Z0-9_-]{39}'
    'AWS_SECRET_ACCESS_KEY\s*=\s*["\x27]?[A-Za-z0-9/+=]{40}'
    'password\s*=\s*["\x27][^"\x27]{8,}["\x27]'
    'api_key\s*=\s*["\x27][a-zA-Z0-9_-]{20,}["\x27]'
)

# 除外パターン
EXCLUDE_PATTERNS=(
    "*.md"
    ".claude/*"
    ".claude-making/*"
    "*.example"
    "tests/*"
)

# ダミー値パターン
DUMMY_PATTERNS=(
    "sk-xxxx"
    "sk-xxx"
    "YOUR_"
    "your-"
    "example"
    "dummy"
    "test"
    "placeholder"
)

should_check() {
    local file="$1"
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        if [[ "$file" == $pattern ]]; then
            return 1
        fi
    done
    return 0
}

for file in $FILES; do
    if [[ ! -f "$file" ]]; then
        continue
    fi

    # .env ファイルチェック
    if [[ "$file" == ".env" ]] || [[ "$file" == *".env.local"* ]] || [[ "$file" == *".env.production"* ]]; then
        echo -e "${RED}⚠️  .env ファイルがステージされています: $file${NC}"
        HAS_ERROR=1
        continue
    fi

    # 除外パターンチェック
    if ! should_check "$file"; then
        continue
    fi

    for pattern in "${SECRET_PATTERNS[@]}"; do
        if grep -Eq "$pattern" "$file" 2>/dev/null; then
            matched_line=$(grep -E "$pattern" "$file" 2>/dev/null | head -1)
            is_dummy=0
            for dummy in "${DUMMY_PATTERNS[@]}"; do
                if echo "$matched_line" | grep -qi "$dummy"; then
                    is_dummy=1
                    break
                fi
            done
            if [ $is_dummy -eq 0 ]; then
                echo -e "${RED}⚠️  秘密情報の可能性: $file${NC}"
                echo "   パターン: $pattern"
                HAS_ERROR=1
            fi
        fi
    done
done

if [ $HAS_ERROR -ne 0 ]; then
    exit 1
fi

echo -e "${GREEN}✓ 秘密情報なし${NC}"
exit 0
