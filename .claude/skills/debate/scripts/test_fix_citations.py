#!/usr/bin/env python3
"""Standalone tests for fix_citations.py (repo convention: not pytest).

Run directly:
    python3 .claude/skills/debate/scripts/test_fix_citations.py

Exits 0 on success, 1 on the first failure (module-level, like the pipeline
test scripts). No third-party dependencies.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit_document as ad  # noqa: E402
import fix_citations as fc  # noqa: E402

_passed = 0


def check(cond, msg):
    global _passed
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    _passed += 1
    print(f"ok: {msg}")


# ---------------------------------------------------------------------------
# Fixture: the defect a human reviewer found — refs authored out of file order (a later round
# slotted 10 and 28 into the themed group), plain-text citations, and quote
# links that never name their source.
# ---------------------------------------------------------------------------

BROKEN = """# Doc

## 1. Body

Ad5 attaches via [the coxsackievirus and adenovirus receptor](https://pubmed.ncbi.nlm.nih.gov/30125593/#:~:text=The%20cellular%20internalization) [25].

DSG2 is [the receptor for Ad3, Ad7, Ad11 and Ad14](https://pubmed.ncbi.nlm.nih.gov/26292319/#:~:text=We%20recently%20discovered) and
is [an epithelial junction protein](https://pubmed.ncbi.nlm.nih.gov/26292319/#:~:text=A%20number%20of%20widely) [28].

GSVA scores gene sets [1].

## Appendix E - References

**Methods**

1. <a id="e1"></a>Hanzelmann S et al. *GSVA.* — [competitive scoring](https://pmc.ncbi.nlm.nih.gov/articles/PMC3618321/#:~:text=GSVA%20calculates)

**Viruses**

25. <a id="e25"></a>Stepanenko AA. *Tropism of oncolytic adenovirus 5 vectors.* — [Ad5 attaches via CAR](https://pubmed.ncbi.nlm.nih.gov/30125593/#:~:text=The%20cellular%20internalization)
28. <a id="e28"></a>Wang H et al. *Desmoglein 2 shedding.* — [DSG2 is the receptor](https://pubmed.ncbi.nlm.nih.gov/26292319/#:~:text=We%20recently%20discovered)
"""

fixed, rep = fc.fix_citations(BROKEN)

# --- renumbering ------------------------------------------------------------
check(rep.entries == 3, "all three reference entries are found")
check(rep.renumbered == 2, "the two out-of-order entries are renumbered")
check("2. <a id=\"e2\"></a>Stepanenko" in fixed, "entry 25 becomes entry 2 in file order")
check("3. <a id=\"e3\"></a>Wang H" in fixed, "entry 28 becomes entry 3 in file order")
check("1. <a id=\"e1\"></a>Hanzelmann" in fixed, "the first entry keeps its number and anchor")

# --- in-text citations ------------------------------------------------------
check("[2](#e2)" in fixed, "in-text [25] is remapped and linked as [2](#e2)")
check("[3](#e3)" in fixed, "in-text [28] is remapped and linked as [3](#e3)")
check("[1](#e1)" in fixed, "an already-correct number is still turned into a link")
check(rep.citations == 3 and rep.remapped == 2, "citation counts are reported")
check("[25]" not in fixed and "[28]" not in fixed, "no plain-text citation survives")

# --- quote pairing ----------------------------------------------------------
# Relinking runs first, so a quote that already had a plain `[N]` after it now
# has a linked one and needs no pairing; only the naked quote is paired.
check(rep.quotes_paired == 1, "the quote link with no reference at all gets one")
check(rep.quotes_already_paired == 2, "a quote whose number was relinked is left alone")
check(
    "#:~:text=The%20cellular%20internalization) [2](#e2)" in fixed,
    "the CAR quote is followed by its source number",
)
check(
    "#:~:text=We%20recently%20discovered) [3](#e3) and" in fixed,
    "the naked DSG2 quote gains the number of the entry its URL belongs to",
)
check(
    "#:~:text=A%20number%20of%20widely) [3](#e3)" in fixed,
    "the second DSG2 quote is paired even though a sibling quote precedes it on the line",
)
check(not rep.unmatched_quotes and not rep.ambiguous_urls, "every quote URL resolves to one entry")

# --- the linter agrees ------------------------------------------------------
before = ad.audit(BROKEN, only={"reference-numbering", "quote-without-reference"})
check(any("out of file order" in f.detail for f in before), "the linter sees the defect first")
check(
    any(f.check == "quote-without-reference" for f in before),
    "the linter sees the unpaired quote links first",
)
after = ad.audit(fixed, only={"reference-numbering", "quote-without-reference"})
check(not after, "the fixed draft passes both citation checks")
check(not ad.audit(fixed, only={"broken-anchor"}), "every generated link resolves to an anchor")

# --- idempotence ------------------------------------------------------------
again, rep2 = fc.fix_citations(fixed)
check(again == fixed, "running the fixer on its own output changes nothing")
check(rep2.quotes_paired == 0 and rep2.remapped == 0, "the second pass reports no work")

# --- the second citation idiom: `[ref N](#eN)` ------------------------------

# Found by the round-8 Critic: the first version of this script only recognised
# citations whose label was exactly the number, so `[ref 21](#e21)` kept BOTH a
# stale label and a stale target. Label and target agreed with each other, so the
# link looked fine while pointing at the wrong paper — the exact failure this
# script exists to prevent, in a form a label-vs-target check cannot see.
IDIOMS = """# Doc

## 1. Body

The methods are described in [1](#e1) and [2](#e2).

VGLL3 is a TEAD cofactor ([ref 3](#e3)), and the markers are described in
[refs 3, 4](#e3). A prose label like [the 2019 crystal structure](#e4) also links.
Not a citation: [Fig 5](#fig5), [Box 2](#box2), [Appendix C](#c1-normalisation).

## Appendix E - References

**Methods**

1. <a id="e1"></a>Author A. *One.*
2. <a id="e2"></a>Author B. *Two.*

**Later additions**

3. <a id="e3"></a>Hori N et al. *VGLL3, a cofactor for TEAD transcription factors.*
4. <a id="e4"></a>Author D. *Four.*

## Anchors

<a id="fig5"></a><a id="box2"></a>

### <a id="c1-normalisation"></a>C.1 Normalisation
"""
idi, irep = fc.fix_citations(IDIOMS)
check("[ref 3](#e3)" in idi, "a `ref N` label whose number did not move is untouched")
check("[refs 3, 4](#e3)" in idi, "a multi-number `refs` label is preserved when nothing moved")
check("[Fig 5](#fig5)" in idi and "[Box 2](#box2)" in idi, "links to non-entry anchors are untouched")
check("[Appendix C](#c1-normalisation)" in idi, "a hyphenated anchor is not mistaken for an entry")

# Now the case that actually bit: entries authored out of order, so `[ref N]`
# must be remapped in BOTH its label and its target.
MOVED = IDIOMS.replace("3. <a id=\"e3\"></a>Hori", "13. <a id=\"e13\"></a>Hori").replace(
    "4. <a id=\"e4\"></a>Author D.", "14. <a id=\"e14\"></a>Author D.").replace(
    "([ref 3](#e3))", "([ref 13](#e13))").replace(
    "[refs 3, 4](#e3)", "[refs 13, 14](#e13)").replace(
    "[the 2019 crystal structure](#e4)", "[the 2019 crystal structure](#e14)")
mov, mrep = fc.fix_citations(MOVED)
check("[ref 3](#e3)" in mov, "`[ref 13](#e13)` is remapped in label AND target")
check("[refs 3, 4](#e3)" in mov, "every number in a `refs a, b` label is remapped")
check("Hori" in [l for l in mov.splitlines() if l.startswith("3. ")][0],
      "the remapped target is the entry that actually holds the cited paper")
check("[the 2019 crystal structure](#e4)" in mov, "a prose label keeps its text; the target moves")
check([s for _, s in mrep.relabel_review] == ["[the 2019 crystal structure](#e14)"],
      "a prose label carrying a number is reported for human review")
check(not ad.audit(mov, only={"reference-numbering", "broken-anchor"}),
      "the remapped draft passes the citation checks")

# --- entries with no anchor get one -----------------------------------------
NO_ANCHOR = """# Doc

## 1. Body

A claim [2].

## References

1. Author A. *One.*
2. Author B. *Two.*
"""
anch, _ = fc.fix_citations(NO_ANCHOR)
check('1. <a id="e1"></a>Author A.' in anch, "an entry without an anchor is given one")
check("[2](#e2)" in anch, "its citation links to the new anchor")
check(not ad.audit(anch, only={"broken-anchor"}), "the invented anchors resolve")

# --- unresolvable and ambiguous quote URLs are reported, not guessed --------
ODD = """# Doc

## 1. Body

An [uncited passage](https://example.org/other#:~:text=something) in the prose.

Two entries share [this host](https://example.com/shared#:~:text=a%20passage).

## References

1. <a id="e1"></a>Author A. *One.* — [q](https://example.com/shared#:~:text=a%20passage)
2. <a id="e2"></a>Author B. *Two.* — [q](https://example.com/shared#:~:text=another)
"""
odd, orep = fc.fix_citations(ODD)
check(
    [u for _, u in orep.unmatched_quotes] == ["https://example.org/other"],
    "a quote URL no entry cites is reported as unmatched",
)
check(orep.ambiguous_urls == ["https://example.com/shared"], "a URL claimed by two entries is reported")
check(orep.quotes_paired == 0, "neither ambiguous nor unmatched quotes are paired blindly")
check("example.org/other#:~:text=something) in the prose" in odd, "the unmatched link is left intact")

# --- code fences are not rewritten ------------------------------------------
FENCED = """# Doc

## 1. Body

```markdown
See [2] and [q](https://example.com/x#:~:text=y) in the template.
```

Real citation [2].

## References

1. <a id="e1"></a>Author A. *One.*
2. <a id="e2"></a>Author B. *Two.*
"""
fen, _ = fc.fix_citations(FENCED)
check("See [2] and [q](https://example.com/x#:~:text=y)" in fen, "content inside a fence is untouched")
check("Real citation [2](#e2)." in fen, "prose outside the fence is still fixed")

# --- CLI --------------------------------------------------------------------
import tempfile  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "d.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(BROKEN)
    check(fc.main([p]) == 0, "dry run exits 0 and writes nothing")
    with open(p, encoding="utf-8") as fh:
        check(fh.read() == BROKEN, "the draft is unchanged by a dry run")
    out = os.path.join(tmp, "next.md")
    check(fc.main([p, "--output", out]) == 0, "--output exits 0")
    with open(out, encoding="utf-8") as fh:
        check(fh.read() == fixed, "--output writes the fixed draft")
    check(fc.main([p, "--in-place"]) == 0, "--in-place exits 0")
    with open(p, encoding="utf-8") as fh:
        check(fh.read() == fixed, "--in-place rewrites the draft")
    o = os.path.join(tmp, "odd.md")
    with open(o, "w", encoding="utf-8") as fh:
        fh.write(ODD)
    check(fc.main([o]) == 1, "an unmatched or ambiguous quote URL exits 1")

print(f"\nAll {_passed} assertions passed.")
sys.exit(0)
