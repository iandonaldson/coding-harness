#!/usr/bin/env bash
# SessionStart hook: stdout is added to the agent's context at the start of every
# session, so the startup protocol in AGENTS.md never depends on the agent remembering it.
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0

echo "## Session context (from .claude/hooks/session-start.sh)"
echo "pwd: $(pwd)"

if git rev-parse --git-dir >/dev/null 2>&1; then
  echo "branch: $(git branch --show-current 2>/dev/null || echo '(detached)')"
  echo
  echo "### git status --short"
  git status --short | head -30
  echo
  echo "### git log --oneline -10"
  git log --oneline -10 2>/dev/null || echo "(no commits yet)"
else
  echo "WARNING: not a git repository"
fi

echo
MODE_FILE=documents/harness-mode
MODE=$(sed -n 's/^mode:[[:space:]]*\([a-z]*\).*/\1/p' "$MODE_FILE" 2>/dev/null)
echo "### Harness mode: ${MODE:-normal}"
if [ "$MODE" = "prototype" ]; then
  LIMIT=$(sed -n 's/^chain-limit:[[:space:]]*\([0-9]*\).*/\1/p' "$MODE_FILE")
  echo "PROTOTYPE MODE — follow AGENTS.md › Prototype mode. Slices branch from and merge"
  echo "into origin/prototype; chain-limit: ${LIMIT:-10} sessions in a row."
fi

echo
PROGRESS=documents/claude-progress.md
if [ -f "$PROGRESS" ]; then
  echo "### $PROGRESS"
  cat "$PROGRESS"
else
  echo "### $PROGRESS is missing — this is an INITIALIZER session (see AGENTS.md › Initializer)."
fi

BASELINE=documents/test-baseline.json
if [ -f "$BASELINE" ] && command -v python3 >/dev/null 2>&1; then
  echo
  echo "### Last full test run ($BASELINE)"
  python3 - "$BASELINE" <<'PY' || echo "(could not parse $BASELINE)"
import json, sys
found = json.load(open(sys.argv[1]))
print(f"{found['date']}: {found['passed']} passed, {found['failed']} failed, "
      f"{found['skipped']} skipped (fingerprint {found['fingerprint']}). "
      "`scripts/test.sh --baseline` skips the full run when the code is unchanged.")
PY
fi

FEATURES=documents/feature-list.json
if [ -f "$FEATURES" ] && command -v python3 >/dev/null 2>&1; then
  echo
  echo "### Pending slices ($FEATURES)"
  python3 - "$FEATURES" <<'PY' || echo "(could not parse $FEATURES)"
import json, sys
slices = json.load(open(sys.argv[1])).get("slices", [])
pending = [s for s in slices if not s.get("passes")]
print(f"{len(slices) - len(pending)}/{len(slices)} slices passing")
for s in pending:
    print(f"- {s.get('id')}: {s.get('title')}")
if not pending:
    print("No pending slices — discuss the next objective with the human (AGENTS.md › Working on a slice).")
PY
fi
exit 0
