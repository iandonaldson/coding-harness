#!/usr/bin/env python3
"""audit_document.py — convention linter for `/debate` drafts.

Part of the `/debate` skill. Mechanically screens a markdown draft against the
standing conventions in `rules/conventions.md` and reports **candidate** defects
with line anchors:

  unresolved-annotation  C-  a `[[human note]]` or `[CRITIC: …]` left in a draft
  undefined-term         C2  acronym/gene symbol used before it is expanded or
                             linked to a glossary entry
  late-introduction      C3  a term whose first use falls after the Introduction
  unsourced-data-claim   C7  numbers/tables with no source-file footnote
  figureless-data-block  C6  a data-bearing section with no figure
  register               C1  second person, colloquialism, unhedged claim
  unsourced-attribution  C8  "marker of / canonical / signature" with no citation
  broken-anchor          C9  `](#…)` with no matching heading or anchor
  reference-numbering    C9  reference list numbered out of file order (renderers
                             renumber it, so in-text [N] misdirects), a citation
                             with no entry, citations left as plain text, or an
                             entry nothing cites
  quote-without-reference C8 a highlighted `#:~:text=` quote link that is not
                             followed by a `[N](#eN)` naming its source

Findings are CANDIDATES, not verdicts. The Writer uses them to catch its own
omissions; the Critic must confirm each by reading the location before
annotating it, and must add the defects this cannot see (C4 narrative thread in
particular is not mechanically checkable).

Pure standard library — no third-party deps, so it runs anywhere python3 does.

CLI
    python3 audit_document.py DRAFT.md [--format md|json] [--strict]
        [--only CHECK[,CHECK…]] [--skip CHECK[,CHECK…]] [--max-per-check N]
        [--stoplist FILE] [--summary-only]

Programmatic
    from audit_document import audit, Finding, CHECKS
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import NamedTuple

# --------------------------------------------------------------------------
# Finding model
# --------------------------------------------------------------------------


class Finding(NamedTuple):
    check: str
    severity: str  # high | medium | low
    line: int  # 1-indexed
    excerpt: str
    detail: str

    def as_dict(self) -> dict:
        return dict(
            check=self.check,
            severity=self.severity,
            line=self.line,
            excerpt=self.excerpt,
            detail=self.detail,
        )


CHECKS = (
    "unresolved-annotation",
    "undefined-term",
    "late-introduction",
    "unsourced-data-claim",
    "figureless-data-block",
    "register",
    "unsourced-attribution",
    "broken-anchor",
    "reference-numbering",
    "quote-without-reference",
)

_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}

# --------------------------------------------------------------------------
# Term recognition
# --------------------------------------------------------------------------

# Acronyms and gene/protein symbols: 2+ chars, upper-case start, digits allowed,
# optional hyphenated suffix (IFN-γ is not matched — the greek letter is fine).
_TERM_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}(?:-[A-Z0-9]{1,5})?\b")

# Tokens that are structure, formatting or file-format noise rather than
# subject-matter terms. Kept deliberately short: a real term wrongly listed here
# would be silently excused, which is worse than a false positive.
DEFAULT_STOPLIST = frozenset(
    """
    OK TODO FIXME NOTE NB NA URL HTTP HTTPS PDF HTML CSV TSV JSON YAML XML MD
    README SKILL CRITIC SCORE VERDICT ACCEPT REVISE PASS FAIL PARTIAL WRITER
    AND OR NOT THE FOR WITH FROM INTO ONLY ALL ANY NEW OLD YES NO IF IS ARE WAS
    BUT ITS OUR API CLI CPU GPU RAM ID IDS URI UUID ASCII UTF
    JAN FEB MAR APR JUN JUL AUG SEP SEPT OCT NOV DEC
    I II III IV V VI VII VIII IX X XI XII
    """.split()
)

# --------------------------------------------------------------------------
# Document parsing
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_ANCHOR_RE = re.compile(r"<a\s+(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.I)
_INTERNAL_LINK_RE = re.compile(r"\]\(#([^)\s]+)\)")

_APPENDIX_RE = re.compile(
    r"\b(glossar|appendix|references?|bibliograph|provenance|source definitions?)\b", re.I
)
_INTRO_RE = re.compile(r"\b(introduction|background|aims? and|prior research|the players)\b", re.I)
# Meta sections quote the prose they are commenting on — linting them re-reports
# defects the draft has already fixed (a disposition table quoting "quiet hero").
_META_RE = re.compile(
    r"\b(response to (the )?(round-\d+ )?(review|critique)|scorecard|convention check"
    r"|round-\d+ critique)\b",
    re.I,
)
_FRONT_RE = re.compile(r"\b(abstract|bottom line|summary|contents|executive)\b", re.I)


class Section(NamedTuple):
    start: int  # 0-indexed line of the heading
    end: int  # 0-indexed, exclusive
    level: int
    title: str


class Doc:
    """A parsed markdown draft: raw lines plus code-stripped 'clean' lines."""

    def __init__(self, text: str):
        self.raw = text.splitlines()
        self.clean = _strip_code(self.raw)
        self.sections = _sections(self.raw)
        self.anchors = _anchors(self.raw, self.sections)
        self.intro_end = _intro_end(self.sections, len(self.raw))
        self.appendix_start = _appendix_start(self.sections, len(self.raw))
        self.meta_ranges = [(s.start, s.end) for s in self.sections if _META_RE.search(s.title)]
        self.glossary_terms = _glossary_terms(self)

    def in_appendix(self, idx: int) -> bool:
        return idx >= self.appendix_start

    def in_meta(self, idx: int) -> bool:
        """True inside a section that quotes the draft to comment on it."""
        return any(a <= idx < b for a, b in self.meta_ranges)

    def skip(self, idx: int) -> bool:
        return self.in_appendix(idx) or self.in_meta(idx)

    def section_of(self, idx: int) -> Section | None:
        found = None
        for s in self.sections:
            if s.start <= idx < s.end:
                if found is None or s.level >= found.level:
                    found = s
        return found


def _strip_code(raw: list[str]) -> list[str]:
    """Blank out fenced code, inline code, link hrefs, HTML comments and URLs."""
    out: list[str] = []
    in_fence = False
    in_comment = False
    for line in raw:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence:
            out.append("")
            continue
        s = line
        if in_comment:
            if "-->" in s:
                s = s.split("-->", 1)[1]
                in_comment = False
            else:
                out.append("")
                continue
        while "<!--" in s:
            head, rest = s.split("<!--", 1)
            if "-->" in rest:
                s = head + rest.split("-->", 1)[1]
            else:
                s = head
                in_comment = True
                break
        s = re.sub(r"`[^`]*`", " ", s)  # inline code
        s = re.sub(r"\]\([^)]*\)", "] ", s)  # link/image targets, keep label
        s = re.sub(r"https?://\S+", " ", s)  # bare URLs
        s = re.sub(r"<[^>]+>", " ", s)  # stray html tags
        out.append(s)
    return out


def _sections(raw: list[str]) -> list[Section]:
    heads: list[tuple[int, int, str]] = []
    in_fence = False
    for i, line in enumerate(raw):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    out: list[Section] = []
    for n, (start, level, title) in enumerate(heads):
        end = len(raw)
        for later_start, later_level, _ in heads[n + 1 :]:
            if later_level <= level:
                end = later_start
                break
        out.append(Section(start, end, level, title))
    return out


def slugify(title: str) -> str:
    """Approximate GitHub's heading-anchor slugification."""
    s = re.sub(r"`|\*|_", "", title).strip().lower()
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s).strip("-")


