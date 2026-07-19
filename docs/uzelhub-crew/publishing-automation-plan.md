---
read: full
status: active roadmap (opened 2026-07-18 from the gap analysis of that date); sibling to crawl-to-publish-plan.md (that doc = the Ghost/blog track; this doc = the notes/newsroom track)
---

# Publishing-Automation Plan — the notes/newsroom track

The build order that closes the gaps between "one field note hand-shepherded
through the pipeline" and steady-state publishing. Captured here so picking up
later doesn't require re-deriving the plan from conversation (the
crawl-to-publish principle, inherited verbatim — this plan existed only in a
transcript for a day and was nearly lost to the same failure mode its
pipeline writes stories about).

**Same sequencing rule as the sibling doc: follow the sequence.** Each phase
produces an artifact the next depends on. Phases marked (parallel-safe) may
land any time.

**Not phases — deliberate human gates, load-bearing by design, never to be
automated away:** Editor approval encoded as data (`copyDraft`), the
redaction scrub, the employer-confidentiality gate (NEWSROOM §Editorial
rules), public-repo push review, the pineapple rule.

**Not phases — operator-side, gates the *point* of publishing:** the
identity/online-self setup (`site.json` `identity.profiles`, LinkedIn
refresh, bios pointing at the apex — PUBLISHING.md).

---

## Phase 1 — Ledger lifecycle states ✅ BUILT 2026-07-18

Extend `pipelines/scout/state/leads.yaml` status vocabulary:
`new → claimed → drafted → approved → published`, `spiked` legal from
`new|claimed`. Forward-only transitions via a constrained verb (a `lead-mark`
helper or `--mark` flag): one lead, one transition, validated, refuse loudly,
never freehand YAML — calendar-mark's philosophy applied to the ledger.
Writer pipeline stamps `drafted` when a draft lands in state; `published`
stamps when release.js stamps the note. Scout continues reading back ids +
pitches only — statuses stay invisible to it (pineapple-safe by construction).
Backfill: `2026-07-12-scout-design-was-already-written` → `published`.

**Produces:** true pipeline position per lead; the substrate every later
phase reads.

## Phase 2 — The Wire Editor (hired 2026-07-18) ✅ BUILT 2026-07-18, first pass run

**Topology call (operator):** the editorial triage pass is a NEW agent, not
a Director duty. NEWSROOM keeps role→agent deliberately open; the hire
clears the house bar (conflicting error policies + context firewalls, not
taxonomy): triage is high-volume/low-stakes-per-item over a ~15-20k-token
ledger working set, the Director is low-volume/high-stakes and must not
haul that haystack. The Editor *role* doesn't move — Director stays
Editor-in-chief, operator stays the gate; the Wire Editor is the desk that
triages the wire so the editor reads a shortlist, not the feed.

The pass (weekly or on-demand): read the ledger with Phase 1 states,
cluster related leads, flag overlap against claimed/published work, and
propose per lead — claim-with-register, spike, or hold — one-line reason
each. Output is a **proposals artifact in gitignored state**, shaped for a
two-minute human read. It NEVER writes the ledger; the operator applies
verdicts via `lead_mark` (manual-approval-always, super-flywheel.md).
Proposals flow toward the Editor only, never back to the Scout (pineapple).
Model seat: marketer split — Haiku clustering sweep, Sonnet judgment.

**Boundary (operator, 2026-07-18): the Director's morning brief is an
ops/oversight organ, not a content surface.** It aggregates cross-project
priority (sysadmin reports, blockers, calendar), and carries at most a
one-line newsroom *stat* ("4 new pitches this week") — never leads,
pitches, or proposals. The Wire Editor's shortlist reaches the operator
via its own artifact (and later, if wanted, a listener command), not the
brief. Don't re-conflate the Director's two hats: daily brief = ops
altitude; editorial = content altitude, now delegated to this desk.

