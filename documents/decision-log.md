# Decision log

Every option the agent accepted on the human's behalf in prototype mode
([AGENTS.md › Prototype mode](../AGENTS.md#prototype-mode)), so each can be reviewed
afterwards. Newest last. The prototype-close session reviews every `pending` entry and
marks it `confirmed` or `reopened` (a reopened decision becomes a new slice).

<!-- Entry format:

## DL-NN: <the question decided> — <slice-id>, YYYY-MM-DD

- **Options:** 1. <option> · 2. <option> · …
- **Chosen:** <option>, because <one line>
- **Recorded in:** <ADR NNN / commit / file>
- **Review:** pending
-->