def _anchors(raw: list[str], sections: list[Section]) -> set[str]:
    out = {slugify(s.title) for s in sections}
    for line in raw:
        out.update(m.group(1) for m in _ANCHOR_RE.finditer(line))
    out.discard("")
    return out


def _intro_end(sections: list[Section], n_lines: int) -> int:
    """Line index at which front matter + Introduction stop."""
    tops = [s for s in sections if s.level <= 2]
    for s in tops:
        if _INTRO_RE.search(s.title):
            return s.end
    # No section named like an introduction: fall back to the end of the second
    # top-level section (title/abstract + one more), else the whole document.
    if len(tops) >= 2:
        return tops[1].end
    return n_lines


def _appendix_start(sections: list[Section], n_lines: int) -> int:
    for s in sections:
        if s.level <= 3 and _APPENDIX_RE.search(s.title):
            return s.start
    return n_lines


def _glossary_terms(doc: "Doc") -> set[str]:
    """Terms that have a glossary/appendix entry (heading token or anchor id)."""
    terms: set[str] = set()
    for s in doc.sections:
        if s.start < doc.appendix_start:
            continue
        terms.update(_TERM_RE.findall(s.title))
    for a in doc.anchors:
        if a.startswith(("g-", "glossary-")):
            tail = a.split("-", 1)[1]
            terms.add(tail.upper())
    return {t for t in terms if t not in DEFAULT_STOPLIST}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

