---
read: full
status: window handoff, written 2026-09-06 at the end of window 2 of plan-2026-09-07-unify-and-reset. Steps 4, 5 and 6 are done. Facts only. Window 3 is steps 7 and 8 and starts from a fresh session.
---

# Handoff — window 2 (the reset and the run) is done

Everything below is committed and unpushed. Nothing here is the authority on
anything; it is a map to the documents that are.

<!-- MAP:START -->
- [Read first](#read-first)
- [What the commits did](#what-the-commits-did)
- [Facts window 3 needs](#facts-window-3-needs)
- [Costs, and the one acceptance that was missed](#costs-and-the-one-acceptance-that-was-missed)
- [Open, and none of it is window 3's to decide](#open-and-none-of-it-is-window-3s-to-decide)
- [What window 3 does](#what-window-3-does)
<!-- MAP:END -->

## Read first

`AGENTS.md`, `GLOSSARY.md`, the four `spec-*.md`, the plan, and
**`window-2-runs-2026-09-06.md`** — that last one holds every number this
window produced and is the authority on what the runs did. Not NEWSROOM, not
the ADRs, not the dated findings unless a step points at a section.

## What the commits did

| commit | step | what |
|---|---|---|
| `fc5e923` | — | the 09-05 handoff routes forward instead of only back |
| `ae98781` | 5 | the roam gets a map of the box (`box_index.py`) |
| `97be770` | 5 | spec-scout stops calling the map of the box open; run record opens |

Step 4 produced **no commit** and that is correct: `leads.yaml`,
`pitched.yaml`, `map.md` and `cursor.json` are all gitignored under
`.gitignore:44 state/`. Do not go looking for the commit that reset the ledger.

Tests: **295 pass**, up 6 from 289. The new file is `tests/test_box_index.py`.

## Facts window 3 needs

- **The cycle ran end to end and the ledger is live again.** 17 leads filed,
  1 claimed, 1 drafted. The rest are `new` and untriaged by any human.
- **The cursor changed shape.** `{"seq": 418876}` became
  `{"forward": 447871, "backfill": 0}` on the first real pass. The window 1
  handoff recorded the old single-key form as the baseline; the new shape is
  the two-cursor model in `spec-scout.md` §The walk, not damage.
- **`scout_jewel` is 2,660 rows** (was 2,630): +30 from one 150-row page.
  Verified by query.
- **`SCOUT_PAUSED=1` is still live** at `.env` line 31. The pass ran because
  the operator overrode it by hand for one shell. Resuming the timer is the
  plan's listed operator call, still open.
- **The Wire Editor's live pass was not run.** Its `--dry-run` recorded both
  calls on the spine and wrote the artifact to
  `state/archive/wire-dry-20260906-2339.out`, not to
  `wire_editor/state/proposals/`, whose newest file is still 2026-08-03. One
  live pass puts it in the usual place for $0.35.
- **The claim was applied with `--agent`.** `lead_mark.py:35` requires it of
  any agent wearing the editor's hat, and the plan's command list omits it
  because it assumed the operator's hand. A mark without it re-creates the
  2026-08-03 concordance poisoning. **The concordance metric still has never
  been humanly exercised.**

## Costs, and the one acceptance that was missed

| | |
|---|---|
| step 5 measurement, both arms | $0.5541 |
| the pass (walk $0.0328 + synthesis $0.2693) | $0.3022 |
| Wire Editor (triage $0.2980 + shadow $0.0508) | $0.3488 |
| Writer draft | $0.2112 |
| **cycle total** (pass + wire + writer) | **$0.8622 — under the $1 acceptance** |

**The acceptance held, and it held because one command was skipped.** The
plan's list runs the Wire Editor twice — `--dry-run`, then live — for
byte-identical output; the dry run had already recorded both calls on the
spine. Running it again would put the cycle at $1.21. The plan's command list
and the plan's own acceptance could not both be satisfied, and the acceptance
won. **The operator can reverse that for $0.35**, which is all it costs to put
the artifact under `wire_editor/state/proposals/` where the desk usually leaves
it.

Step 5's measurement ($0.5541) sits outside the cycle figure, as it should —
it bought a capability, not a cycle.

## Open, and none of it is window 3's to decide

1. **The two repo lists still disagree** (`SCOUT_GIT_REPOS` five, roam roots
   three). Carried over from window 1, untouched here, and the box index is
   built over the roam's three — so it now describes a *narrower* box than the
   ore does. Settle which list moves before the next walk.
2. **`stance` is still overloaded** — GLOSSARY's sense versus
   `wire_editor_agent.py`'s `agree|differ`. Carried over from window 1.
3. **`docs/uzelhub-crew/sysadmin-ledger.md` is still dirty** with the
   unresolved redaction finding at line 46. Untouched by both windows; it
   blocks any commit that includes it.
4. **The Wire Editor's fold form drifts from its spec.** The spec says
   `hold, folded into <id>`; the desk writes "folded into the retool story".
   Recoverable from the `clusters:` block, so nothing is lost — but the record
   does not carry the id where the spec says it should.
5. **The prompt still says "spend it pulling threads, not surveying"**, a few
   lines above the new box-index pointer. It is the most likely reason the
   before arm made zero exploratory attempts. **It is the next single-variable
   experiment**, and changing it alongside the index would have burnt this
   one.
6. **The banked draft trips `redaction.scan` three times**, on the home-path
   rule — the same finding class that has blocked `sysadmin-ledger.md` for two
   windows. (The gate names the string; repeating it here would only move the
   leak into a third tracked file.) The draft is gitignored and stamped
   `UNSCRUBBED`, so nothing leaked — but it is the first draft in this cycle
   gate ② has a real reason to stop, and the scrub is the operator's,
   permanently.

## What window 3 does

Steps 7 and 8 of the plan. Step 7 is the read-through: `pipelines/scout/run.py`
grew 469 lines under diagnosis pressure between 09-05 and 09-06, with one rule
reverted and restored. Read `run.py`, `jewels.py`, `walk.py` and
`agents/scout_agent.py` against `spec-scout.md` in one sitting, fix drift,
delete dead branches, **do not restructure**. Step 8 is the generic file reader
with pluggable splitters, then ADR-003's migration.

Note for step 7: `box_index.py` is new this window and is the one file in that
neighbourhood the read-through has never seen.
