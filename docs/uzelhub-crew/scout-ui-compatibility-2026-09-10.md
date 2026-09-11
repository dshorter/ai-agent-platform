---
read: full
status: COMPATIBILITY AUDIT — 2026-09-10. Read-only runtime inspection and isolated contract probes; no model calls, resumed prospecting, migrations or publication. Findings amend the proposed UI spec and working plan, not the running Scout.
---

# Paused Scout and proposed editorial UI — compatibility review

**Conclusion:** the proposed UI fits the Scout's intended place in the
newsroom, but it cannot be connected to the current implementation unchanged.
The September 9 specification checked editorial policy, current UI consumers
and storage direction; it had not completed this runtime compatibility trace.
This review supplies the missing pause/resumption and producer/consumer checks.

The [UI specification](spec-editorial-ui-mvp.md) owns the proposed requirements.
[NEWSROOM-WORKPLAN.md](NEWSROOM-WORKPLAN.md) owns task status and sequencing.
This dated audit records evidence, not another construction board.

<!-- MAP:START -->
- [What is paused and what still runs](#what-is-paused-and-what-still-runs)
- [What resumption would do](#what-resumption-would-do)
- [Compatibility findings](#compatibility-findings)
- [Required compatibility demonstrations](#required-compatibility-demonstrations)
<!-- MAP:END -->

## What is paused and what still runs

On September 10, `scout-pass.timer` was enabled, active and waiting. Its
05:45 service invocation first runs `--ingest`, then `--pass`. `SCOUT_PAUSED=1`
is present in the service's environment file, and today's journal contains
ingestion output followed by the expected paused-pass message. The service's
inactive/dead state after completion is normal for its oneshot configuration.

The pause check lives in
[the Scout CLI](/opt/ai-agent-platform/pipelines/scout/__main__.py:43):

- `--ingest` continues capturing logs while prospecting is paused.
- `--pass` returns before configuration, database connection or model setup
  when paused and invoked alone. An isolated entry-point probe verified this.
- Explicit `--walk` and `--synthesize` intentionally bypass the pause. They
  are paid operator actions, not suitable refresh implementations.
- The predicate is a nonempty environment value; setting the text `0` is not
  an unpause. The UI must not edit this setting as an approval side effect.
- The underlying `run_pass()` function has no equivalent pause guard. A new
  caller cannot assume that importing it preserves the CLI's protection.

The UI should report **Prospecting paused; ingestion active**, with ingestion
health separately observed. Stopping the timer to express this existing pause
would also stop its ingestion leg. That is a different operating action.

## What resumption would do

[The pass runner](/opt/ai-agent-platform/pipelines/scout/run.py:329) reads the
forward/backfill cursors, walks fresh transcript ore within the configured
plate, uses spare capacity for backfill, synthesizes over that walk's jewels,
and files leads. Git/doc/ledger walks remain separately invoked operations.
The timer/pass does not call the Wire Editor, Writer or review-page generators.

Current-state observations, not values to hard-code into acceptance tests:

| Item | Observed September 10 |
|---|---|
| Lead ledger | 17 leads: 16 new, 1 drafted |
| Dedup memory | 17 entries; the normal loader returns only ID and pitch |
| Cursors | Forward 447871; backfill 0 |
| Captured transcript rows | 15,604 total; 1,256 rows ahead of forward |
| Jewels | 2,660: 2,018 transcript and 642 git |
| 006 lead table | Not present in the configured database |
| Configured database role | Not `scout_role` |

Database checks used a read-only transaction. Cursor values are sequence
coordinates: backlog was counted by query, not inferred by subtracting them.
The current jewel total supersedes earlier counts only as a dated observation;
the audit did not mine or alter jewels.

UI deployment must preserve the existing ore, jewels, map, scratchpad,
forward/backfill positions, lead identities and dedup history. In particular,
queue cleanup cannot erase dedup memory, and migration cannot restart coverage
at zero. A completed Scout filing must become visible to the UI independently
of whether a subsequent Wire job succeeds.

## Compatibility findings

| Boundary | Finding and required treatment | Work-plan owner |
|---|---|---|
| Scout output → stored recommendation | The synthesis prompt emits type but no destinations. A synthetic destination list was discarded by `format_lead()` and absent after the normal reader loaded the result. Extend generation, validation, persistence and consumers together. Preserve missing legacy values; do not fabricate historical Scout recommendations. | NR-09 |
| Routing decision → Writer assignment | The Writer reads the ledger's single `type` directly. A UI-only override would not change its assignment. Add an effective assignment projection that selects the saved human type/route while retaining the immutable Scout proposal. | NR-09 |
| Legacy sources → new schema | Current production code emits/reads `sources`; 006 names its column `citations`. The store boundary must translate explicitly and preserve citation values and stable lead IDs for Wire, Writer, review, promotion and reconciliation. Applying SQL alone leaves those consumers on YAML. | NR-08, NR-09 |
| Review loop → lifecycle | Current `lead_mark` is forward-only, and 006 stamps have a `(lead_id, state)` primary key. Reopening review cannot mean repeatedly reversing status or reusing one approval stamp. Versioned approval/revocation events need separate identity and release enforcement. | NR-01, NR-08 |
| Correction request → Writer | The current Writer receives a lead, has no correction-request parameter and overwrites `<lead-id>.json` on redraft. Wire the instruction and draft revision into its assignment and preserve the previous artifact. Existing drafted-state redrafting alone does not implement the proposed correction flow. | NR-01 |
| Automatic drafting → cost boundary | `WRITER_MAX_COST_USD` is parsed into config, but the inspected Writer runner/agent path does not enforce it; it records cost after the call. Model output and roam limits are not that dollar cap. Before D-06 enables automatic jobs, implement and demonstrate the stated budget behavior, including any in-flight overshoot, and prevent duplicate paid attempts. | NR-01, NR-09 |
| Scout read access → editorial records | Normal dedup is status-blind, but direct calls through the Scout's actual default toolbox could read and grep status lines in the current ledger. The file index excluding `state/` does not prohibit access. The configured role also is not the planned restricted Scout role. Verify the firewall through every actual read path before relying on it for new decision records. | NR-02, NR-08 |
| Resumed filing → concurrent UI writes | Scout appends to the ledger; `lead_mark` reads and rewrites the whole file. No shared concurrency guard was found in those paths. A UI writer and newly resumed Scout must not lose each other's changes. Include concurrent filing and editorial decisions in storage/recovery verification. | NR-08, NR-09 |
| Scout filing → fresh Wire advice | No automatic Wire pass follows the current Scout pass. Treat fresh triage as a separately identified, bounded operation over filed lead revisions. Refresh can show leads without current advice; it cannot secretly run paid triage or rerun Scout mining to recover a missing proposal. | NR-09 |

The read-access result confirms an existing weakness already assigned to
NR-02; it is not evidence that the Scout has actually used operator verdicts.
No real editorial prose was exposed by the probes: their output reported only
field presence, access success and aggregate counts.

## Required compatibility demonstrations

Before claiming the upgraded flow is compatible, demonstrate in isolated state:

1. While prospecting is paused, review/refresh/routing actions leave Scout's
   pause, cursors, map, jewels and dedup unchanged; scheduled ingestion retains
   its existing role. Any database cutover outage needs a bounded capture and
   catch-up procedure instead of silently disabling ingestion indefinitely.
2. A newly filed lead travels through every consumer with its original type,
   destination recommendation, identity and citations intact. A human override
   reaches the Writer without changing the original proposal or dedup context.
3. A legacy lead without destinations remains actionable with explicit missing
   advice; any human-supplied route is attributed to the human.
4. A correction request reaches the Writer, preserves the prior draft, and
   yields a separately reviewable revision. Superseding approval blocks release
   of unreviewed content without rewinding lead history.
5. Simultaneous Scout filing and editorial decisions preserve both results.
   Migration moves all producer/consumer paths to one authoritative store;
   failures recover without split ledgers, lost IDs or dedup regression.
6. The actual Scout role and tools refuse editorial decisions and UI records,
   including alternate file/search/Git paths and archived/generated copies.
   Existing legitimate source access still works under the accepted D-01 policy.
7. The next bounded pass continues from the preserved cursor, and a failed Wire
   or UI refresh operation cannot replay mining or reset coverage. Actual
   resumption remains a separately recorded NR-07 operating decision.
8. Automatic drafting/redrafting honors the implemented job/call budget
   controls and reports cost honestly. Do not advertise the currently unused
   Writer config value as an enforced spending guarantee.

These are additions to the proposed acceptance baseline, not tests already
passed by the unbuilt UI. This audit ran only the paused CLI probe, synthetic
formatter/reader check, dedup-shape inspection, toolbox read/search checks,
service/journal inspection and read-only database queries. A live unpaused pass,
concurrent writes and migration rehearsal were not run.
