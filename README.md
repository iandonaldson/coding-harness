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
scripts/init.sh, scripts/test.sh  (test.sh --harness: harness checks only; --baseline: skip an unchanged full run)
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

---

## Agent Harness Architecture

### Overview

A project built from this template is built and maintained by long-running coding agents
(Claude Code, or any tool that reads `AGENTS.md`) working across many sessions. Each
session starts with a fresh context window, so the repository itself must hold durable
state that lets any new session pick up exactly where the last one left off — and that
lets the human see, review and steer what the agents did. This section describes the
harness design. It is based on Anthropic's published guidance on
[effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) [1],
and extends the original specification written for an earlier project (see
[What changed from the original specification](#what-changed-from-the-original-specification)).

The operational rules live in [`AGENTS.md`](AGENTS.md); this section explains the design
behind them.

### The core problem

A long-running agent working across many sessions faces a fundamental challenge: each new
session begins with no memory of earlier ones. Without explicit state artifacts, agents
repeat work, lose track of decisions, or make inconsistent choices. Context compaction
alone does not solve this — if the agent tries to do too much in one session and runs out
of context mid-task, the next session cannot reconstruct what happened [1][2]. Anthropic's
write-up names the typical failure modes: declaring the project finished too early,
leaving bugs or undocumented half-done work behind, marking features complete without
verifying them, and wasting each session working out how to run the app [1].

There is a second, human-side problem the original specification did not address: when
an agent writes most of the code, the human owner needs artifacts that explain *why* the
code is the way it is, in a form they can review without replaying every session. Much of
what this template adds beyond the original — ADRs, the glossary, walkthroughs, the
decision log, the AI review section in each PR — serves that reader.

### Two-agent harness pattern

The harness uses two roles. As in Anthropic's design, they are the same agent with the
same tools; only the starting instructions differ [1]. Here the `SessionStart` hook picks
the role: if `documents/claude-progress.md` does not exist, the session is an initializer.

**Initializer agent** — runs once, after a human-led planning session has filled in
`documents/product_description.md` and `documents/feature-list.md`. Responsibilities
(see [AGENTS.md › Initializer](AGENTS.md#initializer)):

- Confirm the git repository is properly initialised and on `main`
- Verify the planning documents no longer carry `TEMPLATE PLACEHOLDER` markers
- Fill in `documents/feature-list.json` from the slices in `feature-list.md`, all
  `"passes": false`
- Make `scripts/init.sh` (environment set-up and smoke test) and `scripts/test.sh` (the
  single test entry point) work for the project's stack
- Record the stack choice as ADR 001 and seed the glossary with the product's terms
- Create `documents/claude-progress.md` from its template and replace the `<…>`
  placeholders in `AGENTS.md` and `README.md`
- Commit all set-up artifacts with the message `chore: initialise agent harness`

**Coding agent** — runs in every later session. Responsibilities (see
[AGENTS.md › Working on a slice](AGENTS.md#working-on-a-slice)):

- Follow the session startup protocol below
- Implement exactly one slice per session — the first `"passes": false` entry in
  `feature-list.json` — on its own branch
- Start the slice with a short investigation (existing standards and libraries) and
  record significant decisions as ADRs
- Pass the slice's end-to-end tests via `scripts/test.sh` before flipping `passes` to
  `true`
- Run an independent AI code review (and a security review where relevant) before the PR
- Run `session-close`: update the progress log, add durable lessons to `code-learnings`,
  write a walkthrough
- Update `documents/claude-progress.md` at session end whether or not the slice is
  complete, then push and open a PR for the human to merge

### Key state artifacts

The original harness had four artifacts, all for the agent. This template has more, and
they serve two readers: the next agent session and the human owner.

| Artifact | Purpose | Main reader |
|---|---|---|
| `AGENTS.md` (imported by `CLAUDE.md`) | Standing agent instructions: startup protocol, slice discipline, git workflow, when to ask the human, prototype mode | Agent |
| `.claude/hooks/session-start.sh` | Injects working directory, branch, recent commits, harness mode, progress log and pending slices into every session | Agent |
| `documents/claude-progress.md` | Cross-session hand-off log: status, active slice, completed slices, blockers, test status, notes for the next session | Agent and human |
| `documents/product_description.md` | What we are building, with open questions (`[OQ-n]`) | Human and agent |
| `documents/feature-list.md` | Features and their slice definitions in prose (elephant carpaccio) | Human and agent |
| `documents/feature-list.json` | Single source of truth for slice status (`passes`); agents may only flip `false` → `true` or append | Agent |
| `documents/adr/` | Architecture decision records: context, investigation with cited sources, options, outcome | Human and agent |
| `documents/glossary.md` | Controlled vocabulary and acronyms, enforced by the harness checks | Human and agent |
| `documents/code_walkthroughs/` | Per-slice reference documents explaining the code end to end | Human |
| `documents/harness-mode` and `decision-log.md` | Normal or prototype mode; the options the agent accepted on the human's behalf | Human |
| `.claude/skills/code-learnings/` | Durable lessons (G-NN generic, L-NN project) that stop agents repeating mistakes | Agent |
| `scripts/init.sh`, `scripts/test.sh`, `documents/test-baseline.json` | One way to set up, one way to test, and the last full run's result with the code's fingerprint | Agent |
| `tests/harness/` | Checks that keep the harness documents themselves consistent | Agent |
| Git history and pull requests | Ground truth of what code exists, when and why it was added, and how it was reviewed | Human and agent |

### Session startup protocol

Every coding session begins with these steps before touching any code (the
`SessionStart` hook does the first two automatically):

1. Confirm the working directory, branch and recent commits
2. Read `documents/claude-progress.md` and the pending slices in `feature-list.json`
3. Reconcile: if a commit completed a slice still marked `"passes": false`, verify and
   fix the record first
4. Branch from an up-to-date `origin/main` (or `origin/prototype` in prototype mode)
5. Run `scripts/test.sh --baseline` — confirm the baseline is green (it is skipped when
   the code is unchanged since the recorded run)
6. Skim the `code-learnings` index
7. Begin the investigation and implementation of the next pending slice

This ritualised startup prevents the "where was I?" failure mode and keeps progress
consistent and incremental.

### Coding agent discipline

- One slice per session, on its own branch, through its own PR
- Tests pass via `scripts/test.sh` before a slice is marked complete
- Independent AI review before every PR; findings fixed or listed in the PR, never hidden
- A clean commit (explicit paths, never `git add -A`) after each slice
- `documents/claude-progress.md` updated at every session end
- The human is asked when a slice needs credentials or spending, infrastructure,
  data-model or API-contract decisions, destructive actions, or when test failures
  remain unexplained after one investigation pass — and prototype mode keeps all of
  these as hard stops

### Feature list format (elephant carpaccio)

The planning session produces `documents/feature-list.md` as a list of features, each
split into thin vertical slices [11]; the initializer mirrors the slices into
`documents/feature-list.json`. Following Anthropic's finding that models are less likely
to rewrite a JSON record than a Markdown one [1], status lives only in the JSON file and
agents may change only its `passes` field. Each slice must be:

- **Independently deployable** — does not depend on a later slice to be useful
- **Testable end to end** — has a clear pass/fail condition
- **Small** — implementable in one agent session
- **Numbered** — so progress tracking is unambiguous (`<feature>-01`, `<feature>-02`, …)

### What changed from the original specification

| Original | This template | Why |
|---|---|---|
| `CLAUDE.md` holds the instructions | `AGENTS.md` holds them; `CLAUDE.md` imports it | `AGENTS.md` became the cross-tool convention [5] |
| `claude-progress.txt` | `documents/claude-progress.md` from a template | Structured Markdown, kept with the other docs |
| Status in `feature-list.md` | Prose in `.md`, status in `.json` (`passes`) | Agents tamper less with JSON [1]; harness checks validate it |
| Startup steps run by hand | `SessionStart` hook injects state | Startup cannot be skipped |
| "Run existing tests" | `scripts/test.sh` with a fingerprinted baseline | One entry point; unchanged code skips the baseline run |
| No record of decisions | ADRs with an investigation step and cited sources | Decisions are reviewable and not re-litigated [12][13] |
| — | Glossary, walkthroughs, `code-learnings` | Human understanding and durable agent memory |
| — | AI code review before each PR | A separate reviewer catches what the author misses [3] |
| Human approves everything | Optional prototype mode with a decision log | Fast chaining while keeping every choice reviewable |

### Discussion

#### How this way of working has evolved

**From prompts to repository instructions (2023–2025).** Early agentic coding relied on
the conversation: the human re-explained the project each time. Tools then added
per-repository instruction files — `CLAUDE.md`, `.cursorrules`, `.windsurfrules` and
others — and in 2025 these converged on `AGENTS.md`, a plain-Markdown convention now
read by many agents and stewarded under the Linux Foundation [5]. Reusable procedures
followed the same path: Anthropic's `SKILL.md` format, loaded on demand so many skills
cost little context, was released as the open Agent Skills standard [6]. This template
uses both.

**From context windows to context engineering (2025).** As tasks outgrew one window,
attention moved from the prompt to *what is in context*. Anthropic's context-engineering
guidance names three techniques for long-horizon work — compaction, structured
note-taking outside the window, and sub-agents with clean contexts [2]. The progress log,
feature list and learnings here are structured note-taking; the AI review and the
`debate` skill's writer and critic are sub-agents.

**From one long session to many short ones (late 2025).** The long-running harness
paper [1] made the session, not the conversation, the unit of work: an initializer sets
up the environment, and each coding session makes one increment, verifies it and leaves
a clean, mergeable state with notes for its successor. The practitioner "Ralph Wiggum
loop" reached the same idea from the other direction — a shell loop that feeds the same
prompt file to a fresh agent until a plan file is empty, with all state kept in files
and git [7].

**From one agent to separated roles (2026).** Anthropic's follow-up [3] split the work
between a planner (expands a short brief into a specification), a generator, and an
evaluator that tests the running application and grades it against agreed criteria,
because tuning a separate sceptical evaluator is easier than making a generator critical
of its own work. In parallel, *spec-driven development* tools (GitHub Spec Kit, Kiro,
Tessl) made the specification a first-class, versioned artifact that drives
implementation [8][9]. Böckeler distinguishes *spec-first*, *spec-anchored* and
*spec-as-source* approaches [9]; this template is spec-anchored — the product
description, feature list and ADRs stay alongside the code and are updated with it.

**Evidence and counterweights.** METR's measurements show the length of task frontier
agents complete autonomously doubling roughly every four to seven months [10], which is
why harness components should be revisited: Anthropic's own follow-up removed its sprint
structure and moved evaluation to a single end-of-run pass as models improved, noting
that every harness component encodes an assumption about what the model cannot do alone
[3]. Two results argue for restraint. An ETH Zürich study found that LLM-generated
context files *reduced* task success and raised cost by over 20%, and that human-written
files helped only marginally, mainly when kept minimal [14]. And a randomised trial of
experienced open-source developers found AI tools made them 19% slower while they
believed they were faster [15] — a reminder to measure outcomes (tests passing, slices
merged) rather than trust the feeling of speed. Hence `AGENTS.md` here holds rules, not a
tour of the code, and tests decide when a slice is done.

#### Adapting the harness to different kinds of project

The core — durable state in the repository, one verified increment per session, a human
merge — fits most projects. What should vary is how much ceremony surrounds it:

| Project type | Keep | Change |
|---|---|---|
| **Throwaway script or spike** | Git, a short `AGENTS.md`, tests | Skip ADRs, walkthroughs and the glossary; one session may cover several trivially small slices |
| **Greenfield prototype** | Everything, in prototype mode | Let the agent chain slices and accept its own options; review the decision log and ADRs at prototype-close |
| **Production or regulated system** | Everything, in normal mode | Human-accepted ADRs; `security-review` on every slice touching authentication, data or egress; a human reviewer on every PR; consider a separate evaluator agent [3] |
| **Existing (brownfield) codebase** | Progress log, slices, tests | The initializer inventories the code and adds characterisation tests before the first slice; keep `AGENTS.md` minimal and let the code speak for itself [14] |
| **Web front end** | Slices, tests | End-to-end tests through a real browser (e.g. Playwright), which Anthropic found essential for verifying features [1][3]; grading criteria for subjective design quality [3] |
| **Library or public API** | ADRs for every contract change | Contract and compatibility tests in `scripts/test.sh`; slices sized by public behaviour, not files |
| **Data analysis or research** | `results/` and `data/` conventions, manifest, ADRs for method choices | Slices end in a reproducible result rather than a feature; tests check data invariants and pipeline outputs; the `debate` skill for the write-up |
| **Infrastructure as code** | Hard stops for provisioning, spending and secrets | Slices end in a reviewed plan, not an applied change; the human applies |
| **Team of humans and agents** | Branch per slice, explicit `git add` paths, PRs | Agents in separate worktrees; the progress log records who holds which slice; prototype mode off |
| **Long-form writing** | Glossary, ADR-style decision records | The `debate` skill (writer ↔ critic to a rubric score) in place of code tests |

Some knobs apply whatever the project type:

- **Slice size** follows model capability [10]. When slices finish with plenty of context
  left, make them larger; when sessions run out mid-slice, cut them thinner.
- **Remove what the model no longer needs.** Periodically try a slice without a harness
  component (say, a mandatory walkthrough) and keep it only if quality drops [3].
- **Separate the judge from the author.** A fresh-context reviewer or evaluator is the
  cheapest quality lever this template has; strengthen it before adding more process.
- **Keep instructions short and specific** [14]; move procedures into skills, which load
  only when needed [6].

### References

Supporting the design and the discussion:

1. Young, J. (2025). [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents). Anthropic Engineering, 26 November 2025.
2. Anthropic (2025). [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). Anthropic Engineering, 29 September 2025.
3. Rajasekaran, P. (2026). [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps). Anthropic Engineering, 24 March 2026.
4. Anthropic (2024). [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents). Anthropic Engineering, 19 December 2024.
5. [AGENTS.md](https://agents.md/) — a simple, open format for guiding coding agents; see also InfoQ, [AGENTS.md emerges as open standard for AI coding agents](https://www.infoq.com/news/2025/08/agents-md/) (August 2025).
6. [Agent Skills](https://agentskills.io/) — the open `SKILL.md` format, originally developed by Anthropic.
7. Huntley, G. (2025). [Ralph Wiggum as a "software engineer"](https://ghuntley.com/ralph/); background in VentureBeat, [How Ralph Wiggum went from The Simpsons to the biggest name in AI](https://venturebeat.com/ai/how-ralph-wiggum-went-from-the-simpsons-to-the-biggest-name-in-ai-right-now).
8. GitHub. [Spec Kit](https://github.github.com/spec-kit/) — toolkit for spec-driven development.
9. Böckeler, B. (2025). [Understanding spec-driven development: Kiro, spec-kit, and Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html). martinfowler.com, October 2025.
10. Kwa, T. et al. (2025). [Measuring AI ability to complete long tasks](https://arxiv.org/abs/2503.14499). METR, arXiv:2503.14499; updated estimates on [METR's site](https://metr.org/).
11. Cockburn, A. and Kniberg, H. [Elephant Carpaccio facilitation guide](https://blog.crisp.se/2013/07/25/henrikkniberg/elephant-carpaccio-facilitation-guide). Crisp blog, 2013.
12. Nygard, M. (2011). [Documenting architecture decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions). Cognitect blog, 15 November 2011.
13. [Markdown Architectural Decision Records (MADR)](https://adr.github.io/madr/) — the ADR template used here (ADR 000).
14. Gloaguen, T., Mündler, N., Müller, M., Raychev, V. and Vechev, M. (2026). [Evaluating AGENTS.md: are repository-level context files helpful for coding agents?](https://arxiv.org/abs/2602.11988) arXiv:2602.11988.
15. Becker, J., Rush, N., Barnes, E. and Rein, D. (2025). [Measuring the impact of early-2025 AI on experienced open-source developer productivity](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/). METR, 10 July 2025 (arXiv:2507.09089).

Further reading:

- Anthropic. [Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices) — instruction files, explore-plan-code-commit, and multi-session workflows.
- Anthropic. [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — orchestrator and sub-agents with clean contexts.
- Anthropic. [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills).
- Böckeler, B. [Exploring generative AI](https://martinfowler.com/articles/exploring-gen-ai.html) — an ongoing series on AI-assisted software delivery.
- Cockburn, A. [Elephant Carpaccio exercise](https://docs.google.com/document/d/1TCuuu-8Mm14oxsOnlk8DqfZAA1cvtYu9WGv67Yj_sSk/pub) — the original exercise handout.
- [adr.github.io](https://adr.github.io/) — ADR templates, tooling and examples.
