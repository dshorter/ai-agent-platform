# AGENTS.md — how to find out before you change something

**This file is a router, not a reference.** It is deliberately thin. Nothing here
is the authority on anything; every row points at the document that is. If this
file and a linked document disagree, the document wins and this file is stale —
fix it.

It exists because of a specific failure on 2026-08-31. A request for "spend in
the Director's report" was answered by writing 445 aggregate rows into
`agent_decisions`, a table whose every other row is a single agent invocation.
Nothing was broken by it and the code worked — which is exactly the problem. A
locally-efficient fix had quietly re-decided a boundary the estate had already
decided on purpose. The knowledge was written down; it just wasn't reachable in
the moment it was needed.

**The rule this file exists to serve:** when a change would cross a boundary
between two components — a new writer to a shared table, a new dependency
between repos, a new consumer of someone else's data — stop and read the row
below before writing code. Either of us can call it: *"check the map."*

## Shared surfaces — read the authority before you write to one

| Surface | What it is | Read first |
|---|---|---|
| `agent_decisions` (Postgres) | The crew's decision trace. **One row per invocation**, with a curated vocabulary behind a foreign key (`decision_types`). Adding a type is a decision, not a detail. | `ops/desk/agent-roster.html`, and the OPEN question below |
| `hvac-postgres` cluster | Two databases (`ai_agent_platform`, `hvac_demo`) in one container. Backups are `pg_dumpall` only — **no per-table or per-database restore point.** Rolling back to undo a small mistake destroys everything written since. | `/opt/_host/README.md` §Databases, §Backups |
| `ops/calendar.ics` | The to-do/calendar SSOT. Agents write **only** through `calendar-add` / `calendar-mark`; freehand edits are operator-only. Namespaces are the security model. | `ops/CALENDAR.md` |
| Redaction gate | Blocks secrets reaching this **public** repo. `allow.txt` keys are value-level with **no path scoping**, so a dismissal silences that string everywhere, permanently. Dismissals are the operator's call, not an agent's. | `/opt/_host/redaction-gate/README.md` |
| This repo | **Public. A push is a publish.** Transcript-derived material stays in gitignored state, never the tracked tree. `ops/desk/` is gitignored (assembled/served). | `/opt/_host/README.md` |
| Apex docroot | `/opt/uzelhub-web` working tree **is** the live site. A file dropped in is published instantly, before any commit. | `/opt/_host/README.md` |

## Where design lives

| Area | Authority |
|---|---|
| The whole box — layout, ports, databases, overlaps | `/opt/_host/README.md` (`read: full`; _host has **no remote**, never add one) |
| What actually runs, verified against timers and tables | `ops/desk/agent-roster.html` |
| Newsroom: registers, routing, who holds which text | `docs/uzelhub-crew/NEWSROOM.md` |
| Calendar helpers, namespaces, verbs | `ops/CALENDAR.md` |
| SEO across apex/blog/corpus/syndication | `/opt/_host/SEO.md` (`read: full`) |
| Director's own memory across runs | `docs/director/director-ledger.md` |
| Predictor: charter, domains, pipeline, deployment | `/opt/predictor_ingest/AGENTS.md` |
| Predictor cost governance and the film decisions | `/opt/predictor_ingest/docs/architecture/adr-011-*.md` |
| How silent failures happen here, with worked examples | `docs/uzelhub-crew/silent-instruments-2026-08-29.md` |

## Neighbours, and what is deliberate about them

- **`/opt/predictor_ingest` is a separate repo with its own charter** — plain
  Python + SQLite, no infra dependencies. It does not import from this repo and
  must not gain a Postgres dependency casually; a Postgres outage must never be
  able to fail or truncate a predictor run.
- **The predictor is deliberately outside `agent_decisions`.** It is a pipeline,
  not an agent with a persona.
- **`/opt/_host` is the cross-project truth map and has no remote.** That is
  deliberate: it holds the redaction vocabulary, and a list of employer
  identifiers in a public repo is the disclosure it exists to prevent.

## Open questions — where drift happens

Settled boundaries are safe; open ones are where a locally-sensible change
casts a vote without anyone noticing. These are open:

- **Should pipelines that spend money unattended be in `agent_decisions`?**
  Today they are not, on the grounds that they are not agents. ADR-011 D4 argues
  the test should be "calls a paid API unattended," not "is an agent" — which
  would pull the predictor in. **Do not add a pipeline to that table without
  settling this first**, and if it is settled, it wants one row per *run* with a
  real `run_id`, not backfilled aggregates.
- **Should the visitor-facing agents be in the trace?** `agent-roster.html`
  records the finding and the fix ("what's missing is an INSERT and a grant").
- **Should redaction dismissals be path-scoped?** They are global today, which
  is why two commits sit blocked rather than dismissed.

## Conventions

- A document marked `read: full` is read whole before acting on it. Never
  conclude from a range-read. (Convention defined in `/opt/_host/README.md`.)
- Docs are never silently rewritten. Corrections carry a date and keep the
  original claim visible.
- Operator/sudo work ships as a runnable script — backup, validate, self-verify,
  restore on failure — never as a config paste.
