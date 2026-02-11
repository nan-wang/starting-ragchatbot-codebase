#!/bin/bash
# Code quality check script for the RAG chatbot project
# Usage:
#   ./scripts/quality.sh          - Check formatting (CI mode, no changes)
#   ./scripts/quality.sh format   - Auto-format all Python files
#   ./scripts/quality.sh check    - Check formatting only (default)

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

TARGETS="backend/ main.py"

check_formatting() {
    echo "Checking code formatting with black..."
    if uv run black --check $TARGETS; then
        echo "All files are properly formatted."
    else
        echo ""
        echo "Formatting issues found. Run './scripts/quality.sh format' to fix."
        exit 1
    fi
}

format_code() {
    echo "Formatting code with black..."
    uv run black $TARGETS
    echo "Formatting complete."
}

case "${1:-check}" in
    check)
        check_formatting
        ;;
    format)
        format_code
        ;;
    *)
        echo "Usage: $0 {check|format}"
        echo "  check   - Check formatting without making changes (default)"
        echo "  format  - Auto-format all Python files"
        exit 1
        ;;
esac
