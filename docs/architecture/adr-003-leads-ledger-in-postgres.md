# ADR-003: The Leads Ledger Belongs in Postgres, Not in Hand-Parsed YAML

**Status:** **Accepted — direction settled, migration not scheduled** (2026-09-04)
**Date:** 2026-09-04
**Deciders:** dshorter, Claude (Opus 5)
**Supersedes:** nothing. Amends the storage half of the three-concerns finding
in `docs/uzelhub-crew/newsroom-design-review-2026-09-04.md` §2.
**Related:** `pipelines/scout/leads.py`, `pipelines/scout/lead_mark.py`,
`database/ai_agent_platform/004_scout_jewel.sql`

## Context

### The finding that started it

The design review found `leads.yaml` doing three jobs whose lifetimes disagree:
the Editor's working queue (wants pruning), the Scout's dedup memory (can never
be pruned — pruning re-admits duplicates), and the record of what ambient
prospecting found (wants immutability). One file cannot satisfy all three, and
the forever-growing synthesis cost is the symptom.

### What was built before this ADR

Two changes landed on 2026-09-04, in this order:

1. **The pitch digest** (`ca10ed7`). The dedup payload rides as a 240-character
   digest per pitch rather than the whole thing: 279,744 chars → 130,815 over
   the live 477-lead ledger, 53% off the dominant term in every synthesis call
   and off its growth rate permanently.
2. **`pitched.yaml`** (`c51d7a0`). The dedup memory as its own file, holding id
   and digest and nothing else, so the file the Scout reads *physically
   contains* no status.

A third change was about to be built and **was stopped by the operator's
question**, which is the reason this ADR exists: *"this works if you're sure —
doing something in code and flat files that database tables with PK/FK couldn't
do better?"*

It could not. The argument collapsed immediately, on a fact that had been in
view the whole time.

### The fact that settles it

**The Scout already cannot run without Postgres.** `run.py` opens a connection
in all three verbs — walk (238), pass (305) and synthesis (350) — and
`scout_jewel`, `scout_session_log` and `agent_decisions` all live in the
cluster. A file-based ledger therefore buys **no** independence from the
database. It only means the newsroom's state lives in two places under two
different sets of guarantees.

Every argument previously made for flat files rested on an availability
property the system does not have.

### Point by point, against the flat-file design

| Enforced in code today | What the database does instead |
|---|---|
| A `verify()` asserting the ledger's id set equals the index's | A foreign key — on every write, at every call site, including ones not yet written |
| The status ban as *file shape* — `pitched.yaml` has no status column | A view plus a column `GRANT`. A file can be regenerated wrong; a grant cannot be bypassed by a bug |
| `lead_mark.TRANSITIONS`, forward-only and actor-matched, in Python | `CHECK` + trigger against a transitions table. The `rejected`-from-`drafted` gap that silently refused the review desk's verdicts for months would have surfaced as a schema question |
| The index is *derived* so a transition never moves a lead between files | A transaction. The derived design was a workaround for missing atomicity in a cluster that is already running |
| Gitignored state dir, because leads are transcript-derived and origin is public | A table cannot be `git add -f`'d by accident **at all** — this argues for the database on the estate's own top-rated risk |

One further point, which is the uncomfortable one. The pineapple rule is
currently enforced by a hand-rolled parser's **incompleteness**: `load_pitched`
matches two patterns and has none for `status`. That is genuinely clever, and it
is a safety property that depends on nobody ever improving a parser. A `GRANT`
has no such shape.

### The doctrine that was misapplied

"External, inspectable, warm-bootable" was written about the Scout's **cursor
and map** — *learned* state, where the concern was opaque weights and a rut you
cannot see without a retrain. The leads ledger is records, not learned state,
and `psql` is inspectable. The rule was applied outside the case it was written
for.

## Decision

**The leads ledger becomes Postgres tables. The migration is deferred and not
scheduled.**