_ANNOTATION_RES = (
    (re.compile(r"\[\[(?!\s*\])[^\]]{2,}\]\]"), "human `[[…]]` review annotation"),
    (re.compile(r"\[CRITIC:"), "`[CRITIC: …]` marker"),
)


def check_unresolved_annotation(doc: Doc) -> list[Finding]:
    out = []
    for i, line in enumerate(doc.clean):
        for rx, what in _ANNOTATION_RES:
            m = rx.search(line)
            if m:
                out.append(
                    Finding(
                        "unresolved-annotation",
                        "high",
                        i + 1,
                        _excerpt(doc.raw[i]),
                        f"unresolved {what} — resolve it and strip the marker",
                    )
                )
                break
    return out


def _defined_inline(raw_line: str, term: str) -> bool:
    """True if the line expands `term` or links it to a glossary anchor."""
    t = re.escape(term)
    # "cancer-associated fibroblast (CAF)"  /  "(CAF)" straight after words
    if re.search(rf"[a-z]\w*[\s,)-]*\(\s*{t}\s*[,;)]", raw_line):
        return True
    if re.search(rf"\(\s*{t}\s*\)", raw_line) and re.search(r"[a-z]{3,}\s*\(", raw_line):
        return True
    # "CAF (cancer-associated fibroblast)" — a prose expansion, not "CPM (log2FC 3.1)"
    if re.search(rf"{t}\s*\(\s*[a-z][a-z \-]{{4,}}\)", raw_line):
        return True
    # "CAF — cancer-associated fibroblast" (glossary-entry style)
    if re.search(rf"{t}\s*[—–:]\s*[a-z]", raw_line):
        return True
    # first use is itself a link into the glossary
    if re.search(rf"\[[^\]]*\b{t}\b[^\]]*\]\(#\s*(?:g-|glossary)", raw_line, re.I):
        return True
    return False


def _first_uses(doc: Doc, stoplist: frozenset) -> dict[str, int]:
    """term -> 0-indexed line of first body (non-appendix) use."""
    first: dict[str, int] = {}
    for i, line in enumerate(doc.clean):
        if doc.skip(i):
            continue
        if _HEADING_RE.match(doc.raw[i]):
            continue
        for term in _TERM_RE.findall(line):
            if term in stoplist or len(term) < 2:
                continue
            first.setdefault(term, i)
    return first


def check_undefined_term(doc: Doc, stoplist: frozenset) -> list[Finding]:
    out = []
    for term, i in sorted(_first_uses(doc, stoplist).items(), key=lambda kv: kv[1]):
        if _defined_inline(doc.raw[i], term):
            continue
        if term in doc.glossary_terms:
            out.append(
                Finding(
                    "undefined-term",
                    "low",
                    i + 1,
                    _excerpt(doc.raw[i]),
                    f"'{term}' has a glossary entry but its first use does not link to it",
                )
            )
        else:
            out.append(
                Finding(
                    "undefined-term",
                    "medium",
                    i + 1,
                    _excerpt(doc.raw[i]),
                    f"'{term}' is used without expansion and has no glossary entry (C2)",
                )
            )
    return out


