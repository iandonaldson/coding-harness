#!/usr/bin/env python3
"""Standalone tests for link_reference.py (repo convention: not pytest).

Run directly:
    python3 .claude/skills/debate/scripts/test_link_reference.py

Exits 0 on success, 1 on the first failure (module-level, like the pipeline
test scripts). No third-party dependencies.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import link_reference as lr  # noqa: E402

_passed = 0


def check(cond, msg):
    global _passed
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    _passed += 1
    print(f"ok: {msg}")


# --- classify_locator -------------------------------------------------------
check(lr.classify_locator("https://example.com/a") == "web", "http(s) URL -> web")
check(lr.classify_locator("http://example.com") == "web", "http URL -> web")
check(lr.classify_locator("references/paper.pdf") == "pdf", "local .pdf -> pdf")
check(lr.classify_locator("https://x.org/paper.PDF?dl=1") == "pdf", ".PDF with query -> pdf")
check(lr.classify_locator("data/notes.txt") == "other", "local .txt -> other")

# --- encode_fragment_text ---------------------------------------------------
enc = lr.encode_fragment_text("a b,c-d")
check("%20" in enc, "space is percent-encoded")
check("%2C" in enc, "comma is percent-encoded (directive separator)")
check("%2D" in enc, "hyphen is percent-encoded (context separator)")

# --- build_web_fragment: short quote ---------------------------------------
frag = lr.build_web_fragment("https://example.com/page", "hello world")
check("#:~:text=" in frag, "web fragment contains #:~:text=")
check(frag.endswith("hello%20world"), "short quote encoded whole")
check(frag.startswith("https://example.com/page#:~:text="), "fragment appended to base URL")

# pre-existing fragment on the URL is dropped before appending
frag2 = lr.build_web_fragment("https://example.com/page#section", "hi there")
check(frag2 == "https://example.com/page#:~:text=hi%20there", "old #fragment dropped")

# --- build_web_fragment: long quote -> textStart,textEnd -------------------
long_q = "one two three four five six seven eight nine ten eleven"
lfrag = lr.build_web_fragment("https://example.com/p", long_q)
check("," in lfrag.split("text=", 1)[1], "long quote uses start,end form")
check("one%20two%20three%20four" in lfrag, "start = first 4 words")
check("eight%20nine%20ten%20eleven" in lfrag, "end = last 4 words")

# --- make_link: web (link vs block) ----------------------------------------
web_link = lr.make_link("https://example.com/p", "some claim text", title="Source A")
check(web_link.startswith("[Source A](https://example.com/p#:~:text="), "web make_link inline form")

web_block = lr.make_link("https://example.com/p", "some claim text", title="A", fmt="block")
check("> some claim text" in web_block, "web block form appends blockquote")

# --- make_link: pdf ---------------------------------------------------------
pdf_link = lr.make_link("references/paper.pdf", "the finding", page=7, title="Paper")
check("references/paper.pdf#page=7" in pdf_link, "pdf link has #page=7")
check(pdf_link.endswith(", p.7"), "pdf inline link notes the page")

pdf_nopage = lr.make_link("references/paper.pdf", "the finding", title="Paper")
check(pdf_nopage == "[Paper](references/paper.pdf)", "pdf link without page has no #page")

# --- make_link: fallback (Tier 3 always shows the passage) -----------------
fb = lr.make_link("data/local_note.txt", "supporting sentence here")
check("> supporting sentence here" in fb, "fallback shows blockquote")
check("`data/local_note.txt`" in fb, "fallback shows locator when not a URL")

fb_url = lr.make_link("ftp://host/file", "passage")  # non-http URL, non-pdf
check("> passage" in fb_url, "non-web/non-pdf locator still shows passage")

# --- label defaults to a truncated quote snippet ----------------------------
auto = lr.make_link("https://e.com/x", "x" * 80)
check("…" in auto.split("]", 1)[0], "long auto-label is truncated with an ellipsis")

# --- --ref: the paired quote + numbered source form (C8) --------------------
check(lr.reference_citation(12) == "[12](#e12)", "reference_citation renders [N](#eN)")
check(lr.reference_citation("[7]") == "[7](#e7)", "a bracketed number is accepted")
check(lr.reference_citation(3, "ref") == "[3](#ref3)", "the anchor prefix is configurable")

paired = lr.make_link("https://example.com/p", "some claim text", title="A", ref=12)
check(paired.endswith(") [12](#e12)"), "web link is followed by its numbered source")
check("#:~:text=" in paired, "the highlight is still generated alongside the number")
check(lr.make_link("https://example.com/p", "q", title="A") .endswith(")"),
      "without --ref the link is unchanged")

paired_block = lr.make_link("https://example.com/p", "some claim", title="A", fmt="block", ref=5)
check(paired_block.splitlines()[0].endswith("[5](#e5)"), "block form carries the number on the link")
check("> some claim" in paired_block, "block form still shows the passage")

paired_pdf = lr.make_link("references/paper.pdf", "the finding", page=7, title="P", ref=9)
check(paired_pdf == "[P](references/paper.pdf#page=7), p.7 [9](#e9)", "pdf tier pairs after the page note")

paired_fb = lr.make_link("data/local_note.txt", "passage", ref=4)
check(paired_fb.splitlines()[0].endswith("[4](#e4)"), "fallback tier pairs before the blockquote")

import io  # noqa: E402
import contextlib  # noqa: E402

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    lr.main(["--locator", "https://example.com/p", "--quote", "hello world", "--ref", "12"])
check(buf.getvalue().strip().endswith("[12](#e12)"), "CLI --ref emits the paired form")

print(f"\nAll {_passed} assertions passed.")
sys.exit(0)
