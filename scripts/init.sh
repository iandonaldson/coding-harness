#!/usr/bin/env bash
# Set up the development environment and run a quick smoke test.
# TEMPLATE PLACEHOLDER — the initializer agent fills this in for the project's stack.
set -euo pipefail
cd "$(dirname "$0")/.."

# Examples:
#   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
#   npm ci
#   docker compose up -d db
# Then the baseline: the full suite, unless the code is as at the recorded run (AGENTS.md):
#   scripts/test.sh --baseline

echo "scripts/init.sh: not configured for this project yet" >&2
exit 1
