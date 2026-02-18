#!/bin/bash
# =============================================================================
# Environment Check Script
# =============================================================================
# テスト実行前に環境が要件を満たしているか確認するスクリプト
#
# Usage:
#   ./scripts/check-env.sh           # 全チェック
#   ./scripts/check-env.sh --quick   # 最小限チェック（CI用）
#   ./scripts/check-env.sh --docker  # Docker関連のみ
#   ./scripts/check-env.sh --python  # Python関連のみ
#   ./scripts/check-env.sh --node    # Node.js関連のみ
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=============================================="
    echo -e "$1"
    echo -e "==============================================${NC}"
}

print_check() {
    echo -n "  Checking $1... "
}

print_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    ((WARNINGS++))
}

print_info() {
    echo -e "    ${BLUE}→ $1${NC}"
}

check_command() {
    local cmd=$1
    local name=${2:-$cmd}
    print_check "$name"
    if command -v "$cmd" &> /dev/null; then
        local version=$($cmd --version 2>&1 | head -n1)
        print_pass "$version"
        return 0
    else
        print_fail "not found"
        return 1
    fi
}

check_version() {
    local cmd=$1
    local min_version=$2
    local name=${3:-$cmd}
    local current_version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -n1)

    if [ "$(printf '%s\n' "$min_version" "$current_version" | sort -V | head -n1)" = "$min_version" ]; then
        return 0
    else
        return 1
    fi
}

# =============================================================================
# Check Functions
# =============================================================================

check_python_env() {
    print_header "Python Environment"

    # Python version
    print_check "Python 3.11+"
    if command -v python3 &> /dev/null; then
        py_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        if check_version python3 "3.11"; then
            print_pass "Python $py_version"
        else
            print_fail "Python $py_version (requires 3.11+)"
        fi
    else
        print_fail "Python not found"
    fi

    # uv package manager
    print_check "uv (package manager)"
    if command -v uv &> /dev/null; then
        uv_version=$(uv --version 2>&1)
        print_pass "$uv_version"
    else
        print_warn "not found (recommended: curl -LsSf https://astral.sh/uv/install.sh | sh)"
    fi

    # pip
    print_check "pip"
    if python3 -m pip --version &> /dev/null; then
        pip_version=$(python3 -m pip --version 2>&1)
        print_pass "$pip_version"
    else
        print_fail "pip not found"
    fi

    # Virtual environment
    print_check "Virtual environment (.venv)"
    if [ -d ".venv" ]; then
        print_pass "exists"
    else
        print_warn "not found (run: uv sync)"
    fi

    # Dependencies installed
    print_check "Python dependencies"
    if [ -f "pyproject.toml" ]; then
        if python3 -c "import fastapi; import temporalio; import langgraph" 2>/dev/null; then
            print_pass "core packages installed"
        else
            print_warn "some packages missing (run: uv sync)"
        fi
    else
        print_fail "pyproject.toml not found"
    fi

    # Type checker
    print_check "mypy (type checker)"
    if python3 -m mypy --version &> /dev/null; then
        mypy_version=$(python3 -m mypy --version 2>&1)
        print_pass "$mypy_version"
    else
        print_warn "not found (run: uv sync)"
    fi

    # Linter
    print_check "ruff (linter)"
    if python3 -m ruff --version &> /dev/null; then
        ruff_version=$(python3 -m ruff --version 2>&1)
        print_pass "$ruff_version"
    else
        print_warn "not found (run: uv sync)"
    fi

    # pytest
    print_check "pytest"
    if python3 -m pytest --version &> /dev/null; then
        pytest_version=$(python3 -m pytest --version 2>&1)
        print_pass "$pytest_version"
    else
        print_warn "not found (run: uv sync)"
    fi
}

