---
name: session-close
description: >
  End-of-slice documentation pass, run on the slice branch before it is pushed,
  so docs land in the same PR as the code. Reconciles
  `documents/feature-list.json` / `feature-list.md`, updates
  `documents/claude-progress.md`, adds lessons to the `code-learnings` skill,
  writes a walkthrough via the `code-walkthrough` skill, and updates
  `README.md`. Docs only — never changes code or test counts. Use whenever the
  user says "close out the session", "close the slice", "wrap up", "run
  session-close", or lists these doc tasks without naming the skill. Also
  supports a standalone `close-<name>` PR when reconciling several slices that
  already merged.
---

# session-close

A documentation reconciliation pass so the next session can start cold without digging
through git history. It changes **only docs**; it never alters code or test counts.

## Modes

- **Fold-in (default):** run on the slice branch after the slice's tests pass and
  before pushing. The docs commit goes into the slice's PR.
- **Standalone:** when several slices have already merged without a close (or another
  agent's work needs reconciling), create a branch from `origin/main`:
  `git fetch origin && git switch -c close-<name> origin/main`, and open a docs-only PR titled
  `docs: close <name>`. Never `git checkout main` (see AGENTS.md › Git workflow).

## Steps

### 1. Baseline

Record the pass count of the last full `scripts/test.sh` run on the code being closed: in
fold-in mode, the run made after the slice's last code change (AGENTS.md › *Finishing a
slice*); in standalone mode, the count recorded in the progress log for `main`.
`documents/test-baseline.json` holds that run's counts and the code's fingerprint:
`scripts/test.sh --fingerprint` must print the same fingerprint, or the code changed after
the run. Run the full suite only when no such run exists for the current code; it records
itself. Commit `documents/test-baseline.json` with the close (step 7 stages `documents/`). If it is red beyond the known
failures, stop and ask the human — fixing code is out of scope here.

### 2. Slice status — `documents/feature-list.json` and `feature-list.md`

For each slice completed in this session or PR:

- `passes` is `true` only if its acceptance tests exist and pass. Flip it if needed; never
  edit, reorder or delete other entries.
- The slice's description in `feature-list.md` still matches what was built. If scope
  changed, fix the prose and tell the human what changed.
- New slices discovered during the work are **appended** to both files only if the human
  has agreed; otherwise list them under *Next steps* in the progress log.

### 3. Progress log — `documents/claude-progress.md`

Update the sections defined in
[`documents/templates/claude-progress.template.md`](../../../documents/templates/claude-progress.template.md):

- **Last updated / Current status / Active slice / Test status** — reflect this session.
- **Walkthroughs** — add any walkthrough written in step 5.
- **Next steps** — remove what's done; add gaps this session *found* but didn't fix. Order:
  blockers > behaviour gaps > polish. Every item must trace to an artefact (TODO, failing
  check, learning), not a hunch.
- **Notes for next agent session** — anything the next session needs that isn't obvious
  from the above.

Don't copy walkthrough content into the progress log; link to it.

### 4. Lessons — `code-learnings`

Ask: *did this session teach something a future agent needs that isn't derivable from the
code?* If so, add `L-NN` entries following the template and rules in
[`code-learnings`](../code-learnings/SKILL.md), citing the PR or commit.

### 5. Walkthrough — `code-walkthrough`

For a slice of non-trivial size (roughly >100 lines of changed code, or a new module), write
`documents/code_walkthroughs/NNN.<name>.md` following
[`code-walkthrough`](../code-walkthrough/SKILL.md), which owns the structure. Add a row
to `documents/code_walkthroughs/README.md`.

### 6. `README.md`

Update the sections the slice affected — usage/CLI, configuration, architecture, and the
*Documentation* links. If you notice a gap caused by other work, record it under
*Next steps* instead of fixing it here.

### 7. Verify and commit

```bash
scripts/test.sh --harness           # the tests docs can break
git diff --stat                     # docs only
git add documents/ README.md .claude/skills/code-learnings/SKILL.md
git commit -m "docs: close <slice-id> — progress, learnings, walkthrough"
```

A docs-only change cannot change the full suite's count, so the full suite is not re-run
here: the docs can break only the harness checks (`tests/harness/`: the feature list, ADR
index and glossary acronyms), which run in seconds. If `git diff --stat` shows anything
outside `documents/`, `README.md` and `.claude/skills/code-learnings/`, it is not a close:
stop (see *Anti-patterns*).

Stage explicit paths only (see [G-01](../code-learnings/SKILL.md#g-01)). Then continue
with AGENTS.md › Git workflow › *Finishing a slice* (push, PR, ask the human to merge).

## Checklist

- [ ] The harness checks pass; the recorded pass count is the last full run's on this code (step 1)
- [ ] `git diff --stat` shows only `documents/`, `README.md`, `.claude/skills/code-learnings/`
- [ ] `feature-list.json` `passes` values match reality; no existing entries edited
- [ ] Progress log *Next steps* has nothing already done, and each item cites an artefact
- [ ] New `L-NN` entries cite a PR or commit
- [ ] New walkthrough (if any) is linked from the walkthrough index and the progress log

## Anti-patterns

- Fixing code or tests during close — open a separate slice instead.
- Inventing next steps without evidence.
- Marking a slice `passes: true` because the code "looks done".
- Re-deriving the walkthrough or lesson formats here instead of deferring to their skills.
