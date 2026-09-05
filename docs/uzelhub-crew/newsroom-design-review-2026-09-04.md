---
read: full
status: design review of the 09-01..04 newsroom work, written 2026-09-04 from a fresh context window. Six critiques; four are unbuilt-work rather than defects. Findings 1 and 2 should land before Phase 1 runs.
---

# Newsroom design review — the week of 2026-09-01

A read of the whole newsroom corpus in one sitting, with fresh context and no
memory of the sessions that produced it: NEWSROOM.md, ADR-001, ADR-002,
jewels-are-transcript-only, scout-retool, scout-mining-economics, and the
reasoning arc in loose-words-hide-decisions.

The brief was the design work, not the code. Where a finding is about code it is
because the code contradicts a document, which is a design problem wearing
overalls.

## What is strong, specifically

**The pineapple rule, and the way it is enforced.** ADR-001's prior-art survey
earned the right to claim novelty: HLER has a backward edge and does not examine
it; Denario has a critique loop and does not examine it either. Neither peer
system asks whether repeated human selection narrows the space it selects from.
Enforcement by omission — load_pitched having no pattern for status, so breaking
the rule requires a visible diff rather than a quiet erosion — is the correct
implementation, not merely a stated intention.

**HLER's 59% to 13% is the right number to have gone looking for.** It is the
only quantified external evidence that constraining the input beats instructing
the model, which is this estate's standing preference. Worth citing whenever that
preference needs defending.

**The correction discipline.** NEWSROOM's Model tiers section keeps the wrong
claim visible under a dated correction rather than editing it away. Mining
economics records that three of four hypotheses died, two of them the author's
own. That habit is a larger asset than any single decision in the corpus.

## The critiques

Ranked by what they cost if Phase 1 runs before they are addressed.

### 1. The A/B has a confound nobody has named, and the fix is one word

Synthesis reads its already-pitched payload from the leads ledger at run time:
477 entries, roughly 74,830 tokens, larger than the jewels it is reasoning over
and the dominant term in that prompt's cost.

Run Arm A live and it files about thirteen leads. Arm B's payload now contains
them, and Arm B is instructed not to duplicate what has already been pitched. The
second arm is therefore structurally prevented from surfacing the first arm's
best material — and the shortfall reads as a quality difference in exactly the
output the experiment is judging.

ADR-002 §6b lists what is held constant: model, period, jewels on disk. The
dedup payload is not on that list and needs to be. Both arms run with --dry-run,
which persists nothing, or against a snapshotted ledger.

This matters more than its size suggests: it is invisible in the lead lists it
corrupts, and it lands on an experiment that is already 40 days overdue and about
to be run under supervision.

### 2. The retool sized the plate. ADR-002 grows the pile. Nothing sizes the selection.

The retool's own success criterion was conversion in the 0.4–0.7 band rather than
near 0.2, and it got there by making the plate *smaller* — 150 rows, because
output is homeostatic at about thirteen leads a pass regardless of what goes in.

ADR-002 opens five more sources and runs a full re-mine. But the row budget
governs the **walk**. Once synthesis is a consumer of a substrate rather than a
stage inside a pass, the dial that matters is the **selection**, and there is no
doctrine for it and no default: jewels.select() applies a LIMIT only when one is
passed. A synthesize over a fully mined six-source layer hands the model
thousands of jewels and still gets thirteen leads — conversion an order of
magnitude below the number the retool was declared successful for.

Unwelding the walk from the leap is what made mining cheap enough to do this, and
it is the same change that opened this gap. The missing piece belongs to the
retool, not to ADR-002.

### 3. Coverage is the wrong constraint for the ambient path, and the right one for the pathway that is not built

Verified against the live ledger on 2026-09-04:

| status | leads |
|---|---|
| new | 470 |
| rejected | 4 |
| drafted | 2 |
| published | 1 |

The apex contract is one to two URLs a week and the drip has been held since
2026-07-18. The newsroom is roughly sixty times oversupplied, draining at a rate
that makes the standing backlog multi-year. More complete coverage of six sources
does not improve that.

The coverage argument is genuinely load-bearing, though — for the **directed
hunt**. That is jewels-are-transcript-only's sharpest passage: a hunt against a
transcript-only layer would be blind to five of six sources *while believing it
had searched the box*. But the directed hunt is pathway 2, which ADR-001 records
as parked and unbuilt.

So ADR-002 builds infrastructure whose real customer is commissioned prospecting
while arguing for it in ambient terms — that the lead list will look better. The
§6b diversity hypothesis is strong and is the best new idea in the week's work:
commit messages record what was decided and why, *after*, where session logs
record problems *while they are being fought*. But diversity wants a balanced
**sample**; completeness wants a **ledger**. They are different mechanisms, and
the expensive one is being built for the goal that needs the cheap one.

