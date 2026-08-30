---
read: full
status: findings from one continuous session spanning 2026-08-26 to 2026-08-30 (four working days, one context). The 08-29 in the filename is the writing date, kept stable because three documents link here. Corrected 2026-08-30 by reading the session log rather than trusting recall -- the first draft said "a single session, 2026-08-29", which was wrong by four days. Every number here was measured, not estimated; where a claim was made and later falsified in the same session, the correction is kept rather than the claim. Fixes landed are named by commit; what remains open is listed as open.
---

# Silent instruments — what a housekeeping session found

<!-- MAP:START -->
- [The shape of every finding](#the-shape-of-every-finding)
- [Chain one: the pager ate itself](#chain-one-the-pager-ate-itself)
- [Chain two: the cost meter failed open](#chain-two-the-cost-meter-failed-open)
- [The cause behind both causes](#the-cause-behind-both-causes)
- [What the brief was doing meanwhile](#what-the-brief-was-doing-meanwhile)
- [Fixed](#fixed)
- [Open](#open)
- [Claims made and falsified in-session](#claims-made-and-falsified-in-session)
- [What generalises](#what-generalises)
<!-- MAP:END -->

**Companion:** [asking-one-level-up-2026-08-29.md](asking-one-level-up-2026-08-29.md)
records the reasoning arc — the eight turns where the question in play was one
level too low. This doc is what was found; that one is how the thinking moved.

The session opened by reading the Director's morning brief and asking what the
oldest items on it actually were. It ended somewhere else entirely. The findings
below are unrelated on the surface — a disk alert, a dead pipeline stage, five
weeks of missing cost data — and turn out to be two causal chains plus one
shared root.

## The shape of every finding

Not "things broke." Everything breaks. The pattern is narrower and worse:

**In every case, the instrument that existed to report the failure reported
success instead.**

- `movers` ran daily, exited 0, and logged `moversRows=10324` — the same
  three-week-old number every morning.
- `trending` failed every day and the run was recorded as `partial`, because
  the stage is marked non-fatal.
- `_compute_cost` returned `None` for an unpriced model, so the most expensive
  day of the year stored a `NULL` cost rather than an error.
- The backup on 08-28 completed in 43 seconds with no off-site upload line,
  against a 3-minute norm, and reported success.
- The shadow-comparison harness has existed, fully built with promotion
  thresholds, holding zero rows, since it was written.
- The one alarm that fired correctly — disk, hourly — is the one that got
  tuned out.

## Chain one: the pager ate itself

Seven links, and only the first is a real problem:

1. **08-22** — disk crosses 90%. `agent-platform-health` begins paging hourly.
   Correct behaviour.
2. `notify-telegram` enforces `NOTIFY_MAX_PER_DAY`, **shared across every agent
   on the box, defaulting to 10**.
3. 24 hourly disk pages against a budget of 10 exhausts the estate's entire
   daily allowance by mid-morning. Every morning.
4. One "notification storm" notice goes out. Then silence.
5. Meanwhile **film's `trending` stage has been timing out at 600s since
   08-06**. `score_all()` is an N+1: one query to list entities, then
   `score_entity()` per row — 27,846 calls for film, 14,594 for
   semiconductors. Film crossed the 600s line as its graph grew. That is the
   whole reason film times out and semiconductors does not.
6. `run_movers.py` reads `trend_history` with
   `SELECT MAX(run_date) ... WHERE run_date <= ?`, so when `trending` writes
   nothing it silently falls back to the last good snapshot — and reports OK.
7. `run_pipeline.py` pages `[PREDICTOR]` on **every** outcome, and did:
   `film daily — PARTIAL: failed: trending, submit`, every morning for 23 days.
   All of it suppressed by link 3.

On 2026-08-29 alone: 15 SYSTEM, 12 HEALTH and 5 PREDICTOR messages dropped.

**The failure was never silent. It was drowned** — by the disk alert, which was
itself the thing the session had set out to fix.

Film's cost during those 23 days: roughly $5/day, for output nothing consumed.

## Chain two: the cost meter failed open

1. **07-20** — `PRIMARY_MODEL` switches to `claude-sonnet-5`.
2. The predictor's `_TOKEN_PRICES` has no `claude-sonnet-5` row. `_compute_cost`
   returns `None` when nothing matches, and `None` is stored as `NULL`.
3. **2,139 rows in film alone**, 07-23 through 08-26, every one with a null
   cost. Five weeks with no cost data at all.
4. **07-23** — film's 40-document batch runs **nine times**: 360 calls,
   **$31.28 in one day** against a ~$5 norm. About 20% of film's entire
   extraction spend, in a single day.
5. Nobody noticed for five weeks, and nobody *could* have: a null cost cannot
   breach a budget, and there was no budget to breach.
6. **The predictor had no cost ceiling.** Every other agent has one — Scout at
   $2.00 a pass, plus Director, sysadmin, and the blog pipeline. The predictor
   spent $234 in five weeks, more than all of them combined.

The spend was fully recoverable after the fact: `token_usage` records
`input_tokens` and `output_tokens` as NOT NULL, so only the *price* was
missing. Reconstructed at intro rates, film $153.25 / semiconductors $79.42 /
weapons_detection $1.89.

That reconstruction also falsified the live plan — see below.

## The cause behind both causes

The predictor was never given a cost ceiling because **governance was scoped to
the noun "agent" rather than to the property that actually matters: spends money
on someone else's API.**

The predictor has agentic behaviour. It calls a paid model in a loop, per
document, unattended, on a timer. But it was built as a *pipeline*, lives in its
own repo, and was never part of the "crew" mental model — so it inherited none
of the crew's controls, and nobody noticed the omission because the category, not
the risk, was doing the reasoning.

Its *notification* governance, by contrast, is better than the crew's: it pages
on every outcome with a rich summary and has a staleness pager as a backstop.
The gap was never uniform neglect. It was one category boundary drawn in the
wrong place.

## What the brief was doing meanwhile

The Director's morning brief led, every day for six weeks, with
`scout-ab-flip-to-sonnet-r2` — an A/B decision that had been impossible since
July. `SCOUT_SYNTHESIS_MODEL` appears exactly once in the codebase, read with a
`claude-fable-5` default, and is set nowhere. **Week 2 never ran. There is no
Sonnet week to compare against**, and the publishing hold gated on that
comparison has now frozen the release drip for 42 days waiting on a measurement
that cannot be taken.

The brief was not wrong. It reads git state and the ops calendar and ranks
faithfully from them. It has no way to check whether an item's premise is still
true, so a task whose foundation dissolved in July keeps ranking first in
August on the strength of its due date.

## Fixed

| Fix | Where |
|---|---|
| Repeat backoff + per-agent quota on the pager; cap 10 → 100 | `56cb4f2`, `2910b63` (server-maintenance) |
| Gated install path for the pager, with rollback | `cb06e7f` |
| Predictor cost ceiling (`PREDICTOR_MAX_COST_USD`, default 15) | `2cbd4e5` (predictor) |
| `claude-sonnet-5` added to `_TOKEN_PRICES`; unpriced models now warn | `2cbd4e5` |
| Haiku 4.5 corrected from Haiku 3.5's rate — 4x understated in both repos | `5f6f7b6`, `c2dc32f` |
| Article text capped at 50K chars, mirroring the EDGAR guard | `bbc6a2b` |
| Sept 1 cost boundary as one dry-runnable script | `5ca552a` |
| Per-domain `models` + `feature_enabled`, with schema and 34 tests | `51c5766` |
| Live model selections moved to the current generation | `c2dc32f` |
| Disk: audit script, journal bound at 2G, root Claude prune | server-maintenance |

Disk went 94% → 88% across the session.

## Open

- **`score_all` is still N+1.** Nothing downstream of film's `trending` works
  until it is set-based. It is also the only path to ever validating film,
  since film cannot accumulate post-dampening history while the stage is dead.
- **Film's Movers output has never been validated.** ADR-010 finding #6: the
  claim that it is signal rather than relabeled churn "has never been tested on
  real data." Finding #1 calls the validation framework the highest-leverage
  unbuilt component. Film's `trend_history` has two disconnected blocks —
  03-20..04-06 and 07-19..08-06 — with a 104-day dormant gap between them, and
  the D6 dampening window covers all but four days of the second. **Film has
  four trustworthy snapshots, ever.** Semiconductors has 28 continuous days and
  crosses Δ=30 on 08-31, so the retrospective should be built and proven there.
- **No cost anomaly detection.** The ceiling stops a runaway; a slow 30% drift
  still passes unnoticed.
- **The predictor has no ledger**, unlike the Director, sysadmin, and security
  agents.
- **The publishing hold**, 42 days, gated on a measurement that cannot be taken.
- **42 of 44 ops-calendar todos overdue**, several with premises that have since
  dissolved. A baseline reset that sorts by *premise still true* rather than by
  age is the durable fix.

## Claims made and falsified in-session

Kept deliberately — the corrections are more useful than the claims were, and
each one shows a way this estate is easy to misread.

- **"Nothing is watching the filesystem."** Wrong. `agent-platform-health`
  checks disk at >90% and had been paging hourly for four and a half days. The
  monitoring worked; the *delivery* was saturated.
- **"Batch submission is broken — zero batch submissions."** Wrong; a bad grep.
  Batch runs daily and correctly. Sync fallback catches 1–3 docs of 40, ~6%.
- **"Film's extra cost is retries from poor source quality."** Wrong. Excluding
  one bad day, film's calls-per-document is 1.138 against semiconductors' 1.02.
  The repeat cost is almost entirely 07-23, where the whole batch ran nine
  times — an incident, not a pattern. Exact integers across a whole day are the
  tell: real per-document failures produce a ragged distribution.
- **"`run_extract` can resolve to an empty model."** Wrong — it falls back on
  the next line, which the grep did not show. The real drift was narrower: five
  copies of one constant, and one site that skipped `.strip()`.
- **"The Sept 1 cut is 0.75x."** The todo's own figure, falsified by
  reconstruction. It assumed the intro period ran at 0.87 of the pre-migration
  baseline; measured, it runs at **1.06**. Flat is **0.63x**, not 0.75x. The
  todo's *other* number was exactly right: flat-vs-intro-period was given as
  0.67x and measures 0.667.

## What generalises

1. **A global rate cap on an alerting channel converts one stuck condition into
   estate-wide silence.** Cap repetition at the source and give each sender its
   own quota; a shared ceiling makes the noisiest agent the censor of all the
   others.
2. **Alert fatigue is not solved by sending fewer alerts.** It is solved by not
   repeating. The old cap of 10 was doing two jobs — runaway backstop and
   attention manager — and was bad at the second while actively harmful at
   scale.
3. **A non-fatal stage plus a downstream reader that falls back to "most
   recent" is a silent freeze that reports success.** Either of those choices
   alone is reasonable. Together they are undetectable.
4. **A cost meter that returns null for an unknown model fails open.** Any
   ceiling built on it is decorative. Unpriced must be loud.
5. **Scope governance by property, not by category.** "Is it an agent" is a
   noun test and it silently excluded the biggest spender on the box. "Does it
   spend money on someone else's API" is the property that actually predicts
   the risk.
6. **A ranking agent that cannot check premises will rank a dead task first
   forever.** Reading state faithfully is not the same as reading it usefully.
