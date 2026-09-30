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
| [`documents/feature-list.json`](documents/feature-list.json) | **Single source of truth for slice status** (`passes`) | Agent — see rules below |
| `documents/claude-progress.md` | Session hand-off log (created by the initializer) | Agent, every session |
| [`scripts/init.sh`](scripts/init.sh) | Set up the dev environment + smoke test | Initializer, then as needed |
| [`scripts/test.sh`](scripts/test.sh) | Run the full test suite — the only test entry point | Initializer, then as needed |
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
4. **Baseline** — run `scripts/test.sh`. If it is red, stop and investigate before
   touching anything (see *When to ask the human*).
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
4. Make `scripts/init.sh` and `scripts/test.sh` work for this project's stack.
5. Create `documents/claude-progress.md` from
   [`documents/templates/claude-progress.template.md`](documents/templates/claude-progress.template.md).
6. Replace the `<…>` placeholders in this file and in `README.md`.
7. Commit: `chore: initialise agent harness`.

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

**Finishing a slice:** run session-close (optional), push the branch, open a PR, then
tell the human to merge it. Do not start the next slice until they confirm.

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
  elsewhere.
- Run tests in the **foreground** and wait for them. Do not start a test run in the
  background and carry on working.
- If a run hangs, stop it, then re-run a smaller subset in the foreground to isolate it.

---

## When to ask the human

Pause and ask before proceeding if:

- A slice needs an external account or credential (<e.g. OpenAI, Anthropic, Azure>).
- Infrastructure must be provisioned (<e.g. Azure>).
- A decision affects the data model or an API contract.
- Tests fail and the cause is unclear after one investigation pass.
- You are about to delete or overwrite something non-trivial.
