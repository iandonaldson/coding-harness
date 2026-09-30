# Document conventions — {{NAME}}

**Standing conventions for every draft in this debate.** These are the default
behaviour of `/debate`. They are *human-owned*, exactly like `rubric.md`: the
Writer and the Critic both read this file every round, and neither may edit it —
an agent that wants a change writes a proposal into `rules/proposals/`.

To turn a convention off or retune it for this debate, edit the switch block
below (or tell the orchestrator at invocation time and it will edit it for you).

```yaml
register:  academic        # academic | explanatory | informal
glossary:  required        # required | optional | none
boxes:     required        # required | optional | none
figures:   required-when-data-accessible   # required | required-when-data-accessible | optional | none
provenance: required       # required | optional  (source-file footnote per number)
appendices: required       # required | optional
```

The rubric criteria in [`rubric.md`](rubric.md) score these conventions:
C1 → *Register & tone*; C2, C3, C5, C9 → *Narrative thread & accessibility*;
C4 → *Argument & reasoning*; C6, C7 → *Data provenance & figures*;
C8 → *Accuracy & evidence*.

---

## C1 — Register

**Writer.** Write in a disciplined, objective, academic register. No second
person and no address to the commissioner of the document; refer to a prior
position impersonally. No colloquialism, no rhetorical flourish, no
self-congratulation. Hedge every claim to the strength of its evidence:
observations are stated as observations, interpretations as interpretations.

**Critic.** Flag second-person pronouns, informal idiom, and interpretive claims
stated as fact. `category=register`.

| Instead of | Write |
|---|---|
| "Your original directional read of the Hallmark GSVA figure…" | "An early and superficial reading of the Hallmark GSVA scores…" |
| "Both are reported below rather than smoothed over." | "Both are reported below." |
| "The stromal transcripts are genuinely leaving." | "This is consistent with loss of the stromal compartment and its transcripts." |
| "That is what losing a myofibroblast compartment looks like." | "This would be consistent with loss of a myofibroblast compartment." |
| "…but it is best read as the transcriptional core of…" | "…but may be best interpreted as the transcriptional core of…" |
| "The Mock-vs-Mock comparison is the quiet hero of the design." | "The Mock-vs-Mock comparison is the strongest element of the design." |
| "…which is scientifically comfortable and epistemically dangerous." | "…which creates a risk of confirmation bias, addressed in §N by …" |

## C2 — Define every term before use

**Writer.** Expand every acronym, gene symbol, protein, pathway, signature,
method and cell-state name at its **first** use, and link that first use to an
entry in the Glossary appendix. Every later mention links to the same anchor.
The Glossary entry carries a one-to-three sentence description and **numbered,
hyperlinked references** — the reader must be able to check the claim that a
gene marks a compartment without leaving the document.

```markdown
…an interferon-stimulated-gene ([ISG](#g-isg)) programme…

<!-- Appendix A -->
### <a id="g-isg"></a>ISG — interferon-stimulated gene
Genes transcriptionally induced downstream of type I/II interferon receptor
signalling … See refs [12], [13].
```

**Critic.** For each acronym/gene symbol, find its first occurrence and check it
is expanded and glossary-linked, and that the Glossary entry carries references.
`category=glossary`.

## C3 — Front-load the background

**Writer.** The Introduction introduces **all** the players the argument will
later rely on — genes, proteins, signatures, pathways, compartments, methods —
briefly, with references, before any of them is used in an argument. The purpose
is that a reader meeting the competing hypotheses can already evaluate them.
Keep the introductory description short; the detail belongs in the Glossary and
in inset boxes.

No concept may make its first appearance in the Evidence, Discussion or
Conclusion sections. If the argument needs it, the Introduction owes it.

**Critic.** Sweep for concepts whose first mention falls after the Introduction
("out of left field") and annotate at that first mention, naming the Introduction
subsection where it should have been introduced. `category=late-intro`.

## C4 — Maintain the narrative thread

**Writer.** The document is read once, linearly, by a human. Think of the
bouncing ball above song lyrics: it must trace a continuous path through the
argument, such that a reader who accepts each step in turn is carried to the
conclusion.

- **Point → counterpoint → synthesis** when introducing an opposing idea:
  state the position, state the objection, resolve it.
- **Steelman.** State any position the document will argue against in its
  strongest, referenced form *before* reframing it. Do not paraphrase it into a
  weaker claim, and do not delete it once it has been reframed — the contrast is
  what makes the new reading intelligible.
- **Caveats where the reader would insert them**, not in a later section.
- **Consistency.** The abstract states only what the body demonstrates. If the
  body ends with two competing hypotheses that the data cannot separate, the
  abstract may not assert one of them.
- **Label post-hoc reasoning as post-hoc.** An interpretation reached after
  seeing the data is not a prediction the data confirmed.
- **Method motivation.** When an analysis is introduced, state the ambiguity it
  was meant to resolve and why it was performed, before its results.

**Critic.** Audit abstract↔conclusion consistency; check that each opposing
position appears in a strong, referenced form; flag post-diction presented as
prediction and analyses whose motivation is never stated. `category=narrative`
and `category=consistency`.

## C5 — Inset boxes for assumed knowledge

**Writer.** Background that a specialist treats as common knowledge but a
competent general reader may not, goes in an inset box with references, placed at
or linked from the point of use:

```markdown
> **Box 3 — M1 and M2 macrophage states.** …two-to-four sentences… Refs [21], [22].
```

Boxes carry anatomy, receptor biology, marker-panel definitions, and any
mechanism the argument leans on. Link to a box from the prose that needs it.

**Critic.** Where the prose assumes knowledge that is not in a box, the
Glossary or the Introduction, annotate at that point. `category=narrative`.

