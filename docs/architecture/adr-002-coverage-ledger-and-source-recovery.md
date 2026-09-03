# ADR-002: A Coverage Ledger for All Six Sources, and the Supervised Recovery Runs

**Status:** Proposed
**Date:** 2026-09-03
**Deciders:** dshorter, Claude (Fable 5)
**Depends on:** schema 1.4.0 (`005_jewel_source.sql`, applied 2026-09-03)
**Related:** `docs/uzelhub-crew/jewels-are-transcript-only-2026-09-03.md`

## Context

Schema 1.4.0 made a jewel able to cite a non-transcript source. Nothing yet
mines one. This ADR covers how the other five sources get walked, and how the
first runs are conducted so we learn what they cost and what they drop.

**This is a re-walk, not a new capability — the distinction matters.** Git, the
docs, the ledger, the calendar, the survey and `agent_decisions` have been in the
Scout's source catalog since v1 and have always been readable via free roam.
Nothing is being added to what the Scout can *see*. What is being added is
**retention**: until 1.4.0 it could read those sources and could not keep what it
found there. So the exercise is recovering value from ground already walked,
which is also why the yield may be better than a first pass over cold material —
this is material the Scout has had reason to roam into.

*(Framing corrected by the operator 2026-09-03: an earlier draft of this section
called these "new bodies of ore", which conflated two different things.)*

Genuinely new, by contrast: **documentation imported from an employer-gated
external testing platform**, and **additional session logs**. The session logs
ride the existing ingest. The imported docs are a new source and carry a gate
question (§Gated references).

### The doctrine this appears to contradict, and why it does not

`NEWSROOM.md` §The Scout's sources is explicit:

> Scope the cursor to the logs, and nowhere else. […] For **every other source**
> — git, docs, `agent_decisions`, the ledger — the Scout is **cursor-free and
> temporally bidirectional.** […] A forward cursor there would *close the
> Scout's temporal aperture* — exactly what the pineapple rule forbids.
> **Coverage is linear (cursor); investigation is not (free roam).**

That reasoning has one flaw: it treats *having a cursor* and *being reachable
only through the cursor* as the same thing. They are not, and the logs already
prove it — the walk is cursor-driven while `read_transcript` remains a free-roam
tool, so the Scout can reach any turn regardless of the watermark. Coverage and
investigation already coexist on that source.

**The operator's framing, which is the correct one: the cursor is a return
address, not a leash.**

> "the cursor is there for the recovery, but that doesn't stop the scout from
> reading that and deciding to jump over to something else based on what it
> [found]. As long as it realizes that that's where it jumped from. When it
> finishes, it comes back. The loop ends, cursor next."

That is a stack discipline. Depart from the cursor, roam freely, return, then
advance. The aperture is unchanged — the Scout may still go anywhere — and
coverage becomes guaranteed instead of accidental. **This is additive, not a
relaxation:** free roam alone gives freedom without coverage; this gives both.

Amendment owed to `NEWSROOM.md`: the "cursor nowhere else" rule should be
narrowed to what it was actually protecting — *no cursor may be the sole access
path to a source* — which the design below satisfies.

## Decision

### 1. One coverage ledger, not six cursors

The sources do not share a shape, so six bespoke cursors would be six bespoke
bugs. One table answers "what is unmined?" uniformly:

```
scout_coverage(source_type, unit_ref, content_hash, mined_at, run_id)
```

Three access patterns fall out of it, and every source is one of the three:

| Pattern | Sources | Coverage question | Why |
|---|---|---|---|
| **Watermark** | transcripts, git, `agent_decisions`, ledger | "what is past my high-water mark?" | append-only and naturally ordered |
| **Version** | docs, calendar | "have I mined *this hash* of this unit?" | they MUTATE — a doc rewritten in August is not July's doc, a VTODO's status flips. A forward watermark sails past changes and reports full coverage while being wrong |
| **Snapshot diff** | survey | "what changed since the last walk?" | re-walked wholesale, never patched — versioned snapshots |

The version pattern is the one a naive six-cursor design gets wrong, and it is
the pattern the imported gated docs need.

This also subsumes the two cursors the retool added (`forward`, `backfill`):
both are watermark queries against the same ledger.

### 2. The excursion rule — where the cursor advances

**The cursor advances on completion of the excursion, not on the read.** If it
moved when a unit was opened and the Scout then jumped away and exhausted its
budget mid-thread, that unit would be marked covered while the thread it opened
was abandoned. The existing walk already has this discipline — it saves the
cursor only after persisting the page's jewels, so "a crash between here and the
leap costs nothing already paid for." Extend it; do not reinvent it.

