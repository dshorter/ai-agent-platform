# Director Rework — Scope (the autonomous-agent paradigm)

> **Status:** Scope / plan, 2026-06-27. The target we build against for the rework Dan's eureka
> triggered ([`devlog.md`](devlog.md) "BIG PARADIGM QUESTION"; the Director's own diagnosis in
> [`director-self-scope.md`](director-self-scope.md)).
>
> **One-line goal:** turn the Director from a *reactive one-shot chatbot* into an *autonomous,
> full-parity, scheduled agent* — same capabilities as the other agents, with persona discipline as
> the guardrail.

---

## The shift

| | Now (walking skeleton) | After (rework) |
|---|---|---|
| **Brain** | one `messages.create` call | an **agentic loop** (Claude Agent SDK) — reads/acts over multiple round-trips |
| **Sight** | a pre-fed git snapshot (metadata only) | **full filesystem read** — opens ADRs, backlogs, devlogs, *on demand* |
| **Memory** | none (only Dan's messages logged) | a **ledger** it writes to + loads at startup → continuity across sessions |
| **Trigger** | reactive only (Telegram) | reactive **+ scheduled** (weekly cron, morning timer) |
| **Model** | `claude-sonnet-4-6` (a default) | **`claude-opus-4-8`** (best Opus candidate in the crew) |

## What changes (the core)

1. **Agentic run, not one-shot.** Replace `DirectorAgent.respond()`'s single call with an agentic loop
   (the **Claude Agent SDK** — already a dependency) that has tools: read-file, grep, run-git. Bounded
   by an **iteration cap + a cost cap** (`PIPELINE_MAX_COST_USD` pattern) so it never spelunks forever.
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

1. **Persist the output** + fix the injected-context label. *(Tiny; do first — closes evaporation.)*
2. **Opus 4.8 flip** — `DIRECTOR_MODEL=claude-opus-4-8` + add it to `pricing.py` rates.
3. **Agentic run with full read** — SDK loop + read/grep/git tools, capped. *(The paradigm slice.)*
4. **Ledger write + load-at-startup** — memory across sessions.
5. **Scheduled wake** — weekly cron (poll the agents) + morning timer.
6. *(Later)* propose-writes to files; per-agent dispatch; systemd-ify the listener.

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