def check_late_introduction(doc: Doc, stoplist: frozenset) -> list[Finding]:
    out = []
    firsts = _first_uses(doc, stoplist)
    counts: dict[str, int] = {}
    for i, line in enumerate(doc.clean):
        if doc.skip(i):
            continue
        for term in _TERM_RE.findall(line):
            counts[term] = counts.get(term, 0) + 1
    for term, i in sorted(firsts.items(), key=lambda kv: kv[1]):
        if i < doc.intro_end:
            continue
        if counts.get(term, 0) < 2:
            continue  # a term used once in passing is not a load-bearing concept
        where = doc.section_of(i)
        out.append(
            Finding(
                "late-introduction",
                "medium",
                i + 1,
                _excerpt(doc.raw[i]),
                f"'{term}' first appears in '{where.title if where else '?'}', "
                f"after the Introduction ends at line {doc.intro_end} (C3)",
            )
        )
    return out


_NUMERIC_RES = (
    re.compile(r"\d\s*%"),
    re.compile(r"log2\s*FC|log₂|\bNES\b|\bCPM\b|\bTPM\b|\bFPKM\b"),
    re.compile(r"\bpadj\b|\bFDR\b|\bp\s*[<=≤]\s*0?\.\d|\bq\s*[<=≤]"),
    re.compile(r"\d\s*[×x]\s*10|10[⁻⁺−-]\d|e[-+]\d\d"),
    re.compile(r"\bn\s*=\s*\d"),
    re.compile(r"[−–-]?\d+\.\d+\s*(?:to|–|—)\s*[−–-]?\d+\.\d+"),
    # a run of "SYMBOL value" pairs — "VGLL3 -11.04, TEAD1 -8.39, TEAD2 -5.58"
    re.compile(r"(?:[A-Z][A-Z0-9]{1,9}\s*\(?[+−–-]?\d+\.\d+\)?[,;.]?\s+){3,}"),
)
_DECIMAL_RE = re.compile(r"\d+\.\d+")
_SOURCE_RES = (
    re.compile(r"\[\^[^\]]+\]"),  # footnote reference or definition
    re.compile(r"\b(?:results|data|background|references|documents)/[\w./-]+"),
    re.compile(r"\.(?:csv|tsv|txt|rds|h5ad|xlsx|json|parquet)\b"),
)


def _blocks(doc: Doc) -> list[tuple[int, int]]:
    """Contiguous non-blank line runs, as (start, end) 0-indexed, end exclusive."""
    out = []
    start = None
    for i, line in enumerate(doc.clean):
        if line.strip():
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(doc.clean)))
    return out


def _is_data_block(doc: Doc, start: int, end: int) -> bool:
    text = "\n".join(doc.clean[start:end])
    hits = sum(1 for rx in _NUMERIC_RES if rx.search(text))
    if len(_DECIMAL_RE.findall(text)) >= 4:
        hits += 1  # a paragraph dense with decimal values is reporting data
    if hits >= 2:
        return True
    is_table = sum(1 for i in range(start, end) if doc.clean[i].count("|") >= 2) >= 2
    return bool(hits and is_table)


def _has_source(doc: Doc, start: int, end: int, lookahead: int = 3) -> bool:
    stop = min(len(doc.raw), end + lookahead)
    text = "\n".join(doc.raw[start:stop])
    return any(rx.search(text) for rx in _SOURCE_RES)


def check_unsourced_data_claim(doc: Doc) -> list[Finding]:
    out = []
    for start, end in _blocks(doc):
        if doc.skip(start) or _HEADING_RE.match(doc.raw[start]):
            continue
        if not _is_data_block(doc, start, end):
            continue
        if _has_source(doc, start, end):
            continue
        out.append(
            Finding(
                "unsourced-data-claim",
                "medium",
                start + 1,
                _excerpt(doc.raw[start]),
                "numeric claim or data table with no source-file footnote (C7)",
            )
        )
    return out


_FIGURE_RES = (
    re.compile(r"!\[[^\]]*\]\("),
    re.compile(r"\b(?:Fig(?:ure)?\.?\s*\d|see\s+Fig)", re.I),
    re.compile(r"_figs/"),
)


