---
name: debate
description: >
  Run an iterative writer↔critic refinement loop over a document until it
  passes a scoring threshold. The main session acts as ORCHESTRATOR: it spawns a
  Writer subagent (drafts) and a Critic subagent (annotates + scores) in
  alternating rounds — they never call each other, they hand off through files
  in a debate area under `results/debate_YYYY-MM-DD_HH-MM/` (gitignored; registered
  in `results/manifest.md` per the AGENTS.md results/ convention) unless the user names another directory. Use this skill whenever the
  user says "start a debate", "run the writer/critic loop", "refine this document
  with a critic", "/debate <name>", "iterate this to a score", or asks to have
  two agents draft-and-critique a document to a quality bar. Also use it to feed a
  human-annotated draft back into the loop — "process my review annotations",
  "I marked up the draft with [[notes]]", "here's my markup, do another round".
  Takes an optional debate name and an optional seed brief (`document_0.md`).
  Drafts obey the standing document conventions in `templates/conventions.md`
  (academic register, define-before-use glossary, front-loaded background,
  narrative thread, inset boxes, figures, data provenance) unless the user
  overrides them. Defers citation-link generation to `scripts/link_reference.py`,
  convention linting to `scripts/audit_document.py`, citation renumbering and
  quote-to-reference pairing to `scripts/fix_citations.py`, and per-agent behaviour to
  the `writer` and `critic` agents in `.claude/agents/`.
---

# debate skill

## When to invoke

Invoke when the user wants a document iteratively drafted and critiqued to a
quality threshold by two cooperating subagents. Typical prompts:

- "/debate climate-adaptation" — start (or resume) a named debate
- "run a writer/critic loop on this brief"
- "refine this until a critic scores it at least 8/10"
- "have two agents draft and critique X"

**Prerequisite:** this skill only works where the orchestrating session has the
`Agent` tool available (interactive Claude Code, or the app surface that exposes
subagents). The Writer/Critic are the `writer` and `critic` agents defined in
`.claude/agents/`. They are spawned via the `Agent` tool with
`subagent_type: "writer"` / `"critic"`.

## Core architecture (read first)

Subagents **cannot call each other**. The loop is driven entirely by YOU, the
orchestrator: spawn Writer → spawn Critic → read the Critic's score → decide stop
or continue. The two agents communicate only through files. Each spawn starts
**cold**, so continuity lives in the debate area (`writer/`, `critic/`, the
`document_N.md` chain), not in agent context. Numbering: **odd = Writer draft,
even = Critic annotated + scored.** A human markup of any draft is saved beside
it as `document_<N>[.<M>]_human_review.md` and feeds the next Writer round
(Step 5b).

Drafts are held to the standing conventions in `rules/conventions.md` — academic
register, define-before-use with a glossary, front-loaded background, a
maintained narrative thread, inset boxes, figures in a sidecar
`document_<N>_figs/`, and a source-file footnote on every number. They are
**on by default**; the human can retune them per debate (Step 4).

## Step 1 — Resolve the debate area

- **Default (no directory indicated by the user):** a fresh timestamped area
  `results/debate_YYYY-MM-DD_HH-MM/`. `results/` is **gitignored** (debate output is
  a local artifact, not tracked), and each area is registered in `results/manifest.md` per
  AGENTS.md › Directory conventions (see Step 2).
  No need to ask — just create it and tell the user the path.
- **If the user names a directory or a bare name** → honor it: a path is used as
  given; a bare `<name>` becomes `results/<name>/`. (A caller who explicitly wants the
  debate tracked in git can point it at, e.g., `documents/debates/<name>/`.)
- If the resolved directory already exists → this is a **resume**: read its
  `state.json` and continue from `round + 1`. Do not overwrite existing
  `document_N.md`, and do not re-register it in the manifest.

## Step 2 — Scaffold (first run only)

Create the area by copying the templates, substituting `{{NAME}}`, `{{CREATED}}`,
and `{{AGENT}}`. For the default location, `NAME`/`DIR` come from a timestamp; for a
user-named area, set them to the resolved name/path from Step 1 instead.

