---
read: full
status: measured 2026-08-19..21 against the live corpus (14,198 turns / 477 leads / 35 passes). Findings settled and reproducible; the three tuning changes they imply are NOT built — see §What follows. Supersedes nothing in NEWSROOM.md; it explains behaviour that doc specifies.
---

# Scout mining economics — what the machine actually does with ore

<!-- MAP:START -->
- [The corpus](#the-corpus)
- [The rate limiter nobody set deliberately](#the-rate-limiter-nobody-set-deliberately)
- [Output is fixed, not emergent](#output-is-fixed-not-emergent)
- [Conversion falls as the plate grows](#conversion-falls-as-the-plate-grows)
- [What the walk keeps: almost nothing](#what-the-walk-keeps-almost-nothing)
- [Where the money actually goes](#where-the-money-actually-goes)
- [Recency bias — real, ~2x, and easy to misdiagnose](#recency-bias--real-2x-and-easy-to-misdiagnose)
- [What no stage ranks on](#what-no-stage-ranks-on)
- [A display finding that is not about mining](#a-display-finding-that-is-not-about-mining)
- [What follows](#what-follows)
- [How these numbers were produced](#how-these-numbers-were-produced)
<!-- MAP:END -->

NEWSROOM.md says what the Scout is *for*. This says what it measurably *does*
with the material it is fed, because several of those behaviours are not
obvious from the design and at least two of them are the opposite of what a
reasonable person would guess. Every number here came from the live corpus and
is reproducible with `tools/leads_assay.py` or the queries named inline.

The short version: **the Scout's output is a constant, its input is capped, and
it keeps almost nothing it finds.** Everything below follows from those three
facts.

## The corpus

14,198 turns across 88 sessions, 2026-01-21 to 2026-08-19 — about 13.9 MB of
raw text, roughly 3.6M tokens. Small. The whole ore fits in a few context
windows, and a full-table text scan for a term takes about 200ms with no index.
Any instinct to sample rather than read exhaustively is inherited from working
on bigger corpora and does not apply here.

**59% of it predates the Scout.** 8,348 turns are pre-July, from before the
agent existed; it ingested six months of history at once and walked it in bulk.
That share matters for every question about coverage.

## The rate limiter nobody set deliberately

`SCOUT_WALK_PAGES` is 3, `SCOUT_PAGE_ROWS` is 150. **The Scout has never been
permitted to see more than 450 rows in a pass.** The walk is a proper keyset
(`WHERE seq > cursor ORDER BY seq LIMIT n`), so the large gaps in `seq` — an
artifact of `ON CONFLICT DO NOTHING` burning sequence values on re-ingest — are
cosmetic and each page really is 150 rows.

35 passes at 450 rows covers 14,198 rows almost exactly once, and the cursor
now sits at `max(seq)`. So the corpus has been walked, completely, one time.
No period was skipped and none was skimmed harder than another: scratchpad
annotation runs between 6.7% and 7.9% in *every* month of the corpus. The walk
is uniform. Everything uneven happens downstream of it.

## Output is fixed, not emergent

Leads filed per pass: min 9, median 13, max 24, mean 13.6 across 35 passes.
That number barely moves regardless of what goes in, and two natural
experiments show it is not a model-side limit:

- **2026-08-12** — the synthesis output ceiling was raised from 8,192 to 20,000
  tokens (`585ef91`). Mean output *fell*, 13.96 before to 12.5 after. More than
  doubling the room to speak produced slightly fewer leads.
- **2026-07-14** — 9,268 turns landed in a single day (the bulk rollout
  ingest), a tenfold input shock. Output that day was 19; the following week ran
  13, 15, 16, 13, 14. The surplus was absorbed as unwalked backlog, not
  converted into leads.

The homeostasis is real. It is a property of the pass, not of the model's taste.

## Conversion falls as the plate grows

The consequence, and the counterintuitive part. Jewels found per pass against
leads filed:

| date | rows walked | jewels | leads | leads per jewel |
|---|---|---|---|---|
| 2026-08-12 | 450 | 106 | 19 | 0.18 |
| 2026-08-11 | 450 | 81 | 19 | 0.23 |
| 2026-08-06 | 450 | 93 | 20 | 0.22 |
| 2026-08-16 | 155 | 39 | 15 | 0.38 |
| 2026-08-17 | 123 | 18 | 12 | 0.67 |
| 2026-08-19 | 24 | 10 | 10 | 1.00 |

Synthesis emits ~13 leads whether it is handed 106 jewels or 10. On a full
450-row plate roughly four of every five jewels are found, considered, and
dropped. On a 24-row plate every one becomes a lead.

**So feeding the Scout more ore per pass makes its mining thinner, not richer.**
Idle walk capacity is not an opportunity to fill — filling it lowers yield per
unit of ore. The plate should be sized so the machine's natural output consumes
what the walk finds, which the data puts somewhere around 100-150 rows.

## What the walk keeps: almost nothing

**Jewels are never persisted.** They are accumulated in a local list in
`pipelines/scout/run.py`, handed to synthesis, and discarded when the process
exits. No table, no file. Roughly 1,645 were extracted across 35 passes; the
477 leads are the only durable trace.

10,404 turns — **73.3% of the corpus** — are cited by no lead at all, and that
is a generous count (citation ranges were expanded up to 40 rows when
measuring, so true coverage is lower).

The one surviving annotation is the `scratchpad` column: 1,025 rows, 7.2%,
explicitly opaque and by contract read by nothing downstream. 486 of those rows
were flagged by the triage as interesting and then cited by no lead ever.

This is what makes re-mining necessary rather than optional. The expensive
cognitive work was done and the product was thrown away.

## Where the money actually goes

Costs inverted between the two eras, which is the tell:

| era | plate | cost per pass |
|---|---|---|
| July — walking the backlog | full 450 rows | $0.61 – $1.23 |
| August — fresh ore only | a few dozen rows | $1.63 – $2.14 |

The full plate was **cheaper**. Cost stopped being a function of ore some time
ago. It is now dominated by the already-pitched dedup payload, which goes into
every synthesis call and currently runs 477 entries / 299,322 chars / ~74,830
tokens — growing every day the ledger grows.

That payload is deliberately status-blind (`load_pitched` never reads verdicts —
the pineapple rule enforced by omission, so no editor signal can reach the
Scout). **That design is correct and must not change.** But it means the cost
scales with the ledger rather than with the work, and disposing the backlog will
not shrink it. Whether a near-identical check needs full pitch text or just a
slug and a first line is open.

For scale on the other side: one Haiku walk page costs about $0.0105, and the
entire corpus is 95 pages. **Re-walking everything costs about a dollar.** The
only reason that is not the obvious move is that today the walk cannot be run
without also triggering a synthesis per pass, each carrying that payload. Walk
and synthesis are welded; unwelding them is worth ~200x on any re-mining job.

## Recency bias — real, ~2x, and easy to misdiagnose

Mapping every lead's cited seqs back to session dates against each month's share
of the ore:

| month | share of ore | share of leads | over/under |
|---|---|---|---|
| 2026-04 | 8.5% | 9.3% | 1.09x |
| 2026-05 | 18.1% | 13.8% | 0.76x |
| 2026-06 | 29.7% | 17.7% | 0.60x |
| 2026-07 | 26.0% | 28.5% | 1.10x |
| 2026-08 | 15.2% | 29.2% | 1.92x |

It is **not** a decay curve. April, four months old, mines at the same density
as July. What predicts under-mining is not age but *how much ore was in the pass*
— June is the worst-mined month precisely because it is the largest, skimmed at
the same fixed 13-lead yield as everything else. A freshness explanation was
proposed twice during this analysis and does not survive April.

(The `why_now` required field plausibly costs something at the margin for old
material, since a months-old story cannot honestly fill it. It is not the main
driver and should not be treated as one.)

## What no stage ranks on

Worth stating because it is invisible until written down. The Scout filters for
durability and surprise; the Wire Editor filters for **capacity** — every rule
in its prompt descends from the apex publishing 1-2 URLs a week. Neither asks
whether a story is the *biggest* thing that happened. There is no magnitude
ranking anywhere in the chain.

Two things partly stand in for one:

- **Register is a magnitude proxy.** Wire claim rate tracks it monotonically —
  blog 73.2%, newsletter 52.8%, note 43.4%, ticker 32.5%. Two independent judges
  agree on the gradient, so the Scout is ranking; it just files the result under
  a question about form.
- **Clusters are the arc index.** The 257 triaged leads are 39 clusters plus 88
  singletons — about 127 distinct stories. 124 of the 127 spikes are leads
  *inside* a cluster, so the spike pile is overwhelmingly deduplication, not
  rejection; only three leads were ever spiked on their own merits.

Note the loss this implies: when the Wire Editor finds a many-lead arc it claims
the single strongest telling and spikes the rest into it, exactly as instructed.
The arc is discovered and discarded as redundancy in the same operation.

## A display finding that is not about mining

The slug layer inverts the pitch layer. Slugs read 64 win / 57 problem while the
pitches beneath them read 134 / 59 — 50 leads carry a problem-shaped slug over a
pitch that is nothing of the kind. Since triage happens by scanning a column of
slugs, that skew biases the human against a corpus that is mostly wins. Fixed in
the leads archive by leading each row with the pitch; the slugs themselves must
not be rewritten, being both the ledger primary key across ~53 call sites and
the eventual published URL.

## What follows

Three coupled changes, none of which adds an agent:

1. **Persist the jewel layer**, as a published interface rather than Scout-private
   state — enough carried context that a reader months later need not re-open the
   transcript. It must be verdict-blind for the same reason `load_pitched` is, or
   it becomes the backpropagation channel the newsroom is built not to have.
2. **One page per pass, not three**, so output consumes what the walk finds.
3. **A second cursor** for backfill, so under-mined history can be re-walked
   without disturbing the forward position.

Together they turn the Scout from a pipeline into a substrate: once jewels are a
table, synthesis is a *consumer* of that table rather than a stage inside the
pass, and any later agent — a directed hunt on a named topic, a monthly arc
digest — is another consumer that never re-reads a transcript.

## How these numbers were produced

`tools/leads_assay.py` runs the corpus assays: name two lexicons and it
cross-tabs the split by register, wire verdict, week filed, and **layer** (do the
slugs say what the pitches say). It prints all four tabs every time, so the
flattering one cannot be chosen after the fact.

The method matters more than the lexicons: state the claim, pick the tab that
could *falsify* it, and when it dies form the next claim from the wreckage. Three
of four hypotheses died during this analysis, including two of the author's own —
a claimed recent drift toward negative framing turned out to be an artifact of
adding terms to one lexicon mid-analysis without balancing the other. A tab that
merely agrees with you has told you nothing.