def check_figureless_data_block(doc: Doc) -> list[Finding]:
    out = []
    for s in doc.sections:
        if doc.skip(s.start) or s.level < 2:
            continue
        # only leaf-ish sections: skip a parent that contains sub-sections
        if any(o.level > s.level and s.start < o.start < s.end for o in doc.sections):
            continue
        body = "\n".join(doc.raw[s.start : s.end])
        if any(rx.search(body) for rx in _FIGURE_RES):
            continue
        data_blocks = [
            (a, b)
            for a, b in _blocks(doc)
            if s.start <= a < s.end and _is_data_block(doc, a, b)
        ]
        if data_blocks:
            out.append(
                Finding(
                    "figureless-data-block",
                    "medium",
                    s.start + 1,
                    _excerpt(doc.raw[s.start]),
                    f"'{s.title}' asserts data ({len(data_blocks)} block(s)) with no figure (C6)",
                )
            )
    return out


_REGISTER_RES = (
    (re.compile(r"\b(you|your|yours|yourself)\b", re.I), "high", "second person (C1)"),
    (re.compile(r"\bmy\b|\bI\s+(?:think|found|checked|noted|believe|suspect)\b"), "medium",
     "first person (C1)"),
    (
        re.compile(
            r"\b(quiet hero|out of left field|smoothed over|smoothing over|needless to say"
            r"|at the end of the day|in a nutshell|textbook form|the crux"
            r"|obviously|of course|frankly|honestly|staggering|wildly)\b",
            re.I,
        ),
        "medium",
        "colloquialism (C1)",
    ),
    (
        re.compile(
            r"\b(proves|proven|definitely|certainly|without doubt|no doubt|genuinely"
            r"|clearly shows|simply is|is simply)\b"
            r"|is what .{3,40} looks like",
            re.I,
        ),
        "medium",
        "unhedged interpretive claim — hedge to the strength of the evidence (C1)",
    ),
)


def check_register(doc: Doc) -> list[Finding]:
    out = []
    for i, line in enumerate(doc.clean):
        if doc.in_meta(i) or _HEADING_RE.match(doc.raw[i]):
            continue
        seen: set[str] = set()
        for rx, sev, what in _REGISTER_RES:
            for m in rx.finditer(line):
                hit = m.group(0).lower()
                if hit in seen:
                    continue
                seen.add(hit)
                out.append(
                    Finding("register", sev, i + 1, _excerpt(doc.raw[i]), f"{what}: “{m.group(0)}”")
                )
    return out


_ATTRIBUTION_RE = re.compile(
    r"\bmarkers?\b|\bsignature of\b|\bhallmark of\b|\bcharacteristic of\b"
    r"|\bis expressed (?:in|by)\b|\bidentifies\s+\w+\s+cells\b",
    re.I,
)
_CITATION_RE = re.compile(r"\]\((?:https?://|#)|\[\^")


def check_unsourced_attribution(doc: Doc) -> list[Finding]:
    out = []
    for i, raw in enumerate(doc.raw):
        if doc.in_meta(i) or _HEADING_RE.match(raw):
            continue
        if not _ATTRIBUTION_RE.search(doc.clean[i]):
            continue
        window = "\n".join(doc.raw[max(0, i - 1) : min(len(doc.raw), i + 2)])
        if _CITATION_RE.search(window):
            continue
        out.append(
            Finding(
                "unsourced-attribution",
                "medium",
                i + 1,
                _excerpt(raw),
                "marker/signature attribution with no citation or glossary link (C8)",
            )
        )
    return out


