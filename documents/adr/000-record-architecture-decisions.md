---
status: accepted
date: 2026-10-22
decision-makers: the human owner (adopted with the coding-harness template)
---

# 000. Record architecture decisions as MADR files, with a prior-art investigation

## Context and Problem Statement

The team is one human and many agent sessions, and each session starts cold. Significant
decisions (the stack, a data format, a library, an API contract) must be written down where
the next session will find them, in a shape that is quick to review in a pull request and
that a test can check. Building something that an open standard or a maintained library
already provides should need a stated reason.

Which format and process do we use for architecture decision records (ADRs)?

## Decision Drivers

- Each decision shows the investigation behind it: candidates, licence, adoption,
  maintenance, fit with the project's constraints and integration cost, plus the rejected
  options and why.
- Plain files in the repository, readable with no tooling.
- An open, widely used template rather than an invented one.
- Reviewable in a pull request in minutes.

## Investigation

Candidates looked at:

- **MADR 4.0.0** (Markdown Architectural Decision Records, released 2024-09-17). MIT/CC0,
  maintained by the `adr` GitHub organisation, the most common Markdown ADR template. YAML
  front matter (status, date, decision-makers) and sections for context, drivers, options,
  outcome, consequences, confirmation and pros/cons. Sources: <https://adr.github.io/madr>,
  <https://ozimmer.ch/practices/2022/11/22/MADRTemplatePrimer.html>.
- **Nygard ADR** (2011: title, status, context, decision, consequences). The original, very
  light, widely copied. No place for options considered or their pros and cons.
- **Y-statements** ("In the context of …, facing …, we decided …"). Compact, but one sentence
  cannot hold a licence and maintenance evaluation.
- **adr-tools / log4brains** (tooling). Optional helpers for numbering and publishing. Not
  needed at our scale; a test does the checks we care about.

## Considered Options

1. MADR 4.0, extended with an **Investigation** section.
2. Nygard ADRs.
3. Y-statements.
4. Our own template.

## Decision Outcome

Chosen option: **1. MADR 4.0 with an Investigation section**. It is the most widely adopted
Markdown template and already has places for options and their pros and cons. One added
section records the investigation. We do not invent a format.

### The process

1. Every slice starts with a short investigation (AGENTS.md › Research and investigation).
   A significant decision becomes an ADR in the same pull request as the code it shapes.
2. Files are `documents/adr/NNN-kebab-title.md`, numbered from `000` without gaps, and
   listed in [`README.md`](README.md). Copy [`template.md`](template.md).
3. Required: YAML front matter with `status` (proposed, accepted, rejected, deprecated or
   superseded) and `date`, a `# NNN. Title`, and the sections *Context and Problem
   Statement*, *Investigation*, *Considered Options* and *Decision Outcome*. Other MADR
   sections are optional.
4. *Investigation* lists each candidate with licence, adoption, maintenance, fit and
   integration cost, and cites its sources. Not adopting a relevant open standard needs a
   stated reason.
5. An agent writes an ADR as `proposed`. It is accepted when the human merges the pull
   request; merging is the approval. In prototype mode (AGENTS.md › Prototype mode) the
   agent accepts it itself and adds `review: pending` to the front matter; the
   prototype-close review sets it to `confirmed` or `reopened`.
6. Accepted ADRs are not rewritten. A changed decision gets a new ADR, and the old one's
   status becomes `superseded` (naming the new ADR). Typos and broken links may be fixed in
   place.
7. An ADR records the decision; code walkthroughs record how it was built.

### Consequences

- Good: every decision shows its evidence and its rejected options, in one place.
- Good: `tests/harness/test_documents.py` checks numbering, front matter, required sections
  and the index, so a malformed ADR fails `scripts/test.sh`.
- Bad: one extra document per decision-bearing slice. Slices without a significant decision
  do not need one.

### Confirmation

`tests/harness/test_documents.py` enforces the structure. Content quality is checked in
human review of each pull request.

## Pros and Cons of the Options

- **MADR**: good, widely used, has options and pros/cons, has a minimal variant. Neutral,
  more headings than Nygard.
- **Nygard**: good, minimal. Bad, no structured place for rejected options.
- **Y-statements**: good, terse. Bad, too small for an investigation record.
- **Own template**: bad, invents a format.
