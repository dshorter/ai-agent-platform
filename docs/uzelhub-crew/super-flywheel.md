---
read: full
status: whiteboard sketch (opened 2026-07-13) — NOT a build plan; three commitments captured, everything else open
---

# The super flywheel — prompt tuning for agents, every __ turns

> Seed: operator whiteboard, 2026-07-13 evening chat. Captured because the
> box's founding grievance is insight evaporation. The manual ancestor already
> exists: [prompt-tuning.md](prompt-tuning.md) is this loop run by hand for
> the content agent — log observations per draft, tune on patterns, never
> after one sample. The super flywheel is that doctrine, automated and
> generalized to the crew: the agents' own observability (spine, checklists,
> quality gates) periodically reviewed into **proposed prompt diffs**.

<!-- MAP:START -->
- [Committed at the whiteboard (2026-07-13)](#committed-at-the-whiteboard-2026-07-13)
- [The seat split — who is in the program](#the-seat-split--who-is-in-the-program)
- [Open (everything else)](#open-everything-else)
<!-- MAP:END -->

## Committed at the whiteboard (2026-07-13)

1. **Manual approval, always.** The tuner proposes a prompt diff with the
   accumulated observations as receipts — copyDraft-for-prompts. Nothing
   self-applies. Prompts are code; the approval gate is the operator (or,
   by design lineage, the Director's editorial pass — which routes and
   approves but never writes).
2. **"No changes needed" is a first-class verdict.** The review must be able
   to end in a legitimate, evidence-cited null result — a reviewer that must
   find something optimizes for finding things, and prompt churn would wear
   the costume of diligence. This generalizes prompt-tuning.md's
   don't-tune-after-one-good-sample rule into the meta-loop's constitution.
3. **The Scout is (probably) not in the program.** Its returned content is
   by definition not part of what defines it — judging the leads is taste,
   and tuning its prompt from lead outcomes would be the pineapple loop
   wearing a maintenance costume. Story quality stays a *manual editorial
   review of the stories*. At most, explorer seats could someday tune on
   pure navigation/mechanics evidence (malformed output, missed sources) —
   and even that deserves suspicion.

## The seat split — who is in the program

Convergers — seats with something like ground truth — are the natural
patients: the **content agent first** (277 runs, a per-draft checklist, a
living tuning log — the loop's manual ancestor is already its operating
doc), the marketer behind it. Explorer seats (the Scout's discovery half)
stay out per commitment 3.

## Open (everything else)

- The `__` in "every __ turns": review *cadence* (look every N turns) vs the
  *acting bar* (patterns, not counts) — probably both, separately set.
- What counts as signal per seat: checklist observations, quality-gate
  stats, cost-per-outcome from the spine, editor outcomes (convergers only).
- Who runs the review: a ghost-crew batch process? the Director's weekly
  pass growing a section? its own small agent?
- Mechanics (cheap, mostly exists): prompts live in git, versions could be
  env-var'd like the Scout's synthesis model, and the `agent_decisions`
  spine prices any before/after A/B automatically.
- Whether tuned-prompt adoption requires an A/B pass or approval suffices.
