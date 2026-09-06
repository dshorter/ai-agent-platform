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

**PHASE 1 RUN RECORD — the first two runs, 2026-09-05.** Recorded in the shape
this section asks for, so the caps question is answerable rather than
impressionistic.

| | git walk | transcript re-mine |
|---|---|---|
| units walked | 1,080 commits (22 pages) | 15,126 rows (101 pages) |
| jewels found | 642 | 1,945 |
| jewels persisted | 642 | 1,930 |
| dropped by `resolve_anchor` | **0** | 15 (0.8%) |
| cost | $0.53 | $2.89 |
| wall time | 13 min | ~40 min |
| **how it terminated** | **exhausted the ore** | **exhausted the ore** |

**The last row is the point of the exercise, and it answers the question.**
Neither run ended by hitting anything — not the cost ceiling, not a page cap,
not a budget. Per this section's own test, *"a run that ends because it ran out
of material tells us the cap was never binding."* Both did. So on the evidence
so far the coverage caps were not what was limiting the recovery, and lifting
them further buys nothing; the ceiling never came close (the transcript run used
$2.89 against a $5 ceiling raised for it, and $0.53 against $2 for the git run).

Two things the runs taught that no amount of reasoning would have:

- **The cost estimate was 4x low, in three documents**, because $0.0105/page was
  measured on thin August pages and applied to full 150-row ones. Corrected in
  `scout-retool.md`, `scout-mining-economics.md` and
  `jewels-are-transcript-only-2026-09-03.md`.
- **The anti-hallucination guard is doing real work and the rate differs by
  source.** 15 fabricated seqs on transcripts, 0 fabricated refs on git. Schema
  1.4.0 traded the foreign key away for exactly this check, and it is now
  measured rather than assumed.

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

**MEASURED 2026-09-03, and the cost half is now settled — the operator's
estimate was low.** From `agent_decisions`:

| | calls | avg/call | total | max |
|---|---|---|---|---|
| `scout_synthesis` (Fable 5) | 39 | **$1.3274** | **$51.77** | $2.1367 |
| `scout_walk` (Haiku 4.5) | 106 | $0.0071 | $0.75 | $0.0105 |

**187× per call. 69× in total.** And rising: $0.448/call the week of 07-06 →
$1.847 by 08-10, 4× in six weeks, because the dedup payload rides in the
synthesis prompt and scales with the ledger. Synthesis gets dearer with every
lead ever filed.

This does not just favour the swap — it **falsifies the reasoning that put Fable
there.** §Model tiers justified the spend as "pennies per pass" on two premises:
*ambient (weekly-ish)*, which a scheduling change to daily on 2026-07-22 quietly
overtook, and *low-token*, which $1.33 a call on a $10/$50 model plainly is not.
`NEWSROOM.md` now carries a dated correction.

**Done: `SCOUT_SYNTHESIS_MODEL` defaults to Sonnet 5.** The quality argument is
untouched and still unmeasured, so the burden is **inverted rather than
abandoned** — default cheap, and spend 5× on Fable per run where it is shown to
pay.

### 6b. Two variables are moving at once — isolate them or lose the experiment

The operator's hypothesis (2026-09-03): *"the lead list is gonna look better just
by having a balance of sources now that we have fixed the jewel situation"* —
i.e. the source mix, independent of the model.

It is plausible on two mechanisms, both concrete:

- **Register.** Session logs record problems *while they are being fought*, which
  is why leads read thin and problem-shaped. Commit messages record what was
  decided and why, *after* — 1,527 commits averaging 106 words in
  `ai-agent-platform`. That register is entirely absent from the jewel layer
  today.
- **`agent_decisions` becomes first-class.** The story-worthiness heuristic ranks
  a lead by how many agents its sequence spans, but `agent_decisions` is a
  free-roam source that cannot currently produce a jewel. Once it can, the
  cross-agent seams the whole "stories live at the seams" thesis rests on become
  *mineable material* rather than a SQL hint applied after the fact.

And `scout-mining-economics.md` predicts the *shape* of the effect: output is
homeostatic at ~13 leads per pass regardless of input, so **expect differently
sourced leads, not more of them** — which is exactly the balance being asked for,
not a shortfall.

**The methodological problem.** Synthesis just moved Fable → Sonnet (§6), and the
source mix is about to change. If both move together, a better lead list is
uninterpretable: the source mix may have done the work while Sonnet coasted, or
Sonnet may have cost us depth that the richer sources masked. That destroys the
A/B `NEWSROOM.md` has been waiting on since 2026-07-26 rather than finally
settling it.

**The fix is free, because the retool already unwelded walk from leap.** Both
arms can leap over jewels *already on disk*, mining nothing:

> **Add `--source-type` to `--synthesize`**, mirroring the existing repeatable
> `--kind`. `jewels.select()` already filters on `since`/`until`/`kinds`/
> `run_id`/`limit`; `source_type` is a column as of 1.4.0, so this is one
> parameter and one `WHERE` clause.

That turns both questions into controlled comparisons over identical ore:

| Question | Arm A | Arm B | Held constant |
|---|---|---|---|
| Does the source mix help? | `--source-type transcript` | all sources | model, period, jewels on disk |
| Is Fable worth 5×? | `SCOUT_SYNTHESIS_MODEL=claude-sonnet-5` | `=claude-fable-5` | source mix, period, jewels on disk |

Run them in that order — source mix first, since it is the larger expected
effect and the operator's actual hypothesis — and each result means something on
its own. `NEWSROOM.md`'s rule still governs the reading: *the Editor judges, not
the contestant.*

**A THIRD variable, found 2026-09-05 while proving the git reader — the arms
do not cover the same period unless they are made to.**

| ore | earliest | latest |
|---|---|---|
| transcripts (`scout_session_log`) | 2026-01-21 | 2026-09-05 |
| git (all five repos) | **2025-09-26** | 2026-09-05 |

Git history reaches four months further back than any transcript. 53 commits —
5% of 1,133, all in `ai-agent-platform` — predate the corpus entirely, and
because a walk pages chronologically from the start they are *exactly page one*.
The first live proving run mined them and came back with jewels about ngrok and
n8n webhooks: durable material, honestly mined, and about a subsystem that is
out of scope and that no transcript has ever seen.

So an unbounded git arm against a transcript arm measures **era** as much as
register. The fix is free and must be deliberate: `--since 2026-01-21` on the
git walk, so both arms cover the same window. Both verbs already take it.

This is the third instance of one pattern in two days — the model swap moving
with the source mix (§6b above), filing dates standing in for source dates in
the arc analysis, and now era riding along with register. Same shape each time:
two things moving together, and the one nobody is looking at explains the
result. Worth treating as the default suspicion rather than a recurring
surprise.

The pre-2026 ore is not discarded by this. It is genuinely part of "the platform
narrating its own building" and deserves mining on its own terms — it is simply
not *comparable* material, so it must not be blended into a controlled
comparison.

**Recommendation: do not settle the QUALITY half on price. Settle it with these
runs.**
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
