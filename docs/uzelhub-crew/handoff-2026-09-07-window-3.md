---
read: full
status: window handoff, written 2026-09-07 at the end of window 3 of plan-2026-09-07-unify-and-reset. Steps 7 and 8 are done and the plan's checklist is complete. Facts only. Window 4 starts from a fresh session and is not in that plan.
---

# Handoff — window 3 (the read-through and the build) is done

Everything below is committed and unpushed. Nothing here is the authority on
anything; it is a map to the documents that are.

<!-- MAP:START -->
- [Read first](#read-first)
- [What the commits did](#what-the-commits-did)
- [Facts window 4 needs](#facts-window-4-needs)
- [What the read-through found](#what-the-read-through-found)
- [Open, and none of it is window 4's to decide alone](#open-and-none-of-it-is-window-4s-to-decide-alone)
- [What window 4 could do](#what-window-4-could-do)
<!-- MAP:END -->

## Read first

`AGENTS.md`, `GLOSSARY.md`, the four `spec-*.md` and the plan — the same set
window 2 named. Add `database/ai_agent_platform/006_scout_lead.sql` if the next
job is the cutover; its header carries the reasoning and the ADR-003 amendment
carries what changed from the sketch.

## What the commits did

| commit | step | what |
|---|---|---|
| `53d941c` | 7 | the read-through: three code fixes, one spec fix, one hole named and left |
| `9ad2f1e` | 8 | `file_ore.py` — docs and ledgers become ore, one reader with splitters |
| `fac924a` | 8 | `006_scout_lead.sql` and its verify, rollback and apply script. **Not applied** |

Tests: **310 pass, 10 skip**, up from 295. The skips are all
`tests/test_lead_schema_parity.py`, which arms itself when 006 is applied.

**No model was called this window. Nothing was spent.** Everything here is code,
schema and prose; the reader has never been run against the walker.

## Facts window 4 needs

- **The synthesis prompt changed.** Two edits, both the A6 class: the user turn
  no longer says "Jewels from this pass's transcript walk (seqs are
  read_transcript coordinates)", and the opening clause no longer says
  "transcript jewels". Window 2's step-5 A/B numbers were bought under the old
  wording, so they are a baseline for that experiment and not a baseline for
  this prompt.
- **The surveying line was NOT touched.** "Your tool budget is small; spend it
  pulling threads, not surveying" is still live in `SCOUT_SYNTHESIS_PROMPT`, and
  it is still the next single-variable experiment.
- **`file_ore` produces 345 doc units and 18 ledger entries** under
  `docs/uzelhub-crew`, dated 2026-06-23..09-07 by last commit. Measured by
  reading, not by mining: **no doc or ledger jewel exists**, and the walker has
  never seen one of these pages.
- **`file_ore.DEFAULT_PAGE` is 30 and is a guess.** `git_ore.DEFAULT_PAGE` is 50
  and was measured. The first live `--walk --source doc` is what turns 30 into a
  number; the truncation guard is what makes a wrong guess loud rather than
  silent.
- **006 is not applied and nothing reads it.** `leads.yaml` is still the ledger,
  with the 17 leads window 2 filed. `./database/ai_agent_platform/apply-006-scout-lead.sh --check`
  touches nothing and says so.
- **`SCOUT_PAUSED=1` is still live** at `.env` line 31, and resuming the timer
  is still the operator's call.
- The Wire Editor's live pass is still unrun; its artifact is still in
  `state/archive/wire-dry-20260906-2339.out`. $0.35 puts it in the usual place.

## What the read-through found

Four disagreements. Three were the code's:

1. The synthesis user turn told the model its jewels are transcript seqs. A6
   (`9e36a50`) removed that claim from the system prompt, `a861925` reverted it,
   `cd64959` restored it — and all three worked the prompt constant while the
   same sentence sat in the turn built beside it.
2. `triage()` carried two copies of the truncation guard, one per source, with
   the transcript path returning early. That is the shape of the `a861925` miss.
   One guard after the branch now, pinned by `tests/test_scout_triage_dispatch.py`.
3. `jewels.py` still called itself "write-side only" with `select()` underneath
   it, and `run.py` called a dry run "fully read-only" when it writes the run row
   and every call's cost to the spine.

One was the spec's: "a cost ceiling on every verb" is false — `--synthesize` has
none and could not have the one described, because the ceiling is checked
between pages and a synthesis is one call. `spec-scout.md` now says walking leg,
in both places it made the claim.

**One hole named and deliberately left.** On `stop_reason=refusal` the synthesis
returns the fallback call's usage alone, so the roam that preceded it is billed
to nobody. Never seen live. The honest fix is two spine rows, which is a build;
it is recorded at the top of `run.py`.

## Open, and none of it is window 4's to decide alone

1. **The two repo lists still disagree** (`SCOUT_GIT_REPOS` five, roam roots
   three). Carried from windows 1 and 2. The file reader took a side for its own
   ore — `read_units` refuses a path outside the three roam roots — which
   narrows the question rather than settling it: git ore may still be mined from
   two repos the roam cannot open.
2. **`stance` is still overloaded** — GLOSSARY's sense versus
   `wire_editor_agent.py`'s `agree|differ`. Carried from window 1. `file_ore`
   now uses the GLOSSARY sense in code (`STANCES`), so the collision is live in
   two modules.
3. **`docs/uzelhub-crew/sysadmin-ledger.md` is still dirty** with the unresolved
   redaction finding at line 46, untouched by three windows. It blocks any commit
   that includes it. Note that it is now also mineable ore.
4. **The Wire Editor's fold form still drifts from its spec** (`hold, folded
   into <id>` versus "folded into the retool story").
5. **The banked draft still trips `redaction.scan` three times.** Gitignored,
   stamped `UNSCRUBBED`. The scrub is the operator's, permanently.

## What window 4 could do

The plan's checklist is complete, so this is a list and not a runbook:

- **The cutover** (the larger half of step 8): a store module, the 17 call sites
  moved off `leads.yaml`, the 17 live leads carried across, and the Scout
  connecting under its own DSN as `scout_role`. Apply 006 first with its script.
  A grant the process never connects under enforces nothing.
- **The first doc walk.** `--walk --source doc --path docs/uzelhub-crew` at
  `--pages 1` is one Haiku page: it measures the page size, produces the first
  non-transcript, non-git jewels, and is the only way to learn whether a doc
  section yields jewels the way a commit does.
- **The surveying-line experiment**, single variable, both arms `--dry-run`.
- **The Wire Editor's live pass**, $0.35, if the artifact is wanted in its usual
  home.
