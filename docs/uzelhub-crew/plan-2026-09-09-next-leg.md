---
read: full
status: SUPERSEDED as a work plan by NEWSROOM-WORKPLAN.md, marked 2026-09-10. Retained September 9 merge rationale connecting the operator-confirmed follow-up and September 8 critique. Its historical proposals and dated correction remain intact; this merge performed no construction or operating actions.
---

# NEWSROOM — the next leg, merged against the review

> **Superseded as a work plan — 2026-09-10.**
> [NEWSROOM-WORKPLAN.md](NEWSROOM-WORKPLAN.md) owns the current sequence,
> decision states and acceptance criteria. This document remains the dated
> explanation of how the original eight items and the critique were merged.

> **2026-09-09 follow-on:** current execution state and the sequence being
> finalized now live in [NEWSROOM-WORKPLAN.md](NEWSROOM-WORKPLAN.md).
> The operator corrected the type/destination framing below: they are
> independent, and the Scout's recommendations remain human-overridable.
> The dated correction at the end supersedes the former open choice between
> short-note and longer-article syndication. This document remains the dated
> merge rationale, not the current task board.

The eight follow-up items fit the critique well. They cover a banked draft,
source access, two vocabulary defects, a first human editorial exercise,
small discovery experiments, operating decisions and the ledger cutover.
They need broader acceptance criteria around approval and evidence, and they
need to reconnect to the existing publishing-automation roadmap to complete
the user's actual publishing routine.

This document preserves the eight items as references. Its proposed sequence
follows dependencies and the operator's clarified goal. It does not reopen
the three completed windows of the unify-and-reset plan.

