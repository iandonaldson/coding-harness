---
name: code-learnings
description: >
  Durable index of lessons learned in development sessions: generic lessons
  (G-NN) that apply to any project, and project lessons (L-NN) numbered
  L-01, L-02, …. Read the index at session startup (AGENTS.md › Session startup)
  and append at session close when a non-obvious bug, workflow constraint, or
  successful unusual approach was discovered. Use this skill whenever the user
  asks to "add a learning", "record a lesson", "save what we just learned", to
  write up a post-mortem finding, or to reference a lesson by ID ("L-12",
  "G-03"). Trigger even when the user just says "this is worth remembering" or
  "we should write this down for future agents". Do not invent learnings —
  every project entry must cite a specific PR, commit, or incident.
---

# code-learnings

Lessons that are **not derivable from reading the current code**. Read the index at
session startup; open individual entries when they look relevant.

- **Generic lessons (G-NN)** ship with the harness template and apply to any project.
- **Project lessons (L-NN)** start empty and accumulate for this project.

## Adding a project lesson

Add one when a session hit a subtle bug that took more than one investigation pass, a
non-obvious workflow constraint, a plan that had to be corrected mid-session, or an unusual
approach the human explicitly confirmed. Do **not** add lessons that restate `AGENTS.md`,
describe how the code works (that belongs in a walkthrough), or record a one-off fix with no
general principle.

1. Take the next free `L-NN` number and add a row to the index.
2. Append the entry under *Project lessons* using this template:

```markdown
<a id="l-NN"></a>
## L-NN: <rule-shaped statement>

**Lesson (YYYY-MM-DD — <slice-id>, PR #N):** <symptom, then root cause>

**Rule:** <actionable guidance>

**Detection:** <optional: a grep / test / command that catches it>

See §G-NN / §L-NN for related lessons.
```

A lesson that later proves useful beyond this project can be promoted to a G-NN entry in the
harness template repo.

---

## Index