Deferred because the operation is blocked on the *register of the copy* (see
`NEWSROOM.md` §The Scout's sources, corrected 2026-09-04), not on ledger
storage, and because 17 modules currently read or write the ledger. This ADR
settles the direction so the decision is not re-litigated, and records the
schema so the migration is a day's work rather than a design exercise.

### Schema sketch

```sql
CREATE TABLE scout_lead (
    id         TEXT PRIMARY KEY,          -- the slug: ledger key AND published URL, never re-keyed
    filed      DATE        NOT NULL,
    register   VARCHAR(16) NOT NULL,
    agent_span INT         NOT NULL DEFAULT 1,
    pitch      TEXT        NOT NULL,
    why_now    TEXT        NOT NULL,
    sources    TEXT[]      NOT NULL DEFAULT '{}',
    model      VARCHAR(64) NOT NULL,
    redaction  VARCHAR(16) NOT NULL DEFAULT 'required',
    status     VARCHAR(16) NOT NULL DEFAULT 'new' REFERENCES lead_state(state)
);

-- The lifecycle as rows. Stamps accumulate today as lines in a block; as rows
-- they are queryable, so time-to-publish reads off a join instead of a parser.
-- The PK makes a transition idempotent and unrepeatable by construction.
CREATE TABLE scout_lead_stamp (
    lead_id  TEXT        NOT NULL REFERENCES scout_lead(id),
    state    VARCHAR(16) NOT NULL REFERENCES lead_state(state),
    stamped  DATE        NOT NULL,
    actor    VARCHAR(32) NOT NULL,
    by_agent BOOLEAN     NOT NULL DEFAULT FALSE,   -- concordance excludes agent verdicts
    PRIMARY KEY (lead_id, state)
);

-- Forward-only transitions and actor-matching become data, not a Python dict.
CREATE TABLE lead_state (
    state      VARCHAR(16) PRIMARY KEY,
    from_state VARCHAR(16)[] NOT NULL,
    actor      VARCHAR(32)   NOT NULL
);
```

### The pineapple rule becomes a permission

```sql
CREATE VIEW scout_pitched AS SELECT id, digest(pitch) AS pitch FROM scout_lead;
GRANT SELECT ON scout_pitched TO scout_role;
-- and NO grant on scout_lead or scout_lead_stamp to that role
```

The Scout cannot read a status because it is **not permitted to**, rather than
because the reader it happens to use does not look. `digest()` is the first
sentence, not `left()` — see `leads._digest` for why a cut lands on a sentence
boundary.

**This is the single strongest reason to migrate**, ahead of cost and
ergonomics. The rule the whole newsroom rests on stops depending on discipline.

## Alternatives Considered

**A. Keep YAML; add a store module with a rigid contract, one write path.**
This was the plan as of an hour before this ADR, and the operator was right to
question it. Rejected: it is an elaborate hand-rolled reimplementation of
`PRIMARY KEY`, `FOREIGN KEY`, `CHECK`, `GRANT` and transactions, and it leaves
the pineapple property resting on a parser staying incomplete.

**B. Three independent YAML files, each a source of truth.** Rejected: a
lifecycle transition would have to MOVE a lead between the queue and the
archive — a two-file write that can leave it in both or neither, where today a
transition is one in-place stamp. This is the hazard that forced `pitched.yaml`
to be derived rather than authoritative, and it disappears entirely under a
transaction.

**C. SQLite rather than Postgres.** Genuinely tempting: one file, still
inspectable, and it matches the predictor's "plain Python + SQLite + JSONL"
charter. Rejected because the Scout's other state is already in Postgres, so
this would add a second engine and a second backup story to save a dependency
the Scout already has.

## Consequences

**Good.** Constraints hold at every call site rather than the ones that
remembered. The pineapple rule becomes a grant. The public-repo hazard — a
gitignored file is one `git add -f` from publishing transcript-derived material
— disappears, because a table cannot be committed. `leads_assay`'s cross-tabs
become SQL over a hand-rolled parser. And the Director stops answering from a
truncated tenth of a 371KB file, which is a documented live failure
(`pipelines/director/tools.py:45`).

**Costs and risks.** 17 modules touch the ledger today. The cluster has **no
per-table restore point** (`AGENTS.md` §Shared surfaces), so a bad migration is
a `pg_dumpall` restore that destroys everything written since — the same
constraint `005` handled by taking a `pg_dump` of the table first, and the same
discipline applies here. Hand-editing in an editor is lost; `lead_mark` already
exists because freehand editing was discouraged, but the loss is real and the
operator raised it. Slugs are the ledger key **and** the published URL across
~53 call sites, so the PK must carry them unchanged.

**What today's work means under this decision.** The digest survives unchanged —
payload size is worth fixing in either storage, and it becomes the view's
`digest()`. `pitched.yaml` becomes `scout_pitched`. The store module is **not
built**, and that is the point of stopping here: it is the piece that would have
become dead weight.

**Reversible?** The migration is one direction; a dump back to YAML is
mechanical if it is ever wanted.

## Not decided here

- **Whether the queue/archive split happens at all.** Measured 2026-09-04 it is
  a no-op: 472 of 477 leads would land in the queue and 5 in the archive,
  because 470 sit `new`. The queue is oversized because gate ① has not been
  worked, not because terminal leads are mixed into it. Under this schema the
  question dissolves — a queue is a `WHERE` clause — which is a further argument
  for the migration.
- **Whether `agent_decisions`-style governance applies.** The ledger is not an
  agent trace, but putting it in the cluster invites the question, and
  `AGENTS.md` §Open questions is where it belongs if asked.