check_node_env() {
    print_header "Node.js Environment"

    # Node.js version
    print_check "Node.js 20+"
    if command -v node &> /dev/null; then
        node_version=$(node --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        if check_version node "20.0"; then
            print_pass "Node.js v$node_version"
        else
            print_fail "Node.js v$node_version (requires 20+)"
        fi
    else
        print_fail "Node.js not found"
    fi

    # npm
    print_check "npm"
    if command -v npm &> /dev/null; then
        npm_version=$(npm --version 2>&1)
        print_pass "npm v$npm_version"
    else
        print_fail "npm not found"
    fi

    # UI dependencies
    print_check "UI dependencies (apps/ui/node_modules)"
    if [ -d "apps/ui/node_modules" ]; then
        print_pass "installed"
    else
        print_warn "not installed (run: cd apps/ui && npm install)"
    fi

    # TypeScript
    print_check "TypeScript (apps/ui)"
    if [ -f "apps/ui/node_modules/.bin/tsc" ]; then
        tsc_version=$(./apps/ui/node_modules/.bin/tsc --version 2>&1)
        print_pass "$tsc_version"
    else
        print_warn "not found (run: cd apps/ui && npm install)"
    fi
}

check_docker_env() {
    print_header "Docker Environment"

    # Docker
    print_check "Docker"
    if command -v docker &> /dev/null; then
        docker_version=$(docker --version 2>&1)
        print_pass "$docker_version"

        # Docker daemon running
        print_check "Docker daemon"
        if docker info &> /dev/null; then
            print_pass "running"
        else
            print_fail "not running (start Docker Desktop or dockerd)"
        fi
    else
        print_fail "Docker not found"
    fi

    # Docker Compose
    print_check "Docker Compose"
    if docker compose version &> /dev/null; then
        compose_version=$(docker compose version 2>&1)
        print_pass "$compose_version"
    else
        print_fail "Docker Compose not found"
    fi

    # docker-compose.yml
    print_check "docker-compose.yml"
    if [ -f "docker-compose.yml" ]; then
        print_pass "exists"

        # Validate config
        print_check "Docker Compose config validation"
        if docker compose config --quiet 2>/dev/null; then
            print_pass "valid"
        else
            print_fail "invalid config"
        fi
    else
        print_fail "not found"
    fi

    # Dockerfiles
    print_check "Dockerfiles"
    local dockerfiles=("docker/Dockerfile.api" "docker/Dockerfile.worker" "docker/Dockerfile.ui")
    local missing=()
    for df in "${dockerfiles[@]}"; do
        if [ ! -f "$df" ]; then
            missing+=("$df")
        fi
    done
    if [ ${#missing[@]} -eq 0 ]; then
        print_pass "all present"
    else
        print_fail "missing: ${missing[*]}"
    fi
}

check_files() {
    print_header "Required Files"

    local files=(
        "pyproject.toml"
        ".env.example"
        "docker-compose.yml"
        "scripts/bootstrap.sh"
        "scripts/reset.sh"
        "scripts/init-db.sql"
        "apps/api/main.py"
        "apps/worker/main.py"
        "apps/ui/package.json"
    )

    for file in "${files[@]}"; do
        print_check "$file"
        if [ -f "$file" ]; then
            print_pass "exists"
        else
            print_fail "not found"
        fi
    done
}

check_env_file() {
    print_header "Environment Variables"

    # .env file
    print_check ".env file"
    if [ -f ".env" ]; then
        print_pass "exists"

        # Load .env
        set -a
        source .env 2>/dev/null || true
        set +a

        # Check LLM API keys
        print_check "LLM API keys"
        if [ -n "$GEMINI_API_KEY" ] || [ -n "$OPENAI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
            print_pass "at least one configured"
        elif [ "$USE_MOCK_LLM" = "true" ]; then
            print_warn "none set, but USE_MOCK_LLM=true"
        else
            print_warn "none set (set at least one or USE_MOCK_LLM=true)"
        fi

        # Check database config
        print_check "Database config (POSTGRES_*)"
        if [ -n "$POSTGRES_USER" ] && [ -n "$POSTGRES_PASSWORD" ]; then
            print_pass "configured"
        else
            print_warn "using defaults"
        fi

        # Check MinIO config
        print_check "MinIO config (MINIO_*)"
        if [ -n "$MINIO_ROOT_USER" ] && [ -n "$MINIO_ROOT_PASSWORD" ]; then
            print_pass "configured"
        else
            print_warn "using defaults"
        fi

    else
        print_warn "not found (copy from .env.example)"
        print_info "Run: cp .env.example .env"
    fi
}

check_services() {
    print_header "Running Services (optional)"

    # Check if docker is available first
    if ! docker info &> /dev/null; then
        print_info "Docker not running, skipping service checks"
        return
    fi

    local services=("postgres" "minio" "temporal" "api" "worker" "ui")

    for service in "${services[@]}"; do
        print_check "$service container"
        if docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "^${service}$"; then
            print_pass "running"
        else
            print_info "not running"
        fi
    done
}

check_ports() {
    print_header "Port Availability"

    local ports=(
        "5432:PostgreSQL"
        "9000:MinIO"
        "9001:MinIO Console"
        "7233:Temporal"
        "8080:Temporal UI"
        "8000:API"
        "3000:UI"
    )

    for port_info in "${ports[@]}"; do
        local port="${port_info%%:*}"
        local name="${port_info##*:}"
        print_check "Port $port ($name)"

        if command -v lsof &> /dev/null; then
            if lsof -i :"$port" &> /dev/null; then
                local proc=$(lsof -i :"$port" -t 2>/dev/null | head -1)
                print_warn "in use (PID: $proc)"
            else
                print_pass "available"
            fi
        elif command -v ss &> /dev/null; then
            if ss -tuln | grep -q ":$port "; then
                print_warn "in use"
            else
                print_pass "available"
            fi
        else
            print_info "cannot check (lsof/ss not available)"
        fi
    done
}

# =============================================================================
# Main
# =============================================================================

print_header "SEO Article Generator - Environment Check"
echo "  Project: $PROJECT_ROOT"
echo "  Date: $(date)"

# Parse arguments
QUICK_MODE=false
DOCKER_ONLY=false
PYTHON_ONLY=false
NODE_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --docker)
            DOCKER_ONLY=true
            shift
            ;;
        --python)
            PYTHON_ONLY=true
            shift
            ;;
        --node)
            NODE_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run checks based on mode
if [ "$DOCKER_ONLY" = true ]; then
    check_docker_env
elif [ "$PYTHON_ONLY" = true ]; then
    check_python_env
elif [ "$NODE_ONLY" = true ]; then
    check_node_env
elif [ "$QUICK_MODE" = true ]; then
    check_files
    check_python_env
    check_docker_env
else
    check_files
    check_python_env
    check_node_env
    check_docker_env
    check_env_file
    check_ports
    check_services
fi

# Summary
print_header "Summary"
echo -e "  ${GREEN}Passed:   $PASSED${NC}"
echo -e "  ${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "  ${RED}Failed:   $FAILED${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Environment check failed. Please fix the issues above.${NC}"
    echo ""
    echo "Quick fixes:"
    echo "  - Python dependencies: uv sync"
    echo "  - Node dependencies:   cd apps/ui && npm install"
    echo "  - Docker not running:  Start Docker Desktop"
    echo "  - .env missing:        cp .env.example .env"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Environment check passed with warnings.${NC}"
    exit 0
else
    echo -e "${GREEN}Environment check passed!${NC}"
    exit 0
fi