**Produces:** a moving queue; the throughput bottleneck (the #1 gap) closed.

### Gate-① shadow mode + migration milestone (operator, 2026-07-18)

From day one the **Editor-in-chief runs in parallel**: on each Wire Editor
shortlist, the Director appends its own suggested verdict per proposal
(ratify / differ-with-reason) — a *shadow routing*, recorded in the
proposals artifact, never marked on the ledger. The operator disposes as
usual via `lead_mark`. **Concordance is the maturity metric**: Director
suggestion vs operator verdict, computable per cycle from the artifact +
the ledger's dated stamps — the system's readiness gets *tracked*, not
felt. Context note: the Director reads the Wire Editor's compressed
shortlist, never the raw ledger — the haystack firewall that justified
the hire stays intact. This is the Director's editorial hat, a separate
invocation from the morning-brief tick (ops hat); the brief boundary above
is unaffected.

**Milestone — Director assumes gate ① (routing):** after sustained
concordance over real cycles (threshold is the operator's call at the
time — the metric exists precisely so this is a data decision, not a
date), the Director's suggestions become the routing verdicts, applied via
`lead_mark` in its own namespace-attributed commits, and the operator's
gate ① compresses to exceptions/appeals. **Gate ② (scrub + approval →
publish) never migrates — permanently the operator's**, per the
never-automate list above.

## Phase 3 — Writer tuning batch (parallel-safe)

The known list from the first story (memory + writer-persona):
`WRITER_ROAM_ITERATIONS=9`; registered project roots stated in the prompt
(~15 wasted roam calls otherwise); exclude the drafts dir from the toolbox
(the self-paraphrase statelessness leak). Plus: the bootstrap-is-not-the-
process doctrine means effort per story should *fall* — track hands-on
minutes per story as the maturity metric (NEWSROOM §Writer).

## Phase 4 — Scrub pre-flight (assist, not gate)

An automated secrets/PII/internal-path scanner over drafts before they reach
the Editor. Speeds approval, catches the mechanical class; the human scrub
gate stays absolute on top. (The employer-confidentiality gate is judgment,
not scanning — stays fully human.)

## Phase 5 — One-command publish

Collapse the operator's three-step last mile (release.js stamp →
generate.js render → git commit) into one reviewed `publish` command.
Operator-run by design (live docroot + public repo); the drip-cadence guard
already lives in release.js. Marks the lead `published` (Phase 1 verb).

## Phase 6 — Syndication API legs

dev.to and Hashnode both take API posts; the kits (`syndication/<slug>/`)
already carry canonicals and front matter. Automate those two; LinkedIn/X
stay manual by nature (excerpt-only and link-post respectively).

---

## Fixed point already on the calendar

`define-why-now-in-scout-schema` (due 2026-07-27, post-A/B): the Scout
synthesis schema gets its `why_now` definition — timeliness OR durability.
Decided, timing-gated only. Fold subject-date spread into the A/B readout.

## Parked (this track)

- **Ticker + newsletter surfaces** — designed in NEWSROOM, separate build
  arcs. **Ticker v1 SHIPPED 2026-07-19** (home-hero crawl of running survey
  nodes, deterministic; NEWSROOM §Editorial rules has the build notes; the
  dedicated ticker table stays the v2 open item). Newsletter still waits on
  the Director's weekly pass.
- **Blog retelling leg** — feeds from the *sibling* track's infrastructure;
  first case banked (`pipelines/writer/state/drafts/` v2-longform +
  blog-skeleton).
- **Batch arc-finder** — still parked per NEWSROOM ("don't build on spec");
  the operator-dictated Codex epic brief is the worked example of its
  target output, and the 07-26 readout re-checks whether inline scratchpad
  pins suffice.
- **Failure alerting on the daily timers** — scout-pass has OnFailure →
  notify-telegram; audit the writer/ingest legs for the same when they get
  timers.
- **Read-only ops dashboard (operator, 2026-07-18: "a few key filterable
  views, not a Power-BI explosion").** The calendar-views pattern grown one
  ring: a generator over agent_decisions + the ledger's lifecycle stamps →
  one static HTML behind a capability URL, inlined data + client-side
  filter toggles (agent, date range, lifecycle state), regenerated by
  timer/hook. Candidate views: story-lifecycle swimlanes, A/B cost bands,
  ore burn-down, subject-vs-filed scatter (the why_now before/after),
  concordance trend. **Requirement (operator, 2026-07-18): at least one
  view leverages the reason fields** — the natural one is concordance-
  with-the-why: wire `reason` vs `chief_reason` side by side on differs
  (the pen-handover evidence is the argument text, not the percentage),
  plus `routing_reason` off the spine and the ledger's `why_now` (whose
  pre/post-07-27 filter shows the aperture opening in the model's own
  words). Merges naturally with the `pipeline-artifact-viewer`
  VTODO (due 07-24) — same hardened read-only page family, possibly one
  page with tabs. Incubates in the 07-23 agent_decisions query session;
  builds only after real queries pick the views that earn freezing.
