# Scoring rubric — {{NAME}}

**Active scoring scheme for this debate.** The Critic scores every draft against
the criteria below, which score the standing conventions in
[`conventions.md`](conventions.md). Agents may *propose* changes by writing a
file into `rules/proposals/`, but a change only takes effect once the **human
ratifies** it and edits this file. Until then, the Critic scores against this
version.

## Scale and stop condition

- **Scale:** 0–10 (integer or one decimal).
- **Threshold to accept:** **8** / 10.
- **Max rounds:** **5** (a writer+critic pair counts as two rounds:
  `document_1`+`document_2` = rounds 1–2, etc.). If the threshold is not reached
  by the max, the loop stops and reports the best-scoring draft for a human call.

## Criteria (weighted; sum of weights = 10)

| # | Criterion | Weight | Conventions | What "excellent" looks like |
|---|---|---:|---|---|
| 1 | **Accuracy & evidence** | 2 | C8 | Every factual claim is correct and backed by a *verifiable* citation link whose quoted passage genuinely supports it — the most directly supporting passage, from full text where the abstract will not carry it. No fabricated or misquoted sources. Marker/attribution claims are referenced; context transferred from another disease, model or species is flagged; statistical claims state significance or are labelled descriptive. |
| 2 | **Argument & reasoning** | 2 | C4 | Claims follow logically; opposing positions are steelmanned before being reframed, and resolved point→counterpoint→synthesis; caveats sit where the reader would raise them; the abstract is consistent with what the body concludes; post-hoc interpretation is labelled as such; no fallacies. |
| 3 | **Completeness** | 1 | — | Covers the scope set by the brief; no material gap or unsupported leap. |
| 4 | **Narrative thread & accessibility** | 2 | C2, C3, C5, C9 | Reads linearly, once, without lookups: every term expanded and glossary-linked at first use; every player introduced with references in the Introduction before the argument uses it; nothing arrives "out of left field"; assumed knowledge sits in referenced inset boxes; the appendices (glossary, algorithms, source definitions, references, provenance) exist and are linked from the prose; no repetition. |
| 5 | **Data provenance & figures** | 1.5 | C6, C7 | Every asserted data pattern carries a figure whose generating script and input file are in the sidecar manifest; every number, table and range carries a footnote naming its source file. |
| 6 | **Register & tone** | 0.5 | C1 | Academic, impersonal, objective throughout; no second person, no colloquialism; interpretations hedged to the strength of their evidence. |
| 7 | **Responsiveness** | 1 | — | The prior round's critique **and every human `[[…]]` review annotation** were addressed — fixed, or reasonably rebutted in writing — not dropped. |

Round 1 has no prior critique, so criterion 7 scores full by default.

## Scorecard format the Critic must emit

At the end of each even `document_N.md`:

```
## Convention check
- C1 register: FAIL — second person in §1; "the quiet hero" §2.1
- C2 define-before-use: FAIL — ISG, EMT, NES, ICD undefined at first use; no glossary
- C3 front-loaded background: FAIL — Hippo/YAP-TAZ first appear in §4.3
- C4 narrative thread: PARTIAL — abstract asserts composition; §4.2 leaves it open
- C5 inset boxes: PARTIAL — myCAF/iCAF boxed; M1/M2 and tumour anatomy not
- C6 figures: FAIL — no figures; data reachable under results/
- C7 data provenance: FAIL — §5.2 tables carry no source-file footnote
- C8 citation depth: PASS
- C9 structure & appendices: FAIL — no glossary, algorithms or source-definition appendix

## Scorecard
- Accuracy & evidence (2): 1.9 — one figure mismatched its source (fix needed)
- Argument & reasoning (2): 1.5 — abstract/conclusion inconsistency
- Completeness (1): 1
- Narrative thread & accessibility (2): 0.8 — no glossary; three late introductions
- Data provenance & figures (1.5): 0.2 — no figures, no source footnotes
- Register & tone (0.5): 0.2
- Responsiveness (1): 1
SCORE: 6.6/10
VERDICT: REVISE
Top changes to raise the score: 1) … 2) … 3) …
```

The `SCORE: <n>/<max>` line MUST appear exactly like that (machine-read by the
orchestrator). `VERDICT:` is `ACCEPT` if score ≥ threshold, else `REVISE`.
