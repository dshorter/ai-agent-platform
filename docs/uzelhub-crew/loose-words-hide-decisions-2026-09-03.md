---
read: full
status: reasoning arc for 2026-09-01..03; companion to the artifacts it lists, written while the context was still hot
---

# Loose words hide decisions

A companion doc in the shape of `asking-one-level-up-2026-08-29.md`: the
**findings** live in their own documents, and this one carries **how the
thinking moved**, because that is the part that evaporates when a context window
closes. Written at the operator's request on 2026-09-03, deliberately while the
reasoning was still recoverable rather than after.

Everything below is reconstructible from the repo. What is *not* reconstructible
is the order — which question forced which answer — and that ordering is most of
the value.

## The pattern that produced most of it

Four of this session's findings came from the operator refusing to let a loose
word stand. Not one came from a bug report.

| The loose word | What it was hiding |
|---|---|
| "session logs are the **primary** ore" | a `NOT NULL` foreign key that made five of six sources unable to produce a jewel at all |
| "all three require a human to supply the **scope**" | two different granularities — picking a topic vs bounding a field — which is the whole line between two build pathways |
| "two **new** bodies of ore" | the difference between adding a *source* and adding *retention* to sources already in the catalog |
| "make a parallel command-line path" | that half the goal needed no code, because `--dry-run` already bypassed the gate |

**The generalisable form: when a description and a mechanism are allowed to
share a word, the mechanism wins silently.** "Primary" was an honest
description of richness. The schema had turned it into an absolute. Nobody lied
and nobody was careless — the word simply stopped meaning the same thing at
different depths, and no one had checked the bottom one.

The audit question that works, in the operator's own words: *"if you are just
measuring the results, that's fine. But in terms of execution…"* — **is this how
we talk about it, or is it in the mechanism?**

## The chains

### Chain 1 — "revisit the publishing pipeline" → two tracks, not one queue

Picking the pipeline back up after three weeks. The blocked-looking state
resolved once the streams were separated: the apex note drip waits only on
identity profiles; the blog project waits only on `routes.yaml`. Neither waits
on the other, and treating them as one queue is what made everything look stuck.

→ `docs/uzelhub-crew/pipeline-state-2026-09-01.md`, and a published gate map.

### Chain 2 — a blocked commit → the gate was re-litigating published content

Five finished changes had been parked for weeks. The redaction gate was
blocking them over content **already in the public tree** — its own test
fixtures re-blocked their file every time a detector rule was added.

The fix was not to dismiss findings but to change the question: block what a
commit *adds*, by comparing against `HEAD`'s copy of the same file.

→ `9a5ce31`; closed the path-scoping open question in `AGENTS.md` *sideways*
— dismissals stayed global, and the per-file judgment moved into the baseline.

### Chain 3 — "walk a lead through" → an ADR that argued itself into deferral

Proposed a file-based assignment path (ADR-001). Then three things happened in
order, and each one shrank the build:

1. **Prior art** (fetched as content, not search snippets) found that the one
   *shipping* content operation surveyed has **no automated discovery at all** —
   the manual path is what production converges on, not a compromise.
2. Separating *who sets the boundary* from *who selects* turned two pathways
   into **three**, and showed the estate had shipped the one with no external
   precedent (ambient) and parked the one with the most (scoped).
3. The operator countered: skip the parallel path, paste into a session. Correct
   — and checking the code showed `run.py:78` gates the claim requirement on
   `not dry_run`, so **the verification half had needed no code since 2026-08-08.**

→ ADR-001, status **Deferred**, with the reasoning for not building it kept.

### Chain 4 — "does the Writer go out?" → what a cap silently costs

Yes: a *convergent* roam (`read_file`, `grep`, `run_git`, `read_transcript`),
bounded at 6 iterations and 120,000 tool characters. The lead supplies citations;
the Writer follows them into the box.

Which raised the real question — a bad draft is visible and gets rejected, but an
**under-researched** draft looks fine and nobody can tell what was left unpulled.
Same argument `NEWSROOM.md` already makes about the Scout's *missing* leads, one
seat downstream.

→ `writer-roam-budget-headroom@operator`, due 2026-09-04.

### Chain 5 — "primary ore" → three layers → a NOT NULL foreign key

The central chain. Checking the challenge produced three different answers at
three depths: **no preference** in the prompt, a **deliberate documented
asymmetry** in coverage, and in the DDL a `seq BIGINT NOT NULL REFERENCES
scout_session_log(seq)` — so a jewel could not exist without a transcript row.

The cause behind the cause: that FK is an anti-hallucination control and is
correct. Its *side effect* was that the schema's only provenance field was a
transcript position, so a control silently answered a question it was never
asked. **And persisting the jewel layer — a change made for cost reasons —
promoted a soft prompt-level preference into the substrate every future leap
reads from.**