A jewel found during an excursion belongs to **where it was found**, not where
the excursion departed from — `source_type` and `source_ref` record the finding
site. The departure point is real information (it is the "seam" the
story-worthiness heuristic prizes), but it goes in the note and the scratchpad,
**not** into a new excursion-graph table. `NEWSROOM.md` is clear that
schema-on-write before the shape is known is the nickel-jar move.

### 3. Order asymmetry is already solved — do not engineer around it

Mining in cursor order means a January commit is mined before the Scout has seen
July's docs, so early units are mined with less context. This is already true of
transcripts and is accepted, because `004` made jewels **accumulate**: "a re-walk
is a new mining run, not a correction — jewels accumulate, nothing is
superseded." A first pass that misses a connection is not lossy; a later pass
adds. Re-mining is affordable precisely because the retool unwelded walk from
leap.

### 4. Gated references — the leak path this opens

`NEWSROOM.md` permits day-job material as ore under one hard rule:
technique-forward, application-anonymous, the employer's application never named
or identifiable. That gate has always been applied to **content**.

**This change introduces a path it does not cover: `source_ref` is itself
publishable text.** A jewel's reference becomes a lead's `sources` field, the
Writer reads whole leads, and a note can cite them. A `source_ref` that is a
file path carrying an employer product name carries that identifier outward even
when every word of content was scrubbed. The employer vocabulary
(`/opt/_host/redaction-gate/terms.txt`, 29 terms) guards content; nothing today
guards a pointer.

**Decision: gated sources get an opaque `source_ref`** — a stable local id that
resolves to the real path through a mapping that never leaves the box. The
pointer stays fully useful to the operator and says nothing to a reader. This
must be settled **before** the gated import, because once those refs are written
they are in every jewel mined from that material.

**Receipt — this stopped being hypothetical while the section was being
written.** The first commit of this ADR was **blocked by the redaction gate**,
which found the platform's name three times in this file: the author had named
the employer's product in a public repo, in the very section arguing that
employer identifiers travel on references. The name was removed rather than
dismissed — a dismissal would have written it permanently into
`allow.txt` and therefore into a public repo's future.

Two things follow. First, the leak path is real and the reflex to name the
source is strong enough to survive writing the warning. Second, the control that
caught it guards *prose in tracked files* — the `source_ref` path this section
describes runs through **Postgres**, which the gate never sees. The gate would
not have caught the thing this section is actually about.

### 5. Phase 1 — supervised runs, caps off, ceiling ON

Ten runs or fewer, watched, with the coverage caps lifted, to learn two things
that cannot be reasoned out: **what this actually costs**, and **what the caps
have been dropping.**

**Two kinds of cap, and only one comes off:**

- **Coverage caps** — `SCOUT_PAGE_ROWS` (150), `SCOUT_PASS_ROW_BUDGET`. These
  shape how much ore is seen. Lifting them is the experiment.
- **The safety ceiling** — `SCOUT_MAX_COST_USD` (default 2.0). This is a kill
  switch, not a coverage decision. It stays.

**A finding that changes this plan: the verb the recovery will use has no
ceiling at all.** `run_pass` passes `cost_cap=config.max_cost_usd`, but
`run_walk` passes **`cost_cap=None`** (`run.py:324`). So `--walk` — the operator
verb, ungated by `SCOUT_PAUSED`, and exactly what a recovery mine runs — is
already uncapped. "Caps off" is its current state, and there is no backstop to
keep.

Further, the ceiling that does exist is checked **between pages**, so a single
expensive page overshoots it. It is a brake, not a fuse.

**The operator's position (2026-09-03), on learning the walk tier is Haiku:**
mining is cheap enough that the walk needs no usage cap at all. The arithmetic
backs the premise — Haiku 4.5 is **$1/$5 per MTok**, a 150-row page measured at
**~$0.0105**, and the whole 95-page transcript corpus at about **a dollar**. Cost
is genuinely not the constraint, and I am not arguing it is.

**I would still keep a ceiling, for a reason that is not about the expected
cost.** Three arguments, in increasing order of how much they matter:

1. **A ceiling set well above the expected spend constrains nothing.** At
   ~$0.01 a page, a $10 ceiling is a thousand pages of headroom. It cannot
   interfere with an experiment it is two orders of magnitude away from.
2. **The unknowns here are on the input side, not the price side.** A commit can
   carry an enormous diff; the imported corpus is an unmeasured quantity the
   operator describes as "quite a bit of stuff"; and `SCOUT_WALK_MODEL` is an env
   var. A walk left on an experimental model over an unmeasured corpus is the
   scenario, and it costs 5–10× per token without anything looking wrong.