```bash
# Default: fresh timestamped area under gitignored results/. Override DIR/NAME with
# the Step-1 resolved path if the user named one.
TS="$(date +%Y-%m-%d_%H-%M)"; NAME="debate_$TS"; DIR="results/$NAME"
SRC=".claude/skills/debate/templates"
mkdir -p "$DIR"/{background,references,writer,critic,rules/proposals,provisioning}
sed "s/{{NAME}}/$NAME/g; s/{{CREATED}}/$(date +%F)/g" "$SRC/README.md"  > "$DIR/README.md"
sed "s/{{NAME}}/$NAME/g; s/{{CREATED}}/$(date +%F)/g" "$SRC/state.json" > "$DIR/state.json"
sed "s/{{NAME}}/$NAME/g" "$SRC/rubric.md"      > "$DIR/rules/rubric.md"
sed "s/{{NAME}}/$NAME/g" "$SRC/conventions.md" > "$DIR/rules/conventions.md"
sed "s/{{NAME}}/$NAME/g" "$SRC/document_skeleton.md" > "$DIR/rules/document_skeleton.md"
sed "s/{{NAME}}/$NAME/g" "$SRC/requests.md" > "$DIR/provisioning/requests.md"
for A in writer critic; do
  sed "s/{{NAME}}/$NAME/g; s/{{AGENT}}/$A/g" "$SRC/journal.md" > "$DIR/$A/journal.md"
  sed "s/{{NAME}}/$NAME/g; s/{{AGENT}}/$A/g" "$SRC/memory.md"  > "$DIR/$A/memory.md"
done
# Per-area manifest (one-line description per subdirectory)
sed "s/{{NAME}}/$NAME/g; s/{{CREATED}}/$(date '+%F %H:%M')/g" "$SRC/manifest.md" > "$DIR/manifest.md"
```

**Register in the results manifest (AGENTS.md › Directory conventions).** When the area is under `results/` (the
default), add a one-line row to the top-level `results/manifest.md` index so the run is
catalogued (create the index with its header if it does not exist). Skip this for a
user-named area outside `results/`, and skip it on a **resume** of an existing area.

```bash
if [ "${DIR#results/}" != "$DIR" ]; then
  [ -f results/manifest.md ] || printf '# Results Directory Manifest\n\nAll subdirectories are gitignored.\n\n| Subdirectory | Created | Description |\n|---|---|---|\n' > results/manifest.md
  printf '| `%s/` | %s | /debate writer↔critic area — document chain, scorecards, background, references, per-agent notes. |\n' "$NAME" "$(date +%F)" >> results/manifest.md
fi
```

## Step 3 — Determine the brief

- If `document_0.md` exists in the area, use it as the brief.
- Otherwise ask the user what the document should argue/cover, and save their
  answer as `<DIR>/document_0.md` (the area resolved in Step 1).

## Step 4 — Read the rubric and settle the conventions

Read `rules/rubric.md` for `threshold`, `max_rounds`, and `score_max` (defaults
8 / 5 / 10). These, not hard-coded values, govern the loop.

`rules/conventions.md` ships **on by default** — do not ask about it round by
round. Edit its switch block only when the user asks for something different
("keep it informal", "no figures", "skip the glossary"), and tell them which
switch you set:

```yaml
register:  academic        # academic | explanatory | informal
glossary:  required        # required | optional | none
boxes:     required
figures:   required-when-data-accessible
provenance: required
appendices: required
```

The conventions are human-owned like the rubric: an agent may only propose a
change into `rules/proposals/`.

## Step 5 — Run the loop

For `round = 1, 2, 3, …`:

**Odd round → Writer.** Spawn `Agent(subagent_type="writer")` with a prompt that
gives `DEBATE_DIR`, `INPUT_FILE`, `INPUT_KIND` and `OUTPUT_FILE`
(`document_<round>.md`). `INPUT_KIND` is `brief` on round 1 (`document_0.md`),
`human_review` when Step 5b applies, else `critique` (the Critic's latest even
`document_(round-1).md`). Wait for it. Note its returned summary/flags, its
figure count, and any residual `audit_document.py` findings.

