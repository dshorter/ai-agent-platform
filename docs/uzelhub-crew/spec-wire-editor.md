---
read: full
status: CURRENT SPEC, rewritable — the triage desk as it should run from 2026-09-07. One rule here is NOT yet in the prompt — clustering by arc versus angles (operator, 2026-09-05) — and the plan puts it there. For day-to-day reading it supersedes publishing-automation-plan.md Phase 2 and NEWSROOM.md §Marketer & Editor.
---

# The Wire Editor — current spec

<!-- MAP:START -->
- [One pass](#one-pass)
- [Verdicts](#verdicts)
- [Clustering: angles fold, arcs do not](#clustering-angles-fold-arcs-do-not)
- [Policy it routes by](#policy-it-routes-by)
- [The shadow](#the-shadow)
- [Seats](#seats)
- [Never](#never)
- [State of the desk](#state-of-the-desk)
<!-- MAP:END -->

**Job.** Turn the queue of new leads into a shortlist the human Editor can
dispose of in two minutes. Propose, never decide. Nothing it writes reaches
the Scout, and nothing it writes touches the ledger.

## One pass

1. Read every lead with status new: id, filed date, type, agent_span,
   pitch, why_now, citations. Read the ids already claimed, drafted,
   published and spiked.
2. Cluster leads that are the same story (see below).
3. Propose exactly one verdict per new lead, with the type confirmed or
   corrected and one tight reason.
4. Write the proposals artifact (clusters, proposals, the chief's shadow) to
   gitignored state. Record both calls on the spine.
5. Stop. The operator applies verdicts with lead_mark. The Director never
   reads the raw queue.

Verb: `python -m pipelines.wire_editor --pass` (`--dry-run` prints the
artifact and persists nothing; `--limit` caps the batch; `--skip-proposed`
leaves already-proposed leads alone; `--concordance` reports the metric).

## Verdicts

- **claim** — worth a Writer assignment; name the type.
- **spike** — not a story, or spent. Judge this lead only, never "this kind
  of lead". A spike is not feedback to anyone.
- **hold** — a real story, not ripe. Say what it waits for: an arc still
  accumulating, a dependency unshipped, a deep dive that must publish first.

Every new lead gets one proposal. A lead the desk returns nothing for
surfaces as a hold marked "operator judgment", never silently.

## Clustering: angles fold, arcs do not

Compute per cluster, from the citations, the distinct source dates and the
distinct source types.

| source dates | source types | it is | proposal |
|---|---|---|---|
| one | one | angles on one event | claim the strongest telling; propose the others as **hold, folded into <id>**, so the record shows they were angles, not non-stories |
| one | many | corroboration across stances: the problem being fought and the decision recorded | keep both; claim as one story citing both |
| many | any | an arc developing over time | never fold the episodes into the first; hold the parts naming the arc, or claim the arc as one story citing every part |

Capacity (one or two a week) constrains publishing order. It never
constrains the record. "The apex never tells the same story twice" is a
publishing rule, not a filing rule. Before 2026-09-05 the desk read it as the
latter, and 124 of 127 spikes were angles folded away.

Filing dates are not source dates. A long session is walked across several
passes, so one source can carry four filing dates. Read dates off the
jewels' source date and anchors, never off the filed field.

## Policy it routes by

The type table in spec-content-types.md. The apex publishes one or two a
week. Field notes are self-awareness first, war stories second. A story has
exactly one canonical home. Day-job leads carry the employer-gate flag; the
flag informs gate ② and is never a spike reason. A claim must have receipts
that plausibly exist. Routing only: the Scout's taste in surfacing is never
its business.

## The shadow

The Editor-in-chief (the Director's editorial hat, a separate invocation
from its morning brief) reads the compressed shortlist, never the raw queue,
and stakes agree or differ per proposal with its own verdict, type and
reason. Nothing it says touches the ledger. Concordance with the operator's
actual lead_mark verdicts, scored on human marks only (agent marks carry
`--agent` and are excluded), is the maturity metric. Gate ① may migrate to
the Director on sustained concordance, at a threshold the operator sets when
the data exists. Gate ② never migrates.

## Seats

Two plain calls, no tools, streamed, output ceiling 64,000, with a
truncation guard that refuses a cut shortlist rather than using it. Seats:
`WIRE_EDITOR_MODEL` (Sonnet 5) for the desk and `DIRECTOR_MODEL` (Sonnet 5)
for the chief. Cost rides on the spine as wire_triage.

## Never

Write the ledger. Speak to the Scout. Touch drafts. Coerce an unknown type
silently (log it; the vocabulary test fails the build if a site drifts).
Generalize a spike.

## State of the desk

Last ran 2026-08-03 on 113 leads. It has not seen the jewel layer, the paper
type, or a git-anchored lead. The end-to-end pass in the plan runs it before
anything is judged.
