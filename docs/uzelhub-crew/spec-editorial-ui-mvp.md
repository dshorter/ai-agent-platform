---
read: full
status: PROPOSED MVP SPEC — revision 0.2, 2026-09-10. Adds explicit compatibility requirements for the currently paused Scout flow. Settled editorial policy is referenced below; interaction choices and storage sequencing remain open in NEWSROOM-WORKPLAN.md. No implementation or deployment is claimed.
---

# NEWSROOM — editorial UI MVP

The MVP makes the existing routing desk, draft desk and publication queue a
dependable way to operate the two human editorial gates. Its purpose is to
reduce the operator's recurring work while preserving judgment over stories,
voice, evidence and publication. A visual refresh alone cannot do this: the
screens must reflect current inputs and durable, versioned decisions.

This is the proposed acceptance contract for UI work inside
[NEWSROOM-WORKPLAN.md](NEWSROOM-WORKPLAN.md), principally NR-01 and NR-09,
rehearsed under NR-05. **The work plan remains the only task/status board.**
Finalization accepts a named revision of this spec or records the changes
needed. Later scope changes require a dated entry here and in the work plan.

<!-- MAP:START -->
- [Policy and scope](#policy-and-scope)
- [The operator's routine](#the-operators-routine)
- [UI-01 — current inputs and refresh](#ui-01--current-inputs-and-refresh)
- [UI-02 — routing desk, gate one](#ui-02--routing-desk-gate-one)
- [UI-03 — draft desk, gate two](#ui-03--draft-desk-gate-two)
- [UI-04 — publication and delivery](#ui-04--publication-and-delivery)
- [UI-05 — durable records and execution boundary](#ui-05--durable-records-and-execution-boundary)
  - [Storage recommendation and D-07](#storage-recommendation-and-d-07)
  - [Decision application and D-05](#decision-application-and-d-05)
- [UI-06 — presentation and effort](#ui-06--presentation-and-effort)
- [Acceptance scenarios and work-plan ownership](#acceptance-scenarios-and-work-plan-ownership)
- [Scout compatibility amendment — 2026-09-10](#scout-compatibility-amendment--2026-09-10)
- [Construction fit and open choices](#construction-fit-and-open-choices)
- [Change record](#change-record)
<!-- MAP:END -->

## Policy and scope

The operator has settled the two human gates and independent content type and
destination choices. The Scout supplies the initial recommendation; the human
can override it. [Content types](spec-content-types.md),
[Wire Editor](spec-wire-editor.md), [Writer](spec-writer.md) and
[SEO policy](/opt/_host/SEO.md) own those rules. This document specifies their
interaction and enforcement; it does not replace their editorial policy.

| Included in the proposed MVP | Outside this UI upgrade |
|---|---|
| Current lead queue, clear recommendations, independent overrides, recorded human decisions | New prospecting agents or a redesigned mining system |
| Reviewable draft revisions, small copy edits, correction requests, scrub evidence and enforceable approval | A general CMS, full page builder or collaborative rich-text editor |
| Destination presentations and delivery/recovery status | Building every unimplemented content type |
| Refresh, stale-state handling, useful errors and usable phone/desktop layouts | A new visual brand, analytics suite or separate mobile app |
| Enough effort measurement to evaluate the stated goal | Automatic changes to Scout taste or automatic promotion of either human gate |

First prove the built note path on the operator's site and DEV. Keep the third
destination explicit until D-03 is settled and its adapter verified. This is
an incremental demonstration, not completion of the three-destination goal.
Reuse an existing blog path for the cross-type routing check; if it cannot
produce a reviewable artifact, record that gap rather than relabeling a note.

## The operator's routine

| Moment | What the operator sees and does | What the system must establish |
|---|---|---|
| Open the desk | Current stories and drafts needing attention; failures that need action | Current input revisions, last successful refresh and honest counts |
| Gate one: choose the story | Read the pitch and advice; accept or override type and destinations; claim, hold or spike | Persist the actual decision and attribution; preserve the original recommendation |
| Between gates | See drafting/preparation progress or a clear failure | Work begins according to D-06; duplicate clicks cannot launch duplicate paid jobs |
| Gate two: approve the copy | Read the exact copy and selected destination presentations; edit, request changes, reject or approve | Approval binds to the reviewed package and completed scrub, with no outstanding blocking checks |
| After approval | See approved, scheduled, releasing and per-destination results | Release follows D-04 and the existing cadence; partial failures remain visible and recoverable |

Saving an edit is not approval. Saving approval is not proof of publication.
Delivery retries and an optional release command are execution actions, not
additional editorial gates. A substantive content revision returns to gate two.
Changing the selected route reopens the existing routing decision and any
affected presentation review; it never creates a third kind of approval.

## UI-01 — current inputs and refresh

Use the live lead ledger to determine current queue membership, then attach
the appropriate proposal by lead ID and input revision. Archived proposals
whose leads no longer exist are historical/orphaned records, never actionable
current cards. A current lead without advice remains visible as **No current
recommendation**; do not fabricate Scout destinations or a Wire verdict.

Record a manifest for each imported proposal batch: artifact identity/hash,
run date, source lead IDs and, when available, their input revisions. Surface
missing, conflicting, malformed and obsolete records separately. File name
ordering alone cannot establish that advice applies to a changed lead.

The existing recovery input is
`pipelines/scout/state/archive/wire-dry-20260906-2339.out`: read-only inspection
on September 9 found a proposals section containing all 17 current lead IDs,
followed by a JSON run summary marked `dry_run`. Implement a deterministic,
validated import of the artifact portion, retaining its origin and hash.
Do not treat the trailing summary as proposal data or present the import as a
new run. These historical outputs contain no destination recommendations;
show that absence rather than retroactively attributing choices to the Scout.
ID agreement is a recovery starting point, not proof of unchanged input text.

Refresh on opening a desk, after a completed operation, and through a visible
Refresh action. Refresh reads existing state; it never invokes a model or
publishes. With direct writes, use a current server response and refresh when
the tab regains focus; frequent background polling is unnecessary for this
volume. A retained snapshot must show when it was generated and when current
state was last checked. Failure to refresh keeps the last view visibly stale.

All writes check current record/package revisions regardless of screen age.
A stale tab receives a conflict with the changed item identified, not a silent
overwrite. Do not replace unsaved edits on background refresh. Browser-local
selections are marked unsaved, keyed to revision and never authoritative.

## UI-02 — routing desk, gate one

Retain the shortlist/card approach. The first screen of each card shows the
pitch, why now, evidence availability, suggested decision and any blocker.
Expandable details carry source references, clustering and the chief's advice.
Use three clearly labeled parts:

1. **Scout recommendation:** original type and destination set, with the
   recorded rationale when available. A missing field says unavailable.
2. **Wire advice:** claim/hold/spike, suggested type, reason, flags and a
   valid fold target; the chief's position remains identifiable as advice.
3. **Your decision:** independently editable type and destinations, initialized
   from the Scout's proposal. Wire advice does not silently replace the defaults.

Changing type never resets the chosen destinations. Selecting DEV never changes
a field note into a blog. Show known destinations and their capability/access
state; a missing adapter is a delivery blocker, not an editorial prohibition.
Preserve an intended unsupported route as unresolved instead of dropping it.

Actions are **Claim**, **Hold** and **Spike**. Claim saves the chosen type and
route along with the decision. Proposed explicit Hold records that the human
reviewed the lead while leaving it eligible for later consideration; untouched
means unreviewed. This requires a review event, not an invented lifecycle
transition. A folded hold carries an existing target ID and explains the
relationship. An override reason is optional so routine approval stays short.

Show the final saved values, actor and time after application. On failure,
retain the pending choices and explain whether anything was saved. A history
view distinguishes Scout, Wire, chief and human decisions; metrics must not
count a machine-applied mark as a human verdict. Corrections remain downstream
of the Scout's taste firewall, including through tool access and database roles.

## UI-03 — draft desk, gate two

Open the exact draft revision for the claimed lead. Show the final type/route,
copyDraft provenance, draft date and revision. Give the copy the main reading
space; place checks and sources beside it or beneath it on a phone.

The review package contains the canonical copy, title/tagline/description,
type-specific fields, intended original URL and each selected destination's
presentation. Where destination copies are identical, show that fact and the
formatting/metadata differences without requiring repeated reading. Clearly
label a local preview; do not claim it proves the remote platform's rendering.

Evidence inspection must support judgment about claims. Show usable references,
available scrubbed excerpts or receipt summaries, and known access/uncertainty
gaps. Keep tentative explanations distinguishable from established facts.
Missing evidence cannot be replaced with a confident generated explanation.
Raw transcripts and private source paths do not enter publishable metadata.

Proposed MVP actions:

- **Edit copy:** a small form for fields in the supported content schema,
  including body sections and metadata. Saving creates a new draft revision
  and reruns applicable checks. No raw JSON editing or page builder is required.
- **Request changes:** save a brief instruction against this revision and
  queue one bounded redraft through the selected execution mechanism. Preserve
  the prior draft and instruction; show a readable comparison when it returns.
- **Reject draft:** a terminal editorial rejection, clearly distinct from a
  correction request and from spiking a lead. Do not label this action “spike.”
- **Approve:** one gate-two action covering the displayed package and scrub.
  The button's wording reflects D-04: approval alone or approval into cadence.

Mechanical checks show **passed**, **findings**, **not run** or **failed** for
the actual revision, with the rule/tool version. Show type/metadata validation,
secret/PII scan, source concerns and destination readiness separately. A clean
scanner result is not the human's editorial approval or an assurance of voice.

Unresolved blocking findings prevent approval at the command boundary. The
operator resolves copy or uses an explicitly supported, audited finding
resolution; the UI must not silently create a global redaction dismissal.
Remove the current unsupported `--redact` instructions. Rendering a finding
with a strike-through does not remove it from the underlying content.

Any change to approved copy, substantive presentation, selected route or
publication metadata supersedes approval of that package and requires review
of the changed package before release. Scan-policy changes require fresh checks;
new blocking findings stop release. A scheduler timestamp alone need not
invalidate editorial approval, but it remains subject to cadence rules.

## UI-04 — publication and delivery

Extend the current queue with one row per approved piece and a result for each
selected destination. Show the original URL, approved revision, release mode,
actual scheduled time if one exists, and the last execution result. A calculated
date is explicitly an estimate, never a booked release.

Each destination can be **not prepared**, **blocked**, **ready**, **scheduled**,
**in progress**, **delivered**, **failed**, or **outcome unknown**. These are
delivery states, separate from the existing lead lifecycle. A remote draft is
not delivered/public. “Complete” requires all selected destinations to have
verified success; an original published with DEV failed is partial delivery.

Release the actual canonical original before syndicated copies that point to
it. Check the original's URL and required metadata before external delivery.
Adapters may transform formatting; they cannot rewrite approved claims or
silently choose a different original. Keep platform requirements in adapter
validation and the SEO authority, not in hard-coded type/destination coupling.

Retry only the unresolved destination using its durable operation identity and
known remote ID. A timeout after an external request means outcome unknown;
reconcile before creating another post. Do not republish successful destinations
to recover a failed one. Show a concise failure explanation, last attempt and
next available action; keep technical diagnostics in expandable details.

Private drafts, decisions, comments and source evidence stay outside the public
docroot. Copying a queued entry into the site's served data files is an exposure
boundary even without a published date; hiding it in a generated listing is
not privacy. The chosen release path must account for that transfer explicitly.

## UI-05 — durable records and execution boundary

The screens and command-line tools must share one validated mutation boundary.
Keep `lead_mark` as the sanctioned lifecycle interface, extending or delegating
its implementation deliberately. Do not add independent UI edits to its YAML
or new writes to `agent_decisions` for human editorial actions.

These are logical records; exact schema names are implementation details:

| Record | Minimum contract |
|---|---|
| Recommendation | Lead ID and input revision; Scout type/destinations; proposal/run identity; separate Wire/chief advice; absence represented explicitly |
| Routing decision | Unique decision ID; expected prior revision; human/agent identity; action; final type/destinations; optional reason/fold target; timestamp |
| Draft revision | Stable piece/lead ID; unique revision and content hash; prior revision; structured copy and destination artifacts; actual author/provenance; correction request when relevant |
| Review/approval | Exact package manifest/hash; check results and versions; human scrub/approval attribution; approved, superseded or unresolved outcome |
| Work operation | Unique request ID; expected input revision; queued/running/succeeded/failed/unknown state; bounded attempt/cost information; recoverable result |
| Delivery | Approved package and destination; canonical URL; remote identity; attempt/result timestamps; error or verified publication URL |

Every mutation validates identity, legal transition, current revision and
capability. It returns the authoritative result, not merely command output or
an optimistic green badge. Repeated submission of the same operation returns
its existing result. Protect against two tabs, retries and worker restarts.
Multi-item application reports each item's result and makes partial completion
explicit; it cannot silently claim the entire batch succeeded.

Approve/queue/lead-status coordination must survive a partial failure. Commit
the approved package and execution intent durably, then let recoverable work
perform file or remote side effects. A failed downstream step cannot be lost
behind a success exit code. Recovery resumes the same intent and version.
Postgres transactions do not make file writes or network calls atomic.

### Storage recommendation and D-07

[ADR-003](../architecture/adr-003-leads-ledger-in-postgres.md) accepts Postgres
and explicitly rejects building an elaborate replacement flat-file store.
The unapplied 006 schema does not, by itself, provide all the records above.

**Recommendation:** design these record contracts during NR-01/09 preparation,
then bring the planned NR-08 cutover and necessary schema additions ahead of
enabling durable UI decisions. This is a proposed sequencing change, D-07,
not an accepted move or permission to apply 006. It has a concrete reason:
human overrides and versioned approvals now need records the current ledger
and mutation verb do not support.

Read-only rendering can proceed independently once authorized. If the operator
keeps NR-08 parked, agree an explicit bounded persistence alternative before
building mutations; do not quietly recreate the flat-file architecture the ADR
rejected. Whichever sequence is accepted must define authority, backup,
verification, recovery and actual Scout-role restrictions before live writes.

### Decision application and D-05

**Direct saving is the recommended interaction**, pending the operator's
answer. A small same-origin Python service can expose typed editorial actions
behind Caddy and dispatch bounded jobs. Reuse the existing generators/views
and domain tools where useful; a new frontend framework is not a requirement.

Direct saving requires an authenticated operator identity at the service,
server-side attribution, origin/CSRF protection and a constrained action API.
The existing secret URL is not sufficient authorization for a write service.
Credentials stay server-side; callers cannot select arbitrary shell commands,
file paths or an arbitrary actor stamp. Bind the service to loopback and give
its process only the access required for these actions. Authentication failure
or expiry must preserve unsaved work without applying it. Verify these
properties through the real deployed boundary before enabling writes.

If D-05 retains copy-and-run, generate commands or a request artifact carrying
the exact item/package revision through the same validation boundary. Use real
CLI syntax, correct working directories and reliable shell argument handling.
Fix the current Writer command to use `--lead`. Show **Awaiting application**
until a refreshed durable result is observed. Count copying, shell execution
and refresh/recovery time in the effort measure; this is not direct UI saving.

For either choice, the durable record identifies who made the editorial
decision and who executed it. An agent must never manufacture human attribution
merely by selecting `--by editor` or replaying a generated command.

## UI-06 — presentation and effort

Keep the current visual language and three destinations within the ops desk:
**Stories**, **Drafts**, **Publishing**. Put actionable counts and input health
on the landing page. Use consistent action labels and status wording across
screens, readable copy width, keyboard focus and controls usable by touch.
Do not rely on color alone. Explain blockers next to the unavailable action.

Progressive disclosure keeps routine approval short: story/copy and the decision
first, recommendations/checks nearby, full history and diagnostics on demand.
No mandatory per-platform form filling when the accepted recommendation and
prepared metadata suffice. Errors retain the operator's work. Returning on
another device shows saved decisions; unsaved browser work is labeled local.

NR-05 records hands-on selection, editing, review, distribution and recovery
minutes. NR-10 compares comparable real releases against an agreed manual
baseline, including operational maintenance. Automated elapsed time is distinct
from operator effort. Record changed-copy scope and redraft count to help judge
voice improvement. Do not add tracking machinery or declare 90% savings from
click counts alone.

## Acceptance scenarios and work-plan ownership

These are required demonstrations for the proposed baseline, not claims that
tests have been written or passed. Use isolated state and a fake delivery
adapter for destructive/failure cases, then a controlled actual-UI rehearsal.

| Scenario | Observable pass condition | Owner task |
|---|---|---|
| Recover today's shortlist | Import the recorded run with provenance; match current leads, identify changed/missing advice, exclude 257 orphaned historical proposals from the actionable queue; no model call | NR-09 |
| Preserve recommendations and override independently | Changing type preserves destinations; changing destinations preserves type; saved human choices and Scout/Wire originals survive reload and remain distinguishable | NR-09 |
| Handle absent or unsupported capabilities | A legacy missing Scout destination is marked missing; an intended unsupported destination stays visible and unresolved; no fabricated recommendation or silent removal | NR-09 |
| Hold, fold and attribution | Reviewed hold differs from untouched; fold points to a valid lead; agent activity is excluded from human concordance and decisions remain inaccessible to Scout | NR-04, NR-09, NR-02 |
| Stale tabs and repeated apply | Changed lead/draft is refused with a useful conflict; repeated request launches one operation; refresh failure never implies currentness | NR-01, NR-09 |
| Correct and redraft | An edit creates a revision; a correction request returns a new draft with comparison; reject remains a separate terminal outcome | NR-01 |
| Enforce actual approval | A changed package, missing review, unresolved finding or stale approval cannot promote/release through UI or CLI; a valid reviewed package can proceed | NR-01 |
| Recover partial local work | Interrupt approval/queue/status coordination; restart exposes the incomplete operation and recovers it without losing approval or duplicating queue entries | NR-01 |
| Review destination presentations | Gate two shows approved copy, metadata and original identity for every selected destination; substantive changes require renewed review | NR-01, NR-09 |
| Prove independent delivery | Same note prepared for different destinations; same destination accepts at least two supported types without conversion; identify fixture, dry-run and actual integration evidence separately | NR-09 |
| Recover remote uncertainty | Original succeeds, one external request fails or times out; show partial/unknown state and reconcile/retry only that destination without duplicates | NR-09 |
| Exercise real access and interaction | On desktop and phone-sized browser: read, select, save/apply, correct, reload and recover; direct-write mode also refuses unauthenticated/forged requests through the actual service boundary | NR-05 |
| Measure the routine | Preserve actual human gate-one and gate-two decisions and hands-on minutes; do not recast the old agent-selected draft as the human rehearsal | NR-05, NR-10 |
| Preserve paused Scout operation | Review and refresh preserve the prospecting pause and Scout-owned state; ingestion continues independently; explicit paid Scout verbs are never refresh helpers | NR-09, NR-05 |
| Preserve producer/consumer contracts | A filed recommendation and citations survive storage/readers; the human override reaches the Writer while the original Scout proposal and dedup remain unchanged | NR-09, NR-08 |
| Preserve the review loop and concurrent work | Reapproval uses a new package event without lifecycle rewind; correction instructions reach the Writer; concurrent Scout filing and UI decisions lose no records | NR-01, NR-08, NR-09 |

Passing local and simulated checks establishes readiness for a controlled live
release, not proof of real delivery. NR-07 separately records authorization
and results for content release, timer resumption and source-code publication.

## Scout compatibility amendment — 2026-09-10

The [paused-flow audit](scout-ui-compatibility-2026-09-10.md) traces actual
entry points, stored state and consumer contracts. It found architectural
alignment but required integration work beyond connecting the screens.
Its compatibility demonstrations supplement the acceptance table above.

Preserve the existing distinction: the enabled timer continues ingestion;
`SCOUT_PAUSED` stops its prospecting pass. The UI can operate on banked leads
and drafts during that pause. It neither stops ingestion nor resumes
prospecting as a side effect. Explicit walk/synthesis commands bypass the pause
and cannot implement Refresh. Any future pass caller must enforce the pause
explicitly; the present guard lives at the CLI entry point.

Carry Scout recommendations through the producer, validation, store and all
readers. The Writer must consume the saved effective assignment, not the
unmodified original `type`. Preserve `sources`/`citations` compatibility at the
store boundary and keep stable IDs and dedup history across migration.
Keep fresh Wire triage a separately identified, bounded job; its failure does
not undo filing or cause a replay of the prospecting pass.

Before enabling automatic drafting or redrafting, demonstrate the promised
spending boundary. The current Writer parses `WRITER_MAX_COST_USD` but does not
enforce it in the inspected call path. Establish admission/between-call controls
and report any in-flight overshoot explicitly; recording cost after a run is
not budget enforcement.

Represent reopened routing, correction and approval as versioned editorial
events, distinct from the forward-only lead lifecycle. Preserve the old draft,
deliver correction instructions to the Writer and check the current approved
package at release. An old `approved` lifecycle stamp alone is insufficient.

Protect new editorial records through the actual Scout credentials and tools,
including file/search/Git access and retained copies. Excluding `state/` from
the navigation index is not an access restriction. Verify simultaneous Scout
filing and UI decisions, as well as preserved cursors, map, ore and jewels,
before enabling the combined flow. D-07 remains a sequencing proposal; this
amendment does not apply 006 or authorize resumption.

## Construction fit and open choices

Within the accepted work-plan order, establish record and approval contracts,
restore current input selection, add routing/review controls, connect execution
and delivery, then rehearse through the actual screens. Author UI-01/02/03
against explicit data contracts so storage timing does not force a redesign.
Resolve D-07 before state-changing implementation. Keep one active task in the
work plan and record an accepted order change there before acting on it.

| Decision | Effect on this specification |
|---|---|
| D-01: source access | Controls which evidence can be opened and the handling of inaccessible references; no source-policy assumption here |
| D-03: third destination | Controls the last adapter/access proof; does not change type independence |
| D-04: approval into cadence or explicit release | Determines the gate-two action's consequence and the publishing queue's controls |
| D-05: direct save or copy-and-run | Determines the service/access work and how an operator decision reaches durable state |
| D-06: claim starts drafting or separate execution | Determines the gate-one action's consequence; either path must prevent duplicate paid work and display its budget boundary |
| D-07: schedule storage work | Determines whether NR-08 moves ahead of durable UI decisions; preserve ADR-003's accepted direction |

The cost of this upgrade is concentrated in durable records, approval/release
enforcement and delivery recovery. Screen layout and current-artifact import
are smaller bounded changes. A responsible time estimate follows D-05/D-07
and verification of adapter coverage; a cosmetic-refresh estimate would omit
most of the work required by the operator's goal.

## Change record

| Revision / date | Basis and change |
|---|---|
| 0.1 / 2026-09-09 | Operator requested an MVP upgrade specification after the UI-readiness assessment. Proposed requirements and acceptance scenarios mapped to existing NR tasks. Decision application, automatic execution and storage sequence remain explicit choices. Documentation only; no served files or runtime behavior changed. |
| 0.2 / 2026-09-10 | Operator asked about compatibility with the paused Scout flow. Added the runtime audit and explicit pause/ingestion, producer/consumer, effective-assignment, correction/reapproval and concurrent-write requirements. Earlier broad compatibility assumptions are replaced by named demonstrations; no runtime change or plan finalization. |
