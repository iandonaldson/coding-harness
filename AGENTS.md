# AGENTS.md — Agent operating instructions

How every coding-agent session behaves in this repository. `CLAUDE.md` imports this
file, so Claude Code and other AGENTS.md-aware tools read the same rules.

> **Template placeholders** — replace every `<…>` below when starting a new project,
> then delete this note.

---

## Project

- **Product:** <one-line description> — full spec in [`documents/product_description.md`](documents/product_description.md)
- **Human owner:** <name> — "the human" below
- **Stack:** <language / framework / runtime>
- **Key architectural decisions:**
  - <e.g. Secrets via Azure Key Vault / Managed Identity — never in code or config files>
  - <…>

---

## Key files

| File | Purpose | Who edits |
|---|---|---|
| [`documents/product_description.md`](documents/product_description.md) | What we are building | Human |
| [`documents/feature-list.md`](documents/feature-list.md) | Features and their slice definitions (prose) | Human + agent in planning |
| [`documents/glossary.md`](documents/glossary.md) | Controlled vocabulary: use its terms, flag invented ones | Human + agent (reviewed) |
| [`documents/adr/`](documents/adr/README.md) | Architecture decision records (process: ADR 000) | Agent proposes, human merges |
| [`documents/feature-list.json`](documents/feature-list.json) | **Single source of truth for slice status** (`passes`) | Agent — see rules below |
| `documents/claude-progress.md` | Session hand-off log (created by the initializer) | Agent, every session |
| [`scripts/init.sh`](scripts/init.sh) | Set up the dev environment + smoke test | Initializer, then as needed |
| [`scripts/test.sh`](scripts/test.sh) | Run the full test suite (in parallel where the runner can) — the only test entry point; `--baseline` skips an unchanged one | Initializer, then as needed |
| `documents/test-baseline.json` | The last full run's result and the code's fingerprint, written by `scripts/test.sh` | `scripts/test.sh`; committed with the slice |
| [`.claude/skills/code-learnings/SKILL.md`](.claude/skills/code-learnings/SKILL.md) | Durable lessons (L-NN) | Agent at session close |
| `documents/code_walkthroughs/NNN.<name>.md` | Per-slice reference docs | Agent at session close |

**`feature-list.json` rules:** agents may only flip `passes` from `false` to `true` (after
tests pass) or append new slices agreed with the human. Never delete, reorder, or reword
existing entries — raise it with the human instead.

---

## Session startup

A `SessionStart` hook ([`.claude/hooks/session-start.sh`](.claude/hooks/session-start.sh))
prints the working directory, branch, recent commits, the progress log and the pending
slices into context. Using that output:

1. **Initializer check** — if the hook reports no `documents/claude-progress.md`, follow
   *Initializer* below instead.
2. **Reconcile** — compare `git log` with `feature-list.json`. If a commit completed a
   slice still marked `"passes": false`, verify its tests and fix the record before
   anything else.
3. **Branch** — follow *Git workflow* to get onto a fresh slice branch.
4. **Baseline** — run `scripts/test.sh --baseline` (`scripts/init.sh` runs it). When the
   code's fingerprint equals the one in `documents/test-baseline.json`, it reports that
   recorded run and runs only the harness checks (and any test that reads prose); otherwise
   it runs the full suite and records it. If it is red beyond the recorded or known
   failures, stop and investigate before touching anything (see *When to ask the human*).
5. **Learnings** — skim the index of [`code-learnings`](.claude/skills/code-learnings/SKILL.md).
6. Only then begin implementation.

---

## Initializer

Runs once, when `documents/claude-progress.md` does not exist.

1. Confirm the repo is a git repo on `main` (`git status`).
2. Check `documents/product_description.md` and `documents/feature-list.md` no longer
   contain `TEMPLATE PLACEHOLDER`. If they do, stop and ask the human to run a planning
   session first.
3. Fill in `documents/feature-list.json` from the slices in `feature-list.md`
   (all `"passes": false`).
4. Make `scripts/init.sh` and `scripts/test.sh` work for this project's stack: in
   `test.sh`, fill in `environment` (toolchain and installed packages, for the
   fingerprint), `run_full` (the full suite, in parallel where the runner can, writing a
   JUnit XML report), `run_some` and `TESTS_READ_PROSE`. Keep the harness checks first.
5. Record the stack choice as `documents/adr/001-<stack>.md` (see ADR 000), add the
   product's terms to `documents/glossary.md`, and remove its `TEMPLATE PLACEHOLDER`.
6. Create `documents/claude-progress.md` from
   [`documents/templates/claude-progress.template.md`](documents/templates/claude-progress.template.md).
7. Replace the `<…>` placeholders in this file and in `README.md`.
8. Commit: `chore: initialise agent harness`.

---

## Working on a slice

- **One slice per session**, taken from the first `"passes": false` entry in
  `feature-list.json`, unless the slices are trivially small.
- A slice is done only when its end-to-end tests pass via `scripts/test.sh`. Then set its
  `passes` to `true`.
