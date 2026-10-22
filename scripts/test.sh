#!/usr/bin/env bash
# Run the test suite. The single test entry point referenced by AGENTS.md and the skills.
#
#   scripts/test.sh                 the harness checks, then the full suite (in parallel
#                                   where the runner can); its result is recorded with the
#                                   code's fingerprint in documents/test-baseline.json
#   scripts/test.sh ARGS...         the harness checks, then the runner with ARGS (a subset
#                                   is not recorded)
#   scripts/test.sh --baseline      the full suite only when the code differs from the
#                                   recorded run's; otherwise the recorded result and the
#                                   harness checks (the tests that read the docs)
#   scripts/test.sh --fingerprint   print the code's fingerprint
#   scripts/test.sh --harness       run only the harness checks (the tests docs can break)
#
# The fingerprint covers everything a test result depends on except prose: every tracked
# and untracked (not ignored) file outside documents/, README.md, AGENTS.md, CLAUDE.md and
# the code-learnings skill, as it is on disk, and what `environment` prints. A docs-only
# change or a merge that brings nothing else keeps it, so the next session's baseline is
# skipped. If a test reads a prose file, add it to TESTS_READ_PROSE so it runs every time.
set -euo pipefail
cd "$(dirname "$0")/.."

BASELINE=documents/test-baseline.json
PROSE='^(documents/|README\.md$|AGENTS\.md$|CLAUDE\.md$|\.claude/skills/code-learnings/)'

# TEMPLATE PLACEHOLDER — the initializer agent fills in these for the project's stack.
#
# What else a result depends on: the toolchain and installed packages. Examples:
#   .venv/bin/python --version; .venv/bin/python -m pip freeze --exclude-editable
#   node --version; cat package-lock.json
environment() { :; }
# The full suite, in parallel where the runner can, writing a JUnit XML report to "$1";
# exit 0 when it passes, 1 when tests fail. Test ids must be the same in every process
# (never a random or time-based parameter), or a parallel runner refuses to start. Examples:
#   .venv/bin/python -m pytest -n auto --dist loadfile --junitxml="$1"
#   JEST_JUNIT_OUTPUT_FILE="$1" npx jest --ci --reporters=default --reporters=jest-junit
run_full() { echo "scripts/test.sh: not configured for this project yet" >&2; return 2; }
# A subset, with the runner's own arguments. Examples:
#   .venv/bin/python -m pytest "$@"
#   npx jest "$@"
run_some() { echo "scripts/test.sh: not configured for this project yet" >&2; return 2; }
# The tests that read prose, run on every baseline (beyond the harness checks).
TESTS_READ_PROSE=()

harness_checks() {
  # Harness checks — keep these whatever the stack (python3, stdlib only): the slice
  # record and planning docs, ADRs and glossary, and the debate skill's own script tests.
  for t in tests/harness/test_*.py .claude/skills/debate/scripts/test_*.py; do
    out=$(PYTHONDONTWRITEBYTECODE=1 python3 "$t" 2>&1) \
      || { printf '%s\nFAILED: %s\n' "$out" "$t" >&2; exit 1; }
  done
  echo "harness checks passed"
}

fingerprint() {
  local files
  files=$(git ls-files -z --cached --others --exclude-standard | tr '\0' '\n' \
          | grep -vE "$PROSE" | while IFS= read -r f; do [ -f "$f" ] && printf '%s\n' "$f"; done)
  {
    paste <(printf '%s\n' "$files") <(printf '%s\n' "$files" | git hash-object --stdin-paths)
    environment
  } | sha256sum | cut -c1-16
}

case "${1:-}" in
  --fingerprint) fingerprint; exit 0 ;;
  --harness) harness_checks; exit 0 ;;
esac

harness_checks

if [ "${1:-}" = "--baseline" ]; then
  shift
  now=$(fingerprint)
  if [ -f "$BASELINE" ] && python3 - "$BASELINE" "$now" <<'PY'
import json, sys
found = json.load(open(sys.argv[1]))
if found.get("fingerprint") != sys.argv[2]:
    sys.exit(1)
print(f"baseline unchanged: the code is as at the full run of {found['date']} "
      f"(fingerprint {found['fingerprint']}): {found['passed']} passed, {found['failed']} "
      f"failed, {found['skipped']} skipped")
for test in found["failures"]:
    print(f"  recorded failure: {test}")
PY
  then
    [ ${#TESTS_READ_PROSE[@]} -eq 0 ] || run_some "${TESTS_READ_PROSE[@]}"
    exit 0
  fi
  echo "baseline: the code differs from the recorded run's; running the full suite"
fi

if [ $# -gt 0 ]; then
  run_some "$@"
  exit
fi

now=$(fingerprint)
report=$(mktemp)
trap 'rm -f "$report"' EXIT
status=0
run_full "$report" || status=$?
# 0: passed, 1: some tests failed; anything else did not finish, so nothing is recorded.
if [ "$status" -le 1 ] && [ -s "$report" ]; then
  python3 - "$report" "$BASELINE" "$now" <<'PY'
import json, sys, xml.etree.ElementTree as ET
from datetime import datetime, timezone

passed = failed = skipped = 0
failures = []
for case in ET.parse(sys.argv[1]).getroot().iter("testcase"):
    node = f"{case.get('classname', '')}::{case.get('name')}"
    if case.find("failure") is not None or case.find("error") is not None:
        failed += 1
        failures.append(node)
    elif case.find("skipped") is not None:
        skipped += 1
    else:
        passed += 1
record = {"fingerprint": sys.argv[3],
          "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
          "passed": passed, "failed": failed, "skipped": skipped, "failures": sorted(failures)}
with open(sys.argv[2], "w") as out:
    json.dump(record, out, indent=2)
    out.write("\n")
print(f"recorded in {sys.argv[2]}: {passed} passed, {failed} failed, {skipped} skipped")
PY
fi
exit "$status"
