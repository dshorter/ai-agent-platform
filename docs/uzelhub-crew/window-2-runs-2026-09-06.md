---
read: full
status: run record for window 2 of plan-2026-09-07-unify-and-reset, 2026-09-06. Steps 4 and 5 are done and measured; step 6 is blocked on one operator permission and is recorded here unfinished. Measurements, not conclusions — every number is from one run unless it says otherwise.
---

# Window 2 — the reset, the box index, and the run that did not start

<!-- MAP:START -->
- [Step 4 — the reset](#step-4--the-reset)
- [Step 5 — the box index, measured](#step-5--the-box-index-measured)
  - [Two things seen while measuring, neither fixed](#two-things-seen-while-measuring-neither-fixed)
- [Step 6 — not run](#step-6--not-run)
<!-- MAP:END -->

## Step 4 — the reset

Archived, then reset. `scout_jewel` and both cursors untouched, as the plan
requires: the jewels were mined under the current triage prompts and re-mining
them was never the point of this window.

| | before | after |
|---|---|---|
| `leads.yaml` | 526 leads, all keyed `register:` | the header alone, byte-identical to `leads.HEADER` |
| `pitched.yaml` | 66 lines | header alone, 0 ids |
| `map.md` | empty | empty |
| `cursor.json` | `{"seq": 418876}` | unchanged |
| `scout_jewel` | 2,630 rows (1,988 transcript / 642 git) | 2,630 rows |

Archive copies carry the stamp `20260906-230801`. The 526 old leads were not
migrated to `type:`; if they are ever wanted live, one `sed` on the archived
copy re-keys them.

**This step produces no commit.** All four files are gitignored under
`.gitignore:44 state/`, which is the tracked-tree rule working as intended —
transcript-derived material never enters a public repo. Worth knowing before
the next window goes looking for the commit that reset the ledger.

## Step 5 — the box index, measured

The build: `pipelines/scout/box_index.py`, committed as `ae98781`, injected
into the synthesis context beside the map tail. 295 tests pass, up 6.

Both arms are `--synthesize --dry-run --limit 250` over the identical 250
jewels (the selection is deterministic and total: `ORDER BY session_date, seq
NULLS LAST, source_ref, id`). One variable moved — the index exists and the
prompt says so. Dry runs both, so neither arm's leads entered the other's dedup
memory.

| | before | after |
|---|---|---|
| leads | 11 | 11 |
| cost | $0.2493 | $0.3048 |
| wall time | 107 s | ~110 s |
| roam calls | 9 | 4 |
| exploratory `read_file` / `grep` | **0** | **1** |
| exploratory calls that failed | — (none attempted) | **0 of 1** |
| leads citing a file | **0 of 11** | **2 of 11** |
| types represented | 4 of 5 | **5 of 5** |
| stop reason | `end_turn`, 7 iterations | `end_turn`, 4 iterations |

**The one thing this measures cleanly.** The roam's exploratory reads were 8 of
8 failures on 2026-09-06 and 0 of 0 attempts in the before arm — it had stopped
trying. The after arm made one exploratory read, and it landed:
`predictor_ingest/docs/architecture/adr-008-batch-api-extraction.md`, off a
path read from the index. That file then became a citation on the
`batch-api-killed-the-cheap-model-bet` lead. File citations went 0 → 2.

**What it does not measure.** One run per arm. Lead count did not move (11 and
11, which matches the known homeostasis at about 10 to 13 regardless of input),
and nothing here says the leads are better — only that two of them now rest on
a file the model actually opened. The type spread widening to all five,
including the first `newsletter`, is one run's worth of evidence and no more.

**Cost.** The index adds about 32,000 characters to the context. It is inside
the cached system prefix after the first turn, and the arm cost 22 percent more
($0.055). That is the price of the capability, and it is worth naming rather
than rounding away.

### Two things seen while measuring, neither fixed

**1. The prompt still tells the roam not to survey.** `Your tool budget is
small; spend it pulling threads, not surveying` sits a few lines above the new
index pointer. That line is the most likely reason the before arm made zero
exploratory attempts, and it now pulls against the index. It was left alone on
purpose: changing it in the same run as the index would have put two variables
in one A/B, which is the confound ADR-002 §6b exists to prevent. **It is the
next single-variable experiment**, not a bug.

**2. The model invented a tool called `none`.** The after arm's roam trace ends
`none() !err` — a `tool_use` block naming a tool that does not exist, rejected
by the toolbox, costing one of six roam iterations. It happened inside the roam
loop, not on the forced-pitch turn. Harmless once, worth watching: if it
recurs, the roam is spending its budget announcing that it is finished instead
of finishing.

**The empty forced pitch did not recur.** Both arms ended `end_turn` with
output, and `state/empty-calls/` is still empty. That failure remains open and
intermittent; two clean runs are not a fix and are not evidence of one.

## Step 6 — not run

**Blocked on one permission, not on a decision.** The plan's command overrides
the operator pause for a single shell:

    SCOUT_PAUSED= .venv/bin/python -m pipelines.scout --pass

The sandbox refuses the `SCOUT_PAUSED=` override. Verified that the pause
itself is live and working: the same command without the override idles and
exits 0, exactly as `pipelines/scout/__main__.py` specifies.

**No substitute was run.** `--walk` plus `--synthesize` are operator verbs and
are ungated, so they would have executed — but they are not the same thing.
`--walk` moves no cursor, and a standalone `--synthesize` selects from stored
jewels rather than from that walk's. Running them would have produced an
artifact that looked like step 6 while quietly skipping the cursor advance,
which is the half the step is named for. That is the substitution AGENTS.md
calls a boundary crossed by a locally-efficient fix.

What step 6 still owes, unchanged: one pass recorded in ADR-002's run-record
shape (rows walked, jewels found and persisted, dropped anchors, map notes,
leads filed, cost, wall time, how it terminated), then one Wire Editor pass,
one claim applied by hand, and one Writer draft.
