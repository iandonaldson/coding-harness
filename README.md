# <Project name>

<!-- TEMPLATE PLACEHOLDER — the initializer replaces this README's <…> sections.
     Until then, this file documents the harness template itself. -->

<One-paragraph description of the project.>

## Getting started

```bash
cp .env.example .env      # fill in local values
scripts/init.sh           # set up the environment + smoke test
scripts/test.sh           # run the test suite
```

## Documentation

- [Product description](documents/product_description.md)
- [Feature list](documents/feature-list.md) — slice status in [feature-list.json](documents/feature-list.json)
- [Architecture decision records](documents/adr/README.md)
- [Glossary](documents/glossary.md)
- [Code walkthroughs](documents/code_walkthroughs/README.md)
- [Agent operating instructions](AGENTS.md)

---

## About this harness

This repo started from the **coding-harness** template: a structure for building software
with coding agents (Claude Code and other AGENTS.md-aware tools) over many sessions, with
each session starting cold.

### Starting a new project from the template

1. On GitHub, **Use this template → Create a new repository**, then clone it.
2. Run a **planning session** with the agent: fill in `documents/product_description.md`,
   then break the work into thin end-to-end slices in `documents/feature-list.md`
   (elephant carpaccio). Remove the `TEMPLATE PLACEHOLDER` markers.
3. Start a new session. The `SessionStart` hook sees there is no
   `documents/claude-progress.md`, so the agent runs the **initializer**: it fills in
   `feature-list.json`, `scripts/init.sh`, `scripts/test.sh`, ADR 001 (the stack), the
   glossary and the `<…>` placeholders, and commits.
4. Each later session investigates, implements one slice on its own branch, runs an AI
   code review, runs `session-close`, and opens a PR for you to merge.

### Prototype mode

Set `mode: prototype` in `documents/harness-mode` to fast-track a prototype. The agent
accepts its own recommended options and ADRs (recording every option in
`documents/decision-log.md` for later review), merges each slice's PR into a `prototype`
branch itself, and starts the next slice's session, up to `chain-limit` sessions in a row.
It still stops for credentials, spending, infrastructure, destructive actions, secrets
and unexplained test failures. A closing session writes the deferred docs, reviews every
auto-accepted decision with you, and opens one PR from `prototype` into `main`. See
[AGENTS.md › Prototype mode](AGENTS.md#prototype-mode).

### Layout

```
AGENTS.md                       agent rules (CLAUDE.md just imports it)
documents/
  product_description.md        what we're building
  feature-list.md               features + slice definitions
  feature-list.json             slice status (passes: true/false)
  harness-mode                  normal | prototype, and the prototype chain limit
  decision-log.md               options auto-accepted in prototype mode
  glossary.md                   controlled vocabulary + acronyms
  adr/                          architecture decision records (MADR; process in 000)
  claude-progress.md            session hand-off log (created by the initializer)
  templates/                    template for the progress log
  code_walkthroughs/            NNN.<name>.md reference docs
scripts/init.sh, scripts/test.sh  (test.sh --harness: harness checks only)
scripts/fingerprint.sh          skip the startup test run when the code is unchanged
tests/harness/                  stdlib checks on the feature list, ADRs and glossary
.claude/
  settings.json                 shared hooks + permissions (committed)
  hooks/session-start.sh        injects git state + progress into each session
  skills/                       code-learnings, session-close, code-walkthrough, debate, find-skills
  agents/                       writer, critic (used by debate)
results/, data/                 local outputs and inputs (gitignored)
```

### Personal settings

`.claude/settings.json` is shared and committed. Put personal overrides in
`.claude/settings.local.json` (gitignored) — for example, extra permissions for your own
workflow:

```json
{
  "permissions": {
    "allow": ["Bash(scripts/test.sh:*)", "Bash(git log:*)", "Bash(gh pr view:*)"]
  }
}
```