- Update `documents/claude-progress.md` at the end of **every** session, even an
  unfinished one.
- When a slice is done, suggest the [`session-close`](.claude/skills/session-close/SKILL.md)
  skill **before pushing** — it folds progress, learnings and a walkthrough into the same
  PR. The human may skip it.
- If a slice is dragging on, suggest writing up the problem under *Notes for next agent
  session* in the progress log, and adding a new slice that starts with a planning session.
- If no slice is pending, start a discussion with the human about the next objective. Once
  agreed, add the feature to `feature-list.md`, split it into thin end-to-end slices
  (elephant carpaccio), and append them to `feature-list.json`. The next session plans and
  implements the first one.

## Research and investigation

Every slice starts with a short investigation step: before building something, look for an
open standard or maintained library that already does it, and record a significant decision
as an ADR ([ADR 000](documents/adr/000-record-architecture-decisions.md)). For web
research, use the `tavily-*` skills (`tavily-search`, `tavily-extract`, `tavily-research`)
when they are installed and `TAVILY_API_KEY` is set; otherwise fall back to WebSearch /
WebFetch. Cite sources in the ADR. To look for an existing agent skill before writing
one, use [`find-skills`](.claude/skills/find-skills/SKILL.md) and follow its local rules.

---

## Git workflow

Branch per slice: `claude/<slice-id>-<short-description>` (e.g. `claude/<abc>-03-<search-api>`).

**Starting a slice (worktree-safe):**

```bash
git fetch origin
git switch -c claude/<slice-id>-<desc> origin/main
```

Never `git checkout main` / `git switch main` — in a git worktree, `main` is usually
checked out elsewhere and the command fails. If the session was already placed on a
fresh branch (e.g. a worktree the app created), keep it and bring it up to date with
`origin/main` instead of creating another.

**Committing:** stage explicit paths (`git add <paths>`), never `git add -A` / `git add .` —
another session may share the working tree (see
[code-learnings §G-01](.claude/skills/code-learnings/SKILL.md#g-01)).

**Finishing a slice:**

1. `scripts/test.sh` is green.
2. **AI review before the PR** — see *Pre-PR AI review* below.
3. Run session-close (optional).
4. Push the branch, open a PR, then tell the human to merge it. Do not start the next
   slice until they confirm.

### Pre-PR AI review

An independent AI review runs on every slice branch before it is pushed, so human review
can focus on design and depth rather than mechanical bugs.

1. Run the built-in Claude Code **`code-review`** skill at `high` against the branch diff
   (`origin/main...HEAD`). It reviews from a fresh context, not the implementing session's
   reasoning. Other agent tools without that skill: spawn a fresh-context reviewer
   subagent with the diff and this file, and ask for correctness findings only.
2. For slices touching <security-sensitive areas, e.g. authentication, permissions,
   tenancy, secrets, egress, sandboxing>, also run the built-in **`security-review`** skill.
3. Fix confirmed findings, add a regression test where a finding was a real bug, and
   re-run `scripts/test.sh`.
4. In the PR description, add an **AI review** section: the review level, findings fixed,
   and findings not fixed with the reason for each. Never hide a finding.

The AI review supplements human review; it never approves or merges anything.

---

## Directory conventions

- `results/` — **gitignored**. All run outputs, scratch analyses and generated artefacts go
  in `results/<name>_YYYY-MM-DD[_HH-MM]/`. Register each new subdirectory with a one-line row
  in `results/manifest.md` (create it if missing) so local runs stay findable.
- `data/` — **gitignored**. Local input/reference data, same naming and manifest rule.
- `documents/` — tracked human- and agent-authored docs.
- Anything a test depends on must be committed (e.g. under `tests/fixtures/`), never read
  from `results/` or `data/`.

---

## Tests

- `scripts/test.sh` is the only way to run the suite — never hard-code a runner command
  elsewhere. With no arguments it runs the full suite (in parallel where the runner can)
  and records the result with the code's fingerprint in `documents/test-baseline.json`;
  commit that file with the slice, so the next session can skip its baseline
  (`--baseline`). With arguments it runs that subset and records nothing.
- While working, run the tests of the code you change; run the full suite once at the end
  of the slice, after the pre-PR reviews' fixes, so the recorded run is of the code that is
  pushed.
- Test ids must be the same in every process that collects them: never build a parameter
  from a random or time-based value (a parallel runner refuses to start otherwise).
- Run tests in the **foreground** and wait for them. Do not start a test run in the
  background and carry on working.
- If a run hangs, stop it, then re-run a smaller subset in the foreground to isolate it.

---

## When to ask the human

Pause and ask before proceeding if:

- A slice needs an external account or credential (<e.g. OpenAI, Anthropic, Azure>).
- Infrastructure must be provisioned (<e.g. Azure>).
- A slice depends on an open question (`[OQ-n]`) in the product description.
- A decision affects the data model or an API contract.
- Tests fail and the cause is unclear after one investigation pass.
- You are about to delete or overwrite something non-trivial.