Nothing here argues against the coverage ledger. It argues for justifying it
where it actually pays — the hunt — and for reaching the diversity goal with a
stratified selection, which is affordable now and needs no new table.

### 4. ADR-001's best content is filed under a rejected build

The three-pathway analysis — separating who supplies the *scope* from who
*selects*, and finding no prior art at all for ambient prospecting — is the most
valuable strategic writing in the corpus. It closes on the observation that the
estate shipped pathway 3 first, parked 2, and never built 1, which is the reverse
of the risk order.

That is not in NEWSROOM.md. AGENTS.md routes to the ADR as "manual Writer
assignments (Deferred)", so a reader routing by status skips it. And the
amendment ADR-001 says it owes — that the Scout's unusual position deserves
stating rather than assuming — is unwritten.

A deferred build is not a deferred finding. The pathway map should be lifted into
NEWSROOM.md on its own, where it survives the ADR's status.

### 5. NEWSROOM.md has crossed a stratigraphy threshold

Five passages in a read:full spine document that a reader cannot currently trust
without three ADRs open beside it:

| Passage | State |
|---|---|
| §Scout's sources — "primary ore… richest by far" | the exact loose word that produced the jewel finding, still standing unqualified |
| §Scout's sources — "scope the cursor to the logs, and nowhere else" | ADR-002 argues the opposite; AGENTS.md already records that the two disagree |
| §Open choices — commissioned prospecting is "pineapple-compatible" | ADR-001 shows this is true of the roam and false of the ledger |
| §Model tiers | three stratigraphic layers: original, CORRECTED, SUPERSEDED |
| §Open choices — "Synthesis-stage model: A/B underway" | present tense, 40 days after the readout was due, describing a design ADR-002 §6b has since replaced |

The per-item discipline is right and should not change. The accumulation is the
problem: honesty about each correction has produced a document whose current
state is not readable in one pass. A standing-corrections block at the head —
what is superseded, and where the current answer lives — costs one edit and
restores the read:full promise.

### 6. The gated source_ref mapping has no home, and the right one already exists

ADR-002 decides that gated sources get an opaque source_ref resolved through "a
mapping that never leaves the box", and observes in the same section that the
redaction gate guards tracked prose while this path runs through Postgres.

It does not say where the mapping lives. Its own reasoning points at _host, which
has no remote and already holds the employer vocabulary and the capability-URL
index for precisely this reason. Naming it costs a line and prevents the mapping
being invented somewhere worse under time pressure, which is the failure mode
§4 of that ADR is otherwise very good at anticipating.

## Where the code contradicts the documents

Four items, carried from the same day's infrastructure audit because they are
newsroom design rather than infrastructure:

- **select() and the walk now hand synthesis different shapes.** The docstring
  directly above the change states the invariant it breaks.
- **The synthesis prompt still tells the model its jewels cite seqs.** False the
  day a non-transcript reader lands. No new tool is needed — read_file, grep and
  run_git already resolve a path or a sha.
- **--walk still passes no cost ceiling, and --source-type does not exist.** Both
  are ADR-002 commitments; the model default has already moved without them.
- **The Scout config docstring still argues for Fable** sixty lines above the
  Sonnet default it now sets.

The --source-type item is more urgent than the infrastructure audit rated it:
without it, finding 1 above cannot be controlled either.

## What generalises

- **A measurement can invalidate a plan two documents away.** Homeostasis was
  measured for a tuning question and quietly governs every later decision about
  how much ore to open. Nothing links them, so the plan reads as sound.
- **Completeness and diversity are different goals with different mechanisms.**
  A coverage ledger and a stratified sample both answer "the mix is wrong", at
  very different prices.
- **A deferred build can carry an undeferred finding.** Status routes readers;
  findings filed under a rejected proposal go unread.
- **Honest corrections accumulate into an unreadable document** unless something
  collects them. The discipline is right and needs an index.

---

# Addendum — the arc, measured (2026-09-04, same day)

Worked out in conversation after the review above. Kept because the *order* of
it is the part that evaporates: two wrong assumptions were held in turn, and
each was corrected by a measurement rather than an argument.

## The operator's distinction, which is the load-bearing one

An **arc** is a story that develops over time and may span more than one
source — Monday, Wednesday, Friday, then the closing piece two weeks later.
That is a different object from **multiple angles on one discrete event**,
where several leads narrate the same thing that happened at one point.

Folding angles into the strongest telling is ordinary editing. Folding an
arc's episodes into its first episode destroys the thing worth telling. The
Wire Editor does the same operation for both, because nothing distinguishes
them.

