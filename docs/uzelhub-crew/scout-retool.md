---
read: full
status: opened 2026-08-21. §§1-4 BUILT and committed 2026-08-22 (3dc8894, 48ba6e1, 5950527, + the cursor commit); rollout steps 4 (reclaim sweep) and resume are NOT done and are operator calls. Decisions below are made, not proposed — where something is genuinely open it says so. Rests entirely on scout-mining-economics.md; read that first or the tuning here looks backwards. Scout is PAUSED (SCOUT_PAUSED=1) for the duration.
---

# Scout retool — from pipeline to substrate

<!-- MAP:START -->
- [1. Persist the jewel layer](#1-persist-the-jewel-layer)
  - [It is an interface, not private state](#it-is-an-interface-not-private-state)
  - [Schema](#schema)
  - [What is deliberately NOT in this table](#what-is-deliberately-not-in-this-table)
- [2. Unweld the pass into verbs](#2-unweld-the-pass-into-verbs)
- [3. Size the plate by row budget, not page count](#3-size-the-plate-by-row-budget-not-page-count)
- [4. The second cursor](#4-the-second-cursor)
- [Rollout order](#rollout-order)
- [Invariants — must not change](#invariants--must-not-change)
- [How we will know it worked](#how-we-will-know-it-worked)
- [Deliberately out of scope](#deliberately-out-of-scope)
- [Open](#open)
<!-- MAP:END -->

A retool of the Scout, not a new agent. Its job description does not change:
mine jewels, surface leads, keep no taste. Both prompts stay exactly as they
are. What changes is that it stops discarding its own work product, takes a
smaller bite, and can read from two positions instead of one.

The reason to do it before anything else is that it converts the Scout from a
pipeline into a substrate. Today the walk and the synthesis are welded into one
indivisible pass, so mining cannot happen without also storytelling — which is
why re-mining the corpus costs ~$200 instead of ~$1. Once jewels are a table,
synthesis becomes a *consumer* of that table, and every later agent we have
discussed (a directed hunt on a named topic, a monthly arc digest) is another
consumer that never re-reads a transcript.

Four changes. The first two are structural, the last two are tuning and
position.

## 1. Persist the jewel layer

Today jewels are accumulated in a local list in `pipelines/scout/run.py`, handed
to synthesis, and lost when the process exits. Roughly 1,645 have been extracted
and discarded. This is the whole problem.

### It is an interface, not private state

The decision that shapes the schema: the jewel table is a **published
interface** other agents read, not Scout-internal scratch. Consequence — a
consumer reading it four months later must be able to make sense of a row
without having been present when it was mined.

That does *not* mean duplicating transcript text. Every jewel carries its `seq`,
and the ore row is one indexed lookup away, so **(jewel + its ore row) is
reconstructible by join** and the table stays lean. What it does mean is
carrying enough dimensions to slice on without a join: time, provenance, and
which mining run produced it.

### Schema

> **AMENDED 2026-09-03 by schema 1.4.0** (`005_jewel_source.sql`). The DDL
> quoted below is 004 as written and is left verbatim as the historical
> record. Two lines of it no longer hold: `seq` is **no longer NOT NULL**, and
> `UNIQUE (seq, kind, note)` was replaced by a unique index over
> `(source_type, COALESCE(seq::text, source_ref), kind, note)`. The reason is
> that the NOT NULL foreign key made it impossible for five of the Scout's six
> sources to produce a jewel at all — see
> `jewels-are-transcript-only-2026-09-03.md`.

New migration, `database/ai_agent_platform/004_scout_jewel.sql`:

```sql
CREATE TABLE scout_jewel (
    id           BIGSERIAL PRIMARY KEY,
    seq          BIGINT NOT NULL REFERENCES scout_session_log(seq),
    kind         VARCHAR(16) NOT NULL,   -- principle|correction|reframe|decision|aha
    note         TEXT NOT NULL,          -- the walker's one tight sentence
    session_date DATE NOT NULL,          -- denormalized: see below
    run_id       UUID NOT NULL,          -- which mining run found it
    walk_model   VARCHAR(64) NOT NULL,   -- the model that mined it
    found_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (seq, kind, note)
);
CREATE INDEX idx_jewel_date ON scout_jewel(session_date);
CREATE INDEX idx_jewel_seq  ON scout_jewel(seq);
CREATE INDEX idx_jewel_run  ON scout_jewel(run_id);
CREATE INDEX idx_jewel_kind ON scout_jewel(kind);
```

**`session_date` is deliberately denormalized** from the ore row. It is
immutable, and every anticipated consumer slices by time — a monthly digest
filters on it constantly, a hunt bounds by period. Paying a join for an
unchanging date on every such query is the wrong trade.

**`run_id` exists because a re-walk is a new mining run, not a correction.**
The first pass's jewels are evidence of what a thin walk found; the second
pass's are what a properly-sized one found. Comparing the two runs over the same
ore is how we will verify the tuning in §3 actually worked. So jewels
**accumulate** — nothing is overwritten or superseded.

**`UNIQUE (seq, kind, note)`** makes an *exact* re-finding idempotent while
letting a genuinely differently-worded finding land. This is imperfect on
purpose: near-duplicate phrasings across runs will survive, and collapsing them
is the consumer's problem, not the writer's. A stricter key would silently drop
real second-run findings, which is the worse failure.

**`walk_model` is recorded** because the mining tier is an env var and will
change; a jewel's quality is not interpretable without knowing what produced it.

### What is deliberately NOT in this table

No `lead_id`. No `became_lead`. No status, no score, no disposition, ever.

The Scout must never learn which of its jewels an editor liked — that is the
pineapple rule, and this table is the most tempting place in the system to break
it. The ban is structural, not disciplinary: **the columns do not exist**, so a
future reader cannot filter on them by accident.

Analysis that joins jewels to lead outcomes is legitimate and belongs in
`tools/`, run by a human, never on the Scout's read path.

## 2. Unweld the pass into verbs

The change that makes persistence pay. Today `--pass` means walk-and-synthesize
as one act. Split the verbs so each can run alone:

| verb | does | cost profile |
|---|---|---|
| `--ingest` | unchanged | trivial |
| `--walk` | triage rows, persist jewels, **no synthesis, no leads** | ~$0.0105 per 150-row page |
| `--synthesize` | read a jewel selection, surface leads, file them | the premium call |
| `--pass` | unchanged in meaning: `--walk` then `--synthesize` over that walk's jewels | as today |

`--pass` stays the daily timer's entry point and behaves as it does now, so the
ambient loop is untouched.

`--walk` is what makes reclaim affordable: the entire 14,198-turn corpus is 95
pages, about **$1 of Haiku, with zero synthesis calls**. It takes an explicit
range (`--from-seq` / `--rows`) and does not touch either cursor — a reclaim walk
is an operator action, not a position change.

`--synthesize` takes a jewel selection (by date range, by run, by kind) and is
where density becomes a dial. This is also the verb both future agents will
grow out of, which is a reason to get its selection arguments right now rather
than retrofitting them.

## 3. Size the plate by row budget, not page count

From scout-mining-economics.md: output is homeostatic at ~13 leads a pass
regardless of input, so conversion runs 0.18 leads per jewel on a full 450-row
plate and 1.00 on a 24-row one. **More ore per pass mines thinner.** The plate
should be sized so the machine's natural output consumes what the walk finds.

- Replace `SCOUT_WALK_PAGES` (3) with **`SCOUT_PASS_ROW_BUDGET`** (default
  **150**) — the total rows a single `--pass` may walk, across both cursors.
- Keep `SCOUT_PAGE_ROWS` (150) as the per-triage-call chunk size. It is a
  different concern (how big one Haiku call is) and should not have been doing
  double duty as the pass cap.
- `--walk` ignores the budget; bounded reclaim is its whole point.

In steady state today this changes almost nothing on the forward path, because
fresh ore rarely reaches 150 rows anyway. Its real job is to bound the pass once
backfill starts topping it up — without it, adding backfill would silently
recreate the 450-row plate and undo the tuning.

**Fresh ore takes priority.** The pass fills its budget from the forward cursor
first and only tops up from backfill with what is left. On a busy day backfill
gets nothing; on a quiet day it gets most of the budget. That is self-balancing
and needs no scheduling logic.

## 4. The second cursor

`state/cursor.json` becomes:

```json
{"forward": 418876, "backfill": 0}
```

Read `{"seq": N}` as `{"forward": N, "backfill": 0}` for one release so the
existing file keeps working; the file is external and inspectable by design and
that property should survive the change.

The backfill cursor walks from 0 toward wherever `forward` stood when it began,
and **stops when it catches up** rather than looping. A second reclaim sweep is
an explicit operator act (reset it to 0), not something that happens quietly
forever.

Backfill order is plain sequential, deliberately. The temptation is to
prioritize "under-mined" ore, but the walk was uniform — annotation runs 6.7% to
7.9% in every month — so there is no thin band to target. The unevenness was all
downstream, and re-walking at the corrected plate size fixes it everywhere at
once.

**This was flagged as the piece to cut if anything got cut**, on the grounds
that a one-shot `--walk` reclaim leaves it little to do. Built anyway, because
it turned out to be ~40 lines once `_walk_stage` already took a cursor key, and
because it is the mechanism that keeps re-mining going after the one-shot sweep
rather than a second thing to remember to run. The reclaim still does not
depend on it.

## Rollout order

1. **Migration + write path.** Jewels persist from the next pass onward. No
   other behaviour changes; this is independently shippable and independently
   useful.
2. **Verbs.** `--walk` and `--synthesize` split out; `--pass` composes them and
   remains the timer's entry point.
3. **Row budget.** Config change plus the fresh-first fill rule.
4. **Reclaim.** One `--walk` sweep over the full corpus. ~95 pages, ~$1.

> **MEASURED 2026-09-05 — the ~$1 figure is wrong by about 4x, and it is
> repeated across three documents.** The first real full-corpus walk came in at
> **$0.037 per 150-row page**, so ~101 pages is **about $3.75**, not a dollar.
> The estimate was derived from `$0.0105` a page, which was measured on the
> *thin* August pages (a few dozen rows of fresh ore) and then applied to full
> 150-row pages. The right number was always going to be ~3.5x higher, because
> the page is ~3.5x the input.
>
> Nothing in the reasoning changes: $3.75 to fill the jewel layer once, against
> ~$200 welded, is still exactly the point the retool was making, and the 200x
> argument is untouched. What changes is that "about a dollar" must not be
> quoted as a budget — the same cheap-sample error also made the git mine's
> estimate 3x low, so it is a habit rather than a one-off.

5. **Second cursor.** Ongoing top-up, if still wanted after 4.

Resume the Scout (delete `SCOUT_PAUSED=1`) once the conversion measurement in
§How we will know it worked has something to measure — that check needs five
passes to have run, so the Scout has to be going. **Corrected 2026-08-22:** the
first draft justified the same instruction by saying a paused Scout keeps the
corpus fixed for the reclaim. That reasoning is wrong. `--walk` takes an
explicit range and moves no cursor, and new ore lands at seq above anything a
reclaim is reading, so a running Scout cannot disturb a reclaim sweep. The two
are independent; only the measurement depends on resuming.

## Invariants — must not change

- **The pineapple rule.** No editor signal reaches the Scout. The jewel table
  carries no disposition columns; `load_pitched` stays status-blind.
- **The aperture.** Both prompts unchanged. "When unsure, include" survives.
- **The forward cursor never moves backward.** Backfill is a separate position
  precisely so this stays true.
- **Raw text is never overwritten.** `scratchpad` appends; `text` is immutable.
- **Lead slugs are never renamed** — ledger primary key across ~53 call sites,
  and the eventual published URL.

## How we will know it worked

- **Conversion.** Leads per jewel over the five passes after step 3 sits in the
  0.4-0.7 band rather than near 0.2. Measurable from the journal exactly as it
  was measured for the spec.
- **Persistence is complete.** After any walk, `count(*)` in `scout_jewel` for
  that `run_id` equals the jewel count that run logged. A silent shortfall means
  the write path is dropping rows.
- **Reclaim is cheap.** The full-corpus `--walk` completes with zero synthesis
  calls and a total cost near $1. Anything materially higher means the verbs are
  still welded somewhere.
- **No ambient regression.** Leads per pass stays ~13 and the forward cursor
  never retreats.

## Deliberately out of scope

- **The dedup payload.** ~74,830 tokens and growing with the ledger rather than
  the work; the dominant per-pass cost. Real, separable, and constrained — any
  trim must keep it status-blind. Next, not now.
- **The hunt agent and the monthly arc agent.** Both are consumers of what this
  spec builds. Speccing them before the substrate exists would design against an
  interface that does not yet have a shape.
- **Prompt changes of any kind**, including the `why_now` field. It plausibly
  taxes old material at the margin, but it is not what drives the recency skew
  and should not be touched on that theory.
- **Renaming slugs.** Settled: display fix only, already shipped in the leads
  archive.

## Open

- **Should `--synthesize` be able to run over a jewel selection spanning
  multiple runs of the same ore?** Union is the obvious default, but two runs
  over one seq will produce near-duplicate jewels and the synthesis has no way
  to know they are the same finding twice. Deciding this needs a real second run
  to look at, so it is deferred to after step 4 rather than guessed now.
