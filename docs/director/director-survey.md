# The Director — Working Blob (Cross-Project Survey)

> **❄️ Frozen snapshot (2026-06-24).** This survey is the research + decision log that *led to* the
> persona — preserved as-is, **not maintained.** For the current role definition see the living doc
> [`director-persona.md`](director-persona.md); some details here (e.g. the ROUTE mode in §1.6) have
> since evolved beyond what's recorded below.

> **Status:** Working draft / scratchpad. Assembled 2026-06-23 by surveying the three
> projects + the host layer. This is raw material for composing the **Director** persona —
> not a finished spec. Untracked on purpose; move/commit when we know where it belongs.
>
> **Goal of the Director:** a higher-level role that helps Dan **manage tasks across the
> three projects** — `predictor_ingest`, `uzelhub-web`, and `ai-agent-platform`. The plain
> name "Director" was deliberately reserved for this role (the blog-review role was renamed
> "Blog Director" to free it up — see PR #10).

---

## 0. How to use this doc

Sections 2–4 are the *map* (what exists, where, current state). Section 5 is the *org chart*
(existing personas the Director coordinates). Section 6 is the *rulebook* (conventions the
Director must respect). Section 7 is the *launchpad* (open questions to answer before writing
the persona). Section 8 is the *source index* for drilling deeper.

---

## 1. Why "Director", and the persona precedent

- **Reserved name.** "Director" (unqualified) = this new cross-project role. "Blog Director" =
  the human who reviews blog drafts in Ghost (scoped to the blog crew).
- **Persona-writing precedent already exists in this repo.** The closest model for what we're
  about to write is [`server-maintenance-agent-persona.md`](../uzelhub-crew/server-maintenance-agent-persona.md).
  Its section shape is a ready-made template: *Who you are · What you own · What you defer on ·
  How you work · Voice · What you refuse · Worked examples · Open questions · Not in v1.*
  The Director persona should mirror this structure at a higher altitude.

---

## 1.5 Live decision log (2026-06-23)

Decisions and leanings as they settle. Not all locked.

- **Calendar: deferred (no cal in v1).** Keep the Director to a prioritized task view for now.
  Revisit later as a *read + propose* layer (never silent writes), building on predictor's
  existing task-`.ics` generator (`/opt/predictor_ingest/calendar.ics` already emits work items
  as `VEVENT`s — `PRODID:...//tasks//EN`).
- **Scope: leaning "project orchestrator only"** — *not locked; more questions pending.* Under
  this lean a **two-vehicle** shape emerges:
  - **Inbox / Front Desk (separate sibling vehicle):** the one universal, frictionless capture
    point. Accepts anything from anywhere, **category-blind** (capture must not force "which
    project?" — that friction kills capture). First-pass triage: project items → forwarded to the
    Director; non-project items (teaching, networking, admin) → held in their own lanes.
  - **Director (project orchestrator):** receives the project-tagged subset; prioritizes and
    sequences across the three repos; surfaces cross-project dependencies; speaks the
    sprint/ADR/model-tagged language.
- **Still open:** the full set of Director responsibilities (Dan has more in mind). The
  orchestrator-vs-operations-chief line stays open until that set is on the table.

**Update 2026-06-24:**
- **Signature deliverable = a priority-setting discussion/report.** Everything (OWN/ROUTE/FRAME)
  feeds it. Confirmed via Dan's #4 answer: the Director engages strategy items *in service of the
  priority report*, not to drive their execution — FRAME items get framed enough to take their
  place in the priority ranking and compete for attention alongside project work.
- **`rag_pipeline`: not yet in scope.** Registry stays at the current 3; rag listed as known/not-registered.
- **First persona skeleton drafted** → [`director-persona.md`](director-persona.md). ROUTE
  destination, cadence, runtime/memory, and the rest of the responsibility set left as `[OPEN]`
  seams to resolve while reviewing the draft.

---

## 1.6 The clarifying lens — Director owns *verbs*, not *nouns* (2026-06-23)

Four real cross-cutting questions from Dan exposed that **"cross-cutting" is not one kind of
thing.** They sort by *cognitive move*, not by topic — and that dissolves the scope fuzz.

**Principle:** the Director owns the *verbs* (sequence, track-dependency, route, frame-a-decision),
**not** the *nouns* (social media, agent architecture, teaching). It's a meta-role. That's what lets
wildly different substance flow through one coherent persona without it becoming the social-media
manager or the platform architect.

**Three ownership modes** the triager assigns to any incoming item:
- **OWN** — project work + sequencing/dependencies. The Director schedules, ranks, tracks. *(Core.)*
- **ROUTE** — architecture/design or someone-else's-domain questions. Flags it, attaches
  context/constraints, sends it to the right forum (an ADR, a design session, a lane), tracks until
  resolved. Does **not** resolve it itself.
- **FRAME + HOLD** — strategy/judgment calls only Dan can make. Lays out options, dependencies,
  phasing; **holds** the decision open and reminds. Doesn't decide.

| Example question | Move | Substance | Mode |
|---|---|---|---|
| Predictor images → marketing pages once marketing's up | track dependency + sequence | project (uzelhub-web ← predictor assets) | **OWN** |
| Should the sysadmin agent know when `make daily` runs? | surface an architecture question | platform/agent design — *constraint:* sysadmin persona already **defers** on predictor pipeline behavior | **ROUTE** → ai-agent-platform design decision / mini-ADR |
| 3 impactful things across 2 projects — which first? | prioritize / sequence | project | **OWN** (the core job) |
| Social reset; when to link blog↔social; phase in? | frame a strategy/timing decision | strategy + non-project (social) + project (blog cadence) | **FRAME + HOLD** |

**Effect on the §1.5 scope fork:** dissolves "orchestrator vs ops-chief." The Director **sees
everything** (nothing orphans) but **ownership is graduated by mode** — it OWNs only project work,
ROUTEs design questions, FRAMEs strategy. *"Sees everything, executes the bounded slice."* The
separate Front Desk still does category-blind *capture*; the Director is the *triager* that assigns
the mode.

---

## 1.7 The project set is DATA, not identity — scaling to N (2026-06-23)

Constraint from Dan: the project list will grow to 4, 5, or more. Implication: **the Director's
persona must be project-count-agnostic.** It describes *how to orchestrate any work-project*; a
separate **registry** says *which projects exist now*. Adding #4 = a registry edit, **not** a
persona rewrite. (Mirrors predictor's own `KNOWN_DOMAINS` single-source-of-truth pattern.)

**A registry already half-exists — and growth is already real:**
- `/opt/_host/README.md` has a maintained **"Projects in /opt" table** (Folder · What it is ·
  Compose? · Auto-start unit), kept current by the sysadmin agent's drift audit (it discovers new
  `/opt` dirs → proposes rows).
- It lists a **work-project not yet in the Director's scope: `rag_pipeline/`** (RAG — Azure OpenAI
  + FAISS + SQLite, run manually). **So the real scope is already ≥4, not 3.** ← confirm with Dan.
- It also lists infra (`server-maintenance/`, `_host/`) and ignorable typo dirs — *not* work-projects.

**Two registries, one source (don't duplicate):**

| Registry | Lens | Owner |
|---|---|---|
| `_host/README.md` projects table | host/ops — "does it run, what unit, compose overlaps" | sysadmin agent (discovery → propose → confirm) |
| Director's work-project registry | work — "backlog location, state doc, conventions, maturity, dev/prod, current focus" | Director (curated subset of the host table + work metadata) |

New projects flow in via the **existing** sysadmin discover→propose→confirm path; the Director
picks up the new row and asks "register as a work-project?"

**What gets harder at N:** projects track work *heterogeneously* (predictor = rich
ADR/backlog/`operational-state.md`; uzelhub-web = loose notes; rag_pipeline = ?). The Director's
core value is **normalizing** these into one comparable view so "N things across M projects — which
first?" stays answerable. Nudge each work-project toward a findable backlog + state doc as N grows,
but meet each where it is — don't force uniformity.

**Front Desk already handles growth:** a brainstorm for a brand-new/unregistered project is
captured category-blind, then triage matches a registered project or flags "new project? → propose
registering."

> **Survey gap:** `rag_pipeline/` has not been surveyed (purpose, state, conventions). Do that
> when it's confirmed in scope.

**Decision — leave `_host` exactly as-is (2026-06-23).** It keeps surfacing because it's the de-facto
**shared spine** (the one artifact that knows all projects + how they interrelate) — that's a *role*
signal, not a cue to build around it. It's already a local git repo **and** already in the off-site
B2 backup (`backup.sh` tars `opt/_host`; README §"What's captured" line 154). Version-controlled ✓,
recoverable ✓. **Do not** give it a GitHub remote — it maps host internals (ports, what-runs-where,
credential *control points*), which belong local + backed-up, not on a code host. Caveat (not a todo):
the backup excludes `.git`, so off-site preserves current content but not commit history — acceptable
for a map doc. The Director **reads** `_host` as its host-lens registry; it does not duplicate or
promote it.

---

## 2. The three projects at a glance

| Project | Path (on VPS) | Git remote | Role in the ecosystem | Maturity | Live URL |
|---|---|---|---|---|---|
| **predictor_ingest** | `/opt/predictor_ingest` (dev) | `git@github.com:dshorter/predictor_ingest.git` | The intelligence engine: RSS/social → LLM entity/relation extraction → knowledge graph → trend scoring → Cytoscape.js viewer | **Most mature** (beta `0.1.0b1`, ~263 PRs, Sprint 18, 10 ADRs, ~209 tests) | `uzelhub.com/apps/predictor/` (dev) |
| **predictor_prod** | `/opt/predictor_prod` | *(same remote)* | **Deployed clone** of predictor_ingest, pinned to `main`; serves prod via data symlinks back to dev | Mirror of dev | `predictor.uzelhub.com` |
| **uzelhub-web** | `/opt/uzelhub-web` | `git@github.com:dshorter/uzelhub-web.git` | The public face: marketing site + "Studio" portfolio + the Uzella chat persona | Active design churn (~45 PRs); README empty, work tracked in notes | `uzelhub.com` |
| **ai-agent-platform** | `/opt/ai-agent-platform` (this repo) | `https://github.com/dshorter/ai-agent-platform.git` | The automation/observability spine: Claude-Agent-SDK crews, Postgres decision logging, the commit→blog pipeline | **Newest** (Sprint Zero) | (internal / Ghost target) |
| **_host** | `/opt/_host` | *(local git repo)* | Host-level reconciliation: `/opt/_host/README.md` is the source-of-truth for what runs on the VPS; `incidents/` holds immutable post-mortems | Operational | n/a |

All four user-facing things live on **one Hetzner VPS**, fronted by **Caddy** (`/etc/caddy/Caddyfile`
is the only public listener — operator-only).

---

## 3. How they interrelate (the value chain)

```
  predictor_ingest (dev tree)
     ingest ~10–30 sources/day → clean → LLM extract (Batch API) → resolve
     → export 4 graph views → trend scores/narratives
            │                                   │
            │ generated JSON (symlinked)        │ commit history
            ▼                                   ▼
  predictor_prod  ──►  predictor.uzelhub.com    ai-agent-platform
  (pinned to main)     (live graph explorer)    "Uzelhub Crew" blog pipeline:
                                                reads predictor commits → drafts
            ▲                                   in Dan's voice → SEO package →
            │ showcased / marketed              Ghost drafts → Blog Director review
            │                                          │
  uzelhub-web  ◄───────────────────────────────────────┘ (blog.uzelhub.com)
  uzelhub.com — markets Predictor (+ other systems) as a "sale-ready product line";
  Studio holds the deep-dives; Uzella = the site's chat persona
```

**One-liner:** predictor_ingest **produces** (intelligence + a commit stream); uzelhub-web
**presents** (marketing + portfolio); ai-agent-platform **automates** (turns the commit stream
into a blog, and is the home for future cross-cutting agents). The **Director** is the role that
sees all three at once and helps decide *what to work on next, where, and in what order.*

---

## 4. Per-project deep notes

### 4.1 predictor_ingest — the engine

- **What it is:** a domain-agnostic pipeline building AI/trend knowledge graphs. Two extraction
  modes: **Mode A** (Anthropic Batch API, current default per ADR-008) and **Mode B** (manual
  ChatGPT copy/paste, no API key). Four CPU/zero-token **quality gates** (evidence fidelity,
  orphan endpoints, zero-value, high-conf+bad-evidence) run before scoring.
- **Domains** (`domains/<slug>/`): `ai`, `biosafety`, `film`, `semiconductors`. Framework code
  (`src/`) is domain-agnostic — enforced by `tests/test_grep_audit.py`.
- **Current state (2026-06-10):** ⚠️ **pipeline is DORMANT in all four domains.** No cron
  installed. [ADR-010](file:///opt/predictor_ingest/docs/architecture/adr-010-two-domain-restart.md)
  plans a **two-domain restart** (film as the "Movers" proof-point, semiconductors as the
  "Landscape" archetype); AI + biosafety stay paused.
  - **Landmine:** Sprint-14 smoke test inserted **synthetic `trend_history` rows** into ai/film/
    biosafety DBs — must be deleted before first real run (ADR-010 D5), but **not** for
    semiconductors (real history overlaps the date).
- **Single source of truth for run config:** [`docs/backend/operational-state.md`](file:///opt/predictor_ingest/docs/backend/operational-state.md)
  — read first when resuming.
- **Dev/prod split (Sprint 18):** dev = `/opt/predictor_ingest` (edits live on save); prod =
  `/opt/predictor_prod` (pinned to `main`, deployed by GitHub Action on merge). Dev is **not**
  auto-updated — pull `main` manually. Prod serves dev's JSON via symlinks.
- **Process discipline (high):** sprints (~2hr focused units), 10 ADRs, `docs/project-plan.md`
  (unified backlog, stability-ordered, model-tagged `[Opus]`/`[Sonnet]`/`[Manual]`),
  `docs/backlog.md` (EXT-* items). This is the most process-mature of the three.

### 4.2 uzelhub-web — the public face

- **What it is:** the marketing site (`uzelhub.com`) + a "Studio" for deep-dives + **Uzella**,
  the site's chat persona (`services/uzella-proxy`).
- **Current state:** README is **empty**; real work lives in `BACKLOG.md`, `editing-notes.md`,
  `mktg-notes.txt`, and `marketing/{README,TODO,TEMPLATE}.md`. Heavy in-progress **marketing-site
  rebuild**: product "cut-sheet" catalog (no commerce), light/Inter visual identity decoupled
  from the Studio, deep-linkable URLs.
- **Notable active threads:**
  - **Uzella is being retired** as a named persona → rebranded to an **unbranded "Ask about this
    system" chat** that reuses the `uzella-proxy` infra. (A `BACKLOG.md` item still wants a
    tone-toggle: thinker/engineer/pitch.)
  - Marketing copy must stay **accuracy-guardrailed** (e.g. scale is "~10–30 docs/day," *not*
    "thousands"; no "RSS" in Explorer copy; corroboration is "planned, not implemented").
  - Per-project **about pages**, badge states reflecting reality (`Live`/`Beta`/`In development`),
    `studio.uzelhub.com` not yet stood up.
  - **Brand/trademark sensitivities:** `Uzelhub™`, `Uzella™`, and the **4Cs** phrase are
    trademark candidates. "Predictor" is explicitly *not* a TM target.

### 4.3 ai-agent-platform — the spine (this repo)

- **What it is:** "a generic spine for running semi-autonomous AI crews against real projects."
  Claude Agent SDK + Postgres (`ai_agent_platform` DB) + Docker. Sequence-aware decision logging
  (`pipeline_runs`, `pipeline_inputs`, `agent_decisions`, `posts`).
- **First tenant — the "Uzelhub Crew" blog pipeline:** reads `predictor_ingest` commits → Content
  agent drafts in Dan's voice → Marketer agent SEO-packages → Ghost drafts → **Blog Director**
  review. (HVAC digital-twin is an archived earlier proof.)
- **Current state:** Sprint Zero. Just landed: Blog Director rename (#10) and Sprint-Zero
  hardening (cost caps, run resilience, cache-token tracking — the open PR `claude/sprint-zero-hardening`).
- **Existing/forward personas live in `docs/uzelhub-crew/`:** Blog Director checklist;
  sysadmin/server-maintenance agent (design + persona, Sprint One+, **not yet built**).

---

## 5. The org chart — roles the Director will sit above/beside

| Role | Scope | Status | Home | Director relationship (TBD) |
|---|---|---|---|---|
| **Blog Director** | Reviews/approves blog drafts in Ghost | Active (human role) | ai-agent-platform | A *function under* the Director's content concern? |
| **Content / Marketer agents** | Draft + SEO-package blog posts | Built (Sprint Zero) | ai-agent-platform | Worker agents the Director's plans feed |
| **Sysadmin / server-maintenance agent** | The *host* (`/opt`, backups, units, drift) | Designed, not built (Sprint One+) | ai-agent-platform → runs on host | Peer — owns infra; Director owns *project work* |
| **Uzella** | Site chat persona | Being retired → unbranded chat | uzelhub-web | Not a manager; a product surface |
| **Director (this)** | **Tasks/priorities across all three projects** | **Being composed now** | TBD (likely ai-agent-platform) | The new top of the stack |

**Sharpening question this raises:** is the Director a *manager* (plans, prioritizes, routes work
to projects/agents, surfaces cross-project dependencies) or also a *doer*? The sysadmin persona
draws a hard "propose, human approves, human applies" line — the Director likely wants the same
discipline.

---

## 6. Conventions the Director must respect (cross-cutting rulebook)

These are already-established patterns the Director should inherit, not reinvent:

1. **Read-before-write, observed/proposed/would-not.** From the sysadmin persona: every claim
   cites a just-run command; outputs distinguish what was *observed* vs *proposed* vs explicitly
   *rejected*. High-value pattern for a cross-project status role.
2. **Human approves, human applies.** No agent applies its own proposals. Blast radius bounded by
   a proposals dir / PR.
3. **Source-of-truth files over forensic reconstruction.** predictor's `operational-state.md` and
   the host `_host/README.md` are canonical; update them rather than spelunking git logs.
4. **Dev/prod separation.** Never treat `/opt/predictor_prod` as editable; it tracks `main`. Don't
   auto-pull dev. Caddy is operator-only.
5. **Sprint + ADR + stability-ordered planning.** ~2hr sprint units; architectural decisions get
   ADRs; backlogs are ordered safest-change-first and **model-tagged** (`[Opus]`/`[Sonnet]`/`[Manual]`).
   The Director's output should *speak this language*.
6. **The 4Cs methodology** — **Converse, Constrain, Construct, Curate** — is Dan's stated working
   philosophy (it's the uzelhub.com thesis and a TM candidate). A Director persona should embody it:
   *"build systems where thinking happens at a higher altitude."*
7. **Cost discipline + decision logging.** Pipelines log every LLM call to `agent_decisions` with
   token/cost; ai-agent-platform now has cost caps. A Director coordinating LLM work should be
   cost-aware.
8. **Brand/accuracy guardrails.** Respect `Uzelhub™`/`Uzella™`/4Cs marks and the no-overclaim copy
   rules when any work touches public surfaces.

---

## 7. Launchpad — open questions to answer before writing the persona

These are the decisions that will shape the persona. (Flagging, not deciding.)

1. **What does "manage tasks across three projects" concretely mean?** Candidate jobs:
   (a) **aggregate status** — one cross-project picture from each repo's backlog/plan/operational-state;
   (b) **prioritize** — propose what to do next and in which project, stability-ordered;
   (c) **route** — hand work to the right project/agent (Blog Director, sysadmin agent, a sprint);
   (d) **watch dependencies** — e.g. "predictor restart (ADR-010) must precede fresh blog material";
   (e) **track follow-ups** — the dated TODOs/landmines scattered across docs (synthetic-row cleanup, etc.).
   *Which of these is the Director's core? Probably (a)+(b)+(d).*
2. **Altitude: coordinator vs doer.** Propose-only (like the sysadmin agent), or allowed to open
   PRs / run sprints itself?
3. **Inputs & memory.** What does it read each cycle — the three repos' `git log`, `backlog.md` /
   `project-plan.md` / `operational-state.md`, the `_host` README, open PRs? Does it keep a
   cross-project ledger (where)?
4. **Cadence & trigger.** Scheduled (daily/weekly reflection like the sysadmin agent), or
   on-demand when Dan asks "what should I work on"?
5. **Relationship to sibling roles.** Does the Director *supervise* the Blog Director and sysadmin
   agent, or just *coordinate around* them? (Host vs project-work boundary already exists.)
6. **Where it lives / runs.** Likely codified in `ai-agent-platform` (`agents/director_agent.py`
   eventually), persona doc alongside the others. Confirm.
7. **Voice.** The sysadmin agent is deliberately SRE-terse with *no personality*. The Director is
   closer to Dan's own planning voice (4Cs, "higher altitude") — probably **more conversational than
   the sysadmin agent, still precise and non-hedging.** Decide the register explicitly.
8. **What it refuses.** Mirror the sysadmin agent's refusal list at project altitude (no touching
   prod, no applying own proposals, no editing Caddy, respect immutable incidents, etc.).

---

## 8. Source index (surveyed + drill-deeper)

**Read for this survey (high-signal):**
- predictor_ingest: [`README.md`](file:///opt/predictor_ingest/README.md), [`CLAUDE.md`](file:///opt/predictor_ingest/CLAUDE.md) (= AGENTS.md), [`docs/backend/operational-state.md`](file:///opt/predictor_ingest/docs/backend/operational-state.md), `docs/backlog.md` (head), `docs/project-plan.md` (head), `plan.md`, `CHANGELOG.md` (head)
- uzelhub-web: `BACKLOG.md`, `editing-notes.md`, `marketing/README.md`, `marketing/TODO.md` (README.md is empty)
- ai-agent-platform: [`README.md`](../../README.md), [`docs/uzelhub-crew/README.md`](../uzelhub-crew/README.md), [`server-maintenance-agent-persona.md`](../uzelhub-crew/server-maintenance-agent-persona.md), [`sysadmin-agent-design.md`](../uzelhub-crew/sysadmin-agent-design.md)
- host: `/opt/_host/README.md` (+ `incidents/`)

**Not yet read — drill here when composing (depth reserves):**
- predictor: `docs/architecture/adr-010-two-domain-restart.md` (the active plan), `docs/architecture/convergence-narrative.md` ("read first for big picture"), full `docs/project-plan.md` (968 lines, the sprint backlog), full `docs/backlog.md`, `docs/methodology/prediction-methodology.md`
- uzelhub-web: `mktg-notes.txt`, `services/uzella-proxy/PROMPT-LOG.md` (the existing persona-prompt log — directly relevant to persona craft), `marketing/TEMPLATE.md`
- ai-agent-platform: `docs/uzelhub-crew/sysadmin-agent-design.md` (full), `docs/uzelhub-crew/crawl-to-publish-plan.md`
- host: `/opt/_host/README.md` (full — the cross-project host map the Director may want to mirror at the project level)

---

## 9. Suggested next step

Two viable paths from here:
- **(A) Draft the persona now** off this blob, using the sysadmin-persona structure, and iterate.
- **(B) Deepen first** on the "drill-here" reserves in §8 (especially the Uzella PROMPT-LOG for
  persona craft and ADR-010 for what's actually in flight), then draft.

Recommendation: **(A)** — draft a skeleton persona answering §7's questions as explicit
"OPEN" placeholders, so the gaps drive the next round of reading rather than reading exhaustively
up front.
