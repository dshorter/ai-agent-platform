---
read: full
status: WORKING PLAN — revision 0.6, 2026-09-10; entry routes verified and replaced roadmaps explicitly marked superseded. UI spec remains revision 0.2. The operator decisions marked settled below remain settled; construction sequence and acceptance are proposed. No construction item has started under this plan.
---

# NEWSROOM — working construction plan

This is the current entry point for the next construction leg. Update its
current state in place, as the operator requested. Preserve changes to scope,
order, decisions and completion criteria in the dated change record below.
The [September 9 merge](plan-2026-09-09-next-leg.md) explains the reasoning;
the [September 8 critique](newsroom-design-critique-2026-09-08.md) remains verbatim.
Neither historical document is a competing task board.

The [documentation index](README.md#newsroom-start-here) catalogs this leg's
plan, proposed specification, audits and history, with each document's role.

The proposed [editorial UI MVP specification](spec-editorial-ui-mvp.md)
defines screen behavior, durable decisions and acceptance scenarios for the
existing NR tasks. It has no separate task/status board.

<!-- MAP:START -->
- [At a glance](#at-a-glance)
- [Goal and fixed constraints](#goal-and-fixed-constraints)
- [Decisions](#decisions)
- [Task board](#task-board)
- [UI readiness — inspected 2026-09-09](#ui-readiness--inspected-2026-09-09)
- [Proposed order](#proposed-order)
- [Scout compatibility — reviewed 2026-09-10](#scout-compatibility--reviewed-2026-09-10)
- [What counts as done](#what-counts-as-done)
- [Make departures visible](#make-departures-visible)
- [Change record](#change-record)
- [Parking lot and implementation gaps](#parking-lot-and-implementation-gaps)
- [Current handoff](#current-handoff)
<!-- MAP:END -->

## At a glance

| Field | Current value |
|---|---|
| Plan revision / baseline | 0.6 / not finalized |
| Current task | **NR-00 — finalize the working plan** |
| Current activity | Documentation routes verified and superseded planning documents labeled with their replacement; UI spec revision 0.2 and compatibility evidence remain ready for review |
| Construction started | None |
| Next action | Resolve D-04/05/06 interaction choices and D-07 storage sequencing; review the specification and finalize the baseline. D-01 still blocks dependent source changes |
| Unrecorded departures | None identified during plan preparation |
| Next operating action | None selected; NR-07 records publication, timer and push decisions separately |

## Goal and fixed constraints

Regular content on the operator's website, DEV, and a third destination
(provisionally Hashnode), with writing close to the operator's own and roughly
90% less personal effort. Both editorial gates remain human. Start live
publishing at acceptable MVP quality, then improve subsequent pieces and the
effort required. Reaching 90% is measured over real operation; it is not a
condition that must already hold for the first release.

**Type and destination are independent.** The rule lives in
[spec-content-types.md](spec-content-types.md#content-type-and-destination).
The Scout recommends; the operator can override at gate one. The platform's
current adapter coverage must not quietly become the editorial policy.

A piece need not acquire a companion of another type to be syndicated.
Unsupported creation or delivery capabilities are explicit gaps. Adding every
unbuilt content type is not implied by the first publishing MVP.

## Decisions

| ID | State | Decision / unresolved question | Where it matters |
|---|---|---|---|
| D-00 | SETTLED — operator, 2026-09-09 | Content type does not determine syndication destinations. Retain the Scout's recommendations, subject to human override. | NR-09; all future routing changes |
| D-01 | OPEN | Resolve mining/read repository access and the handling of already retained material whose references the roam cannot open. The old suggestion to narrow mining has not been accepted as policy. | NR-02; any affected new mining |
| D-02 | SETTLED — operator, 2026-09-09 | Use the Scout's destination recommendation as the proposed set. The operator may accept or change it at gate one. Do not substitute an all-platform default or require selection from scratch. | NR-09 and NR-05 |
| D-03 | OPEN | Confirm the third enabled destination and its usable publishing access; Hashnode is provisional. | Final third-destination delivery acceptance, not the independence rule |
| D-04 | OPEN | Whether gate-two approval schedules release or leaves a separate execution action. Both must use the same approved content; no third editorial gate. | NR-09 release interaction; NR-07 publication |
| D-05 | OPEN — operator asked | Save decisions directly through a protected UI service, or retain copy-and-run for MVP. Direct saving is recommended for the effort goal; it changes the current read-only service boundary. | NR-01/09 interaction and access design |
| D-06 | OPEN — operator asked | Whether gate-one claim starts bounded drafting automatically or waits for an explicit execution action. No additional editorial gate is introduced. | NR-09 orchestration; NR-05 rehearsal |
| D-07 | OPEN — proposed dependency | After designing the new record contracts, move NR-08 ahead of durable UI decisions, or agree an explicit bounded persistence alternative. ADR-003's Postgres direction remains settled; a new flat-file ledger must not appear by default. | NR-01/09 state-changing implementation; NR-08 scheduling |

Finalizing a plan with an open decision is possible if its affected work stays
explicitly blocked. An unknown must not be replaced with an assumption merely
to turn a status green.

## Task board

NR-01 through NR-08 preserve the original follow-up's item numbers. NR-09
reconnects its publishing roadmap; NR-10 measures the stated outcome. IDs are
stable references, not execution order. Status is maintained only in this table.

| ID | Work / owner | Status | Depends on | Completion evidence |
|---|---|---|---|---|
| NR-00 | Finalize this plan / operator + assistant | ACTIVE | Review of this document | Working draft, UI audit, paused-Scout compatibility audit and proposed UI spec revision 0.2; finalized baseline still pending |
| NR-01 | Banked-draft review, approval enforcement and lifecycle consistency / assistant builds, operator approves copy | QUEUED | Finalized plan; D-05/07 before dependent mutations | — |
| NR-02 | Source policy and consistent role/tool access / operator decides, assistant builds | BLOCKED | D-01; finalized plan | — |
| NR-03 | Resolve the dirty ledger finding / operator owns wording decision | READY | Finalized plan | — |
| NR-04 | Shadow vocabulary and explicit fold target IDs / assistant | READY | Finalized plan | — |
| NR-05 | Human-selected drafting/review rehearsal / operator + assistant | QUEUED | NR-01, NR-02, NR-04, NR-09 | — |
| NR-06 | First document page and matched surveying experiment / assistant | PARKED | Source policy for the tested input; agreed bounded run scope | — |
| NR-07 | Publication, timer resumption and source-code push decisions / operator | QUEUED | Separate conditions below; never one combined approval | — |
| NR-08 | Complete the 006 Postgres cutover / assistant builds, operator owns live cutover decision | PARKED | ADR-003; design NR-01/09 record contracts before migration; D-07 may move its place | — |
| NR-09 | Scout recommendations, independent destination routing and complete delivery / assistant builds, operator ratifies route | QUEUED | Finalized plan; D-03 for third destination; D-04/05/06 for interaction; D-07 before dependent mutations | — |
| NR-10 | Measure recurring effort and refine approved writing / operator + assistant | QUEUED | First authorized real release; comparable manual baseline for percentage claims | — |

READY means the task is defined and has no unresolved task-specific decision;
the finalized-plan prerequisite still applies. QUEUED waits on predecessors or
its place in the sequence. BLOCKED must name the missing decision or evidence.
PARKED is deliberately outside the immediate sequence. ACTIVE names the current
work. DONE requires the evidence below. A task may be partially built without
being DONE; describe the partial result in its evidence cell.

## UI readiness — inspected 2026-09-09

The current tools support reading and collecting verdicts, but do not yet
support the agreed workflow. This assessment inspected generator code and
the generated files referenced by the ops desk, and exercised parsing and
rendering in memory. It did not exercise a live browser or the HTTP endpoint,
regenerate the served pages, or apply any editorial decisions.

| Surface | What exists | Gap relevant to this leg |
|---|---|---|
| Gate one, `tools/wire_review.py` | Pitch, Wire/chief advice, claim/spike buttons; untouched cards remain holds | No type selector, destination recommendations or destination override. The displayed type comes from the Wire proposal. Clicks store browser-local choices and emit commands; they do not persist operator decisions to the ledger. |
| Gate two, `tools/draft_review.py` | Note-shaped copy, metadata, source references, scan findings, approve/reject choices and projected dates | No editing/correction workflow, per-destination preview or reviewed-version binding for browser selections. The generator claims promotion supports `--redact` and refuses without it; `promote_draft.py` has neither that option nor the claimed enforcement. |
| Publication queue | Local notes with live/queued status and projected dates | No per-destination delivery results, URLs, failures or retry state. Projected dates are arithmetic, not a persisted delivery schedule. |
| State freshness | Generated snapshots reachable through ops-desk links | Routing snapshot last modified August 19; draft and queue snapshots August 11. The September draft is absent. The normal proposal directory ends on August 3; all 257 merged proposal IDs are absent from the current 17-lead ledger. Regeneration alone would produce obsolete cards, not the current shortlist. |

Both decision surfaces deliberately hand back commands for the operator to
run. Their `localStorage` selections are not server-side approvals. Draft
choices are keyed by slug rather than content version, so the browser can
carry a prior selection into a changed draft with the same slug. The generated
commands also leave drafting, release, reconciliation and page refresh as
separate operations. These are material parts of the operator's effort.

**Proposed acceptance additions, before NR-05:**

- **NR-09, gate one:** show the Scout's original type/destination proposal,
  distinct Wire advice and the operator's chosen values; permit both overrides.
  Make a browser selection visibly different from a successfully persisted
  decision. Surface a failed or stale apply instead of implying success.
- **NR-01, gate two:** invalidate a prior selection when the reviewed content
  changes; show the actual revision and scan/review state; provide a clear
  correction/redraft path; remove promises the promotion implementation cannot
  enforce. Review the required destination presentations within the same gate.
- **NR-09, delivery and freshness:** show each selected destination's outcome;
  identify snapshot/input freshness; do not present obsolete or missing
  proposals as the current queue. Connect the recent run artifact deliberately
  rather than repeating a paid model run merely to obtain another filename.
- **NR-05:** exercise the actual operator surfaces, including persistence,
  refresh, failures and recovery. Command-line success alone does not establish
  readiness of the two-approval UI.

How decisions are applied remains a bounded design choice under NR-09. The
existing read-only, copy-and-run contract is explicit; changing it to direct
UI writes requires a concrete access/attribution design. This audit does not
silently make the capability-protected static desk a write-capable service.

**Specification prepared, 2026-09-09:**
[spec-editorial-ui-mvp.md](spec-editorial-ui-mvp.md), revision 0.1, turns these
findings into proposed screen, record, refresh, access and recovery contracts.
Its acceptance table allocates each demonstration to the NR task that owns it.
The archived September Wire output was also inspected: its proposal section
contains all 17 current lead IDs and is followed by a JSON dry-run summary.
Import must preserve provenance and validate input compatibility; an ID match
does not justify inventing historical Scout destination recommendations.

The record design exposes a possible sequencing change: ADR-003 already rejects
an elaborate new file-based store, while the current ledger lacks independent
route decisions and versioned approvals. D-07 proposes moving NR-08 after
contract design and before durable UI decisions. **NR-08 remains PARKED until
that order change is accepted and recorded.** This is a reason to evaluate the
dependency, not a claim that a full migration is automatically an MVP gate.

## Proposed order

1. **Finalize NR-00.** Keep D-00 and D-02 settled. Record the accepted baseline
   revision and sequence. Resolve D-01 before dependent source changes.
2. **NR-03 and NR-04: bounded cleanup.** Each can be completed independently.
3. **NR-02 and NR-01: dependable access, evidence and approval.** Work on the
   unblocked task if D-01 is still open. Design the approval/routing records
   before choosing their implementation sequence under D-07. State which is active.
4. **NR-09: independent recommendations and delivery.** Build against the
   actual type/destination contract, including the gaps in current storage and
   adapters. Formatting limitations cannot silently select destinations.
5. **NR-05, then the publication part of NR-07.** Exercise both human gates
   and demonstrate the route; begin live publication when the operator finds
   the copy acceptable and delivery is dependable.
6. **NR-10: operate and refine.** Account for all recurring operator effort.
   Improvements to writing can continue on newly produced content.

NR-06 and NR-08 retain their scope and can be scheduled when their value or a
demonstrated dependency justifies it. Moving either earlier requires a recorded
order change, naming what it unblocks. Timer resumption and source-code pushing
remain independent NR-07 decisions; neither is synonymous with content release.

## Scout compatibility — reviewed 2026-09-10

The [compatibility audit](scout-ui-compatibility-2026-09-10.md) checked service
configuration and today's journal, the paused CLI path, live state through
read-only queries, producer/consumer formats and the Scout's actual toolbox.
The UI design fits the intended flow but is not compatible without the specified
integration work. UI spec revision 0.2 adds explicit requirements for pause and
ingestion separation, preserved Scout-owned state, recommendations through all
consumers, effective Writer assignments, versioned reapproval and concurrent
filing/decisions. These remain inside NR-01/02/08/09 and are rehearsed in NR-05.

The timer is enabled and continues ingestion; `SCOUT_PAUSED=1` gates the
prospecting pass. **“Timer resumption” in the earlier rows means resuming
prospecting under NR-07, not enabling a stopped timer.** Neither deploying the
UI nor approving a story may change that pause. A cutover must account for
continuing ingestion, preserved coverage and dedup, and every consumer;
applying 006 alone is insufficient. No order change under D-07 has been accepted.

## What counts as done

| ID | Required result |
|---|---|
| NR-00 | Operator accepts the sequence and completion criteria. Record revision 1.0, date, accepted order, and any explicitly open decisions with their blockers. Do not claim finalization from silence. |
| NR-01 | Operator resolves scrub and substantive-copy concerns. The draft preserves the source's uncertainty. Promotion recognizes approval of the actual reviewed version, refuses unresolved review, and exposes/recoverably handles a partial queue/status update. Evidence includes refusal and successful approved-path checks. An automated scan never stands in for human judgment. |
| NR-02 | Record the chosen source policy. Verify it through reading, search, Git arguments and the real database role where used. Address alternate access to editorial dispositions and the handling of inaccessible references. State any residual limitation; restricting whole sources or deleting stored evidence requires the corresponding decision. |
| NR-03 | The operator's intended ledger wording survives, the flagged material is resolved without broadening a dismissal, and the scoped redaction check passes. |
| NR-04 | The shadow uses the unambiguous vocabulary; a fold names the correct target lead ID. Relevant consumers agree. Chronology/input-quality limitations are recorded separately, not declared solved by the rename. |
| NR-05 | Actual operator selection/override at gate one, supported Writer output, and operator scrub/approval at gate two. Preserve Scout proposals separately from final choices and retain actual human/agent attribution. Exercise delivery preparation and recovery; include hands-on minutes. The existing agent-selected draft cannot be retrospectively labeled a two-human-gate cycle. |
| NR-06 | Keep the two experiments separate. Record inputs, prompt version, cost, termination, source/date limits and useful findings. The surveying comparison uses matched inputs and a current baseline. Do not turn file-modification dates or additional citations into proof of chronology or causal improvement. |
| NR-07 | Record each operating decision and its result separately below. Partial decisions stay partial; no automatic timer or push action follows a content approval. |
| NR-08 | Existing IDs, citations, types and attribution survive; every consumer uses the store; the running Scout uses its restricted credentials; verify and recovery procedures pass. Coordinate independent recommendation/override and approval records. A database transaction alone does not make site files or remote publication atomic. |
| NR-09 | Store and display the Scout's distinct type and destination recommendations; preserve human overrides. Carry approved content and its canonical identity to selected destinations with per-destination outcomes and safe retries. Evidence must show the same destination can receive different supported types and the same type can reach different destinations without type conversion. Show delivery gaps explicitly; do not mark an unsupported destination delivered or silently remove it. |
| NR-10 | At the operator-agreed review point, record actual releases, edits, selection/review/distribution/recovery minutes and comparison with the manual baseline. State whether the 90% objective was met, missed or still lacks sufficient evidence. The observation window is agreed when this work starts, not invented after seeing the result. |

At finalization, explicitly accept or revise the UI specification's
[acceptance scenarios](spec-editorial-ui-mvp.md#acceptance-scenarios-and-work-plan-ownership).
They supply the concrete UI evidence for NR-01/09 and the actual-surface
rehearsal for NR-05; they do not silently mark those tasks started or complete.

For NR-07, keep three separate entries when decisions occur:

| Action | Current decision | Evidence needed for the decision |
|---|---|---|
| First live content release | Not requested under this working plan | NR-05; approved version and selected destinations; usable release/recovery path |
| Resume the Scout timer | Not requested under this working plan | Source/access readiness, bounded operation and a reason to replenish leads |
| Push source-code commits | Not requested under this working plan | The actual changes being published and their applicable checks |

## Make departures visible

Before substantive work, name the active NR ID and its intended result. Keep
one ACTIVE construction item unless a recorded dependency explains overlapping
work. This governs this construction leg, not the estate's unrelated activity.

Before switching tasks, update the board: result or blocker, evidence, and the
next action. A newly discovered idea belongs in the parking lot unless it is
necessary to finish the active task. Necessary additional work gets an ID or
an explicit addition to that task's acceptance, with the reason recorded.

After finalization, changes to task scope, order, dependencies, completion
criteria or settled decisions require a change-record entry **before** the
changed work proceeds. Record old → new, why, impact and the decision's basis.
Routine implementation choices within an accepted task do not require another
approval. Changes to operator-owned boundaries go back to the operator.

Do not lower completion criteria after a failed check, report dry-run outcomes
as live results, mark partially wired behavior DONE, or let a documentation
claim replace evidence. A blocker is a legitimate status. A task removed from
scope must remain visible with its disposition and reason.

Each session closes with five facts here or in a linked handoff: active ID and
status, what changed, evidence, outstanding decisions/departures, and the exact
next action. Handoffs point back to this board; they do not create a second
current task list.

## Change record

| Revision / date | Change and basis | Impact |
|---|---|---|
| 0.1 / 2026-09-09 | Created at the operator's request. Corrected the review's proposed type-versus-destination choice. Operator settled independent type/destination recommendations and human override of the Scout's proposal. | NR-00 active; original eight items retained; NR-09/10 added from the existing roadmap and outcome goal. Construction order remains proposed. |
| 0.2 / 2026-09-09 | Operator asked whether current UI tools support the flow. Code/generated-file audit found missing overrides, browser-only selections, stale inputs, incorrect scrub instructions and no per-destination delivery state. | Proposed UI acceptance added to NR-01/09 and actual-surface validation to NR-05. NR-00 remains active; no UI construction or decision-application mechanism has been selected. |
| 0.3 / 2026-09-09 | Operator requested an MVP UI upgrade specification. Added spec revision 0.1 with independent routing controls, versioned review/correction, current inputs, durable outcomes and recovery demonstrations. Asked D-05/06 and the existing D-04; recorded D-07 after checking ADR-003. | Proposed UI work remains inside NR-01/09, validated through NR-05. NR-08's earlier placement is a proposal, not an applied order change. NR-00 remains the only active task; no runtime changes. |
| 0.4 / 2026-09-10 | Operator asked whether the proposed UI fits the paused Scout. Completed the runtime/contract audit and added explicit compatibility demonstrations in UI spec revision 0.2. Clarified that the enabled timer still ingests while the pass is paused. | Existing NR tasks gain concrete producer/consumer, pause-preservation, reapproval and concurrency evidence requirements. NR-00 alone remains active; D-07 remains open; no models, resumed prospecting, migration or publication. |
| 0.5 / 2026-09-10 | Operator requested discovery paths for the new documents. Added a current NEWSROOM catalog to the crew README and links from the host README, repository README, shared AGENTS/CLAUDE router and historical design/merge entry points. | Navigation and document roles clarified; no task scope, order, decision or acceptance change. The verbatim critique remains unchanged. |
| 0.6 / 2026-09-10 | Operator clarified that replaced documents may be marked superseded. Labeled the July publishing roadmap and September 9 merge as superseded work plans, and the September 7 runbook as a completed leg superseded for new work. Each points here; historical bodies remain. | Removes competing “active”/“next session” directions without changing the current task order, acceptance or open decisions. |

At finalization, add the immutable baseline row with accepted order and criteria
reference. Preserve subsequent changes here while updating current-state
sections in place. This document provides visible control and history; it does
not claim a software enforcement mechanism has been installed.

## Parking lot and implementation gaps

| Item | Disposition / next review |
|---|---|
| Current Scout/lead output has a type but no explicit destination-recommendation field in the paths inspected | Included in NR-09; policy settled, wiring pending |
| Existing note kits and blog-only DEV adapter impose different input paths | Included in NR-09; implementation gap, not a destination rule |
| Other unbuilt content types and delivery features | Record capability coverage in NR-09; no implicit requirement to build every creation pipeline for first MVP |
| Full historical chronology and versioned document references | NR-06 records limitations; NR-01/05 must establish the evidence of the selected piece |
| Richer dashboards or further source readers | Parked until a measured operating need earns a scoped task |

## Current handoff

NR-00 is the only active item. The working document, policy clarification and
UI-readiness assessment now have a proposed UI MVP specification, revision 0.2,
and the September 10 paused-Scout compatibility audit.
These are discoverable through the crew index, host/repository README routes
and the shared AGENTS/CLAUDE router.
No construction task is complete. Next: resolve interaction choices D-04/05/06,
evaluate the storage sequence D-07, and accept or revise the order and criteria
before recording a finalized baseline. D-01 remains the source-access decision;
D-03 controls completion of the third destination. D-00 and D-02 are settled.
No served page, runtime, timer, publication state or user-owned ledger wording
was changed by this specification work.
