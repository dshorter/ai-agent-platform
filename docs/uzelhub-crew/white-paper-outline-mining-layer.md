---
read: full
status: STUB — partial abstract plus resume hooks, pinned 2026-08-23. Deliberately not drafted: it is blocked on one measurement (see §The one thing missing). Every number below is already established and cited; resuming should be lookup, not re-analysis.
---

# White paper — the layer between the ore and the argument

<!-- MAP:START -->
- [Working thesis](#working-thesis)
- [Partial abstract (draft, not final)](#partial-abstract-draft-not-final)
- [Resume hooks — the load-bearing numbers](#resume-hooks--the-load-bearing-numbers)
- [Falsified hypotheses (the credibility section)](#falsified-hypotheses-the-credibility-section)
- [The one thing missing](#the-one-thing-missing)
- [Caveats that belong inside the paper](#caveats-that-belong-inside-the-paper)
- [Where it would publish](#where-it-would-publish)
- [Where the evidence lives](#where-the-evidence-lives)
<!-- MAP:END -->

## Working thesis

**Put a durable layer between raw sources and the reasoning step.**

Not a findings dump. The individual results are the supporting cast: the
homeostasis result is the hook that earns a reader, the mining-vs-storytelling
cost ratio is the argument, the archive-versus-index asymmetry is the design
principle that falls out, and the falsification method is what makes it
credible rather than a vendor post.

## Partial abstract (draft, not final)

> An agent that reads a corpus and reasons over it usually does both in one
> pass. We measured five weeks of such an agent — a newsroom prospector that
> walks its own operators' session transcripts and files story leads — and
> found its output rate was not a property of the model, the prompt, or the
> material. It filed roughly thirteen leads per pass no matter what went in.
> Doubling its output token ceiling slightly *lowered* the number. A tenfold
> input shock moved it not at all. The governor turned out to be a page-count
> constant nobody had set deliberately.
>
> The consequence inverts the obvious tuning move. Because output is fixed,
> feeding the agent more material per pass does not yield more findings — it
> yields the same findings drawn from more ore, and discards the rest. At a
> 450-row plate the agent converted 0.18 findings per candidate it had already
> extracted; at 24 rows, 1.00. Four out of five things it noticed, it noticed
> and dropped.
>
> Dropped irrecoverably, because the extraction layer was never written down.
> It existed only as a local variable handed to the reasoning step and
> discarded on process exit — so re-reading the corpus meant re-paying for the
> reasoning too, at roughly two hundred times the cost of the reading itself.
> Persisting that intermediate layer decoupled them: the corpus can now be
> re-mined for about a dollar, and every later consumer queries the layer
> instead of re-reading a transcript.
>
> We argue this generalises to any extract-then-reason pipeline, and that the
> useful design question is not how to make the reasoning better but which
> half of the work is unrecoverable. [RESULTS OF THE CONTROLLED CHANGE GO
> HERE — see §The one thing missing.]

## Resume hooks — the load-bearing numbers

All established and reproducible; sources in §Where the evidence lives.

**The homeostasis result (the hook)**

| | |
|---|---|
| leads per pass, 35 passes | min 9, median 13, max 24, mean 13.6 |
| output ceiling raised 8,192 → 20,000 (2026-08-12) | mean output *fell* 13.96 → 12.5 |
| 9,268 turns ingested in one day (2026-07-14) | output 19, then 13/15/16/13/14 |

**Conversion falls as the plate grows (the inversion)**

| rows walked | jewels | leads | leads per jewel |
|---|---|---|---|
| 450 | 106 | 19 | 0.18 |
| 450 | 93 | 20 | 0.22 |
| 155 | 39 | 15 | 0.38 |
| 123 | 18 | 12 | 0.67 |
| 24 | 10 | 10 | 1.00 |

**The cost ratio (the argument)**

- one walk page (150 rows, cheap tier): ~$0.0095–0.0105
- whole corpus: 95 pages ≈ **$1**
- one synthesis call (premium tier): $0.96–2.14
- welded, re-mining the corpus ≈ **$200**; unwelded ≈ **$1**
- cost inversion that exposed it: July full plates $0.61–1.23, August near-empty
  plates $1.63–2.14 — the *full* plate was cheaper, because cost had stopped
  being a function of ore and become a function of the dedup payload
  (477 entries / 299,322 chars / ~74,830 tokens, growing with the ledger)

**What was being lost**

- ~1,645 jewels extracted across 35 passes, persisted nowhere
- 73.3% of the corpus cited by no lead at all (generous count)
- only surviving trace: a scratchpad column on 1,025 rows (7.2%), which by
  contract nothing downstream reads
- the walk itself was *uniform* — annotation runs 6.7%–7.9% in every month —
  so the unevenness was entirely downstream of extraction

**Recency bias, and why the obvious explanation is wrong**

August over-represented 1.92x, June 0.60x — but April sits at 1.09x, mining at
July's density four months later. Not a decay curve. Under-mining tracks *ore
volume per pass*, not age: June is worst-mined precisely because it is the
largest month, skimmed at the same fixed yield as everything else.

**Replay variance (the probabilistic-testing section)**

Same 150 rows, same model, same prompt, twice: 28 vs 30 jewels; **zero**
byte-identical notes; 61% agreement on the exact turn flagged; ~90% at a ±2
turn tolerance. Metric choice alone moves the conclusion from "wildly unstable"
to "highly stable" — which is the section's whole point.

**The capability that never operated**

Across all 35 passes the agent's free-roam budget produced 63 transcript reads,
4 greps, 0 file reads, 0 git reads — and all 4 greps hit paths that do not
exist, because the prompt named its sources by relative path without saying
what they were relative to. A documented capability, measured to have never
once succeeded.

## Falsified hypotheses (the credibility section)

Six died against the corpus during the work. Naming them, including whose they
were, is what separates this from a post-hoc success story.

1. "The prospector never surfaces accomplishments, only problems." — Died:
   wins outnumber problems ~1.8:1.
2. "Wins get demoted to the terse register." — Died: wins get *more* long-form
   treatment (17.4% vs 7.7%).
3. "The downstream editor spikes wins more often." — Died: 50.0% vs 51.2%
   claim rate, statistically indistinguishable.
4. "Framing has drifted negative in recent weeks." — Died, **and it was the
   analyst's own artifact**: terms were added to one lexicon mid-analysis
   without balancing the other, and "never" is common in recent material.
5. "A required why-now field is the freshness tax driving recency bias." —
   Died on April sitting at 1.09x.
6. "Fill the idle walk capacity." — **The analyst's own recommendation**,
   killed one turn later by the conversion data. It would have made mining
   thinner, not richer.

## The one thing missing

**Do not draft this before the controlled after-measurement exists.**

Everything above is observational. The paper currently says "we found the
governor, predicted that more ore mines thinner, and changed the plate from 450
rows to 150." The version worth publishing says *and here is what happened*:

- five passes at the new plate, leads-per-jewel measured exactly as the
  observational figures were — the prediction is that it lands in 0.4–0.7
  rather than near 0.2;
- optionally a second, larger data point: the reclaim sweep re-mining the same
  ore at the corrected plate size, with `run_id` separating the runs — which is
  what that column was added for.

Both need the prospector resumed. Ingest already runs regardless, so nothing
is being lost while it waits.

## Caveats that belong inside the paper

Not in a footnote, not omitted — a reader will assume the stronger claim.

- **N=1 system**, one model pair, one corpus, one operator.
- **Quality is entirely unmeasured.** One published note, 470 leads never
  dispositioned, the human-concordance metric never once exercised. Nothing
  here shows that better-mined ore produces *better stories* — only that more
  of what was found is retained per unit of ore. Say so plainly.
- The cost figures are one provider's, at one moment, on two specific tiers.

## Where it would publish

Not any of the four registers (ticker / note / newsletter / blog). Closest is
the deep-dive tier. The retelling test from `/opt/_host/SEO.md` applies: if the
only honest title for this and for a blog post about the same work is the same
sentence, it is a retelling and must not be both.

## Where the evidence lives

- `docs/uzelhub-crew/scout-mining-economics.md` — the measured model, all
  figures with their queries.
- `docs/uzelhub-crew/scout-retool.md` — the spec, its four changes, and its
  own corrected error.
- `tools/leads_assay.py` — the falsification instrument; four cross-tabs
  printed every run so the flattering one cannot be chosen after the fact.
- Commits `3dc8894`, `48ba6e1`, `5950527`, `b015b70`, `ff8c57c` — the build.
