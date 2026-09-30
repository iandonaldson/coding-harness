#!/usr/bin/env python3
"""link_reference.py — tiered citation → source → highlighted-link generator.

Part of the `/debate` skill. Given a source locator and the exact supporting
quote, emit the best-available clickable markdown link:

  Tier 1 (web)   : Chrome/Edge text-fragment URL  <url>#:~:text=<quote>
                   -> a USER click scrolls to and HIGHLIGHTS the passage.
                   NOTE: the highlight fires only when (a) `quote` is a VERBATIM
                   substring of the rendered page (a paraphrase silently fails),
                   and (b) the link is opened by user action in a Chromium
                   browser. Other viewers just open the page at the top.
  Tier 2 (pdf)   : page anchor                     <path-or-url>#page=N
                   -> opens the PDF at the supporting page.
  Tier 3 (other) : plain link + a blockquote of the passage (always works).

A highlighted quote tells the reader *where* the passage is but not *which
numbered source* it is, so `--ref N` emits the paired form the conventions
require (C8) — the link followed by a hyperlinked citation into the reference
list:

    [the quoted passage](https://…#:~:text=…) [12](#e12)

Pure standard-library — no third-party deps, so it runs anywhere python3 does.

CLI
    python3 link_reference.py --locator <url|path> --quote "<text>" \
        [--page N] [--title "..."] [--format link|block] \
        [--ref N] [--anchor-prefix e]

Programmatic
    from link_reference import make_link, classify_locator, build_web_fragment
"""
from __future__ import annotations

import argparse
import sys
from urllib.parse import quote as _urlquote

# How many words before we switch a web fragment from `text=<whole>` to the
# more robust `text=<startWords>,<endWords>` (textStart,textEnd) form.
_LONG_QUOTE_WORDS = 8
_EDGE_WORDS = 4  # words taken from each end when truncating a long quote


def classify_locator(locator: str) -> str:
    """Return 'web', 'pdf', or 'other' for a source locator."""
    loc = (locator or "").strip()
    low = loc.lower()
    is_url = low.startswith("http://") or low.startswith("https://")
    # Strip any query/fragment before checking a .pdf extension.
    path_part = low.split("#", 1)[0].split("?", 1)[0]
    if path_part.endswith(".pdf"):
        return "pdf"
    if is_url:
        return "web"
    return "other"


def encode_fragment_text(text: str) -> str:
    """Percent-encode a string for use inside a `#:~:text=` directive.

    urllib's quote() leaves the unreserved set `-._~` untouched. Within a text
    directive, `-` is the prefix/suffix context separator and MUST be encoded
    when it is a literal part of the quote, so we encode it explicitly.
    Commas and ampersands (directive separators) are already handled by
    quote(safe='').
    """
    s = _urlquote(text.strip(), safe="")
    return s.replace("-", "%2D")


def build_web_fragment(url: str, quote_text: str) -> str:
    """Build a text-fragment URL that highlights `quote_text` at `url`."""
    base = url.split("#", 1)[0]  # drop any pre-existing fragment
    words = quote_text.split()
    if len(words) > _LONG_QUOTE_WORDS:
        start = " ".join(words[:_EDGE_WORDS])
        end = " ".join(words[-_EDGE_WORDS:])
        directive = f"{encode_fragment_text(start)},{encode_fragment_text(end)}"
    else:
        directive = encode_fragment_text(quote_text)
    return f"{base}#:~:text={directive}"


def _blockquote(quote_text: str) -> str:
    """Render a passage as a markdown blockquote (multi-line safe)."""
    lines = quote_text.strip().splitlines() or [""]
    return "\n".join(f"> {ln}" for ln in lines)


def reference_citation(ref: int | str, anchor_prefix: str = "e") -> str:
    """Render `[N](#eN)` — a citation that links into the reference list (C8/C9)."""
    n = str(ref).strip().lstrip("[").rstrip("]")
    return f"[{n}](#{anchor_prefix}{n})"


def make_link(
    locator: str,
    quote_text: str,
    page: int | None = None,
    title: str | None = None,
    fmt: str = "link",
    ref: int | str | None = None,
    anchor_prefix: str = "e",
) -> str:
    """Return a markdown citation snippet using the best available tier.

    fmt="link"  -> a single inline markdown link (Tier 3 also appends a
                   blockquote, since a bare link cannot show the passage).
    fmt="block" -> the link followed by a blockquote of the passage, for
                   every tier (useful in a references/footnotes section).

    ref         -> the reference-list number this quote comes from. When given,
                   the link is followed by `[N](#eN)`, so a reader who follows
                   the highlight can also see which numbered source it is (C8).
    """
    kind = classify_locator(locator)
    label = title or (quote_text.strip()[:60] + ("…" if len(quote_text.strip()) > 60 else ""))
    label = label.replace("\n", " ").strip() or "source"
    cite = f" {reference_citation(ref, anchor_prefix)}" if ref not in (None, "") else ""

    if kind == "web":
        href = build_web_fragment(locator, quote_text)
        link = f"[{label}]({href}){cite}"
        if fmt == "block":
            return f"{link}\n\n{_blockquote(quote_text)}"
        return link

    if kind == "pdf":
        base = locator.split("#", 1)[0]
        href = f"{base}#page={page}" if page else base
        page_note = f", p.{page}" if page else ""
        link = f"[{label}]({href}){page_note}{cite}"
        if fmt == "block":
            return f"{link}\n\n{_blockquote(quote_text)}"
        return link

    # Tier 3 — fallback. A bare link can't highlight, so always show the passage.
    if locator.lower().startswith(("http://", "https://")):
        link = f"[{label}]({locator})"
    else:
        link = f"`{locator}`" if locator else "(source unknown)"
    return f"{link}{cite}\n\n{_blockquote(quote_text)}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a tiered citation link.")
    ap.add_argument("--locator", required=True, help="Source URL or file path")
    ap.add_argument("--quote", required=True, help="Exact supporting passage")
    ap.add_argument("--page", type=int, default=None, help="PDF page number")
    ap.add_argument("--title", default=None, help="Link label (defaults to a quote snippet)")
    ap.add_argument("--format", choices=["link", "block"], default="link", dest="fmt")
    ap.add_argument(
        "--ref",
        default=None,
        help="reference-list number for this source; emits the paired `[N](#eN)` after the link",
    )
    ap.add_argument("--anchor-prefix", default="e", help="entry anchor prefix (default: e)")
    args = ap.parse_args(argv)
    sys.stdout.write(
        make_link(
            args.locator,
            args.quote,
            args.page,
            args.title,
            args.fmt,
            args.ref,
            args.anchor_prefix,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
