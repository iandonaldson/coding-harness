#!/usr/bin/env python3
"""Guards on the decision record (ADRs) and the project glossary.

Standalone, stdlib only (like the debate skill's script tests), so they run whatever the
project's stack. Run through `scripts/test.sh` (or `scripts/test.sh --harness`).
Exits 0 on success, 1 on the first failure.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR_DIR = ROOT / "documents" / "adr"
GLOSSARY = ROOT / "documents" / "glossary.md"

ADR_NAME = re.compile(r"^(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
STATUSES = {"proposed", "accepted", "rejected", "deprecated", "superseded"}
REVIEWS = {"pending", "confirmed", "reopened"}  # prototype mode (ADR 000, step 5)
# MADR 4.0 sections every ADR keeps, plus the investigation record (ADR 000).
REQUIRED_SECTIONS = (
    "## Context and Problem Statement",
    "## Investigation",
    "## Considered Options",
    "## Decision Outcome",
)

# Upper-case words that are codes, identifiers or keywords, not acronyms. Add the
# project's own (role names, slice feature codes, field values, CLI metavariables, …)
# here rather than to the glossary. A plural ("SDKs") counts as its singular.
NOT_ACRONYMS = {
    *("MUST", "SHOULD", "MAY", "NOT", "RECOMMENDED", "REQUIRED", "SHALL"),  # RFC 2119
    *("AGENTS", "CLAUDE", "LICENSE", "README", "SKILL", "TODO"),  # file names
    *("NN", "NNN", "YYYY", "MM", "DD"),  # numbering and date patterns
    *("TEMPLATE", "PLACEHOLDER", "WARNING", "INITIALIZER"),
}

_passed = 0


def check(cond, msg):
    global _passed
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    _passed += 1
    print(f"ok: {msg}")


# --- ADRs -------------------------------------------------------------------------------

adrs = sorted(p for p in ADR_DIR.glob("*.md") if ADR_NAME.match(p.name))
stray = {p.name for p in ADR_DIR.glob("*.md")} - {p.name for p in adrs}
check(stray <= {"README.md", "template.md"}, f"no stray files in documents/adr: {stray or '-'}")
numbers = [int(ADR_NAME.match(p.name)[1]) for p in adrs]
check(numbers == list(range(len(numbers))) and numbers, "ADRs are numbered from 000, no gaps")

index = (ADR_DIR / "README.md").read_text(encoding="utf-8")
for adr in adrs:
    text = adr.read_text(encoding="utf-8")
    front = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    check(front is not None, f"{adr.name}: has front matter")
    status = re.search(r"^status:\s*(\w+)", front[1], re.M)
    check(status is not None and status[1] in STATUSES, f"{adr.name}: has a valid status")
    check(
        re.search(r"^date:\s*\d{4}-\d{2}-\d{2}$", front[1], re.M) is not None,
        f"{adr.name}: has a date",
    )
    review = re.search(r"^review:[ \t]*(.*)$", front[1], re.M)
    check(review is None or review[1].strip() in REVIEWS, f"{adr.name}: review is one of {REVIEWS}")
    check(re.search(r"^# \S", text, re.M) is not None, f"{adr.name}: has a title")
    for section in REQUIRED_SECTIONS:
        check(section in text, f"{adr.name}: has {section!r}")
    check(f"]({adr.name})" in index, f"{adr.name}: is listed in documents/adr/README.md")


# --- Glossary ---------------------------------------------------------------------------


def acronyms(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # code is not prose
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"\]\([^)]*\)|https?://\S+", "", text)  # link targets
    text = re.sub(r"<!--.*?-->|<[^>\n]*>", "", text, flags=re.S)  # comments, <placeholders>
    pattern = r"(?<![A-Za-z0-9_/.-])([A-Z][A-Z0-9]*[A-Z][A-Z0-9]*)s?(?![A-Za-z0-9_])"
    return set(re.findall(pattern, text))


defined = set(re.findall(r"^\| \*\*(.+?)\*\*", GLOSSARY.read_text(encoding="utf-8"), re.M))
documents = [p for p in (ROOT / "documents").rglob("*.md") if "templates" not in p.parts]
missing = {}
for document in sorted([*documents, ROOT / "README.md"]):
    for word in acronyms(document.read_text(encoding="utf-8")) - defined - NOT_ACRONYMS:
        if not (word.endswith("S") and word[:-1] in defined | NOT_ACRONYMS):
            missing.setdefault(word, document.relative_to(ROOT).as_posix())
check(missing == {}, f"the glossary spells out every acronym the documents use {missing or ''}")

print(f"\nAll {_passed} assertions passed.")
sys.exit(0)