_REF_SECTION_RE = re.compile(r"\b(references?|bibliograph)\b", re.I)
_ENTRY_RE = re.compile(r"^\s{0,3}(\d{1,3})\.\s+\S")
_CITE_RE = re.compile(r"\[(\d{1,3})\](?!\()")
_LINKED_CITE_RE = re.compile(r"\[(\d{1,3})\]\(#([^)\s]+)\)")
# Any link into the reference list, whatever its label reads — `[12](#e12)`,
# `[ref 12](#e12)`, `[Öhlund et al.](#e18)`. A citation is a citation however it
# is worded, and a label that names a different number than it links to is a
# renumbering that only got half applied.
_ENTRY_LINK_RE = re.compile(
    r"\[(?P<label>[^\]\n]{0,60}?)\]\(#(?P<prefix>[A-Za-z_-]*)(?P<num>\d{1,3})\)"
)
_ENTRY_ANCHOR_RE = re.compile(r"<a\s+(?:id|name)\s*=\s*[\"'](?P<prefix>[A-Za-z_-]*)(\d{1,3})[\"']", re.I)


def _ref_range(doc: Doc) -> tuple[int, int] | None:
    for s in doc.sections:
        if _REF_SECTION_RE.search(s.title):
            return (s.start, s.end)
    return None


def check_reference_numbering(doc: Doc) -> list[Finding]:
    """Numbered references must render as authored, and be reachable.

    A markdown ordered list renumbers sequentially from its first item, so
    authored numbers that run out of file order (typical when new references
    are appended into themed groups) silently display as different numbers —
    every in-text `[N]` then points a reader at the wrong entry.
    """
    rng = _ref_range(doc)
    if rng is None:
        return []
    lo, hi = rng
    out: list[Finding] = []

    entries: list[tuple[int, int]] = []  # (authored number, 0-indexed line)
    in_fence = False
    for i in range(lo, hi):
        if _FENCE_RE.match(doc.raw[i]):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _ENTRY_RE.match(doc.raw[i])
        if m:
            entries.append((int(m.group(1)), i))
    if not entries:
        return []

    numbers = [n for n, _ in entries]
    for prev, (n, line) in zip(numbers, entries[1:]):
        if n != prev + 1:
            out.append(
                Finding(
                    "reference-numbering",
                    "high",
                    line + 1,
                    _excerpt(doc.raw[line]),
                    f"reference [{n}] follows [{prev}] — numbering is out of file order, so a "
                    f"markdown renderer will renumber this list and every in-text citation after "
                    f"it will display against the wrong entry (C9)",
                )
            )
            break  # one report: the whole tail is affected

    known = set(numbers)
    # Prefixes actually used by the entry anchors, so a link to `#fig3` or
    # `#box2` is not mistaken for a citation.
    entry_prefixes = {
        m.group("prefix").lower()
        for i in range(lo, hi)
        for m in _ENTRY_ANCHOR_RE.finditer(doc.raw[i])
    }
    cited: set[int] = set()
    unlinked = 0
    first_unlinked: tuple[int, str] | None = None
    in_fence = False
    for i, raw in enumerate(doc.raw):
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence or lo <= i < hi:
            continue
        for m in _ENTRY_LINK_RE.finditer(raw):
            if _in_inline_code(raw, m.start()) or m.group("prefix").lower() not in entry_prefixes:
                continue
            target = int(m.group("num"))
            cited.add(target)
            label_nums = [int(d) for d in re.findall(r"\d{1,3}", m.group("label"))]
            if label_nums and label_nums[0] != target and label_nums[0] in known:
                out.append(
                    Finding(
                        "reference-numbering",
                        "medium",
                        i + 1,
                        _excerpt(raw),
                        f"citation reads [{label_nums[0]}] but links to entry [{target}] — a "
                        f"renumbering that reached the link but not its label, or the reverse (C9)",
                    )
                )
        for m in _CITE_RE.finditer(raw):
            if _in_inline_code(raw, m.start()):
                continue
            n = int(m.group(1))
            if n not in known:
                out.append(
                    Finding(
                        "reference-numbering",
                        "medium",
                        i + 1,
                        _excerpt(raw),
                        f"citation [{n}] has no entry in the reference list (C9)",
                    )
                )
                continue
            cited.add(n)
            unlinked += 1
            if first_unlinked is None:
                first_unlinked = (i + 1, _excerpt(raw))
    if unlinked and first_unlinked:
        line, excerpt = first_unlinked
        anchored = any('id="e' in r for r in doc.raw[lo:hi])
        detail = (
            f"{unlinked} in-text citation(s) are plain text rather than links to their entry"
            + (" — the entry anchors exist but nothing uses them" if anchored else "")
            + "; make each one `[N](#eN)` so a misnumbered list cannot misdirect the reader (C9)"
        )
        out.append(Finding("reference-numbering", "low", line, excerpt, detail))

    # An entry nothing cites is either a dropped citation or dead weight (C9).
    for n, line in entries:
        if n in cited:
            continue
        out.append(
            Finding(
                "reference-numbering",
                "low",
                line + 1,
                _excerpt(doc.raw[line]),
                f"reference entry [{n}] is never cited in the text — cite it where it is "
                "used, or drop it (C9)",
            )
        )
    return out


