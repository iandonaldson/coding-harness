#!/usr/bin/env bash
# Run the full test suite. The single test entry point referenced by AGENTS.md
# and the skills. Extra arguments are passed through to the runner.
# TEMPLATE PLACEHOLDER — the initializer agent fills this in for the project's stack.
set -euo pipefail
cd "$(dirname "$0")/.."

# Examples:
#   exec python3 -m pytest -q "$@"
#   exec npm test -- "$@"

echo "scripts/test.sh: not configured for this project yet" >&2
exit 1