3. **The ceiling is an instrument, not just a limit — and removing it removes a
   signal.** If a walk expected to cost $0.15 trips a $10 ceiling, that is
   information: the ore is bigger than believed, the loop is not terminating, or
   the model is not the one intended. Without it the same three failures produce
   a large bill and no notification. This estate has written that lesson down
   twice, in `silent-instruments-2026-08-29.md` and in ADR-011's governance test,
   which landed on **"calls a paid API unattended"** rather than "is an agent"
   precisely because the category error left the biggest spender on the box
   uncapped.

So the disagreement is small in practice and worth being explicit about: **set it
generously, do not remove it.** A ceiling's job here is to catch the case nobody
predicted, and its cost when nothing goes wrong is zero.

**Therefore, before Phase 1 runs: give `--walk` a cost ceiling.** Supervision is
not a control — this estate's own lesson from the redaction gate is "they were
clean. That is not a control." A human watching a terminal is exactly that kind
of non-control, and the failure mode here is unbounded spend against 1,500
commits plus imported docs plus new logs.

**What Phase 1 must record per run**, so the caps question is answerable rather
than impressionistic: rows/units walked, jewels found, cost, wall time, and —
the point of the exercise — whether the run terminated by exhausting the ore or
by hitting something. A run that ends because it ran out of material tells us
the cap was never binding. A run that ends any other way is the interesting one.

This is the Scout-side twin of `writer-roam-budget-headroom@operator` (due
2026-09-04), which asks the same question of the Writer's roam. Same shape: what
is a cap silently costing us?

### 6. Model tier — settle the open A/B with these runs

The operator's position: **Fable 5 now bills at full price and is expensive;
Sonnet 5 is close to Opus 5 on cross-topic reasoning and its promotional rate is
permanent, so drop synthesis to Sonnet 5.**

The prices are not in dispute (`blog_pipeline/pricing.py`): Sonnet 5 **$2/$10**,
Opus 5 $5/$25, Fable 5 **$10/$50**. Fable is **5×** Sonnet — wider than
`NEWSROOM.md` §Model tiers assumes, since that section priced Sonnet at $3/$15
before the promotional rate became permanent.

Two things temper how much this decision matters here:

- **This phase is mostly WALK, not synthesis.** Mining is the walk tier
  (Haiku 4.5), which is where the volume and therefore the cost lives. Synthesis
  is a separate, later, low-volume consumer of the jewel layer. The
  Fable-vs-Sonnet question barely bites on a recovery mine.
- **The argument for Fable was never about cost.** §Model tiers argues synthesis
  is the creative *ceiling* of the newsroom because the Editor filters bad leads
  but nothing filters *missing* ones — false negatives are invisible and
  uncounted. That argument survives a price change unchanged.

**Recommendation: do not settle this on price. Settle it with these runs.**
`NEWSROOM.md` already specifies the experiment and it has never been run — one
pass each through Sonnet and Fable over the same ore, lead lists read side by
side, *"the Editor judges, not the contestant."* It was due 2026-07-26 and is 39
days overdue. Phase 1 is ten supervised runs over fresh ore: the A/B costs
nothing extra beyond duplicating the synthesis step on a subset, and it closes a
decision that has been blocking the drip by proxy since July.

If the lead lists are comparable, Sonnet 5 wins on price and the doctrine gets
amended with evidence rather than overridden by assertion. If Fable's are
visibly richer, we have finally priced what that richness costs.

Mechanically this is already supported: `SCOUT_SYNTHESIS_MODEL` is an env var,
and `SCOUT_SYNTHESIS_FALLBACK` moved to `claude-opus-5` on 2026-09-01.

## Consequences

**Good.** Coverage becomes a uniform, queryable property across all six sources
instead of one cursor and five hopes. The mutating sources get correct semantics
rather than a watermark that silently lies. The gated-reference leak is closed
before the import that would have opened it. The 39-day-overdue model A/B gets
settled as a by-product of work already being done.

**Costs and risks.** A coverage ledger is a new shared table and therefore a
`AGENTS.md` §Shared surfaces question in its own right — it should be
Scout-owned and Scout-written, with no other writer, and that boundary wants
stating when it is built. Phase 1 spends real money by design. And the schema is
already ahead of the pipeline; this ADR widens that gap until the readers land.

**Not decided here.** Which source gets a reader first. Git is the obvious
candidate on evidence — 1,527 commits across the estate, and messages averaging
**106 words** in `ai-agent-platform` and 51 in `predictor_ingest`, so the
reasoning is already written down and already dated. It is also the corrective
the operator is reaching for: session logs record problems *while they are being
fought*, which is why leads read thin and problem-shaped; commit messages record
what was decided and why, *after*. Same chronology, opposite register.