# A link whose target carries a Chromium text-fragment directive: the reader is
# taken to a highlighted passage, but nothing tells them which numbered source
# it is unless a `[N](#eN)` follows (C8).
_QUOTE_LINK_RE = re.compile(r"\]\([^)\s]*#:~:text=[^)]*\)")


def check_quote_without_reference(doc: Doc) -> list[Finding]:
    """Every highlighted quote link must be followed by its numbered source.

    A text-fragment link takes the reader to the passage but never names the
    entry it came from, so a reviewer auditing the bibliography cannot tie quote
    to reference without opening the URL and matching it by hand.
    """
    rng = _ref_range(doc)
    lo, hi = rng if rng else (len(doc.raw), len(doc.raw))
    out: list[Finding] = []
    in_fence = False
    for i, raw in enumerate(doc.raw):
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        # The reference entries ARE the sources; they do not cite themselves.
        if in_fence or lo <= i < hi or doc.in_meta(i):
            continue
        for m in _QUOTE_LINK_RE.finditer(raw):
            if _in_inline_code(raw, m.start()):
                continue
            window = raw[m.end() :]
            nxt = doc.raw[i + 1] if i + 1 < len(doc.raw) else ""
            if nxt.strip() and not _HEADING_RE.match(nxt) and not _FENCE_RE.match(nxt):
                window += " " + nxt
            # Stop at the next highlighted quote so its number is not credited here.
            cut = window.find("#:~:text=")
            if cut != -1:
                window = window[:cut]
            if _LINKED_CITE_RE.search(window):
                continue
            out.append(
                Finding(
                    "quote-without-reference",
                    "medium",
                    i + 1,
                    _excerpt(raw),
                    "highlighted quote link is not followed by a `[N](#eN)` naming its "
                    "source — the reader cannot tie the passage to a reference entry (C8)",
                )
            )
    return out


def check_broken_anchor(doc: Doc) -> list[Finding]:
    out = []
    in_fence = False
    for i, raw in enumerate(doc.raw):
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _INTERNAL_LINK_RE.finditer(raw):
            if _in_inline_code(raw, m.start()):
                continue
            target = m.group(1).strip().lower()
            if target and target not in {a.lower() for a in doc.anchors}:
                out.append(
                    Finding(
                        "broken-anchor",
                        "medium",
                        i + 1,
                        _excerpt(raw),
                        f"internal link '#{target}' matches no heading or anchor (C9)",
                    )
                )
    return out


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def _in_inline_code(line: str, pos: int) -> bool:
    """True when `pos` falls inside a `backticked` span.

    A draft that documents its own conventions writes things like "make each one
    `[N](#eN)`" — that is an example of a link, not a link, and neither the
    anchor nor the citation checks should read it as one.
    """
    return any(m.start() <= pos < m.end() for m in _INLINE_CODE_RE.finditer(line))


def _excerpt(line: str, width: int = 96) -> str:
    s = " ".join(line.split())
    return s if len(s) <= width else s[: width - 1] + "…"


