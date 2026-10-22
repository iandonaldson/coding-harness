#!/usr/bin/env python3
"""Guards on the agent harness itself: the slice record stays consistent with the plan.

Standalone, stdlib only (like the debate skill's script tests), so they run whatever the
project's stack. Run through `scripts/test.sh` (or `scripts/test.sh --harness`).
Exits 0 on success, 1 on the first failure.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURE_JSON = ROOT / "documents" / "feature-list.json"
FEATURE_MD = ROOT / "documents" / "feature-list.md"
PRODUCT = ROOT / "documents" / "product_description.md"
SLICE_ID = r"[a-z]+-\d{2}"

_passed = 0


def check(cond, msg):
    global _passed
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)
    _passed += 1
    print(f"ok: {msg}")


# Planning must be done before anything else here means anything.
for path in (FEATURE_MD, PRODUCT):
    check(
        "TEMPLATE PLACEHOLDER" not in path.read_text(encoding="utf-8"),
        f"{path.relative_to(ROOT)} has no TEMPLATE PLACEHOLDER (run a planning session)",
    )

slices = json.loads(FEATURE_JSON.read_text(encoding="utf-8"))["slices"]
ids = [s["id"] for s in slices]
check(len(ids) == len(set(ids)), "slice ids are unique")
for s in slices:
    check(re.fullmatch(SLICE_ID, s["id"]) is not None, f"{s['id']}: id is <feature>-NN")
    check(
        bool(s.get("title")) and bool(s.get("acceptance")) and isinstance(s.get("passes"), bool),
        f"{s['id']}: has a title, acceptance and a boolean passes",
    )

md = FEATURE_MD.read_text(encoding="utf-8")
md_ids = re.findall(rf"^\| `({SLICE_ID})` \|", md, re.M)
check(set(md_ids) == set(ids), "every JSON slice is defined in the Markdown, and vice versa")
# Appended slices (agreed later with the human) may extend the JSON beyond the plan.
check(ids[: len(md_ids)] == md_ids, "the JSON lists slices in the Markdown's order")

# Optional: a "## Delivery order" section whose bold-led lines list slice ids. If present,
# it must name every slice once, explicitly — a range (`a-01` → `a-04`) hides the slices
# between it, and sessions misread it.
if "## Delivery order" in md:
    section = md.split("## Delivery order", 1)[1].split("\n## ", 1)[0]
    lines = [line for line in section.splitlines() if line.startswith("**")]
    planned = [i for line in lines for i in re.findall(rf"`({SLICE_ID})`", line)]
    check(len(planned) == len(set(planned)), "the delivery order lists no slice twice")
    check(set(planned) == set(ids), "the delivery order lists every slice, with no ranges")
    check(ids[: len(planned)] == planned, "the JSON follows the delivery order")

print(f"\nAll {_passed} assertions passed.")
sys.exit(0)
