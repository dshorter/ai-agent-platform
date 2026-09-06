---
read: full
status: finding from 2026-09-06, measured. The metric works; what it counts is looser than its readers assume. No code changed — this is the evidence for a decision not yet made.
---

# `agent_span` counts strings, and half of them are not agents

`NEWSROOM.md` leans on one cross-agent signal: *stories live at the seams
between agents*, so a lead whose evidence spans several agents gets extra
weight. `agent_span` is that signal. It came up because a lead surfaced on
2026-09-06 carried `agent_span: 4`, the highest in its run, and the operator
asked what the four agents were.

## What the four were

```
content_agent
marketer_agent.extract
marketer_agent.package
ghost.create_draft
```

Counted as *actors* rather than as strings that is two agents — the content
agent and the marketer — plus one external system. `ghost.create_draft` is a
blog API call. `marketer_agent.extract` and `marketer_agent.package` are two
methods of one agent.

The lead was not wrong: the chain is real and the story it tells is real. The
**number attached to it** claims more than the data supports.

## The measurement

`sources.py` computes the span as `COUNT(DISTINCT agent_name)` grouped by
`workflow_sequence_id`. `agent_name` is free text. Measured across the whole
table on 2026-09-06:

| | |
|---|---|
| rows | 1,644 |
| distinct `agent_name` values | 12 |
| rows carrying a **dotted** name | **823 — 50.1%** |
| `step_number` values in use | **1, on all 1,644 rows** |

The dotted names are `marketer_agent.package` (276), `marketer_agent.extract`
(276), `ghost.create_draft` (270) and `ask.explorer` (1). So **half the table
inflates span by convention**, and the convention was never a decision — it is
how three call sites happened to name themselves.

## Two more things the same query showed

**`step_number` is dead.** Every row carries 1. `sources.py` selects sample
reasons `ORDER BY step_number`, which therefore orders nothing — the chain
sequence a reader sees is insertion order wearing a column name. The ordering
looks recorded and is not.

**A `workflow_sequence_id` is not one run.** One sequence held 24 rows: six
repetitions of the same four-name cycle. So a "sequence" bundles an unknown
number of passes, and `COUNT(*)` as `steps` measures rows, not steps.

## Why this matters beyond the metric

`ADR-002` §the reader work gives `agent_decisions` a mineable unit: *a
sequence*, addressed by `workflow_sequence_id`. That was written before any of
the above was measured. A reader built on it today would mine units of
unknown multiplicity, ordered by a dead column, and weight them with a count of
naming conventions.

**This is not an argument against the reader.** It is an argument that its unit
has to be settled first, and the estate's own router already flags the table's
one-row-per-invocation property as `observed` rather than `spec` — this is what
that looseness costs when something starts reading from it.

## What generalises

- **A metric over a free-text column measures the convention, not the thing.**
  Nobody chose to make the marketer count twice; two call sites just named
  themselves with dots.
- **A column that is always the same value reads as recorded and is not.**
  `ORDER BY step_number` is honest-looking code that sorts nothing, and it will
  keep looking correct until someone counts the distinct values.
- **The same shape as `jewels-are-transcript-only`:** a description
  (`agent_span` = "distinct agents touched") and a mechanism
  (`COUNT(DISTINCT agent_name)`) sharing a word, with the mechanism winning
  silently.

## Related

- `pipelines/scout/sources.py` — the span query
- `docs/uzelhub-crew/NEWSROOM.md` §the seam weighting this feeds
- `docs/architecture/adr-002-coverage-ledger-and-source-recovery.md` §the reader
  work — the `agent_decisions` row that needs its unit settled
- `AGENTS.md` §Shared surfaces — `agent_decisions`, one-row-per-invocation
  marked `observed`
- `docs/uzelhub-crew/jewels-are-transcript-only-2026-09-03.md` — same shape,
  one layer down