def audit(
    text: str,
    only: set[str] | None = None,
    skip: set[str] | None = None,
    stoplist: frozenset = DEFAULT_STOPLIST,
    max_per_check: int = 25,
) -> list[Finding]:
    """Run the enabled checks over a markdown draft."""
    doc = Doc(text)
    wanted = set(only) if only else set(CHECKS)
    if skip:
        wanted -= set(skip)

    runners = {
        "unresolved-annotation": lambda: check_unresolved_annotation(doc),
        "undefined-term": lambda: check_undefined_term(doc, stoplist),
        "late-introduction": lambda: check_late_introduction(doc, stoplist),
        "unsourced-data-claim": lambda: check_unsourced_data_claim(doc),
        "figureless-data-block": lambda: check_figureless_data_block(doc),
        "register": lambda: check_register(doc),
        "unsourced-attribution": lambda: check_unsourced_attribution(doc),
        "broken-anchor": lambda: check_broken_anchor(doc),
        "reference-numbering": lambda: check_reference_numbering(doc),
        "quote-without-reference": lambda: check_quote_without_reference(doc),
    }

    out: list[Finding] = []
    for name in CHECKS:
        if name not in wanted:
            continue
        found = runners[name]()
        found.sort(key=lambda f: (-_SEVERITY_ORDER[f.severity], f.line))
        if max_per_check and len(found) > max_per_check:
            trimmed = len(found) - max_per_check
            found = found[:max_per_check]
            found.append(
                Finding(name, "low", 0, "", f"…{trimmed} further '{name}' candidate(s) suppressed")
            )
        out.extend(found)
    return out


def summarize(findings: list[Finding]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for f in findings:
        row = out.setdefault(f.check, {"high": 0, "medium": 0, "low": 0})
        row[f.severity] += 1
    return out


def render_md(findings: list[Finding], path: str, summary_only: bool = False) -> str:
    counts = summarize(findings)
    lines = [f"# audit_document — `{path}`", ""]
    if not findings:
        lines.append("No candidate defects found.")
        return "\n".join(lines) + "\n"
    lines += ["| Check | high | medium | low |", "|---|---:|---:|---:|"]
    for name in CHECKS:
        if name in counts:
            c = counts[name]
            lines.append(f"| `{name}` | {c['high']} | {c['medium']} | {c['low']} |")
    lines += ["", f"**{len(findings)} candidate(s).** Confirm each before acting on it.", ""]
    if summary_only:
        return "\n".join(lines) + "\n"
    lines += ["| Line | Check | Sev | Detail | Excerpt |", "|---:|---|---|---|---|"]
    for f in findings:
        loc = str(f.line) if f.line else "—"
        detail = f.detail.replace("|", "\\|")
        excerpt = f.excerpt.replace("|", "\\|")
        lines.append(f"| {loc} | `{f.check}` | {f.severity} | {detail} | {excerpt} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint a /debate draft against the conventions.")
    ap.add_argument("path", help="markdown draft to audit")
    ap.add_argument("--format", choices=["md", "json"], default="md", dest="fmt")
    ap.add_argument("--only", default="", help="comma-separated checks to run")
    ap.add_argument("--skip", default="", help="comma-separated checks to skip")
    ap.add_argument("--max-per-check", type=int, default=25)
    ap.add_argument("--stoplist", default=None, help="file of extra terms to ignore, one per line")
    ap.add_argument("--summary-only", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any candidate is found")
    args = ap.parse_args(argv)

    stoplist = DEFAULT_STOPLIST
    if args.stoplist:
        with open(args.stoplist, encoding="utf-8") as fh:
            extra = {w.strip().upper() for w in fh if w.strip() and not w.startswith("#")}
        stoplist = frozenset(stoplist | extra)

    with open(args.path, encoding="utf-8") as fh:
        text = fh.read()

    findings = audit(
        text,
        only={c.strip() for c in args.only.split(",") if c.strip()} or None,
        skip={c.strip() for c in args.skip.split(",") if c.strip()} or None,
        stoplist=stoplist,
        max_per_check=args.max_per_check,
    )

    if args.fmt == "json":
        payload = {
            "path": args.path,
            "summary": summarize(findings),
            "findings": [f.as_dict() for f in findings],
        }
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(render_md(findings, args.path, args.summary_only))

    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