## Wrong assumption #1 (mine): the desk is only folding angles

`scout-mining-economics.md` says 124 of 127 spikes are cluster-internal. I read
the Wire Editor's prompt expecting a misplaced constraint and found the capacity
number stated **three times** — lines 35, 48 and 62 of `wire_editor_agent.py` —
with the clustering instruction sitting under it at line 45.

Two corrections to the review's account of that:

- `hold` **is** offered ("spiking **or holding** the rest INTO it"), and the
  output schema has a `clusters` array which `run.py` writes into the desk
  artifact. Arcs are detected and named. The desk is not blind.
- It spikes anyway, because everything around line 45 pushes that way: spikes
  are "cheap", the desk must "be decisive", capacity is "the scarcest resource".
  `hold` is present and outgunned by its own context.

**The fair diagnosis is altitude, not error.** Capacity constrains *publishing
order*; it was applied to *record-keeping*. "The apex never tells the same story
twice" is a publishing rule read as a filing rule. Being decisive about what to
publish next never required destroying the record of what else was there.

**And this bug has been fixed here once already.** On 2026-08-03 `rejected` was
split out of `spiked` because one verdict was carrying two meanings. `spiked` is
*still* carrying two: "not a story" and "folded into a better telling of the
same story". Same class, one level over, uncaught.

## Wrong assumption #2 (the operator's): four filing dates ≈ four sources

The cluster themes are overtly temporal — *saga*, *rise and fall*, *ladder*,
*staircase*, *evolution*, *genesis*, *arc coda* — and span up to five distinct
filing dates. The operator reasoned that filing dates must therefore stand in
for distinct sources, since the Scout does not read one source a little at a
time over several days.

It does. **44% of all turns live in sessions larger than the old 450-row pass**,
so long sessions are walked across several passes. Measured against the citation
graph:

| Cluster | Leads | Filing dates | Distinct sessions | Source-dates |
|---|---|---|---|---|
| the 19-lead saga | 19 | 4 | **1** | 4 |
| "rise and fall" | 10 | 2 | **7** | **8** |
| stale-artifact ladder | 5 | 5 | 2 | 3 |
| registry/ledger doctrine | 7 | 4 | 2 | 3 |
| a launch cluster | 5 | 2 | **1** | **1** |

Filing dates over-count sources, sometimes by four to one.

## What the measurement produced: a discriminator

The intuition was right; the proxy was wrong. The right column is the **date of
the source material** — and the last row above is the operator's other case
sitting in the same pile: one session, one day, five angles.

So arc and angle-cluster are mechanically separable:

- **one source-date** → angles on an event. Fold; the strongest telling is the
  story.
- **many source-dates** → a developing arc. Folding destroys it.

This is better than a `folded` verdict alone. A verdict stops the record being
destroyed; it does not tell the desk *when* folding is right. The discriminator
is computable from data the jewel layer already carries.

## And a second dimension, forced by one question

The operator then asked whether the machinery is source-agnostic. The concept
is, and 1.4.0 already did the work — `session_date` is documented as "the DATE
OF THE SOURCE MATERIAL, whatever the source" (misnamed; read it as
`source_date`), and `COALESCE(seq::text, source_ref)` is already the normalized
anchor. The Wire Editor clusters on pitch text and knows nothing about
transcripts.

**The measurement above was not normalized** — it joined through
`scout_session_log`, a transcript-only table with no path for a git jewel. The
normalized form reads the jewel layer: distinct `session_date`, distinct
`COALESCE(seq::text, source_ref)`.

Asking the question exposed a flaw in the one-dimension rule. A cluster holding
a transcript jewel and a git jewel from the **same day** is not redundancy — it
is the problem being fought and the decision being recorded, the two registers,
on one event. That pairing is precisely what the recovery mine exists to
produce, and the rule as first stated would fold it. So:

| source-dates | source-types | verdict |
|---|---|---|
| one | one | angles on an event — fold |
| one | **many** | cross-register corroboration — **keep both** |
| many | any | an arc — do not touch it |

The third dimension only becomes measurable once the readers land, which is a
further reason the register experiment comes before any of this reaches the desk.

## Open, and where source-specificity still leaks

- A lead's `sources` field is free text shaped like transcripts ("jewels seq
  41-49"). It is publishable, it reaches a note, and it is exactly ADR-002 §4's
  concern. It needs a normalized rendering **before** the first non-transcript
  reader, not after.
- One cluster's cited seqs resolve to **zero** rows in the log — some leads cite
  something that is not there. Small, separate, and worth a look.
- The plate went 450 → 150 in the retool, so sessions spanning a pass went from
  7% to 30%. Filing dates will diverge from sources further from here. Nothing
  downstream should read them as a proxy for anything.
