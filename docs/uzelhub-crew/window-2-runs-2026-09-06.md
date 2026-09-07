---
read: full
status: run record for window 2 of plan-2026-09-07-unify-and-reset, 2026-09-06. Steps 4, 5 and 6 are done. Measurements, not conclusions — every number is from one run unless it says otherwise.
---

# Window 2 — the reset, the box index, and the cycle that ran

<!-- MAP:START -->
- [Step 4 — the reset](#step-4--the-reset)
- [Step 5 — the box index, measured](#step-5--the-box-index-measured)
  - [Two things seen while measuring, neither fixed](#two-things-seen-while-measuring-neither-fixed)
- [Step 6 — the pass, in ADR-002's run-record shape](#step-6--the-pass-in-adr-002s-run-record-shape)
  - [The box index, measured again where it counts](#the-box-index-measured-again-where-it-counts)
  - [The Wire Editor, first run since 2026-08-03](#the-wire-editor-first-run-since-2026-08-03)
  - [The Writer, first run since 2026-07-31](#the-writer-first-run-since-2026-07-31)
- [Step 6 acceptance, all six](#step-6-acceptance-all-six)
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

## Step 6 — the pass, in ADR-002's run-record shape

The sandbox refuses the `SCOUT_PAUSED=` override the plan's command needs — it
is the switch that gates the daily timer, and an agent does not get to unset
it. The operator ran the command by hand at 03:35 UTC. The pause itself was
verified live first: the same command without the override idles and exits 0.

| | one pass, 2026-09-07 03:35 UTC |
|---|---|
| rows walked | 150 (one page, seq 431101–447871) |
| jewels found | 31 |
| jewels persisted | 30 |
| dropped by `resolve_anchor` | 1 (bad or off-page seq) |
| scratchpad notes | 10 |
| map notes written | 8 entries, 1,330 bytes |
| leads filed | **17** |
| walk cost | $0.0328 |
| synthesis cost | $0.2693 |
| **total cost** | **$0.3022** |
| wall time | 3 min 8 s |
| **how it terminated** | **`end_turn`, 5 roam iterations, no fallback, no truncation** |

Persisted equals found minus dropped (30 = 31 − 1), which is the acceptance
this shape exists to make answerable. `scout_jewel` went 2,630 → 2,660.

**The cursor changed shape, not just value.** It was `{"seq": 418876}` and is
now `{"forward": 447871, "backfill": 0}` — the two-cursor model `spec-scout.md`
§The walk describes, written on the first real pass since. The window 1 handoff
recorded the single-key form as the untouched baseline, so the next reader
should not take the new shape for damage.

**Every lead carries a `type:` from the five words**, none carries `register:`,
all 17 are `new`. Spread: note 7, ticker 5, blog 2, paper 2, newsletter 1 — all
five types, filed by a Scout that was told what the types are and never told
which to want.

### The box index, measured again where it counts

The step 5 A/B moved one exploratory read. This pass, over different ore and
without a controlled twin, is the stronger evidence:

| | before arm (step 5) | this pass |
|---|---|---|
| exploratory `read_file` / `grep` | 0 attempted | **2 attempted, 2 landed** |
| leads citing a file | 0 of 11 | **10 of 17** |

Both reads went to `docs/uzelhub-crew/` — `scout-mining-economics.md` and
`scout-retool.md` — paths taken off the index rather than guessed. Ten of the
seventeen leads then cite a file. Against 8 of 8 failures on 2026-09-06 and
zero attempts in the before arm, the capability now works; how much it improves
the leads is a separate question nobody has measured.

**One lead is the Scout pitching this exact gap.**
`2026-09-06-roams-four-swings-four-misses` reports that the roam had never once
succeeded outside transcript rows, and names this pass's own index as the
structural response. It mined the failure it was in the middle of having fixed.

### The Wire Editor, first run since 2026-08-03

17 leads in, 17 proposals out, one per new lead. **10 claims, 7 holds, 0
spikes.** The chief shadow agreed on all 17 (`chief_differs: 0`). Cost $0.3488
($0.2980 triage, $0.0508 shadow). Artifact:
`state/archive/wire-dry-20260906-2339.out`.

**The operator-rejected clustering rule is confirmed dead in behaviour, not
just in the prompt.** Two clusters formed — the mining-economics self-audit
(6 angles) and the 2026-09-05 validation sweep (3 angles) — and every folded
angle came back as a **hold**, not a spike. Before 2026-09-05 this desk turned
124 of 127 spikes into exactly this situation. The zero is the whole point.

**One drift from spec-wire-editor.md, small and real.** The spec's fold form is
`hold, folded into <id>`. The reasons say "folded into the retool story" —
naming the story, not the id. The fold target is still recoverable from the
`clusters:` block, so nothing is lost, but the record does not carry it where
the spec says it should. Not fixed here: changing the prompt mid-cycle would
have made this run unreproducible.

**The live pass was not re-run, deliberately.** `--dry-run` already recorded
both calls on the spine (`wire_triage`, `chief_shadow`); the only thing a live
pass adds is the same artifact persisted under `wire_editor/state/proposals/`
instead of the archive. Paying $0.35 a second time for byte-identical output,
to satisfy a command list rather than an acceptance, is the waste this estate
keeps writing down. The cycle's $1 acceptance is the constraint that decided
it. **If the operator wants the artifact in its usual home, one live pass puts
it there.**

### The Writer, first run since 2026-07-31

One claim applied by hand, one draft banked. The claimed lead was
`2026-09-06-roams-four-swings-four-misses` — the Scout's own report that its
roam had never worked.

| | |
|---|---|
| cost | $0.2112 |
| roam calls | 4, **all landed** (`read_transcript`, `grep`, two `read_file`) |
| body | **846 characters** (contract 798–882, target 840) |
| beats | 3 — What happened / One line of the prompt / What shipped |
| title, tagline, metaDescription | all present |
| table | none |
| `deepDive` | absent, correctly — no deep dive exists |
| lead status | `claimed` → **`drafted`**, stamped by the pipeline |

**The claim was applied with `--agent`, and the plan's command list omits it.**
`lead_mark.py:35` requires it of any agent wearing the editor's hat, because on
2026-08-03 concordance was found scoring 6/6 against leads an agent had claimed
`--by editor`: a machine agreeing with a machine. The plan's line assumed the
operator's hand. **Concordance still has never been humanly exercised**, and
this run did not change that — it deliberately kept itself out of the metric.

**The Writer read this document.** Its roam opened
`window-2-runs-2026-09-06.md`, written earlier in the same session, and cited
it. That is the convergent roam working exactly as specified, and it is also a
short circuit worth naming: the draft's receipts include this file's account of
the very measurement it describes, rather than the run logs underneath. Nothing
in the draft is wrong; the provenance is one hop shallower than it looks.

**Gate ② has something real to catch here.** The draft trips
`redaction.scan` three times on the home-path rule — the same finding class
that has blocked `sysadmin-ledger.md` for two windows. The string is not
repeated here: writing it down to document it is how a leak moves from a
gitignored draft into tracked prose, and this file was blocked once for
exactly that before the sentence was rewritten. Nothing leaked — the draft is
gitignored and carries the pipeline's `UNSCRUBBED` stamp. It is the first live
demonstration that the scrub before gate ② is not ceremonial.

## Step 6 acceptance, all six

| acceptance | result |
|---|---|
| jewels persisted = found − dropped | 30 = 31 − 1 |
| `map.md` non-empty | 8 entries, 1,330 bytes, navigation only |
| every lead carries one of the five types | 17 of 17, none carrying `register:` |
| wire artifact: one proposal per new lead, arc/angles form | 17 of 17; 0 spikes, 7 holds folded |
| Writer banks a draft, lead reads `drafted` | both |
| whole cycle under $1 | **$0.8622** |

The budget held **because** the Wire Editor's live pass was skipped. Run it and
the cycle is $1.21. That is the trade, stated plainly: the plan's command list
and the plan's acceptance could not both be satisfied.


