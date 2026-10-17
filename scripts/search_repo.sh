#!/bin/bash
# search_repo.sh - Search codebase with best available tool
#
# Usage: ./scripts/search_repo.sh <pattern> [path] [options]
#
# Examples:
#   ./scripts/search_repo.sh "TODO"
#   ./scripts/search_repo.sh "function.*login" src/
#   ./scripts/search_repo.sh "error" --type ts

set -e

if [[ $# -eq 0 ]]; then
    echo "Usage: search_repo.sh <pattern> [path] [options]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/search_repo.sh 'TODO'"
    echo "  ./scripts/search_repo.sh 'login' src/"
    echo "  ./scripts/search_repo.sh 'error' . --type ts"
    exit 1
fi

PATTERN="$1"
SEARCH_PATH="."
EXTRA_ARGS=()

if [[ $# -ge 2 ]] && [[ ! "$2" =~ ^- ]]; then
    SEARCH_PATH="$2"
    shift 2
    EXTRA_ARGS=("$@")
else
    shift 1
    EXTRA_ARGS=("$@")
fi

# Try ripgrep first (fastest)
if command -v rg &> /dev/null; then
    echo "# Using ripgrep" >&2
    rg "$PATTERN" "$SEARCH_PATH" "${EXTRA_ARGS[@]}" --color=always
    exit $?
fi

# Fall back to grep
echo "# Using grep (install ripgrep for better performance)" >&2

# Convert common rg options to grep options safely using arrays
GREP_ARGS=()
skip_next=false
for arg in "${EXTRA_ARGS[@]}"; do
    if [[ "$skip_next" == true ]]; then
        case "$arg" in
            ts|js|py|go|rs|md)
                GREP_ARGS+=("--include=*.$arg")
                ;;
            *)
                ;;
        esac
        skip_next=false
        continue
    fi
    case "$arg" in
        --type)
            skip_next=true
            ;;
        *)
            GREP_ARGS+=("$arg")
            ;;
    esac
done

grep -rn --exclude-dir=.git --exclude-dir=.venv --exclude-dir=__pycache__ "${GREP_ARGS[@]}" "$PATTERN" "$SEARCH_PATH" --color=always 2>/dev/null || {
    echo "No matches found for: $PATTERN"
    exit 0
}