## C6 — Figures where the text asserts data

**Writer.** Where the text asserts a pattern in data — a change in expression, a
distribution, a time course, a per-sample comparison — accompany it with a
figure. Figures and the code that generates them live in a **sidecar directory
beside the document**, so data and process provenance are traceable:

```
document_<N>_figs/
  README.md              # manifest: figure -> script -> input data file -> caption
  fig01_caf_markers.py   # one script per figure (or one script, clearly sectioned)
  fig01_caf_markers.png
```

Every figure is referenced from the prose (`![Fig 1 — …](document_<N>_figs/fig01_caf_markers.png)`),
has a caption naming the data source, and has a manifest row. When the switch is
`required-when-data-accessible` and the underlying data is not reachable from the
debate area, state that in the text instead of omitting silently.

**Critic.** For each data-bearing passage, check a figure exists, resolves, is
referenced, and that its script and input file are named in the manifest.
`category=figure`.

## C7 — Data provenance

**Writer.** Every number, table, range and percentage carries a hyperlinked
footnote naming the file it came from, and the script that derived it if it was
not read directly:

```markdown
COL1A1 falls from 10,500 CPM to 74 CPM.[^cpm]

[^cpm]: `results/production_2026-06-30/human/counts/human_counts.txt`, via
        `background/verification/percpt.py`.
```

**Critic.** Any numeric claim without a resolvable source is a defect.
`category=provenance`.

## C8 — Citation depth and context transfer

**Writer.**

- Quote the passage that **most directly** supports the claim. If the abstract
  does not contain it but an open-access full text does (e.g. PMC), retrieve the
  full text and cite that.
- Every attribution of a marker to a compartment, cell type or pathway
  ("FAP is a CAF marker", "KRT8 is epithelial") carries a reference — a Glossary
  entry with references satisfies this.
- **Flag context transfer.** Evidence from a different disease, tissue, model or
  species must be labelled as such where it is used, with a sentence on why it
  is expected to carry over.
- State significance for any statistical claim, or label the claim descriptive.
- Never fabricate an anchor; generate every link with
  `scripts/link_reference.py`.
- **Pair every highlighted quote with its numbered source.** A `#:~:text=` link
  takes the reader to the passage but never says *which* reference it is, so a
  reviewer auditing the bibliography cannot tie quote to entry without opening
  the URL and matching it by hand. Every quote link is immediately followed by a
  hyperlinked `[N](#eN)`:

  | | |
  |---|---|
  | Instead of | `…adenovirus receptor (CAR) — [The cellular internalization … is mediated by the initial attachment of the … fiber protein](https://pubmed.ncbi.nlm.nih.gov/30125593/#:~:text=…).` |
  | Write | `…adenovirus receptor (CAR) — [The cellular internalization … is mediated by the initial attachment of the … fiber protein](https://pubmed.ncbi.nlm.nih.gov/30125593/#:~:text=…) [12](#e12).` |

  The helper emits the paired form directly — pass the entry number:

  ```bash
  python3 .claude/skills/debate/scripts/link_reference.py \
    --locator "https://pubmed.ncbi.nlm.nih.gov/30125593/" \
    --quote "<exact supporting sentence>" --ref 12
  ```

**Critic.** Verify quotes verbatim; check attributions carry references; flag
untransferred context and unquantified statistical claims; check that quote
links carry the number of the entry they came from. `category=citation`.

## C9 — Structure and appendices

**Writer.** Follow [`document_skeleton.md`](document_skeleton.md) unless the
brief calls for something else. In particular:

- The **abstract** is short and states only what the document will show. It is
  not a summary of the argument's evidence.
- **Length is not capped; repetition is.** Say each thing once, in the place
  the reader needs it, and cross-link rather than restate.
- Standard appendices: **Glossary** · **Algorithms** (a plain-language account of
  every method whose behaviour the argument depends on) · **Gene sets / source
  definitions** (membership tables, or links to the authoritative definition) ·
  **References** (numbered, hyperlinked) · **Provenance**.
- **Reference numbering must survive rendering.** A markdown ordered list
  renumbers itself sequentially from its first item, so authored numbers that
  run out of file order display as *different* numbers and every in-text `[N]`
  after the first break silently points the reader at the wrong entry. Two rules
  follow, and they bite hardest when a later round **adds** references:
  1. Number the reference list strictly `1, 2, 3, …` **in file order**. When you
     add a source, either append it at the end or renumber the list and every
     in-text citation — never slot number 28 into a thematic group that ends at
     11 because the subject matter fits there.
  2. Make every in-text citation a **link to its entry** — `[28](#e28)` against
     `<a id="e28"></a>` — so a click lands on the right reference even if the
     displayed numbering drifts. Entry anchors that nothing links to are dead
     weight.
  3. Every entry is **cited at least once**. An entry no citation reaches is
     either a dropped citation or a source the argument does not actually use.

  A round that added sources can repair all three mechanically rather than by
  hand:

  ```bash
  python3 .claude/skills/debate/scripts/fix_citations.py <document.md> --in-place
  ```

**Critic.** Check the appendices exist and are actually used by the prose (a
glossary nothing links to is not a glossary), and flag repeated material.
`category=glossary` / `category=narrative`.

---

## Mechanical pre-check

Both agents run the linter before finishing a round:

```bash
python3 .claude/skills/debate/scripts/audit_document.py <document.md> --format md
```

Its output is a list of **candidates**, not verified defects. The Writer uses it
to catch its own omissions; the Critic confirms each hit by reading the location
before annotating it, and adds the defects the linter cannot see (C4 in
particular is not mechanically checkable).
