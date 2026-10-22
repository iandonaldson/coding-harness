<!-- TEMPLATE PLACEHOLDER — replace during the planning session -->
# Feature list

Features and their slices, in delivery order. Slice **status** lives in
[`feature-list.json`](feature-list.json) (`passes: true/false`), not here.

Slices follow *elephant carpaccio*: each is a thin, end-to-end, independently testable
increment that delivers something observable.

## <FEAT> — <Feature name>

<One paragraph: what the feature is and why.>

| Slice id | Title | Acceptance (end-to-end test) |
|---|---|---|
| `<feat>-01` | <thinnest useful end-to-end path> | <what the test proves> |
| `<feat>-02` | <next increment> | <…> |

<!-- Optional, once features interleave: a "## Delivery order" section with one line per
     group, each starting with the group's name in bold, listing every slice id explicitly
     (no ranges), e.g. **Walking skeleton:** `<feat>-01`, `<other>-01`, `<feat>-02`.
     tests/harness/test_harness.py checks it against feature-list.json. -->