**Even round → Critic.** Spawn `Agent(subagent_type="critic")` with `DEBATE_DIR`,
`INPUT_FILE = document_<round-1>.md` (the Writer's latest), and
`OUTPUT_FILE = document_<round>.md`. Wait for it.

After each Critic round:

1. Read `SCORE: <n>/<max>` and `VERDICT:` from the Critic's `document_<round>.md`
   (and its returned summary). Update `state.json` (`round`, `last_score`,
   `last_verdict`, append to `history`).
2. **Stop conditions:**
   - `score ≥ threshold` → set `status: "accepted"`, `accepted_document:
     "document_<round>.md"`; the loop is done.
   - `round ≥ max_rounds` and not yet accepted → set `status: "max_rounds"`;
     stop and report the best-scoring draft for a human decision.
   - otherwise continue to the next (odd) Writer round.

Spawn fresh each round — do NOT reuse a prior agent via SendMessage; the agents'
own `journal.md`/`memory.md` carry continuity across their cold starts.

## Step 5b — Human-review rounds

The human may read any draft and mark it up with `[[double-bracket notes]]`,
saving it beside the original as `document_<N>_human_review.md` (or
`document_<N>.<M>_human_review.md` for a second pass over the same draft). This
is the highest-authority input in the debate — it outranks the Critic's
annotations and any score.

**Before spawning a Writer, check for one:**

```bash
ls -t "$DIR"/document_*_human_review.md 2>/dev/null | head -1
```

If a review file exists that is newer than the last document in the chain — or
the user says "process my markup / my review / my annotations":

1. Spawn the Writer with `INPUT_FILE` = that file and `INPUT_KIND=human_review`;
   `OUTPUT_FILE` is the next **odd** `document_N.md` (so a review of
   `document_4.md` produces `document_5.md`).
2. Record the review in `state.json.history` as
   `{"round": N, "agent": "human", "document": "<review file>"}`. A review may
   arrive **after** a debate was accepted — that reopens it: set
   `status: "in_progress"`, clear `accepted_document`, and carry on numbering
   from the last document rather than starting a new area.
3. When the Writer returns, **read its `## Response to review` table** and check
   it accounts for every annotation: `grep -c '\[\[' <review file>` should match
   the row count. Report any shortfall to the user rather than proceeding.
4. Surface any new files in `rules/proposals/` — an annotation phrased as a
   standing rule ("this should be a built-in behaviour", "do this throughout")
   becomes a convention only when the human ratifies it into
   `rules/conventions.md`. Do that edit yourself once they agree.
5. Then continue the normal loop: the next **even** round is a Critic round over
   the new draft.

If the user hands you a marked-up file that lives outside the debate area, copy
it in under the naming convention first, so the chain stays self-contained.

## Step 6 — Human-in-the-loop gates

- **Rule proposals:** after any round, check `rules/proposals/` for new files. If
  present, **pause** and present the proposal to the user; only apply it (by
  editing `rules/rubric.md` or `rules/conventions.md`) after they ratify. Never
  let an agent change the rules it is scored by.
- **Provisioning requests:** surface any new entries in
  `provisioning/requests.md` to the user (informational; nothing auto-installs).
- **Max rounds hit:** report the score trajectory and ask whether to raise
  `max_rounds`, lower the `threshold`, or accept the best draft.

## Step 7 — Summarize

Report: the accepted (or best) `document_N.md` with a clickable link, the final
score and round count, the Critic's `## Convention check` line, the figure
sidecar path, and any pending proposals/provisioning items. Point the user at
the Critic's copy (annotations + scorecard) and the last clean Writer draft, and
tell them how to mark it up: copy it to `document_<N>_human_review.md`, add
`[[notes]]`, and the next round will resolve every one (Step 5b).

## Citation → source → highlighted link (the central capability)

Agents must turn a supporting reference into a clickable link that lands the
reader on the source with the passage highlighted where possible. **Tiered, best
available wins** — always via the helper, never hand-written fragments:

```bash
python3 .claude/skills/debate/scripts/link_reference.py \
  --locator "<url | references/file.pdf>" --quote "<exact supporting sentence>" \
  --ref <reference-list entry number> \
  [--page N] [--title "label"] [--format link|block]
```

`--ref` appends the paired `[N](#eN)` after the link. A highlight shows the
reader the passage but never says which numbered source it is, so the pairing is
what lets a reviewer audit the bibliography without opening every URL (C8).

- **Tier 1 — Web:** emits a Chrome/Edge text-fragment URL
  (`…#:~:text=<quote>`) that scrolls to and **highlights** the passage. Verify
  the passage first with `tavily-extract` (query-focused chunking) or `WebFetch`.
  **Two hard requirements for the highlight to actually fire:** (1) the `--quote`
  must be a **verbatim substring** of the rendered page — a paraphrase silently
  fails to match (confirmed in testing); pull the exact wording from the source,
  don't retype it from memory. (2) The highlight activates only on
  **user-initiated navigation** (a real click / typed URL) in a Chromium browser;
  it may not fire in programmatic/automated contexts, and Chrome strips the
  `:~:text=` directive from `location.hash` after applying it (expected, not a
  bug). Non-Chromium viewers ignore the directive and simply open the page.
- **Tier 2 — PDF:** emits `references/<file>.pdf#page=N`. Find the page with the
  `pdf-explore` skill (`pdf_scan` → `{page, text}`); resolve papers to a source
  first via pubmed `lookup_article_by_citation` / biorxiv `get_preprint`; cache
  the PDF under the debate's `references/`.
- **Tier 3 — Fallback:** a plain link plus a blockquote of the passage with a
  `source, p.N` caption — always available, never fabricated.

**Phase 2 research path (not in v1):** exact in-PDF passage highlighting via
`pdfplumber` bounding boxes + PyMuPDF annotations, or an HTML page-image overlay
using `pdf-explore`'s `pdf_pages(mode="image")`. Only page-level PDF anchoring is
guaranteed in v1.

## Convention linting (`audit_document.py`)

Mechanical screen for the conventions a fast read misses. The Writer runs it on
its own draft before returning; the Critic runs it first and then confirms each
hit by hand.

```bash
python3 .claude/skills/debate/scripts/audit_document.py <document.md> \
  [--format md|json] [--only CHECK,…] [--skip CHECK,…] [--summary-only] [--strict]
```

| Check | Convention | Catches |
|---|---|---|
| `unresolved-annotation` | — | a `[[…]]` or `[CRITIC: …]` marker left in a draft |
| `undefined-term` | C2 | acronym/gene symbol used with no expansion and no glossary link |
| `late-introduction` | C3 | a load-bearing term first used after the Introduction |
| `unsourced-data-claim` | C7 | numbers or tables with no source-file footnote |
| `figureless-data-block` | C6 | a data-bearing section with no figure |
| `register` | C1 | second person, colloquialism, unhedged interpretation |
| `unsourced-attribution` | C8 | "marker / signature / hallmark of" with no citation |
| `broken-anchor` | C9 | `](#…)` matching no heading or anchor |
| `reference-numbering` | C9 | a reference list numbered out of file order (renderers renumber it, so in-text `[N]` misdirects), a citation with no entry, citations left as plain text, or an entry nothing cites |
| `quote-without-reference` | C8 | a highlighted `#:~:text=` quote link not followed by a `[N](#eN)` naming its source |

Output is **candidates, not verdicts** — C4 (narrative thread, steelmanning,
abstract↔conclusion consistency) is not mechanically checkable and remains the
Critic's own work.

The last two are the only checks with a **mechanical repair**: renumbering the
entries in file order, relinking every in-text `[N]`, and pairing every quote
link with its entry is deterministic, so a Writer should never do it by hand.

```bash
python3 .claude/skills/debate/scripts/fix_citations.py <document.md> --in-place
```

It reports anything it could not resolve — a quote URL no entry cites, or a URL
two entries claim — and is idempotent, so it is safe to run every round.

## Anti-patterns

- ❌ Letting the Writer and Critic try to invoke each other. They can't; the
  orchestrator drives every hand-off.
- ❌ Reusing a warm agent across rounds instead of fresh spawns + file memory.
- ❌ Applying a rule-change proposal without human ratification.
- ❌ Hand-writing `#:~:text=` URLs instead of using `link_reference.py`.
- ❌ Fabricating a citation anchor for a source you did not actually retrieve.
- ❌ Shipping a Writer draft that still contains `[[…]]` or `[CRITIC: …]`.
- ❌ Treating a linter candidate as a confirmed defect without opening the line.
- ❌ Accepting a draft whose concepts first appear in its conclusions, whose
  numbers name no source file, or that addresses the reader in the second person.
- ❌ Applying a human annotation phrased as a general rule at only the one spot
  it was written.
- ❌ Continuing past `max_rounds` silently, or accepting below `threshold`.
- ❌ Overwriting existing `document_N.md` on resume.

## Checklist before reporting done

- [ ] Debate area scaffolded with all subdirs (`background/`, `references/`,
      `writer/`, `critic/`, `rules/proposals/`, `provisioning/`) and
      `rules/{rubric,conventions,document_skeleton}.md`.
- [ ] Brief captured in `document_0.md`.
- [ ] Alternating `document_N.md` chain present (odd Writer, even Critic), plus
      a `document_<N>_figs/` sidecar per Writer draft that asserts data.
- [ ] Any `document_*_human_review.md` routed to a Writer round, and its
      annotation count matched by the draft's `## Response to review` table.
- [ ] Every Critic file ends with a `## Convention check` block and a
      machine-readable `SCORE:`/`VERDICT:`.
- [ ] `state.json` reflects final `round`, `status`, `last_score`,
      `accepted_document` (and any `agent: "human"` review rounds).
- [ ] Each agent's `journal.md`/`memory.md` updated each round.
- [ ] Pending `rules/proposals/` and `provisioning/requests.md` surfaced to the
      human.
- [ ] `python3 .claude/skills/debate/scripts/test_link_reference.py`,
      `test_audit_document.py` and `test_fix_citations.py` pass.
- [ ] `audit_document.py` on the accepted draft reports no
      `unresolved-annotation`, `reference-numbering` or `quote-without-reference`
      findings.

## Further reading

- Writer / Critic behaviour: [`.claude/agents/writer.md`](../../agents/writer.md),
  [`.claude/agents/critic.md`](../../agents/critic.md)
- Standing conventions: [`templates/conventions.md`](templates/conventions.md);
  default structure: [`templates/document_skeleton.md`](templates/document_skeleton.md)
- Citation helper: [`scripts/link_reference.py`](scripts/link_reference.py);
  convention linter: [`scripts/audit_document.py`](scripts/audit_document.py);
  citation repair: [`scripts/fix_citations.py`](scripts/fix_citations.py)
- Scaffold templates: [`templates/`](templates/)