Caught in the cheap window: 58 jewels from 142 turns, 0.96% of the corpus, so
almost nothing to migrate.

→ `jewels-are-transcript-only-2026-09-03.md`, schema **1.4.0**.
→ And a self-inflicted lesson: the migration dropped the constraint
`persist()`'s `ON CONFLICT` named, breaking every walk. Caught immediately —
but it is the same class of mistake the finding is about, made while fixing it.

### Chain 6 — "take the cursor approach" → a return address, not a leash

`NEWSROOM.md` forbids cursors on non-log sources, on the grounds that a forward
cursor closes the temporal aperture. The flaw: that conflates *having* a cursor
with being *reachable only through* one. The logs already disprove it — the walk
is cursor-driven while `read_transcript` stays free-roam.

The operator's framing carried it: depart from the cursor, roam, return, advance.
**Additive, not a relaxation** — free roam alone gives freedom without coverage.

Then the design question underneath: not six cursors but **one coverage ledger**,
because the sources are three patterns and the mutating ones (docs, calendar)
would make a watermark report full coverage while being wrong.

Then the hazard underneath *that*: **`source_ref` is publishable text.** It
reaches a note through the lead's `sources` field, so a gated path name travels
outward even when every word of content was scrubbed.

→ ADR-002. And a receipt: the gate **blocked this ADR's first commit** for
naming the gated platform three times — in the section warning that identifiers
travel. The name was removed rather than dismissed. Two lessons: the naming
reflex survives writing the warning, and the gate guards *tracked prose* while
the `source_ref` path runs through **Postgres**, which it never sees.

### Chain 7 — "Fable is expensive" → measured → the reasoning was falsified

The operator estimated synthesis at ~$1 per call. Measured from
`agent_decisions`: **$1.3274 average, $51.77 across 39 calls**, against **$0.75
for all 106 walk calls combined** — 187× per call. Rising 4× in six weeks
($0.448 → $1.847), because the dedup payload rides in the synthesis prompt and
scales with the ledger.

That did not merely favour the swap; it **falsified the argument that put Fable
there.** `NEWSROOM.md` called it "pennies per pass" on two premises: *ambient,
weekly-ish* — overtaken when the pass went daily on 2026-07-22 — and *low-token*,
which $1.33 on a $10/$50 model is not.

The quality argument was untouched and is still unmeasured, so the burden was
**inverted rather than abandoned**: default cheap, spend 5× deliberately where it
shows.

→ `SCOUT_SYNTHESIS_MODEL` now defaults to Sonnet 5; `NEWSROOM.md` carries a
dated correction with the original claim left visible.

### Chain 7b — and then two variables were moving at once

The operator's hypothesis: the lead list improves from source balance alone.
Plausible on two mechanisms — commit messages carry a *resolved* register that
session logs structurally cannot, and `agent_decisions` stops being a post-hoc
SQL hint and becomes mineable, which is what "stories live at the seams"
actually needs.

But synthesis had just changed model, and the source mix was about to change.
Both moving together makes any improvement uninterpretable and burns the A/B
open since 2026-07-26.

The fix is free because walk and leap are already unwelded: **add
`--source-type` to `--synthesize`** and both questions become controlled
comparisons over jewels already on disk, mining nothing.

→ ADR-002 §6b. Not built.

## What is still open after all this

- **The readers.** Schema 1.4.0 permits non-transcript jewels; no reader
  produces one. The schema is deliberately ahead of the pipeline, and
  `persist()` must carry the allowlist check that the missing FK no longer
  provides. (`jewel-source-readers@operator`, due 2026-09-10.)
- **The opaque `source_ref`** for gated material — must be settled *before* the
  import, because once written those refs are in every jewel mined from it.
- **A cost ceiling on `--walk`**, which currently passes `cost_cap=None`.
  Agreed 2026-09-03; not yet built.
- **`--source-type` on `--synthesize`**, the thing that makes the two
  experiments separable.
- **The Fable/Sonnet A/B**, open since 2026-07-26 — now cheap, and now with a
  confound to control for.

## What generalises

- **A constraint can answer a question it was not asked.** Ask what a new
  control now *forbids*, not only what it prevents.
- **Making something durable makes its assumptions durable too.** The transcript
  bias was survivable while jewels died with the process.
- **Check the layer below the one the docs discuss.** Every narrative layer here
  was honest. The finding was in the DDL.
- **Measure the claim, not the price list.** "Pennies per pass" had been sitting
  in a design doc for weeks while the real figure was 100× higher and climbing —
  and one query settled it.
- **A word shared between a description and a mechanism is a latent bug.**
