#!/usr/bin/env bash
# Run the full test suite. The single test entry point referenced by AGENTS.md
# and the skills. Extra arguments are passed through to the runner.
#   scripts/test.sh --harness   run only the harness checks (the tests docs can break)
set -euo pipefail
cd "$(dirname "$0")/.."

# Harness checks — keep these whatever the stack (python3, stdlib only): the slice record
# and planning docs, ADRs and glossary, and the debate skill's own script tests.
for t in tests/harness/test_*.py .claude/skills/debate/scripts/test_*.py; do
  out=$(PYTHONDONTWRITEBYTECODE=1 python3 "$t" 2>&1) \
    || { printf '%s\nFAILED: %s\n' "$out" "$t" >&2; exit 1; }
done
echo "harness checks passed"
[ "${1:-}" = "--harness" ] && exit 0

# TEMPLATE PLACEHOLDER — the initializer agent fills in the project's test runner below.
# Examples:
#   exec .venv/bin/python -m pytest -q "$@"
#   exec npm test -- "$@"

echo "scripts/test.sh: not configured for this project yet" >&2
exit 1
