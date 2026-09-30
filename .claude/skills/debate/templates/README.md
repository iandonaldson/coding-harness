# Debate: {{NAME}}

A writer↔critic iterative-refinement debate, driven by the `/debate` skill.
The **orchestrator** (the main Claude session) spawns the Writer and Critic
subagents in alternating rounds; they never call each other — they hand off
through the files here.

## Layout

| Path | Owner | Purpose |
|---|---|---|
| `document_0.md` | human/orchestrator | The seed **brief**: what the document should argue/cover. Optional — if absent the orchestrator asks for it. |
| `document_1.md`, `document_3.md`, … | Writer | Odd = Writer drafts. |
| `document_2.md`, `document_4.md`, … | Critic | Even = Critic's annotated copy + `## Convention check` + `## Scorecard`. |
| `document_N_figs/` | Writer | Figure sidecar: one script per figure, the figures, and a manifest (figure → script → input data → caption). |
| `document_N_human_review.md` | human | Your markup of a draft, using `[[double-bracket notes]]`. Feeds the next Writer round and outranks the Critic. |
| `background/` | shared | Source material. Either agent may **add** documents and cross-refer. |
| `references/` | shared | Cached retrieved sources (PDFs) + citation-link artifacts. |
| `writer/` | Writer | `journal.md` (per-round log) + `memory.md` (carry-forward reminders). |
| `critic/` | Critic | `journal.md` + `memory.md`. |
| `rules/rubric.md` | human | Active scoring scheme. Agents may propose changes into `rules/proposals/`; **only the human ratifies** them. |
| `rules/conventions.md` | human | Standing document conventions C1–C9 (register, glossary, front-loaded background, narrative thread, boxes, figures, provenance, citations, appendices) + the switches that turn them off. |
| `rules/document_skeleton.md` | human | Default section order that makes the conventions achievable. |
| `provisioning/requests.md` | agents | Tools/skills/connectors an agent wishes it had. |
| `state.json` | orchestrator | Loop state: round, threshold, max_rounds, last score, status. |
| `manifest.md` | orchestrator | Contents manifest for this area (gitignored under `results/`). |

## The loop (owned by the orchestrator)

1. Writer reads the latest handoff → writes the next odd `document_N.md` (plus
   its `document_N_figs/` sidecar), against `rules/rubric.md` and
   `rules/conventions.md`.
2. Critic reads it → writes the next even `document_N.md` with inline
   `[CRITIC: category=… severity: …]` notes, a `## Convention check` block and a
   `SCORE: n/max` / `VERDICT:` scorecard.
3. If score ≥ threshold → **accept** that document as final. Else if
   `round == max_rounds` → stop and report best-so-far. Else → back to step 1.

**Human review at any point.** Copy a draft to
`document_<N>_human_review.md`, mark it up with `[[notes]]`, and tell the
orchestrator. The Writer must resolve every annotation and account for it in a
`## Response to review` table; annotations phrased as general rules become
proposals in `rules/proposals/` for you to ratify into `rules/conventions.md`.

## Final document

When the loop accepts, the accepted even-numbered `document_N.md` (Critic's copy)
is the record of the final text + its passing scorecard. The last Writer draft
that produced it is the clean prose.
