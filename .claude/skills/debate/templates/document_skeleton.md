# Default document skeleton — {{NAME}}

The section order a `/debate` draft follows unless the brief calls for something
else. It exists to make [`conventions.md`](conventions.md) achievable: C3
(front-loaded background) and C9 (appendices) are structural, not stylistic.

Adapt the headings to the subject. Do not drop the appendices.

---

## 1. Abstract

Short. States **what the document will show**, not the evidence for it. If the
body cannot separate two hypotheses, the abstract says so — it may not assert
one of them (C4).

## 2. Introduction

### 2.1 Aim
What question the work was built to answer, and what it was *not* built to
answer.

### 2.2 The players
Every gene, protein, pathway, signature, compartment, cell state and method the
argument will later use, introduced **briefly, with references**, each linked to
its Glossary entry (C2, C3). Assume the reader will not look anything up.

### 2.3 Prior work and the competing hypotheses
The state of the field, and then each candidate interpretation stated in its
**strongest** form, with references (C4 steelman). This is the setup that makes
the argument in §4 intelligible.

## 3. What was run, and on what
Inputs, versions, parameters, units of analysis; the provenance points that
change how a result should be read.

## 4. The argument
Point → counterpoint → synthesis (C4). Where the readings agree; where they
genuinely conflict; what the data can and cannot adjudicate; then the single
narrative that accounts for the observations. Caveats sit where the reader would
raise them, not in a later section.

## 5. Evidence
One subsection per line of evidence. Each asserts a pattern, shows a **figure**
(C6), and footnotes its **source file** (C7). Inset boxes (C5) carry the
background a reader needs at that point.

## 6. Uncertainty and limitations
What the design structurally cannot decide; where a method is out of domain;
what is hypothesis rather than result.

## 7. Future work
Per item: the ambiguity it resolves, what result favours which reading, why it
is needed rather than merely interesting, and its cost.

## Appendix A — Glossary
One anchored entry per term (`### <a id="g-term"></a>TERM — expansion`), each
with a short description and **numbered, hyperlinked references**. Every first
use in the body links here (C2).

## Appendix B — Boxes
Index of the inset boxes, if there are more than a handful.

## Appendix C — Algorithms
Plain-language account of every method whose *behaviour* the argument depends on
(e.g. how a scoring method normalises, how a normalisation is computed) — enough
that a reader can judge the inference without reading the original paper.

## Appendix D — Source definitions
Gene-set membership tables, marker panels, or links to the authoritative
definition of each signature used.

## Appendix E — References
Numbered, hyperlinked, generated with `scripts/link_reference.py`. Grouped by
theme when long — but numbered strictly **in file order** across the groups, or
a renderer will renumber the list and every in-text `[N]` after the first break
will display against the wrong entry (C9). Each entry carries an anchor
(`1. <a id="e1"></a>Author A. *Title.* — [quote](url#:~:text=…)`), every in-text
citation is `[N](#eN)`, and every quote link in the body is followed by the
`[N](#eN)` of its entry (C8). `scripts/fix_citations.py` repairs all three.

## Appendix F — Provenance and verification
Which numbers were re-derived and how; the scripts and their output; citation
verification status; known open items.

---

## Sidecar figure directory

Beside the document, one directory per draft (C6):

```
document_<N>_figs/
  README.md                 # the manifest below
  fig01_<slug>.py           # or .R — the script that produced the figure
  fig01_<slug>.png
```

`document_<N>_figs/README.md`:

```markdown
# Figures for document_<N>.md

| Figure | Script | Input data | Caption |
|---|---|---|---|
| `fig01_<slug>.png` | `fig01_<slug>.py` | `results/<run>/tables/<file>.csv` | … |
```
