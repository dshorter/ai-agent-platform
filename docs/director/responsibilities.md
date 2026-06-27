# Dan's Responsibility Inventory (working)

> Seeded 2026-06-27 from the Director design sessions — **what's already surfaced in our work + the
> surveys.** A base to add to, *not* exhaustive. This is the kind of inventory the Director triages
> (OWN / ROUTE / FRAME / lane). Tags in brackets. Add, correct, delete freely.

## Build — project work

- **predictor_ingest** — two-domain restart (ADR-010: film + semiconductors); clear synthetic
  `trend_history` rows (D5 — blocks restart); install the cron; calibrate after the first 2 weeks;
  the `project-plan.md` sprint backlog; EXT-* prompt/gate tuning. `[OWN]`
- **uzelhub-web** — marketing-site rebuild (product cut-sheet catalog); per-project about pages;
  landing-page copy/editing pass (`editing-notes.md`); Uzella retirement → unbranded chat; stand up
  `studio.uzelhub.com`; visual-identity sign-off; Uzella tone toggle (backlog). `[OWN]`
- **ai-agent-platform** — Sprint Zero blog pipeline (open PR: `sprint-zero-hardening`); blog crew
  (Content/Marketer) operation. `[OWN]`
- **rag_pipeline** — survey + decide whether to register as a work-project. `[OWN — your call, "not yet"]`

## Cross-project / the agents (platform plumbing)

- **The Director** — this design → build it (persona ~done; build listener, ledger, registry, timers). `[OWN]`
- **The Front Desk** — the capture/intake vehicle (sibling to the Director) — design + build. `[OWN]`
- **Sysadmin / server-maintenance agent** — designed, not built (Sprint One+). `[OWN]`
- **Telegram interaction surface** — implement the bot + listener (leading candidate). `[OWN]`
- **`ai-agent-platform/docs/decisions/`** — stand up at the first cross-project decision. `[OWN — deferred]`
- **Predictor images → marketing pages** — cross-project dependency (blocked on marketing going live). `[OWN — blocked]`
- **"Should the sysadmin agent know when `make daily` runs?"** — routed design decision. `[ROUTE]`

## Get-it-out-there — content / brand / GTM

- **The blog** — publishing cadence; start now vs build audience first. `[FRAME / OWN]`
- **Social-media reset** + when to add blog↔social links (phase in?). `[FRAME]`
- **Marketing site (uzelhub.com)** — positioning + copy accuracy guardrails. `[OWN / FRAME]`
- **Brand / trademark** — Uzelhub™, Uzella™, the 4Cs mark; trademark-attorney consult. `[FRAME / lane]`
- **"Claude Code as a Toolset" case study** — portfolio/content piece (parked). `[lane / OWN]`

## People

- **Collaborator path** — the site's outreach/engagement journey; networking, collaborations. `[lane / FRAME]`

## Teach / share

- **Investigate teaching a class** — your own example. `[lane]`
- Talks / writing (implied). `[lane]`

## Run the shop — ops / admin / legal

- **Host / ops** — `/opt/_host` map upkeep, B2 backups, safe-reboot, systemd units (mostly the
  sysadmin agent's beat). `[sysadmin lane]`
- **Dev/prod split upkeep** (predictor). `[OWN / ops]`
- **Finances / cost** — LLM spend tracking, budgets (lightly touched so far). `[lane]`
- **Legal** — trademark filings (overlaps brand). `[lane]`

## Parked / Not-in-v1 (already decided)

- Calendar integration (deferred).
- `rag_pipeline` registration ("not yet").

## Gaps — your turn (not yet surfaced)

- **Learn / explore** lane — staying current, R&D (nothing specific flagged yet).
- **Personal** lane — undefined (what should the Director be aware of, or explicitly stay *out* of?).
- _…whatever else is in your head._
