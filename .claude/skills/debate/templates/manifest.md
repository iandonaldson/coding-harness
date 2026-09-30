# Debate manifest — {{NAME}}

- Generated: {{CREATED}}
- Produced by: the `/debate` writer↔critic skill (`.claude/skills/debate/`)
- Gitignored: yes (lives under `results/`, per AGENTS.md › Directory conventions)

## Contents (one line per subdirectory / key file)

| Path | Description |
|---|---|
| `document_0.md` | Seed brief: what the document should argue/cover (optional). |
| `document_N.md` | Versioned draft chain — **odd = Writer** draft, **even = Critic** annotated copy + `## Scorecard`. |
| `document_N_figs/` | Figure sidecar for a Writer draft: one script per figure, the rendered figures, and a `README.md` manifest (figure → script → input data → caption). |
| `document_N_human_review.md` | A human markup of a draft, carrying `[[…]]` annotations; feeds the next Writer round. |
| `state.json` | Loop state: round, threshold, max_rounds, last score, status, accepted document, history. |
| `background/` | Shared source material; either agent may add documents and cross-refer. |
| `references/` | Cached retrieved sources (PDFs) + citation-link artifacts. |
| `writer/` | Writer's private `journal.md` (per-round log) + `memory.md` (carry-forward). |
| `critic/` | Critic's private `journal.md` + `memory.md`. |
| `rules/` | `rubric.md` (active scoring scheme), `conventions.md` (standing document conventions C1–C9), `document_skeleton.md` (default structure) + `proposals/` (rule changes awaiting human ratification). |
| `provisioning/` | `requests.md` — tools/skills/connectors an agent wished it had. |
| `README.md` | Human-readable layout + loop guide for this area. |

## Outcome

- Status: _in progress_ (updated in `state.json`; the accepted `document_N.md`, if any,
  is the final record — Critic's copy with the passing scorecard).
