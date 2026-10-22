#!/usr/bin/env bash
# Print a fingerprint of everything tests can depend on: every tracked file except the
# docs-only paths below (an exclude-list, so a new directory is covered automatically).
#   scripts/fingerprint.sh            HEAD; fails if non-doc changes are uncommitted
#   scripts/fingerprint.sh <ref>      e.g. origin/main, origin/prototype
# Identical fingerprints mean identical code, tests and lockfiles — not an identical
# environment (Python/runtime, unpinned dependencies, the clock). See AGENTS.md › Tests.
set -euo pipefail
cd "$(dirname "$0")/.."

DOCS_ONLY=$'\t(documents/|README\\.md$|\\.claude/skills/code-learnings/)'
REF="${1:-HEAD}"

if [ $# -eq 0 ]; then
  dirty=$(git status --porcelain | grep -v -E '^.. (documents/|README\.md$|\.claude/skills/code-learnings/)' || true)
  if [ -n "$dirty" ]; then
    echo "scripts/fingerprint.sh: uncommitted non-doc changes — commit them first:" >&2
    echo "$dirty" >&2
    exit 1
  fi
fi

git ls-tree -r "$REF" | { grep -v -E "$DOCS_ONLY" || true; } | sha256sum | cut -c1-16
