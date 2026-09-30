#!/usr/bin/env python3
"""fix_citations.py — make a `/debate` draft's citations navigable (C8/C9).

Part of the `/debate` skill, and the remediation counterpart to the
`reference-numbering` and `quote-without-reference` checks in
`audit_document.py`. Three transformations, applied in this order:

  1. RENUMBER  the reference entries `1..M` in FILE ORDER, rewriting both the
     list number and its `<a id="eN">` anchor. A markdown ordered list renumbers
     itself from its first item, so entries authored out of file order (what
     happens when a later round slots new sources into a themed group) render as
     DIFFERENT numbers than were authored, and every in-text `[N]` after the
     first break silently points at the wrong entry.
  2. RELINK    every in-text `[N]` to `[N'](#eN')` under that remapping, so a
     click lands on the right entry even if a renderer disagrees about numbering.
  3. PAIR      every highlighted `#:~:text=` quote link with the `[N](#eN)` of
     the entry it came from, resolved by matching the link's URL base against
     the URL bases of the reference entries. A highlight shows the reader the
     passage but never says which numbered source it is.

The transformation is idempotent: running it on its own output changes nothing.

Pure standard library — no third-party deps, so it runs anywhere python3 does.

CLI
    python3 fix_citations.py DRAFT.md              # dry run: report only
    python3 fix_citations.py DRAFT.md --in-place
    python3 fix_citations.py DRAFT.md --output NEXT.md

Programmatic
    from fix_citations import fix_citations, Report
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import NamedTuple

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_REF_SECTION_RE = re.compile(r"\b(references?|bibliograph)\b", re.I)
# "12. <a id="e12"></a>Author A. *Title.* — [quote](url)"
_ENTRY_RE = re.compile(r"^(?P<indent>\s{0,3})(?P<num>\d{1,3})\.(?P<gap>\s+)(?P<body>\S.*)$")
_ENTRY_ANCHOR_RE = re.compile(r"<a\s+(?:id|name)\s*=\s*[\"'](?P<prefix>[A-Za-z_-]*)(?P<num>\d{1,3})[\"']")
_PLAIN_CITE_RE = re.compile(r"\[(\d{1,3})\](?!\()")
_LINKED_CITE_RE = re.compile(r"\[(\d{1,3})\]\(#(?P<prefix>[A-Za-z_-]*)(?P<num>\d{1,3})\)")
# Any link into the reference list, whatever its label reads: `[12](#e12)`,
# `[ref 12](#e12)`, `[refs 12, 13](#e12)`, `[see 12](#e12)`.
_ANY_ENTRY_LINK_RE = re.compile(
    r"\[(?P<label>[^\]\n]{0,60}?)\]\(#(?P<prefix>[A-Za-z_-]*)(?P<num>\d{1,3})\)"
)
_LABEL_NUM_RE = re.compile(r"\d{1,3}")
# A label that is nothing but citation numbers, optionally introduced by a word:
# "12", "ref 12", "refs 12, 13", "see 12 and 13". Only these get their numbers
# remapped; a prose label ("the 2019 trial") keeps its text and is reported.
_CITE_LABEL_RE = re.compile(r"^\s*(?:refs?\.?|see)?[\s\d,;&]*\d[\s\d,;&]*(?:and[\s\d,;&]+)?$", re.I)
_URL_RE = re.compile(r"\((?P<url>https?://[^)\s]+)\)")
_QUOTE_LINK_RE = re.compile(r"\]\((?P<url>[^)\s]*#:~:text=[^)]*)\)")


class Report(NamedTuple):
    entries: int
    renumbered: int  # entries whose number changed
    citations: int  # in-text citations rewritten as links
    remapped: int  # citations whose number changed
    quotes_paired: int
    quotes_already_paired: int
    unmatched_quotes: list[tuple[int, str]]  # (1-indexed line, url base)
    ambiguous_urls: list[str]  # URL bases claimed by more than one entry
    relabel_review: list[tuple[int, str]]  # prose labels carrying a number, remapped target

    def render(self) -> str:
        lines = [
            f"entries            : {self.entries} ({self.renumbered} renumbered)",
            f"in-text citations  : {self.citations} linked ({self.remapped} renumbered)",
            f"quote links paired : {self.quotes_paired} "
            f"({self.quotes_already_paired} already carried a reference)",
        ]
        for line, url in self.unmatched_quotes:
            lines.append(f"  UNMATCHED line {line}: {url} — no reference entry cites this URL")
        for url in self.ambiguous_urls:
            lines.append(f"  AMBIGUOUS {url} — claimed by more than one entry; left unpaired")
        for line, snippet in self.relabel_review:
            lines.append(f"  CHECK LABEL line {line}: {snippet} — target remapped, label left as written")
        return "\n".join(lines)


def _url_base(url: str) -> str:
    return url.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def _ref_range(lines: list[str]) -> tuple[int, int]:
    """(start, end) 0-indexed half-open range of the reference section."""
    heads = [(i, len(m.group(1))) for i, l in enumerate(lines) if (m := _HEADING_RE.match(l))]
    for n, (i, level) in enumerate(heads):
        if not _REF_SECTION_RE.search(_HEADING_RE.match(lines[i]).group(2)):
            continue
        end = len(lines)
        for later_i, later_level in heads[n + 1 :]:
            if later_level <= level:
                end = later_i
                break
        return (i, end)
    return (len(lines), len(lines))


def _fence_mask(lines: list[str]) -> list[bool]:
    """True for lines inside (or delimiting) a fenced code block."""
    out, in_fence = [], False
    for line in lines:
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(True)
            continue
        out.append(in_fence)
    return out


def fix_citations(text: str, anchor_prefix: str = "e") -> tuple[str, Report]:
    """Renumber, relink and pair a draft's citations. Returns (text, report)."""
    lines = text.splitlines()
    lo, hi = _ref_range(lines)
    fenced = _fence_mask(lines)

    # --- 1. entries, in file order ----------------------------------------
    entries: list[tuple[int, int]] = []  # (authored number, 0-indexed line)
    for i in range(lo, hi):
        if fenced[i]:
            continue
        m = _ENTRY_RE.match(lines[i])
        if m:
            entries.append((int(m.group("num")), i))

    remap = {old: new for new, (old, _) in enumerate(entries, start=1)}
    renumbered = sum(1 for old, _ in entries if remap[old] != old)

    # URL base -> new number, for pairing quote links.
    by_url: dict[str, set[int]] = {}
    for old, i in entries:
        for m in _URL_RE.finditer(lines[i]):
            by_url.setdefault(_url_base(m.group("url")), set()).add(remap[old])
    ambiguous = sorted(u for u, ns in by_url.items() if len(ns) > 1)
    url_to_ref = {u: next(iter(ns)) for u, ns in by_url.items() if len(ns) == 1}

    def _renumber_entry(line: str, old: int) -> str:
        new = remap[old]
        m = _ENTRY_RE.match(line)
        body = m.group("body")
        anchor = _ENTRY_ANCHOR_RE.search(body)
        if anchor is None:
            # No anchor to link to: give the entry one, so `[N](#eN)` resolves.
            body = f'<a id="{anchor_prefix}{new}"></a>{body}'
        elif anchor.group("prefix") in ("", anchor_prefix):
            # Rewrite the id attribute only; the rest of the tag stays put.
            body = body[: anchor.start()] + f'<a id="{anchor_prefix}{new}"' + body[anchor.end() :]
        return f"{m.group('indent')}{new}.{m.group('gap')}{body}"

    for old, i in entries:
        lines[i] = _renumber_entry(lines[i], old)

    # --- 2. in-text citations ---------------------------------------------
    citations = remapped = 0
    relabel_review: list[tuple[int, str]] = []
    line_no = [0]  # current 1-indexed line, for report locations

    def _link_plain(m: re.Match) -> str:
        nonlocal citations, remapped
        old = int(m.group(1))
        if old not in remap:
            return m.group(0)  # no entry: leave it for the linter to report
        new = remap[old]
        citations += 1
        remapped += new != old
        return f"[{new}](#{anchor_prefix}{new})"

    def _relink(m: re.Match) -> str:
        """Remap an existing link into the reference list, whatever its label.

        The label is not always the bare number: drafts also write
        `[ref 21](#e21)` and `[refs 21, 22](#e21)`. Those carry the SAME stale
        number as the target after a renumbering, so they stay self-consistent
        while pointing at the wrong paper — invisible to a label-vs-target
        check. Every number in the label is remapped alongside the target.
        """
        nonlocal remapped
        label, target = m.group("label"), int(m.group("num"))
        if m.group("prefix") != anchor_prefix or target not in remap:
            return m.group(0)  # a link into something else
        new = remap[target]
        remapped += new != target
        if _CITE_LABEL_RE.match(label):
            label = _LABEL_NUM_RE.sub(
                lambda d: str(remap.get(int(d.group(0)), int(d.group(0)))), label
            )
        elif _LABEL_NUM_RE.search(label) and new != target:
            # A number in a prose label may or may not be a citation number;
            # the target is remapped either way, but a human should look.
            relabel_review.append((line_no[0], m.group(0)))
        return f"[{label}](#{anchor_prefix}{new})"

    for i, line in enumerate(lines):
        if fenced[i] or lo <= i < hi:
            continue
        line_no[0] = i + 1
        line = _ANY_ENTRY_LINK_RE.sub(_relink, line)
        lines[i] = _PLAIN_CITE_RE.sub(_link_plain, line)

    # --- 3. pair the quote links ------------------------------------------
    paired = already = 0
    unmatched: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if fenced[i] or lo <= i < hi:
            continue
        out, pos = [], 0
        for m in _QUOTE_LINK_RE.finditer(line):
            out.append(line[pos : m.end()])
            pos = m.end()
            tail = line[m.end() :]
            cut = tail.find("#:~:text=")
            window = tail[:cut] if cut != -1 else tail
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if cut == -1 and nxt.strip() and not _HEADING_RE.match(nxt):
                nxt_cut = nxt.find("#:~:text=")
                window += " " + (nxt[:nxt_cut] if nxt_cut != -1 else nxt)
            if _LINKED_CITE_RE.search(window):
                already += 1
                continue
            base = _url_base(m.group("url"))
            ref = url_to_ref.get(base)
            if ref is None:
                # An ambiguous base is already reported once, as ambiguous.
                if base not in by_url:
                    unmatched.append((i + 1, base))
                continue
            out.append(f" [{ref}](#{anchor_prefix}{ref})")
            paired += 1
        if out:
            lines[i] = "".join(out) + line[pos:]

    report = Report(
        entries=len(entries),
        renumbered=renumbered,
        citations=citations,
        remapped=remapped,
        quotes_paired=paired,
        quotes_already_paired=already,
        unmatched_quotes=unmatched,
        ambiguous_urls=ambiguous,
        relabel_review=relabel_review,
    )
    fixed = "\n".join(lines)
    if text.endswith("\n"):
        fixed += "\n"
    return fixed, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Renumber, relink and pair a draft's citations.")
    ap.add_argument("path", help="markdown draft")
    ap.add_argument("--output", default=None, help="write the result here")
    ap.add_argument("--in-place", action="store_true", help="rewrite the draft in place")
    ap.add_argument("--anchor-prefix", default="e", help="entry anchor prefix (default: e)")
    args = ap.parse_args(argv)

    with open(args.path, encoding="utf-8") as fh:
        text = fh.read()
    fixed, report = fix_citations(text, args.anchor_prefix)

    dest = args.path if args.in_place else args.output
    if dest:
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(fixed)
        sys.stdout.write(f"wrote {dest}\n")
    else:
        sys.stdout.write("dry run — pass --in-place or --output to write\n")
    sys.stdout.write(report.render() + "\n")
    return 1 if (report.unmatched_quotes or report.ambiguous_urls) else 0


if __name__ == "__main__":
    raise SystemExit(main())
