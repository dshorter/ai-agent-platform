# The Director — Devlog (the journey, the decisions, the insights)

> **What this is:** the narrative record of how the Director came to be — the arc, the load-bearing
> decisions *and their why*, the conceptual breakthroughs, and where things stand. Captured
> 2026-06-27, at the end of the build session, because the richest copy of this story lives in a
> conversation that doesn't persist. Commits hold *per-change* why; the frozen survey holds the
> *pre-build research*; **this holds the arc and the insights no single commit contains.**
>
> Companion docs: [`director-persona.md`](director-persona.md) (the spec / system-prompt source),
> [`director-survey.md`](director-survey.md) (frozen cross-project research),
> [`responsibilities.md`](responsibilities.md) (work inventory + parking lot).

---

## The arc

1. **Fuzzy idea → reserved name.** A "director" to manage work across projects. Renamed the existing
   blog reviewer to **Blog Director** to free the bare "Director" for this higher role (#10).
2. **Cross-project survey.** Mapped predictor_ingest, uzelhub-web, ai-agent-platform (+ the `_host`
   layer). → `director-survey.md`, later frozen.
3. **Persona, composed in conversation.** Modes, vehicles, runtime, voice — drafted as a prompt-shape,
   iterated against Dan's phone-edits, the Claude Tag research detour, and a lot of "don't over-build."
4. **Walking skeleton built (2026-06-27).** `agents/director_agent.py` + `pipelines/director/`
   (config, raw-httpx Telegram client, store, listener, selftest). Reasoning + logging proven via
   selftest before Telegram even existed.
5. **Live on Telegram.** BotFather bot → token + whitelisted user id → listener picks up the pending
   message → the Director replies *on Dan's phone*. ("Same album as the baby pictures.")
6. **Eyes.** Project registry + a fresh per-turn git snapshot fed into reasoning. "I can't see
   anything" became a ranked, reasoned cross-project plan citing real branches/commits — including,
   amusingly, its own in-progress construction.
7. **Design conversation on persistence + knowledge** (this session's tail) — the insights below.

---

## Load-bearing decisions (and why)

| Decision | Why |
|---|---|
| **Verbs, not nouns** | The Director sequences/tracks/routes/frames/conceptualizes; it is not any project's domain expert. Lets wildly different work flow through one coherent persona. |
| **Three modes: OWN / ROUTE / FRAME** | One triage rule for any incoming item. OWN = project work; ROUTE = design questions (drafts a *proposed* artifact, Dan decides); FRAME = strategy (positions it, Dan decides). |
| **Two vehicles: Front Desk + Director** | Capture must be category-blind (Front Desk); sorting is the Director's job. The Director's **ledger** is its own hopper — *not* the raw inbox. |
| **Signature deliverable = a priority-setting report** | Everything feeds "what to do next, where, in what order, and why." |
| **Runtime = stateless compute + persistent state** | No resident daemon. A thin listener + timers wake it; it loads state, reads fresh, reasons, persists, exits. Reboot-proof, and it *enforces* "rank from what you read just now." |
| **Surface = one Telegram bot, slash-command switchboard** | `/director` `/sysadmin` `/blog`; bare text → Director (default + dispatcher). Long-poll = no inbound exposure. Bots aren't E2E → channel is convenient-not-confidential. |
| **Logging = reuse the spine** | Writes to `agent_decisions` via the existing `SequenceAwareLogManager`. The log doubles as **narrative substrate** for the weekly editorial pass. |
| **Eyes (v1) = git state per registered project** | Cheap, fresh, ground-truth. (Durable-doc *depth* is next; see below.) |
| **Projects-as-data** | Registry (`config/director_registry.json`); adding a project is a data edit, not a rewrite. |

---

## Conceptual breakthroughs (the stuff not in any commit)

- **Persistence is curation, not hoarding — the 4Cs are the Director's metabolism.** We built the
  Director *by* running Converse→Constrain→Construct→Curate on it. It should run the same loop on its
  own stream: the decision log is the *compost* (raw everything); the **ledger is the curated bed**
  (building blocks). At startup it loads *the harvest, not the compost.* "4C fractal, bro."
- **The hygiene-skew was a symptom of git-only eyes.** With only git visible, uncommitted files are
  the loudest signal, so it ranked tidying over substance. Give it the design docs → the ranking
  rebalances. *Behavior = persona × inputs.*
- **Awareness vs. depth.** It needs *awareness* of which design docs exist (always) and *depth* into a
  specific doc's contents (only when a decision touches it). A brief can't *replace* ADR-010; it can
  *point* to it.
- **The brief is the one uniformity; its innards are per-project.** Every registered project has a
  **brief** with a fixed shape (Purpose · Current focus · State-lives-in → · Key-design-docs → ·
  Prioritization notes). What it links to varies by project. The Director codes against *one*
  contract, never N repo layouts. Registering a project = writing its brief.
- **Git is the lie-detector.** A brief is hand-tended and *can* drift; git status can't. Pair them and
  the Director cross-checks: "brief says active focus, git's been dormant 3 weeks → your brief's
  drifting." The ground-truth layer keeps the curated layer honest. Git stays bedrock; briefs sit on top.
- **Insight evaporation is the real cost of no persistence.** We watched the Director produce a genuine
  cross-project insight ("the platform *is* the product story uzelhub is telling") — and it lived only
  in Telegram, never in our spine. That's the motivator for the ledger.

---

## State of play

**Built + live:** walking skeleton (reasoning, logging, Telegram switchboard, whitelist), the eyes
(registry + git snapshot). Running as a background listener (not yet a real systemd service).

**Designed, not built:**
- **Ledger / persistence** (the 4C curation layer) — store the *reply*, curate keepers into building
  blocks, load the harvest at startup. *Highest-leverage next slice; agreed to do before grep.*
  **The weekly report is its payoff:** the Director compiles the week from its accumulated harvest
  (ledger entries + decision-log *reasons* + git) → synthesize → route (stories to the blog pipeline;
  a status roll-up to Telegram). So the weekly report (editorial *and* status flavors) can't be built
  before persistence — it's a *consumer* of the ledger, not a separate design problem. Driven by a
  weekly ambient timer.
- **Briefs** (uniform per-project) + **durable-doc depth** (read the named doc, cached standing
  context — bounded, not a repo crawl). Grep/agentic tools deliberately deferred.
- Ambient timers (morning brief, stall sweeps, weekly editorial pass), the Front Desk, the sysadmin
  agent, per-agent voices, "the Historian" (parking lot).

**⚑ BIG PARADIGM QUESTION (Dan's eureka, 2026-06-27 eve — revisit FIRST):** every *other* agent
(blog crew, sysadmin) is an **autonomous process** — spins up on a schedule, full filesystem
read/write, goes and *does* things, exits. The current Director is the odd one out: a **reactive
one-shot chatbot** that can only reason over the git snapshot we pre-feed it. That inversion — the
*orchestrator* being the *least* autonomous agent — is the friction. The real model is an
**autonomous, full-FS, scheduled agent** that wakes and "pops around the place" (reads files freely
across projects for real summary data; writes its outputs — ledger, briefs, the morning/weekly
report). The Telegram chat is a *window* onto it, not its whole life. Implication: file access isn't a
risky bolt-on we deferred — it's **parity with its own workers.** Discipline: **read freely; *propose*
writes (human approves), à la the sysadmin agent.** Most of what's built survives (runtime, surface,
logging, registry); what upgrades is the *core* — one-shot LLM call → agentic run. **Don't rebuild
tonight; this is the first conversation tomorrow.**

**Open questions:** the brief schema's final fields; "named-doc depth" vs. genuinely needing to *find*
unnamed docs; making the listener a real service; persisting the Director's *output* (not just the
user message) in `agent_decisions`.

---

## 2026-06-29 — slices 1–3: the autonomous loop, built

The eureka became code. Three slices shipped and went live on `claude/director-build`:

- **Slice 1 (`dedfd7f`)** — persist the Director's *reply* into `agent_decisions` (it was evaporating —
  we'd logged only Dan's messages) and fix the "you pasted the state" bug by labelling the injected git
  snapshot as the Director's *own* observation. Small, but it unlocked slice 3.5 (see below).
