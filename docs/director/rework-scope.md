# Director Rework — Scope (the autonomous-agent paradigm)

> **Status:** Scope / plan, 2026-06-27. The target we build against for the rework Dan's eureka
> triggered ([`devlog.md`](devlog.md) "BIG PARADIGM QUESTION"; the Director's own diagnosis in
> [`director-self-scope.md`](director-self-scope.md)).
>
> **One-line goal:** turn the Director from a *reactive one-shot chatbot* into an *autonomous,
> full-parity, scheduled agent* — same capabilities as the other agents, with persona discipline as
> the guardrail.
>
> **Progress (2026-06-29):** slices **1–3 shipped & live** on `claude/director-build` — persist-output
> + label fix (`dedfd7f`), Opus 4.8 + pricing (`d8f53a4`), and the **agentic read-only loop** + a
> **recent-history** turn-memory slice (this commit). The listener now runs the loop on Opus 4.8.
> Remaining: ledger (4), scheduled wake (5), propose-writes / systemd (6).

---

## The shift

| | Now (walking skeleton) | After (rework) |
|---|---|---|
| **Brain** | one `messages.create` call | ✅ an **agentic loop on the anthropic SDK** (not the Claude Agent SDK — see core #1) — reads/acts over bounded round-trips |
| **Sight** | a pre-fed git snapshot (metadata only) | ✅ **read the box on demand** — `read_file` / `grep` / `run_git`, scoped to the registered roots |
| **Memory** | none (only Dan's messages logged) | ✅ **recent-history** turn replay (raw); ⬜ a curated **ledger** it writes + loads at startup (slice 4) |
| **Trigger** | reactive only (Telegram) | ⬜ reactive **+ scheduled** (weekly cron, morning timer — slice 5) |
| **Model** | `claude-sonnet-4-6` (a default) | ✅ **`claude-opus-4-8`** (best Opus candidate in the crew) |

## What changes (the core)

1. **Agentic run, not one-shot.** ✅ `DirectorAgent.respond()` is now a bounded tool loop with
   tools: `read_file`, `grep`, `run_git` ([`pipelines/director/tools.py`](../../pipelines/director/tools.py)),
   bounded by an **iteration cap (`DIRECTOR_MAX_ITERATIONS=8`) + a cost cap** (`config.max_cost_usd`,
   the `PIPELINE_MAX_COST_USD` pattern) so it never spelunks forever.
   **Engine — corrected:** built on the **anthropic SDK** (the crew's own substrate), *not* the Claude
   Agent SDK. The scope originally said "Agent SDK" — that wording carried over from the content &
   marketing agents, which *are* built with it. But the Director's whole value is the sequence-aware
   logging + cost spine; the anthropic loop instruments every round-trip natively (tokens/cost → 
   `agent_decisions`), gives finer control over the caps and read-scoping, needs no `claude` CLI
   subprocess, and keeps the orchestrator on the same substrate as the rest of the crew. More tool
   code, but simpler code we own. (Decided with Dan, 2026-06-29.)
2. **Full-parity filesystem access.** Capability parity with the other agents — it can read the box.
   This dissolves awareness-vs-depth: it confirms what ADR-010 *says* before routing, reads `BACKLOG.md`
   before sequencing, sees the devlog and reasons from what *actually happened*.
3. **Persist the output + a ledger.** Store the Director's *reply* (currently dropped) and let it write
   curated observations as **building blocks**; load the harvest at startup. Closes insight-evaporation;
   enables the weekly report. *(Also fix the "you pasted the state" bug — label injected context as the
   Director's own observation, not Dan's message.)*
4. **Scheduled wake.** A **weekly cron** that polls the other agents' logs + project state (Dan's
   sketch), plus a morning-brief timer. The reactive Telegram listener stays as the on-demand window.

## What stays (reuse — the skeleton wasn't wasted)

- **Telegram surface** — now a *window* onto the agent, not its whole life. Switchboard routing, whitelist.
- **Logging spine** (`agent_decisions` / `SequenceAwareLogManager`) — still the audit + narrative substrate.
- **Registry** (`config/director_registry.json`) — still the map of work-projects.
- **Runtime shape** — wake → load state → work → persist → exit (stateless compute + persistent state).
  The "work" upgrades from one call to an agentic run.

## Guardrails — discipline, not capability limits

Parity means the OS doesn't stop it; the **persona** does — exactly how the sysadmin agent already works.

- **Read freely**, but don't pull secrets/credentials into reasoning.
- **Writes are proposed** (human approves) — *except its own ledger*, which it owns.
- **Never touch** Caddy, credentials, prod, the dev/prod split, or `/opt/_host` (write).
- Whitelist still gates the Telegram surface; iteration + cost caps bound every run.

## Proposed build order (incremental, shippable, observable)

1. ✅ **Persist the output** + fix the injected-context label. `dedfd7f`. *(Closed evaporation.)*
2. ✅ **Opus 4.8 flip** — `DIRECTOR_MODEL=claude-opus-4-8` + `pricing.py` rate. `d8f53a4`.
3. ✅ **Agentic run with full read** — anthropic tool-loop + `read_file`/`grep`/`run_git`, capped by
   iterations + cost. *(The paradigm slice.)*
3.5. ✅ **Recent-history turn memory** — replay the last N (user, reply) turns from the decision log so a
   thread feels continuous (`DIRECTOR_HISTORY_TURNS`, default 6; per-reply char cap). Newly possible
   *because* slice 1 persists replies. Folded in here (Dan, 2026-06-29); token-tunable via N.
4. ⬜ **Ledger write + load-at-startup** — *curated* memory across sessions (distinct from 3.5's raw
   recent turns: the ledger is the harvest of keepers).
5. ⬜ **Scheduled wake** — weekly cron (poll the agents) + morning timer.
6. ⬜ *(Later)* propose-writes to files; per-agent dispatch; systemd-ify the listener.

## Open questions

- **Briefs:** with full read, the heavyweight per-project *brief contract* downgrades to optional — a
  light registry pointer ("key docs live here") still saves a discovery step, but it's no longer the
  only window. Decide how much to invest.
- **Eyes (`project_state.py`):** becomes a *tool the agent calls* on demand, not a pre-load step.
- **Ledger schema:** what a building block is; how the curation pass decides "keeper."
- **Caps:** the right iteration + cost ceilings per run (reactive vs scheduled may differ).

## Pointers

- Eureka + arc: [`devlog.md`](devlog.md) · Director's own diagnosis: [`director-self-scope.md`](director-self-scope.md)
- Persona/spec: [`director-persona.md`](director-persona.md) · Foundation commits: `2977a30` (narrative
  substrate), `e49e8a5` (autonomous eureka), `d5b8cd4` (ledger slice).
