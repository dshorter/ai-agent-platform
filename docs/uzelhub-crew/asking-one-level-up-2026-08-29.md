---
read: full
status: method companion to silent-instruments-2026-08-29.md, written the same day. The arc itself spans 2026-08-26 to 2026-08-30; the filename date is when this was written. Turn 9 was added 2026-08-30 after checking this document against the session log -- it is about that check. That doc records what was found; this one records how the thinking moved, because the reversals are the part commits cannot reconstruct. Attribution is deliberate — most of the reframes below came from the operator, and the record is more useful if it says so.
---

# Asking one level up — how a housekeeping session moved

<!-- MAP:START -->
- [The pattern](#the-pattern)
- [Turn 1: overdue -> dead premise](#turn-1-overdue---dead-premise)
- [Turn 2: the fix that was already holding](#turn-2-the-fix-that-was-already-holding)
- [Turn 3: make it work -> should it run](#turn-3-make-it-work---should-it-run)
- [Turn 4: cut cost -> cut which dimension](#turn-4-cut-cost---cut-which-dimension)
- [Turn 5: the examples gave away the wrong domain](#turn-5-the-examples-gave-away-the-wrong-domain)
- [Turn 6: is the cheap model bad, or bad at something we're dropping](#turn-6-is-the-cheap-model-bad-or-bad-at-something-were-dropping)
- [Turn 7: why is this uncovered -> what should the boundary be](#turn-7-why-is-this-uncovered---what-should-the-boundary-be)
- [Turn 8: a fix -> a configuration](#turn-8-a-fix---a-configuration)
- [Turn 9: documented is not operative](#turn-9-documented-is-not-operative)
- [Right answer, wrong reason](#right-answer-wrong-reason)
- [What to steal from this](#what-to-steal-from-this)
<!-- MAP:END -->

The session was scoped as housekeeping: read the Director's morning brief, look
at the oldest items. It ended with a per-domain model resolver and a rewritten
alerting policy. The findings are in
[silent-instruments-2026-08-29.md](silent-instruments-2026-08-29.md). This is
the other half — the sequence of questions, and specifically the nine times the
question in play turned out to be one level too low. The ninth arrived a day
after this document was written, and is about this document.

## The pattern

Every productive turn in this session had the same shape. A reasonable question
was being answered competently, and the answer was worth less than noticing that
a better question sat directly above it.

| Asked | Should have been asking |
|---|---|
| Which items are most overdue? | Which items' premises are still true? |
| Is Docker eating the disk again? | Is the old fix still holding, and what else changed? |
| How do we make film's trending stage run? | Should film be running at all? |
| How do we cut film's cost? | Cut which dimension — and does cutting it destroy the measurement? |
| Will a string tagger work? | On which domain's vocabulary? |
| Did the cheap model fail? | Fail at *what*, and is it the part we're keeping? |
| Why does the predictor lack a cost cap? | What property should governance be scoped to? |
| Where do we put film's model override? | Why is there an override rather than a configuration? |
| Was the decision written down? | Was it written anywhere that *executes*? |

Six of those nine reframes came from the operator, not from me. That ratio is
the most useful thing in this document.

## Turn 1: overdue → dead premise

The brief ranked 44 open todos by age. The obvious read was a triage list: 42
overdue, oldest first, start at the top.

The useful read was that age is the wrong sort key. `scout-ab-flip-to-sonnet-r2`
was ranked first, 38 days overdue — and it was not late. It was **impossible**,
and had been since July: the flip it depends on never happened, so the Sonnet
week it would compare against does not exist. Nothing about "38 days overdue"
distinguishes *not done yet* from *cannot be done*.

That reframe set the tone for everything after it. It also explains the brief's
behaviour without blaming it: the Director reads git state and the calendar
faithfully, and has no mechanism for checking whether an item's premise still
holds.

## Turn 2: the fix that was already holding

Disk was at 94%. The operator's instinct was Docker — a ~30GB win a few months
back. Checking it was cheap and the answer was better than yes or no: Docker had
been *moved to a separate volume*. That fix wasn't just holding, it had removed
Docker from the root filesystem permanently, which is why it couldn't be the
cause this time.

The general form: "did X regress?" is usually less informative than "what did
fixing X change about the system's shape?" A fix that relocates a problem
changes which future problems are possible.

The real answer — 14GB in root-owned paths an unprivileged walk couldn't see —
only surfaced because the first answer was *no, and here's why not*.

## Turn 3: make it work → should it run

This is the turn I got wrong, and the operator corrected it in one line: *this
is not a perf problem, it is a cost problem.*

I had found film's `trending` stage timing out, traced it to an N+1 in
`score_all`, and started designing the fix. All of that was correct and none of
it was the question. Film is ~65% of extraction spend, its output had been
frozen for 23 days, and **nobody had noticed** — which is evidence about what
that output is worth, not a bug report.

Optimising the expensive thing is what you do *after* deciding it should exist.
I had skipped the deciding step because the broken thing was in front of me and
fixing broken things feels like progress.

## Turn 4: cut cost → cut which dimension

My correction to my own error was still wrong, and the operator caught that too.

Having accepted that film's cost was the question, I proposed pausing it, then a
weighted volume cut. The operator's counter: **don't cull the volume — cut what
each document costs, then evaluate.**

That is better for a reason I hadn't seen. Movers is built from mention counts
over a 7-day window, with `activity_factor = min(mention_count_7d, 20) / 20`.
Halving film's document budget roughly halves its mention counts and changes the
rankings. So a volume cut doesn't just save money — **it corrupts the exact
measurement that would tell you whether film is worth keeping.** You'd evaluate a
degraded corpus and generalise to the full one.

And pausing, my other suggestion, has the same defect in a purer form: it saves
the most money and produces no information at all. Cheap-at-full-volume is the
only option that buys both.

The decomposition confirmed the instinct: film runs 1.55x the documents at 1.25x
the cost per document, so volume is the larger factor — which is precisely why
it is the wrong one to cut. The bigger lever is the one that destroys the
experiment.

## Turn 5: the examples gave away the wrong domain

I explained the mention tagger using TSMC, ASML and Nvidia. The operator stopped
on it: *those are semi entities — it's FILM that's the greedy pig.*

That was a catch about examples that turned out to be a catch about design. I had
reached for semiconductor entities because that's where string matching *works*.
Film's entity vocabulary includes `Bad`, `Plane`, `Dutch`, `RED`, `Coke` and
`Edgar` — film titles are ordinary words, structurally, not as a data-quality
problem. A string matcher would emit a MENTIONS edge for "Plane" every time an
article mentioned an aircraft, and since Movers is *entirely* mention-driven,
that isn't noise at the margin. It's a fabricated trend.

So ADR-010's zero-token tagger is right for semiconductors and actively
dangerous on film — and film is the one that needs the money back. The design
split by vocabulary shape, which no amount of reasoning about the tagger in the
abstract would have produced.

Worth noticing: the tell was in my *examples*, not my argument. Examples encode
assumptions the prose doesn't state.

## Turn 6: is the cheap model bad, or bad at something we're dropping

The operator raised the strongest objection available to their own plan: shadow
mode had been tried before and "never really worked that well" — and if the
cheap model had failed at *mentions*, the whole Movers-only idea collapses and
film should just be switched off.

Precisely the right question, and falsifiable. The post-mortem
(`ext4-cheap-model-escalation-analysis.md`) records every failure, and every one
is a **relation** failure: endpoints that don't match its own entity names,
snippets absent from the source, overconfident relations. And, verbatim: *"Nano
sometimes produces a reasonable entity list but no relations at all —
schema-valid but useless."*

Useless *for the graph*. For Movers, an entity list with no relations is the
entire product. The thing that disqualified the cheap model is the thing being
kept.

That is the highest-value question shape in the whole session: not *did it
fail*, but *fail at which half, and which half are we keeping*.

## Turn 7: why is this uncovered → what should the boundary be

Finding that the predictor had no cost ceiling while every crew agent had one
invites an obvious fix: add a ceiling. The operator asked the better question —
*why was it missing in the first place?* — and answered it: the caps were
applied to things called agents, and the predictor was never in that mental
model, even though it has agentic behaviour.

That converts a patch into a rule. "Is it an agent" is a **noun test**, and it
silently excluded the largest spender on the box. "Does it spend money on someone
else's API" is a **property test**, and it predicts the risk. The predictor
wasn't overlooked by decision; it was excluded by category.

The corollary is that the same audit should now run against anything new: not
"is this an agent" but "does this call a paid API unattended."

## Turn 8: a fix → a configuration

I proposed giving film its own model through a per-instance systemd
`EnvironmentFile` — two lines, ten minutes, works. The operator rejected it on
architecture: the predictor is designed to be **domain-agnostic**, so a
domain-specific behaviour cannot live in a sidecar file keyed on a systemd
instance name. It has to be config.

Correct, and the codebase agreed more than either of us expected. ADR-010's D3
follow-up had already made exactly this move for budgets — "promote the budget
from a hardcoded constant to a `domain.yaml` key alongside the other per-domain
calibration parameters." The precedent existed; I had proposed re-solving a
solved problem in a worse place.

And then the part that only appears once you're looking for config rather than a
patch: **`domain.yaml` already declares `base_relation: MENTIONS`**, validated
against the canonical taxonomy and consumed by the extraction prompt and the
trend scorer. "Movers-only" is already sayable in this system's own vocabulary —
*extract the base relation only*. There was no new concept to invent, and the
quick fix would have buried that.

The clean version also paid a debt: five readers of `PRIMARY_MODEL` had drifted
into two behaviours. The sidecar would have made it six.

## Turn 9: documented is not operative

Added a day later, because the arc produced one more turn after this document
was written — and it is about this document.

On 08-29 the operator ruled that film's document budget must not be cut: the
volume is the Movers signal, so cutting it corrupts the measurement. That is
recorded above, in [Turn 4](#turn-4-cut-cost---cut-which-dimension), in plain
prose.

On 08-30 I proposed cutting film's budget anyway — and when challenged, checked
whether the decision had been recorded, grepped for "budget unchanged", did not
find the phrase "don't cull the volume", and reported that it had never been
written down. Both the proposal and the diagnosis were wrong.

What had actually happened is narrower and worse than "we forgot to write it
down":

- The decision **was** in the narrative.
- It was **not** in `scripts/sept1_cost_boundary.py`, whose `MODES` table
  defaulted to `film-weighted` — the exact cut the decision withdrew.
- It was **not** in `operational-state.md`, the file that opens by declaring
  itself the single source of truth for how each domain runs.

So the machinery and the prose disagreed, and **the machinery won** — with me,
a day later, arguing its side. A default in a script outranks a paragraph in a
companion document, because the default is what executes.

This is the same failure as the Director's brief ranking a dead task first, one
layer up. There, state was read faithfully and the premise went unchecked.
Here, a decision was recorded faithfully and the artifact that acts on it went
unchanged. In both cases the written record was accurate and the running system
did not consult it.

The rule that follows: **a decision is not recorded until it changes something
executable.** Prose is where you explain a decision; a default, a config key, or
a test is where you *store* it. If a decision cannot be expressed in one of
those, it is a preference and will not survive contact with a busy day.

Corollary, learned the same morning: check a claim about the record **against
the record**. Both write-ups here were composed from working context rather than
from the session log, which is exactly how the log came to disagree with them —
and reading the log turned up a four-day dating error in both.

## Right answer, wrong reason

Twice I reached a defensible conclusion by a route the evidence didn't support.
Both are worth recording because the conclusion surviving is what makes them
easy to miss.

- **Rejecting the calendar A/B.** I argued the ore and the scoring had changed
  underneath it. The economics doc says the walk was *uniform* — 6.7% to 7.9%
  annotation in every month — so ore variation isn't the confound. The real
  reason is stronger: output is homeostatic at ~13 leads per pass regardless of
  input, so a comparison scored on lead counts could never show a model
  difference. The A/B was unmeasurable by construction, not spoiled by
  circumstance.
- **"Cheap, done in an afternoon."** I said a paired re-walk would be cheap while
  also worrying that the dedup payload made repeated passes expensive. Both were
  true of different things, and the resolution — walk and synthesis were unwelded
  a week earlier — was work I hadn't accounted for. The estimate was right by
  luck.

Five further claims died outright during the session; they're listed in the
findings doc. The pattern across all of them: a confident reading built on one
observation that was never checked against a second.

## What to steal from this

1. **Sort by whether the premise holds, not by age.** An overdue list conflates
   *not done* with *no longer meaningful*, and the second kind never leaves the
   top of the list on its own.
2. **Before optimising the expensive thing, ask whether it should exist.** A
   broken component in front of you will consume the deciding step if you let it.
3. **Check whether the cheap fix destroys the measurement.** Especially when the
   thing being cut is the thing being measured — for a mention-driven metric,
   volume *is* the signal.
4. **Read your own examples for assumptions.** Reaching for a case where the
   approach works is a signal about scope you haven't stated.
5. **"Did it fail?" is weaker than "failed at which half?"** Especially when
   you're about to drop a half.
6. **When something is uncovered, fix the boundary, not the instance.** Noun
   tests ("is it an agent") exclude silently; property tests ("does it spend
   money") don't.
7. **A domain-specific behaviour in a domain-agnostic system is a config key.**
   If it's landing anywhere else, the design is telling you something.
8. **Look for the concept already in the vocabulary.** `base_relation` had been
   sitting there the whole time.
9. **A decision is not recorded until it changes something executable.** Prose
   explains a decision; a default, a config key or a test stores it. The
   machinery outranks the paragraph, because the machinery is what runs.
10. **Check claims about the record against the record.** Both of these
    documents were written from working context, and both were wrong about
    their own dates until the session log was read.