- **Slice 2 (`d8f53a4`)** — flip the model to **`claude-opus-4-8`** and add its rate to `pricing.py` so
  cost-tracking prices the runs instead of writing NULL. The cross-cutting job is the right Opus candidate.
- **Slice 3** — the paradigm slice: `respond()` is now a **bounded read-only agentic loop** with
  `read_file` / `grep` / `run_git`, capped by iterations + cost.

**The engine decision (the real fork).** The scope said "Claude Agent SDK — already a dependency," and
that was *true* (`claude-agent-sdk 0.1.68` is installed). But we chose the **anthropic SDK tool-loop**
instead. Why: the Director's entire value is the sequence-aware logging + cost spine, and the anthropic
loop instruments every round-trip natively (tokens/cost → `agent_decisions`), gives finer control over
caps and read-scoping, and needs no `claude` CLI subprocess. The "Agent SDK" wording had carried over
from the **content & marketing agents, which *are* built with it** — and that's the insight: it's a
**principled producer-vs-orchestrator split**, not an inconsistency. Producers get the batteries-included
SDK; the orchestrator lives *on* the spine. More tool code, but simpler code we own.

**Guardrail = discipline, made literal.** "Propose writes, human approves" isn't enforced by a permission
prompt — the loop simply has *no write tool*. Reads are scoped to the registered roots (`..`/symlink
rejected), credential-shaped files refused. The OS doesn't stop it; the tool surface does.

**Slice 3.5, folded in — recent-history.** Replay the last N (user, reply) turns from the decision log so
a thread feels continuous. This was Dan's "was the chat context going back to the agent?" question — the
answer was *no* (the `history` hook existed but was never populated). It's newly *possible* precisely
because slice 1 stopped the replies evaporating. Distinct from the slice-4 ledger: 3.5 is raw recent
turns, the ledger will be the curated harvest.

**The moment it proved itself.** First real agentic run, asked to read the rework-scope doc: it read the
doc, then *kept going* — ran `git log`/`status`/`diff`, found its own half-written slice-3 files in the
working tree, cited `dedfd7f`/`d8f53a4`, grepped for the cost cap, and flagged "I see the iteration cap
but not the cost cap — confirm before you commit." (A false alarm — the cost cap *was* wired — but it
hedged honestly instead of asserting.) That's the read-the-box paradigm working: ground truth over
snapshot, with calibrated uncertainty. Logged trace + tokens + cost, all in the spine.

---

## Map

- **Branch `claude/director-build`** — the code (`agents/director_agent.py`, `pipelines/director/*`,
  `config/director_registry.json`) + carries the design docs.
- **Branch `claude/director-persona-docs`** — the spec docs (persona, survey, responsibilities), pushed.
- **Recording convention:** git history = per-change *why* (rich commit messages); survey = frozen
  research; this devlog = the arc + insights. No parallel narrative kept in lockstep.
