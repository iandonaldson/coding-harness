#!/usr/bin/env python3
"""Standalone tests for audit_document.py (repo convention: not pytest).

Run directly:
    python3 .claude/skills/debate/scripts/test_audit_document.py

Exits 0 on success, 1 on the first failure (module-level, like the pipeline
test scripts). No third-party dependencies.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit_document as ad  # noqa: E402

_passed = 0


def check(cond, msg):
    global _passed
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    _passed += 1
    print(f"ok: {msg}")


def checks_of(findings, name):
    return [f for f in findings if f.check == name]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DIRTY = """# A study

## 1. Bottom line

Your original read of the data was correct. The stromal transcripts are
genuinely leaving, which is what a collapsing compartment looks like.

## 2. Introduction

The experiment used three explants. FAP is a canonical activated-CAF marker.

## 3. Evidence

COL1A1 falls from 10,500 CPM to 74 CPM (log2FC -8.03, padj 2.7e-11), a 40-114x
drop across 3 of 3 patients.

The Hippo output module falls together: VGLL3 -11.04 and TEAD1 -8.39. The VGLL3
reading is not the only one available.

See [the glossary](#appendix-z-nonexistent) for details.

```python
# YOU should not be flagged in a code fence; NEITHER SHOULD THESE ACRONYMS
print("padj 0.05 log2FC 3 %")
```

[[human: add a figure here]]

Some claim. [CRITIC: wrong figure. severity: high]
"""

CLEAN = """# A study

## 1. Abstract

This document reports a compositional change and states where the evidence
cannot separate the two candidate explanations.

## 2. Introduction

Fibroblast activation protein ([FAP](#g-fap)) is used here as a marker of
activated cancer-associated fibroblasts ([CAF](#g-caf)), following ref [1].
Collagen type I alpha 1 ([COL1A1](#g-col1a1)) indexes fibrillar matrix output.

## 3. Evidence

![Fig 1 - collagen share](document_9_figs/fig01_collagen.png)

[COL1A1](#g-col1a1) falls from 10,500 counts per million to 74 counts per
million.[^cpm]

[^cpm]: `results/production_2026-06-30/human/counts/human_counts.txt`

## Appendix A - Glossary

### <a id="g-fap"></a>FAP - fibroblast activation protein
A serine protease expressed by activated fibroblasts. See ref [1].

### <a id="g-caf"></a>CAF - cancer-associated fibroblast
The non-malignant fibroblast compartment of a tumour. See ref [1].

### <a id="g-col1a1"></a>COL1A1 - collagen type I alpha 1 chain
The principal fibrillar collagen transcript. See ref [2].
"""

dirty = ad.audit(DIRTY)
clean = ad.audit(CLEAN)

# --- unresolved annotations -------------------------------------------------
ann = checks_of(dirty, "unresolved-annotation")
check(len(ann) == 2, "both [[…]] and [CRITIC: …] markers are flagged")
check(all(f.severity == "high" for f in ann), "unresolved annotations are high severity")
check(not checks_of(clean, "unresolved-annotation"), "clean draft has no annotation findings")

# --- register ---------------------------------------------------------------
reg = checks_of(dirty, "register")
check(any("second person" in f.detail for f in reg), "second person is flagged")
check(any("genuinely" in f.detail for f in reg), "unhedged 'genuinely' is flagged")
check(any("looks like" in f.detail for f in reg), "'is what … looks like' is flagged")
check(not checks_of(clean, "register"), "clean draft passes the register check")

# --- code fences are not linted ---------------------------------------------
fence_line = next(i for i, l in enumerate(DIRTY.splitlines(), 1) if "NEITHER SHOULD" in l)
check(
    not [f for f in dirty if f.line == fence_line],
    "content inside a fenced code block is ignored",
)

# --- undefined terms --------------------------------------------------------
und = checks_of(dirty, "undefined-term")
check(any("COL1A1" in f.detail for f in und), "gene symbol with no definition is flagged")
check(any("CPM" in f.detail for f in und), "acronym with no definition is flagged")
check(not checks_of(clean, "undefined-term"), "glossary-linked first uses are accepted")
check(
    not [f for f in und if "'CSV'" in f.detail or "'PDF'" in f.detail],
    "format tokens on the stoplist are not reported as terms",
)

# _defined_inline recognises the usual expansion forms
check(ad._defined_inline("cancer-associated fibroblast (CAF) markers", "CAF"), "expansion → acronym")
check(ad._defined_inline("CAF (cancer-associated fibroblast)", "CAF"), "acronym → expansion")
check(ad._defined_inline("[CAF](#g-caf) fell", "CAF"), "first use linking to the glossary")
check(not ad._defined_inline("the CAF score fell", "CAF"), "bare use is not a definition")

# --- late introduction ------------------------------------------------------
late = checks_of(dirty, "late-introduction")
check(any("VGLL3" in f.detail for f in late), "a concept first used in Evidence is flagged (C3)")
check(
    all(f.line > ad.Doc(DIRTY).intro_end for f in late),
    "late-introduction findings all sit after the Introduction",
)

# --- data provenance --------------------------------------------------------
src = checks_of(dirty, "unsourced-data-claim")
check(src, "a numeric block with no source footnote is flagged")
check(not checks_of(clean, "unsourced-data-claim"), "a footnoted numeric block passes")

# --- figures ----------------------------------------------------------------
fig = checks_of(dirty, "figureless-data-block")
check(fig, "a data-bearing section with no figure is flagged")
check(not checks_of(clean, "figureless-data-block"), "a section with an image passes")

# --- attribution ------------------------------------------------------------
att = checks_of(dirty, "unsourced-attribution")
check(att, "'canonical … marker' with no citation is flagged")
check(not checks_of(clean, "unsourced-attribution"), "a glossary-linked attribution passes")

# --- anchors ----------------------------------------------------------------
anc = checks_of(dirty, "broken-anchor")
check(len(anc) == 1 and "appendix-z-nonexistent" in anc[0].detail, "dangling #anchor is flagged")
check(not checks_of(clean, "broken-anchor"), "anchors resolving to <a id> entries pass")
check(ad.slugify("## 5.2 The CAF/stromal compartment") == "52-the-cafstromal-compartment",
      "slugify approximates GitHub heading anchors")

# --- structural parsing -----------------------------------------------------
doc = ad.Doc(CLEAN)
check("g-fap" in doc.anchors, "explicit <a id> anchors are collected")
check("3-evidence" in doc.anchors, "heading slugs are collected as anchors")
check({"FAP", "CAF", "COL1A1"} <= doc.glossary_terms, "glossary terms are recognised")
check(doc.appendix_start < len(doc.raw), "the appendix boundary is found")
check(doc.intro_end > 0 and doc.intro_end < doc.appendix_start, "intro boundary precedes appendix")

# --- reference numbering ----------------------------------------------------

# Out-of-file-order numbering: new refs appended into themed groups. A markdown
# renderer renumbers each list from its first item, so [28] lands on the wrong
# entry — the failure a human reviewer found in document_6.md.
REFS_BAD = """# Doc

## 1. Body

DSG2 is cleaved by ADAM17, opening epithelial junctions [10], [28].
An unrelated claim [99].

## Appendix E - References

**Methods**

1. <a id="e1"></a>Author A. *Method paper.*
2. <a id="e2"></a>Author B. *Another method.*

**Viruses**

10. <a id="e10"></a>Author C. *Fibre knob in complex with desmoglein 2.*
28. <a id="e28"></a>Author D. *Desmoglein 2 shedding.*
"""

REFS_GOOD = """# Doc

## 1. Body

The methods are GSVA [1](#e1) and MCP-counter [2](#e2).

DSG2 is cleaved by ADAM17, opening epithelial junctions [3](#e3), [4](#e4).

## Appendix E - References

1. <a id="e1"></a>Author A. *Method paper.*
2. <a id="e2"></a>Author B. *Another method.*
3. <a id="e3"></a>Author C. *Fibre knob in complex with desmoglein 2.*
4. <a id="e4"></a>Author D. *Desmoglein 2 shedding.*
"""

bad = checks_of(ad.audit(REFS_BAD, only={"reference-numbering"}), "reference-numbering")
check(any(f.severity == "high" and "out of file order" in f.detail for f in bad),
      "out-of-order reference numbering is flagged high")
check(sum("out of file order" in f.detail for f in bad) == 1,
      "the out-of-order break is reported once, not per entry")
check(any("citation [99] has no entry" in f.detail for f in bad),
      "a citation with no reference entry is flagged")
check(any(f.severity == "low" and "plain text" in f.detail for f in bad),
      "plain-text citations are flagged when entry anchors exist")
check(any("anchors exist but nothing uses them" in f.detail for f in bad),
      "the report notes unused entry anchors")
check(not ad.audit(REFS_GOOD, only={"reference-numbering"}),
      "sequential numbering with linked citations passes")
check(not ad.audit(CLEAN, only={"reference-numbering"}),
      "a document with no reference list is not flagged")

# An entry nothing cites is either a dropped citation or dead weight.
REFS_UNCITED = """# Doc

## 1. Body

One claim [1](#e1).

## Appendix E - References

1. <a id="e1"></a>Author A. *Cited.*
2. <a id="e2"></a>Author B. *Never cited by anything.*
"""
unc = checks_of(ad.audit(REFS_UNCITED, only={"reference-numbering"}), "reference-numbering")
check(len(unc) == 1 and "entry [2] is never cited" in unc[0].detail,
      "a reference entry no citation reaches is flagged")
check(unc[0].severity == "low", "an uncited entry is low severity")
check(unc[0].line == REFS_UNCITED.splitlines().index('2. <a id="e2"></a>Author B. '
                                                     '*Never cited by anything.*') + 1,
      "the uncited-entry finding points at the entry itself")

# A citation is a citation whatever its label reads. Missing this is what let 20
# stale `[ref N](#eN)` links survive a renumbering in round 7 of the live debate.
REFS_IDIOM = """# Doc

## 1. Body

VGLL3 is a TEAD cofactor ([ref 1](#e1)) and the panel is in [refs 1, 2](#e1).
Öhlund's populations ([Öhlund et al.](#e2)) are pancreatic.
A half-applied renumbering reads [ref 1](#e2).
Not citations: [Fig 5](#fig5), [Box 2](#box2).

<a id="fig5"></a><a id="box2"></a>

## Appendix E - References

1. <a id="e1"></a>Hori N et al. *VGLL3.*
2. <a id="e2"></a>Öhlund D et al. *Distinct populations.*
"""
idm = checks_of(ad.audit(REFS_IDIOM, only={"reference-numbering"}), "reference-numbering")
check(not [f for f in idm if "never cited" in f.detail],
      "a `[ref N](#eN)` or prose-labelled link counts as citing its entry")
check(len(idm) == 1 and "reads [1] but links to entry [2]" in idm[0].detail,
      "a label that names a different entry than it links to is flagged")
check(idm[0].severity == "medium", "a half-applied renumbering is medium severity")

# --- quote links carry their source number (C8) -----------------------------

# Reviewer requirement: a highlighted quote shows the reader the passage but never
# says which numbered source it is unless a [N](#eN) follows.
QUOTES = """# Doc

## 1. Body

Ad5 attaches via [the initial attachment of the capsid fiber
protein](https://pubmed.ncbi.nlm.nih.gov/30125593/#:~:text=The%20cellular%20internalization) [1](#e1).

DSG2 is [an epithelial junction
protein](https://pubmed.ncbi.nlm.nih.gov/26292319/#:~:text=A%20number%20of%20widely) and is cleaved.

A quote whose number sits on the next
line [as a wrapped paragraph](https://example.com/x#:~:text=passage)
[2](#e2) still counts.

```markdown
A [template example](https://example.com/y#:~:text=z) in a fence is not linted.
```

## Appendix E - References

1. <a id="e1"></a>Stepanenko AA. *Tropism.* — [Ad5 attaches via CAR](https://pubmed.ncbi.nlm.nih.gov/30125593/#:~:text=The%20cellular%20internalization)
2. <a id="e2"></a>Author B. *Two.* — [a passage](https://example.com/x#:~:text=passage)
"""
q = checks_of(ad.audit(QUOTES, only={"quote-without-reference"}), "quote-without-reference")
check(len(q) == 1, "only the unpaired quote link is flagged")
check("26292319" in ad.Doc(QUOTES).raw[q[0].line - 1], "the finding points at the DSG2 quote line")
check(q[0].severity == "medium", "an unpaired quote link is medium severity")
check("[N](#eN)" in q[0].detail, "the finding names the required form")
check(not checks_of(ad.audit(CLEAN, only={"quote-without-reference"}),
                    "quote-without-reference"),
      "a draft with no text-fragment links is not flagged")
check("quote-without-reference" in ad.CHECKS, "the check is registered")

# --- a draft that documents its own conventions is not linting itself -------

# Prose that quotes the convention ("make each one `[N](#eN)`") is an example of
# a link, not a link; and a `## Response to the round-6 critique` section quotes
# the defects it is reporting as fixed.
SELF_DESCRIBING = """# Doc

## 1. Body

A real citation [1](#e1).

## Response to the round-6 critique

A reader following `[10]` and `[28]` landed on the wrong entry. Every in-text
citation is now `[N](#eN)`, and every quote link — `[q](https://x.org/#:~:text=y)`
— is followed by its number.

## Appendix E - References

1. <a id="e1"></a>Author A. *One.*
"""
sd = ad.audit(SELF_DESCRIBING)
check(not checks_of(sd, "broken-anchor"), "an anchor example inside backticks is not a link")
check(not checks_of(sd, "reference-numbering"), "citations quoted inside backticks are not citations")
check(not checks_of(sd, "quote-without-reference"), "a quote-link example in backticks is not linted")
check(ad.Doc(SELF_DESCRIBING).in_meta(
    SELF_DESCRIBING.splitlines().index("A reader following `[10]` and `[28]` landed on the wrong entry. Every in-text")),
    "'Response to the round-N critique' is recognised as a meta section")
check(ad._in_inline_code("make each one `[N](#eN)` so", 15), "inline-code spans are located")
check(not ad._in_inline_code("a real [1](#e1) link", 8), "prose outside backticks is not excused")

# --- filters, limits, rendering, exit codes ---------------------------------
only = ad.audit(DIRTY, only={"register"})
check({f.check for f in only} == {"register"}, "--only restricts the checks run")
skipped = ad.audit(DIRTY, skip={"register"})
check("register" not in {f.check for f in skipped}, "--skip removes a check")

capped = ad.audit(DIRTY, only={"undefined-term"}, max_per_check=2)
check(len(capped) == 3, "max_per_check trims and appends a suppression note")
check("suppressed" in capped[-1].detail, "the suppression note is reported")

md = ad.render_md(dirty, "x.md")
check(md.startswith("# audit_document"), "markdown report has a title")
check("| Line | Check | Sev |" in md, "markdown report has a findings table")
check("No candidate defects" in ad.render_md([], "x.md"), "empty report says so")
check("| Line |" not in ad.render_md(dirty, "x.md", summary_only=True), "--summary-only omits rows")

summary = ad.summarize(dirty)
check(summary["unresolved-annotation"]["high"] == 2, "summary counts by check and severity")

import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "d.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(DIRTY)
    check(ad.main([p, "--format", "json"]) == 0, "CLI exits 0 without --strict")
    check(ad.main([p, "--strict"]) == 1, "CLI exits 1 with --strict when findings exist")
    c = os.path.join(tmp, "c.md")
    with open(c, "w", encoding="utf-8") as fh:
        fh.write(CLEAN)
    check(ad.main([c, "--strict"]) == 0, "CLI exits 0 with --strict on a clean draft")

print(f"\nAll {_passed} assertions passed.")
sys.exit(0)