| ID | Lesson |
|---|---|
| [G-01](#g-01) | Concurrent sessions can share one working tree — stage explicit paths, don't move HEAD |
| [G-02](#g-02) | New agents/skills files register only in a new session |
| [G-03](#g-03) | Verify an agent's self-report against the artefact |
| [G-04](#g-04) | A negative assertion must be proven able to fail |
| [G-05](#g-05) | A self-consistent pair of stale values passes a consistency check |
| [G-06](#g-06) | `--dry-run` / lint is necessary, not sufficient |
| [G-07](#g-07) | A missing artefact in an old run is not a missing feature |
| [G-08](#g-08) | A rubric that scores what is present cannot see what is missing |
| [G-09](#g-09) | Editing a template does not update copies scaffolded from it |
| [G-10](#g-10) | Comparing generated outputs: pin the RNG and the environment |
| [G-11](#g-11) | Markdown renumbers ordered lists on render |
| [G-12](#g-12) | GitHub heading anchors delete punctuation — ` / ` becomes `--` |
| [G-13](#g-13) | Text-fragment (`#:~:text=`) links need a verbatim quote |
| [G-14](#g-14) | `set -u` doesn't fire inside a short-circuited `[[ a && b ]]` |
| [G-15](#g-15) | macOS has no `timeout`; treat exit 127 as a hard error |
| — | *No project lessons yet* |

---

## Generic lessons

<a id="g-01"></a>
## G-01: Concurrent sessions can share one working tree — stage explicit paths, don't move HEAD

**Lesson:** Two agent sessions working in the same directory share one HEAD. A sibling's
commit landed in the middle of another session's branch history, and a `git checkout -b` by
one session would have moved HEAD under the other. Authorship didn't help, because both
sessions commit as the same git identity.

**Rule:** (1) `git add <explicit paths>`, never `git add -A` / `.`; (2) don't switch or create
branches while a sibling session is active in the same tree — prefer one worktree per
session; (3) trace who did what with `git reflog` and `git branch --contains`, not
`git log --author`; (4) never rebase or force-push a branch another session is using.

**Detection:** `git worktree list` — a single line means every session shares one tree.

<a id="g-02"></a>
## G-02: New agents/skills files register only in a new session

**Lesson:** A session wrote `.claude/agents/writer.md` and then tried to spawn
`subagent_type: "writer"` — "agent type not found". Agent definitions are enumerated at
session start. (User-level skill *edits* may be picked up live, but don't rely on it.)

**Rule:** If a session both creates and needs a custom agent, test it through the generic
agent with a prompt that reads the new role file, or defer the real run to a fresh session.

<a id="g-03"></a>
## G-03: Verify an agent's self-report against the artefact

**Lesson:** A subagent's "response to review" table claimed a document grew to ~14k words; the
real count was 22.5k. Its analytical claims were all correct — the error was in the claim
about *its own output*, which was narrated from impression, not measured.

**Rule:** Treat "all N fixed", "tests pass", word counts and similar self-reports as
assertions to check. Prefer computed evidence (`wc -w`, exit codes, diff counts) and have the
orchestrator or reviewer re-derive narrated claims.

<a id="g-04"></a>
## G-04: A negative assertion must be proven able to fail

**Lesson:** A test asserted "no row where field == `go_bp`" on a CSV whose fields were
quoted (`"go_bp"`). The equality never matched, so the absence check passed trivially —
whether or not the row existed.

**Rule:** When an "assert absent" check passes first time, prove it can fail (invert it
temporarily, or look at the raw data it matches against). Assert against the artefact's real
serialisation, and prefer quote-independent signals (file globs, `grep -c` on a distinctive
substring) for absence.

<a id="g-05"></a>
## G-05: A self-consistent pair of stale values passes a consistency check

**Lesson:** A renumbering fixer rewrote `[N](#eN)` citations but its regex skipped a second
idiom (`[ref N](#eN)`). Those links kept a stale label *and* a stale target. Every check —
label matches target, target resolves — passed, and 20 citations pointed at the wrong source.

**Rule:** After a transformation that rewrites identifiers, verify against what the identifier
*denotes* (same entry before and after), not mutual consistency. Before writing a mechanical
fixer, enumerate the surface forms actually present (`grep` and count), and make the fixer
report what it did not touch.

<a id="g-06"></a>
## G-06: `--dry-run` / lint is necessary, not sufficient

**Lesson:** An infrastructure wrapper validated only by `bash -n`, shellcheck and `--dry-run`
failed twice on its first real run (a re-mount on an already-mounted share, a root-owned work
dir). A long command run attached over SSH then reported failure (`rc=255` from an idle
timeout) although the job had actually finished.

**Rule:** A script that provisions infra or drives a remote host is unproven until one real
end-to-end run. Run long remote jobs detached and poll; before believing a non-zero exit code,
inspect the actual outputs.

<a id="g-07"></a>
## G-07: A missing artefact in an old run is not a missing feature

**Lesson:** A request to "add X to the workflow if it isn't there" was prompted by an old run
directory that lacked X. The workflow had gained X sixteen days *after* that run.
Reimplementing it would have produced a second, divergent helper.

**Rule:** In a repo of dated run directories, an absent artefact tells you about that run's
code, not today's. `grep` for the artefact name and compare the slice's merge date with the
run date (`git log -S '<name>' --format='%ad %h %s'`). If it already exists, the job is a
backfill using the shipped helpers.

<a id="g-08"></a>
## G-08: A rubric that scores what is present cannot see what is missing

**Lesson:** A reviewer agent scored a generated document 9.7/10 against criteria like
accuracy and clarity. The human then found over a hundred defects — almost all *omissions*
(no glossary, no figures, unsourced numbers, concepts introduced only in the conclusion).
Re-scored with omission-aware criteria, the same document got 5.8/10.

**Rule:** Give review rubrics criteria whose failure mode is omission, and make the reviewer
enumerate ("list every acronym's first use", "name the source for each number"). Treat an
absence as a defect located where the reader needs the missing thing. Back it with a
mechanical screen, with a human or agent confirming each hit.

<a id="g-09"></a>
## G-09: Editing a template does not update copies scaffolded from it

**Lesson:** A skill scaffolds each run with its own copy of `rules/*.md`. A convention was
ratified into the skill's templates, but the live run kept scoring against its older copy and
passed a document that broke the new rule.

**Rule:** When a template that runs copy at scaffold time changes, re-copy it into every live
run you will continue, and tell the next agent which rules changed.

**Detection:** `diff <template> <run>/rules/<file>` before continuing a run.

<a id="g-10"></a>
## G-10: Comparing generated outputs: pin the RNG and the environment

**Lesson:** Rendering the *same* data twice produced different images because a plotting
function used jitter, which consumes the RNG. Comparing against an image rendered on another
OS or library version gave 34% pixel differences from font rasterisation alone.

**Rule:** To prove two paths produce the same output, generate both in the same process with
the seed set immediately before each, and assert on the underlying data separately. Treat
cross-environment comparisons as visual evidence for a human, never as a pass/fail gate.

<a id="g-11"></a>
## G-11: Markdown renumbers ordered lists on render

**Lesson:** A reference list authored as `1–6, 38, 39, 7–11, …` rendered as `1, 2, 3, …`
because CommonMark takes the first number and increments. In-text `[28]` pointed at whatever
displayed as #28.

**Rule:** Number ordered lists strictly in file order. When adding an entry, append or
renumber everything. Link citations to anchors (`[28](#e28)`) so clicks survive renumbering.

<a id="g-12"></a>
## G-12: GitHub heading anchors delete punctuation — ` / ` becomes `--`

**Lesson:** The anchor for `### Memory / resource requirements` is
`#memory--resource-requirements`. GitHub lowercases, *deletes* non-`[a-z0-9 -]` characters and
maps each space to `-`. A wrong anchor fails silently — the page opens at the top.

**Rule:** Derive slugs mechanically, expect double hyphens around removed punctuation, and
verify against the rendered heading. Where precision matters, add an explicit
`<a id="…"></a>` (as this file does).

<a id="g-13"></a>
## G-13: Text-fragment (`#:~:text=`) links need a verbatim quote

**Lesson:** A paraphrased quote produced a valid-looking `#:~:text=` link that silently did
nothing. Chromium also applies the highlight only on user-initiated navigation, and strips the
directive from `location.hash`.

**Rule:** Treat text-fragment links as best-effort presentation. Confirm the quote is a
byte-for-byte substring of the rendered source first, and keep a visible blockquote fallback.

<a id="g-14"></a>
## G-14: `set -u` doesn't fire inside a short-circuited `[[ a && b ]]`

**Lesson:** In `[[ -n "$GTF" && -n "$FASTA" ]]`, `$FASTA` was unset, but because `$GTF` was
empty the `&&` short-circuited and `set -euo pipefail` never saw it. The script produced a
wrong result instead of failing.

**Rule:** Don't rely on `set -u` to catch unset variables inside compound conditions.
Initialise variables explicitly (`: "${FASTA:?}"`) before using them.

<a id="g-15"></a>
## G-15: macOS has no `timeout`; treat exit 127 as a hard error

**Lesson:** `timeout 560 docker wait …` on macOS exited 127 (command not found) instantly. The
guard only special-cased 124, so the wait silently no-op'd and the job was believed finished.

**Rule:** Don't assume GNU coreutils on macOS (`timeout` is `gtimeout` via Homebrew). Prefer the
agent tool's own timeout. When branching on a wrapper's exit code, treat 127 as an error.

---

## Project lessons

*None yet.*
