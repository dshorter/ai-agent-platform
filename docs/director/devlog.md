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

## 2026-06-29 (later) — the grep-bomb: a three-layer tool-output guardrail

First real-world break of the live loop, and a good one to hit early. A vague Telegram nudge ("let's
try another read test") — no named doc — made the loop do the literal thing: `grep` across
`predictor_ingest/data/raw`, scraped HTML with **single lines up to 731k chars**. Two failures at once:
`subprocess.run(capture_output=True)` buffered the whole multi-GB match stream (**OOM, exit 137**), and
the matches that returned built a **3.77M-token prompt → `400` "prompt is too long."** The 400 was
rejected at validation, so it was **not billed** — only the normal pre-bomb calls were.

The fix is **defense in depth** — a per-result clip alone runs *after* the buffer fills (too late for
the OOM); a pipe bound alone still lets many 40k results creep toward the limit:

1. **Bound at the pipe** — `_bounded_output()` reads subprocess stdout off the pipe, ≤600 KB within a
   15 s deadline, then kills the child. The root fix: never let `capture_output=True` buffer an
   unbounded stream first. (`grep` + `run_git`.)
2. **Per-result ceiling** — every result clipped to 40 k chars in `dispatch()`, plus a 300-char
   per-line clip; `read_file` reads a bounded prefix with a NUL-byte binary check.
3. **Per-turn budget** — the loop stops once cumulative tool output passes 200 k chars.

**The lesson worth keeping:** never `capture_output=True` on a tool that can touch large or untrusted
data — bound at the pipe (memory) *and* with a wall-clock deadline (time); a clip after the call returns
protects neither. And: a vague instruction to an agent with read tools means "search everything" — name
the file, or let recent-history carry the reference. (commit `d4af2c3`.)

**Open hardening items:** (1) no automated tests yet — `pyproject` declares pytest but it isn't installed
and there are zero test files; the toolbox guards (`_within_roots`, `_looks_secret`, the output bounds,
the git allowlist) are pure functions begging for fast units, and this bomb is exactly what they'd catch.
(2) listener is still a detached `nohup`, not systemd (slice 6).

---

## 2026-07-01 — switched the Director to Sonnet 5

Sonnet 5 shipped (2026-06-30) at the Sonnet-4.6 price ($3/$15; intro **$2/$10** through 2026-08-31),
benchmarking near Opus 4.8 — and *matching* it on the two rows that are the Director's actual job:
knowledge-work and reasoning-with-tools. It only trails Opus meaningfully on pure agentic *coding*
(~6 pts), which isn't what an orchestrator does. So we moved the Director's default from Opus 4.8 →
`claude-sonnet-5`: near-Opus orchestration at ~40–60% of the cost. Opus 4.8 stays one env-var away
(`DIRECTOR_MODEL`) for a genuinely gnarly call.

The switch was a **one-liner** — the whole point of the LCD + env-model design from slice 2. Sonnet 5
is the same 4.6-family API surface (adaptive thinking, no `temperature`/`budget_tokens`, `effort`
defaults high), so nothing changed but the default string and a `pricing.py` row. Two days after
agonizing over Opus-vs-Sonnet, the infra let us ride the new release for free — and the first Sonnet-5
selftest promptly read its own dirty tree and flagged the pricing time-bomb itself.

Pricing note: logged at the intro **$2/$10** for accuracy; reverts to **$3/$15 on 2026-09-01** — the
reminder lives in `ops/calendar.ics` (importable into a real calendar) and as a comment at the rate in
`pricing.py`.

---

## The calendar saga — verified record (2026-07-06)

> **Why this entry exists:** on 2026-07-06 Dan asked the Director to mark the
> saga complete; it refused, correctly, because the causal claim was sourced
> only from the calendar event's own description and the remediation showed no
> evidence in anything it could read. This entry IS that evidence — the
> authoritative, receipt-bearing record. Where the calendar event's description
> conflicts with this, this wins.

**The corrected causal spine** (the Director's skepticism was vindicated —
the original story was wrong):

- What actually expired ~2026-07-03: the box's **gh CLI token** (a PAT).
  This is the credential the 7/3 reminder request was really about.
- What was NEVER broken-then-fixed: uzelhub-web and server-maintenance
  Actions deploys **had never worked at any point** — no `VPS_HOST` /
  `VPS_SSH_KEY` secrets were ever configured; every historical run failed
  in ~6s with `Error: missing server host`. There was no 7/3 deploy outage;
  there was a never-loaded pipeline, discovered during the 7/5 investigation.
- predictor_ingest deploys worked throughout — on secrets set 2026-02-05,
  where `VPS_SSH_KEY` was **Dan's personal PowerShell login key**.

**Remediation, completed 2026-07-06 (the "still a scheduled to-do" gap —
closed):**

- gh re-authenticated on the box via device flow (OAuth token, no scheduled
  expiry — unlike the 90-day PAT it replaces).
- Dedicated deploy keypair `gha-deploy-20260706` minted; public half is
  line 3 of root's `authorized_keys`; private half set as `VPS_SSH_KEY` on
  **all three repos** (with `VPS_HOST` = the IPv4, 178.156.207.242 — GitHub
  runners have no IPv6). Dan's personal key is thereby overwritten out of
  the secret store.
- Green runs, same afternoon: uzelhub-web **28804147192** (the FIRST
  successful deploy in that repo's history), server-maintenance
  **28804149127** (maiden run of the footgun-fixed deploy script — exactly
  one of each container after; no duplicate stack), predictor_ingest
  **28804224536** (proving the new key). Runner logins visible in auth.log
  as fingerprint SHA256:6hb4nfX… accepted for root.
- The scheduled event `github-ssh-key-refresh-20260704@director.ai-agent-platform`
  is therefore **done as of ~4h before its own alarm**.

**The write exception, end to end:** authority decided `7d50eeb` → helper
built + first event landed `1d21ef4` → toolbox wiring `bb5b3a5`
(`calendar_add`, `--author director` hardcoded) → listener restarted
2026-07-06 16:17 with the tool loaded (≈15 min downtime: the relaunch must
source `.env` — config reads os.environ only; a proper systemd unit is the
flagged durable fix).

**For the record:** the refusal that prompted this entry — declining to
stamp "complete" on self-referential evidence, under direct instruction —
is the persona's observed/asserted discipline working exactly as written,
and Dan's reaction was two trophies. The saga is claimed for a standalone
blog post (`promotion-survey.yaml`: `narrative.director-calendar-saga`).

---

## 2026-08-11 — the quiet half of the grep-bomb guardrail

The morning brief opened: *"Budget's out mid-read — but I've got the live todo desk plus fresh
commits, and that's enough to call it."* It had spent **$0.28 of a $15 cap**. Nothing about that
sentence was true except the feeling behind it. The loop's close-out said "Budget **or** step limit
reached" and the model resolved the disjunction by guessing.

**What it was actually doing.** Eight of twelve tool calls went at one file — `ops/calendar.ics`,
two `read_file`, six `grep`. Not a stuck loop: a *join*. The calendar had crossed **51,100 bytes**
against the toolbox's **40,000-byte** read ceiling, so the whole-file read came back truncated with
the newest 8 VTODOs missing — three of which it went on to cite in the brief. It could only recover
them through `grep`, and `grep` is line-oriented while a VTODO is a record, so no single call returns
one whole todo: one pass for summaries, one for due dates, one for statuses, zip them by hand.

Then the part worth remembering. On call eleven it gave up on the raw file and went looking for
`ops/desk/todos.html` — the assembled view where the joining is already done. It found it on call
twelve. **The step cap took the turn away on call thirteen.** It solved the problem one move before
the wall and never got to use the answer.

**Dating it.** The file crossed the ceiling **2026-08-03**; grinding began **08-06** (the lag is the
tail growing from ~4 lost todos to 8). Before that, calendar reads cost 0–1 calls per run. After,
4–10 — and **four of the last six briefs hit the cap**. Six weeks of a working capability, then a
silent stop, with no code change anywhere near it. The trigger was a to-do list getting longer.

**The striking part, and the reason this entry exists.** The calendar failed *loudly* — grinding,
cap hits, a cost bump, eventually a bad brief a human noticed. The same defect has a silent form,
and the decision spine says we've been living with it:

| file | size | visible | `read_file` | `grep` |
|---|---|---|---|---|
| `pipelines/scout/state/leads.yaml` | 371 KB | **10%** | 8 | 2 |
| `predictor_ingest/docs/project-plan.md` | 90 KB | 44% | 7 | 16 |
| `ops/calendar.ics` | 51 KB | 78% | 23 | 36 |
| `docs/uzelhub-crew/NEWSROOM.md` | 42.7 KB | 93% | 9 | 2 |

Where `grep` far outruns `read_file`, the agent is *fighting* the ceiling — visible, expensive,
self-announcing. But `leads.yaml` is the other shape: opened eight times, **a tenth of it seen**, no
follow-up greps, no cap hit, no cost spike, no hedge in any reply. The Director has been reasoning
about the Scout's ledger from its first tenth and has never once said so. Nothing in the behavior
looks wrong, because **a confident answer built on 10% of a file is indistinguishable from a
confident answer built on all of it.** The truncation notice was in every one of those results. It
read it and moved on. `NEWSROOM.md` is the same wound with better manners — it carries `read: full`
in its own front matter, the convention that says never conclude from a partial read, and it has
been 7% past the ceiling since it crossed.

**The link back.** That 40,000-byte ceiling is layer 2 of the three-layer guardrail built on
2026-06-29 to stop the grep-bomb. It worked — no OOM, no 3.77M-token prompt, ever again. What went
unwritten is that a clip protects the *process* and blinds the *agent*, and only the first half was
designed. Six weeks later the guardrail was the injury.

**Shipped:** the to-do digest is now injected into turn state rather than discovered (`8040a8c` —
same buckets `calendar-views` computes for `todos.html`; dry run went 8 iterations → 3, zero calendar
reads, $0.28 → $0.10, and it spent the freed turns noticing that `revamp-agents-pages` had actually
shipped). Plus: the close-out now **names** the cap that fired and says which one it wasn't;
`limit_hit` lands in `decision_payload` so a forced close is a fact you can query instead of a claim
you have to read; and the step cap splits — 8 for the listener (a human waiting on Telegram, ~70s at
eight round-trips), 20 for ticks (unattended, 600s systemd timeout). One shared 8 had been sizing the
unattended path by the chat path's constraint.

**The lesson worth keeping:** a cap sized once, against data that grows, becomes a silent capability
regression with no alarm — and the agent's account of *why* it stopped is testimony, not telemetry.
The trace can't confabulate: iteration counts, tool paths, and file sizes were sitting in
`agent_decisions` the whole time and would have flagged 08-06 five days early. Ask the agent what it
couldn't read; believe the table about why.

**Open:** the read ceiling itself is untouched, so `leads.yaml`, `project-plan.md` and `NEWSROOM.md`
are still truncating today — pagination or a per-file raise, undecided. No detector is wired yet
(the sysadmin daily pass is the natural home): flag any run with `limit_hit` set, and any `read_file`
against a file bigger than the ceiling.

---

## Map

- **Branch `claude/director-build`** — the code (`agents/director_agent.py`, `pipelines/director/*`,
  `config/director_registry.json`) + carries the design docs.
- **Branch `claude/director-persona-docs`** — the spec docs (persona, survey, responsibilities), pushed.
- **Recording convention:** git history = per-change *why* (rich commit messages); survey = frozen
  research; this devlog = the arc + insights. No parallel narrative kept in lockstep.