Navigation added 2026-09-10: the [documentation index](README.md#newsroom-start-here)
connects this history to the later UI specification and Scout compatibility
audit. The section map below is generated from this document's headings.

<!-- MAP:START -->
- [Basis and current goal](#basis-and-current-goal)
- [How the eight items merge](#how-the-eight-items-merge)
- [Approval, evidence and access: the expanded acceptance](#approval-evidence-and-access-the-expanded-acceptance)
  - [Item 1: a reviewed piece and an enforceable gate](#item-1-a-reviewed-piece-and-an-enforceable-gate)
  - [Item 2: consistent capabilities and sources](#item-2-consistent-capabilities-and-sources)
  - [Items 4 and 6: references that support the editorial judgment](#items-4-and-6-references-that-support-the-editorial-judgment)
- [Bring the publishing roadmap into this leg](#bring-the-publishing-roadmap-into-this-leg)
- [Give the database cutover its proper scope](#give-the-database-cutover-its-proper-scope)
- [Proposed order and stopping points](#proposed-order-and-stopping-points)
- [What proves progress](#what-proves-progress)
- [Decisions still requiring the operator's answer](#decisions-still-requiring-the-operators-answer)
- [Correction — 2026-09-09: type does not choose destinations](#correction--2026-09-09-type-does-not-choose-destinations)
<!-- MAP:END -->

## Basis and current goal

- **Operator-confirmed follow-up:** session
  `752b58bd-8d9a-47fa-81c8-7b92d343a3c7`, assistant reply at
  `2026-09-07T04:43:03.245Z`, JSONL line 863. Seven numbered items, followed
  by the 006 cutover described separately as the next day-sized build.
  The operator confirmed on September 9 that these are the intended eight.
- **Review:** [verbatim September 8 critique](newsroom-design-critique-2026-09-08.md).
  It remains an unchanged historical artifact. Construction findings below
  refer to its six numbered findings.
- **Completed work:** [window 3 handoff](handoff-2026-09-07-window-3.md),
  [window 2 run record](window-2-runs-2026-09-06.md), and
  [completed unify-and-reset plan](plan-2026-09-07-unify-and-reset.md).
- **Existing commitments:** [publishing-automation roadmap](publishing-automation-plan.md),
  [ADR-003 and its amendment](../architecture/adr-003-leads-ledger-in-postgres.md),
  the current desk specifications, and `/opt/_host/SEO.md`.

The goal is regular content on the operator's own website, DEV, and
provisionally Hashnode, with roughly 90% less personal effort. The operator
wants to retain both human approvals and receive writing very close to what
they would have crafted themselves. Live publishing can begin at acceptable
MVP quality, followed by refinement on subsequent content.

Both gates remain human in this plan. Concordance diagnoses editorial
assistance; it is not a prerequisite for transferring gate one to an agent.
The older roadmap's possible transfer milestone does not define this MVP.

The counts of 16 new leads, 17 total leads, 35 inaccessible-source jewels and
16 unpushed commits are historical follow-up counts. Likewise, the recorded
pause and unapplied migration describe the handoff. Recheck relevant state
before execution; these numbers are not a fresh live-state audit.

## How the eight items merge

| Original item | Fit with the critique | Merged treatment |
|---|---|---|
| **1. Scrub the banked draft** | Construction findings 1 and 2: approval enforcement and factual fidelity | Keep the human scrub. Add verification of the draft's central claims and uncertainty, and make the approval/promotion path enforce the completed review. A clean scanner result alone is insufficient. |
| **2. Settle the two repository lists** | Findings 4 and 5: access controls and resolvable evidence | Retain the source-policy decision. Extend the work to consistent restrictions across reading, searching and Git access, and to the Scout's alternate access to editorial verdicts. Root consistency alone does not close these gaps. |
| **3. Fix the dirty ledger entry** | A specific instance of the publication and source-hygiene problem | Keep it as a bounded cleanup, with the operator resolving the wording. Do not broaden a redaction dismissal. Cleaning this file does not establish that the general publishing boundary works. |
| **4. Fix shadow vocabulary and fold references** | Removes vocabulary drift and strengthens the Wire Editor's output | Keep both small fixes. Verify that a folded lead points to the intended lead ID. Keep richer chronology/provenance work explicit rather than burying it inside a rename. |
| **5. Work the 16 new leads by hand** | Finding 6 and the goal of two useful human checkpoints | Use the real shortlist for genuine operator decisions and measure the effort. A useful first batch is enough to start a cycle; clearing the whole reservoir is not an MVP condition. Preserve who actually made each decision. |
| **6. First document walk and surveying-line experiment** | Findings 2, 5 and 6: grounding, provenance and evidence quality | Keep them as two bounded experiments. Add source/date limitations to the readout and evaluate useful supported stories, not only lead count. They need not hold up an acceptable story already supported by existing sources. |
| **7. Decide on timer resumption and pushing commits** | Addresses operating readiness, but does not itself complete publication | Keep the decisions separate. Add the missing connection to the existing publishing roadmap: an approved piece reaching the three destinations with observable outcomes. Source-code push, content publication and timer resumption are distinct actions. |
| **8. Complete the 006 Postgres cutover** | Supports findings 1 and 4 through lifecycle integrity and restricted database access | Keep ADR-003's accepted direction and give it its own bounded build. Include actual runtime credentials and all consumers. Coordinate approval records with it, while recognizing that database transactions alone cannot make a file write or remote publication atomic. |

## Approval, evidence and access: the expanded acceptance

### Item 1: a reviewed piece and an enforceable gate

The September cycle gives us a concrete draft to inspect. It also exposes two
separate needs: the operator must approve the content, and the software must
honor the approval boundary. Neither substitutes for the other.

The merged acceptance is:

- The operator resolves scrub findings and reviews substantive claims. The
  manuscript preserves the source's degree of certainty. In this specimen,
  the surveying instruction is a candidate explanation awaiting an experiment;
  a before/after result over different ore does not establish its causality.
- Approval identifies the content actually reviewed. Material editing after
  approval cannot silently reuse approval of an earlier version. The exact
  storage/identifier mechanism remains an implementation decision.
- Promotion refuses a draft whose required review is unresolved. The automated
  scan assists the human scrub; it does not certify editorial or confidentiality
  judgment on the operator's behalf.
- A queued artifact and its lifecycle record agree, or any incomplete operation
  is visible and recoverable. A failed status stamp cannot be reported as full
  success. A retry must not duplicate the content.

The banked story was selected by an agent. It can exercise gate two, but must
not be retroactively scored as a complete two-human-gate cycle. Item 5 supplies
genuine operator selection for a subsequent complete rehearsal.

The gate repair need not wait for the database cutover. Its approval semantics
should be agreed once and carried into that cutover, avoiding two incompatible
definitions of what was approved.

### Item 2: consistent capabilities and sources

The old follow-up recommended narrowing git mining to the three readable
repositories. The authority map still records the policy choice as open.
The operator's confirmation of which list we found does not silently settle
that source-access choice.

Whichever source policy is chosen, test it across each available access path:
direct reads, searches, Git operations, and database access. The critique
demonstrated that the tools have different restrictions today. In particular,
a secret-shaped filename cannot be protected only on direct reads, and a Git
subcommand allowlist does not establish that every accepted argument is
read-only.

The Scout's normal verdict-free dedup input is useful, but the role's other
read paths must be considered too. Moving the ledger to Postgres does not
automatically remove readable historical state, proposals, drafts, or accounts
of editorial decisions. Review that exposure explicitly; do not quietly
exclude broad swathes of working history and call the discovery policy intact.
Any restriction that reduces the intended source aperture belongs in the
source-policy discussion.

Existing inaccessible-source jewels also need an explicit treatment. The old
recommendation was to leave them in place. Retention can be compatible with
preventing unsupported claims or inappropriate references from progressing
into public copy. Deleting historical evidence is not implied by this merge.

### Items 4 and 6: references that support the editorial judgment

Carrying the fold target's ID removes an avoidable ambiguity. It does not
prove the Wire Editor has the structured dates and source types it needs to
judge arcs reliably. Track that as a separate input-quality concern.

Before relying on document-mining results as a chronology, distinguish the
event date from the document's modification date. The current reader applies
the file's last commit date to ordinary document sections, and path/heading
references are not versioned. An initial one-page experiment may measure that
reader as it stands, but its report must retain these limitations. Production
claims need references that can be resolved to the evidence reviewed.

This does not require a full historical-provenance rebuild before the first
piece. The selected piece needs dependable evidence; expansion to more sources
must carry the same property forward.

## Bring the publishing roadmap into this leg

The eight-item follow-up did not restate the existing publishing roadmap.
That roadmap already contains Writer tuning, hands-on minutes per story,
scrub assistance, one-command release and DEV/Hashnode API delivery. These
are existing commitments to reconnect, not discoveries to credit to this
review. The review supplies evidence that their operating outcome remains
unproven and exposes the current adapter/policy mismatch.

**Open content decision:** will the first cycle syndicate the short field note
or the longer article? The site's publishing guide sends notes with apex
canonicals; the current DEV adapter accepts blog articles with blog canonicals.
The operator has not yet selected between those paths. Three platforms do not
require three different content types.

The chosen route should have one coherent approval and release contract:

- Identify the original piece and its canonical URL. Resolve the policy/code
  disagreement for that artifact; a distinct longer article retains its own
  identity rather than being treated as an identical copy of the short note.
- Gate two covers the content that will reach the destinations. Routine
  rendering or delivery must not introduce substantive unreviewed writing.
- Record delivery success and the resulting URL for each destination. A partial
  release stays visibly partial, and retrying does not create duplicate posts.
  Avoid claiming a lead is fully distributed merely because the website is live.
- Measure editing, clerical distribution and recovery effort together. The
  two intended approvals should account for most normal operator involvement.

An explicit release action may remain, consistent with the existing roadmap.
It should not require another editorial review of every platform copy. Whether
gate-two approval also schedules release, or leaves one execution action for
the operator, remains to be stated when that route is made concrete.

The SEO qualifications in the critique belong in that policy reconciliation:
cadence serves the publication and its audience; it does not neutralize
low-value content. Note length is a house format. Canonicals identify preferred
originals for duplicate or very similar copies. Preserve the source links in
the critique when correcting the older SEO rationale.

## Give the database cutover its proper scope

ADR-003 already settles the storage direction. Reuse that decision and its
existing schema/apply/verify/rollback work. Applying the schema without moving
callers and runtime access does not complete the cutover.

Its acceptance should establish that IDs, content types, citations, lifecycle
history and human/agent attribution survive; each consumer uses the intended
store; and the running Scout actually uses its restricted database role.
Prove refusal through that role as well as the permitted operations. Use the
repository's migration recovery procedure and recheck the live population
before carrying it across.

Coordinate any approval/version record with item 1 and any citation changes
with the evidence work. Do not assume a Postgres transaction also commits
`notes.json` or a remote platform request: those cross-system operations still
need visible partial state and reliable recovery.

This remains a distinct build whose schedule is open. It need not block a
bounded publishing MVP if that route can preserve approval, evidence and
lifecycle integrity with the current store. Avoid extending the temporary
store into another architecture project simply to postpone the accepted
cutover.

## Proposed order and stopping points

1. **Resolve the decisions that select the route.** Choose the first syndicated
   artifact and settle the mining/read source policy. Confirm Hashnode when
   finalizing delivery. The bounded ledger cleanup and vocabulary fixes
   (items 3 and 4) can proceed independently when implementation is requested.
2. **Make the selected route dependable.** Expand items 1 and 2 as above. Check
   the chosen story's evidence and make its review status meaningful at
   promotion. Set the approval contract with the planned store in mind.
3. **Exercise both human checkpoints and delivery.** Use item 5 for actual
   operator selection, then Writer output, factual/voice review and the chosen
   three-destination route. Bring the existing publishing-roadmap work into
   this cycle. Record where operator effort occurs and what still fails.
4. **Begin live publishing at acceptable MVP quality.** Publication readiness
   depends on acceptable copy, preserved human approval and dependable delivery.
   Achieving the entire 90% reduction is a measured refinement target; it is
   not a demand to reach perfection before the first release. Continue
   measuring subsequent cycles and improve the approved voice examples from
   the operator's deliberate corrections.
5. **Schedule discovery experiments and the cutover deliberately.** Item 6's
   first document page and surveying-line comparison remain worthwhile bounded
   work. Run the latter on a matched current baseline: window 3 changed the
   prompt, so older measurements are not a controlled twin. Item 8 keeps its
   own migration scope. Either may move earlier if a demonstrated dependency
   of the selected publishing route requires it.

Item 7 is a set of operating decisions, not one final switch. Review source-code
pushing on the changes being published. Decide timer resumption from bounded
cost, source access and the usefulness of more leads. Decide content publication
from the selected piece and delivery route. None of those approvals substitutes
for either of the others.

## What proves progress

Use a small record per real cycle: what the operator selected, which draft
version they approved, substantive corrections needed, delivery result per
destination, and hands-on minutes for selection, review, distribution and
recovery. Keep development effort separate from recurring operation, while
counting ongoing maintenance honestly. A dashboard is not required to begin
measuring these facts.

The baseline is a comparable manual release across the same destinations.
Without it, a 90% saving cannot yet be claimed. Several successful cycles can
show whether the effort is falling and whether approvals are usually enough.

Do not treat agent-to-agent agreement as human concordance, more leads as
better stories, more source types as stronger evidence, or completing all
sixteen historical new leads as a publishing requirement. First-hand evidence,
faithful writing and completed releases are the useful outcomes.

## Decisions still requiring the operator's answer

- Short field note or longer article for the first three-platform cycle.
- Which source policy resolves the mining/read mismatch, including treatment
  of the already retained inaccessible-source material.
- Final confirmation of the third platform and the release interaction once
  the chosen route is concrete.
- Timing of the separate cutover, paid experiments, timer resumption, public
  pushes and live publication when those actions are proposed for execution.

The merge adds no third editorial approval and does not treat a confirmed
historical list as authorization to perform its operating actions today.

## Correction — 2026-09-09: type does not choose destinations

The operator rejected the implied choice between field-note syndication and
longer-article syndication. Content type and destination are independent.
The Scout's recommendations are retained and can be overridden by the operator.
This supersedes the open-content-choice paragraph, the corresponding item in
the proposed first step, and the first open-decision bullet above.

The current adapter mismatch is implementation work, not a reason to constrain
the editorial model. The settled policy lives in spec-content-types.md
§Content type and destination; the updatable sequence, acceptance criteria,
decision states and change record live in NEWSROOM-WORKPLAN.md. The first real
piece is selected through normal gate-one review, not by choosing a permanent
type-to-platform route in advance. The source-access decision remains open.
