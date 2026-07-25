# Sysadmin Agent — Design

> **Status:** BUILT (daily pass) 2026-07-23 — `agents/sysadmin_agent.py` + `pipelines/sysadmin/` + `ops/ledger-append` + `deploy/systemd/sysadmin-daily.*`; timer install + journal group are operator gates (`deploy/systemd/README.md`). Hourly probe, weekly reflection, monthly drill: not yet built. Design history: draft from manual ops through 2026-05-27; pre-build sweep 2026-07-23 folded in the sibling-build lessons and post-07-06 state changes (§Pre-build sweep)
> **Sprint:** One+ (not yet started; Content/Marketer agents come first)
> **Relationship to crew:** The Sysadmin agent is the *third* role after Content (Sprint Zero) and Marketer (Sprint Zero). Developer and Solution Engineer agents come after.

---

## What this is

The Sysadmin agent is the crew member that owns the host these other agents run on. It is **not** a chatbot for ops questions and **not** an autonomous remediator. It is a scheduled reconciliation loop that:

1. Re-reads what the system actually looks like
2. Compares it to the documented intent (`/opt/_host/README.md`, compose files, systemd units, `safe-reboot`)
3. Flags drift, missing coverage, and recurring incidents
4. Proposes patches (PR-style) that a human approves before they land

The shape is "weekly reflection + targeted reconciliation," not "always-on root agent." A bot with root that can act unilaterally is the wrong shape for a single-operator VPS — the blast radius of a bug is the whole hub.

---

## Why now — what triggered the design

Two weeks of drift made `/opt/_host/README.md` materially wrong in five places, even though it had been "last verified" 17 days prior. The discovery path was a human (the operator + an interactive Claude session) walking the box and noticing. Specifically, by 2026-05-27 the operator found:

| Drift | Time to detect, manual | What a Sysadmin agent should have caught |
|---|---|---|
| `rag_pipeline/` (new project) appeared 2026-05-18, not in README | 9 days | Diff `/opt/` against the projects table |
| `incident-2026-05-11/` (cryptominer evidence) preserved but never linked | 15 days | Watch for `_host/incidents/*` directories; cross-link in README |
| Existing `scripts/backup.sh` was never scheduled | months (unknown) | Audit scripts in repos vs cron/systemd timer coverage |
| `backup.sh` referenced wrong docker volume name (`ghost-content` vs `server-maintenance_ghost-content`) | months | Diff docker volume list against script literal strings |
| Ghost outage recurrence — `server-maintenance.service` didn't prevent the second occurrence | hours of customer-facing downtime | Recurrence detection: same failure mode + same recovery command twice → escalate |
| `safe-reboot`'s scope description in README was reversed (manages server-maintenance, not ai-agent-platform) | unknown | Reconcile prose claims against script `$PROJECT_DIR` value |

None of these are exotic problems. They're all "did the docs keep up with the state" — a tedious but pattern-bound task. The right tool for it is a scheduled agent, not a human re-reading the README every Saturday.

---

## Scope — what it owns, what it doesn't

### Owns

- **Documentation reconciliation.** Re-derive the truth tables in `/opt/_host/README.md` (projects, ports, volumes, systemd units, databases) from live system inspection. Flag deltas as a PR-like patch proposal.
- **Coverage audits.** Every script in any `scripts/` directory under `/opt` should be either (a) scheduled via cron/systemd, (b) called by another scheduled thing (e.g. `safe-reboot` → `backup.sh`), or (c) explicitly marked as manual-only in a `MANUAL.md` or a comment header. Anything else is a "loaded gun unloaded" and gets flagged.

  > **Logged in advance, 2026-07-20 — first real target once this agent exists.**
  > `predictor_ingest`'s daily pipeline (`make daily DOMAIN=<film|semiconductors|weapons_detection>`)
  > has systemd units fully written in `deploy/systemd/` (`predictor-daily@.service`
  > + per-domain `.timer`s, `predictor-staleness.service/.timer` with
  > `OnFailure=notify-telegram@%n.service`) but **not installed** — a textbook
  > "loaded gun unloaded." **Not an oversight to flag as new drift**: the operator
  > made a deliberate, dated choice on 2026-07-20 to run these manually (login
  > ~7pm daily, all three domains) rather than install the timers yet. The agent's
  > coverage audit should recognize this as an acknowledged manual-only case once
  > it's marked as such (a comment header in the unit files, or an entry in
  > `/opt/_host/README.md`'s coverage table) — not re-flag a choice already made.
  > Two related gaps worth the same audit pass: (1) predictor_ingest's entry in
  > `config/director_registry.json` still describes pre-restart state (says
  > "Currently dormant... ADR-010 plans a restart") — Director's project_state
  > snapshot is git-only (branch/commits/working-tree), so it never notices
  > pipeline-level activity or staleness on its own; (2) Director and
  > `notify-telegram` share a bot token but Director's `getUpdates` long-poll
  > never sees `notify-telegram`'s own outbound `sendMessage` pages (Telegram's
  > API doesn't loop a bot's sent messages back to itself) — so today, nobody
  > but the operator's phone sees a predictor staleness page. Session:
  > `session_01Jmi2eGGfSsh1PML5aGcQRQ` in predictor_ingest, if more context is
  > needed later.
  >
  > **Amended 2026-07-23:** the operator ran the install block on 2026-07-22 —
  > `predictor-daily-{film 06:00, semiconductors 06:45, weapons_detection 07:30}`
  > plus `predictor-staleness` (6h) are installed, enabled, and firing (the
  > third domain is weapons_detection, which queue-jumped fusion). The
  > manual-only carve-out above is history; the audit's job here flips to the
  > normal one — verify the timers fire and their `OnFailure=` pages. Related
  > gaps (1) and (2) remain live: the registry note still says "dormant"
  > (re-verified 2026-07-23), and nobody but the operator's phone sees a
  > staleness page.
- **Drift detection between compose files and running containers.** Compare `com.docker.compose.project` labels on running containers against the `docker-compose.yml` files in `/opt/*/`. The current overlap (server-maintenance compose file defines all services but only owns ghost) is exactly the kind of thing this catches.
- **Backup verification.** Beyond "backup ran without error" — periodic *restore drills* into a scratch directory, confirming files extract and DB dumps are valid (mysqlcheck / pg_dump --schema-only roundtrip). Cadence: monthly.
- **Recurring incident detection.** If the same failure mode appears in `journalctl` within N days, that's worth a human's attention — not "another auto-restart."
- **Credential scope audits.** Read the rclone config, B2 key capabilities (via B2 API), and flag if scopes have widened (e.g. delete capability appeared on the backup key).
- **`safe-reboot` coordination.** Expose itself as a pre-flight hook so the operator's reboot command can pause and ask "the sysadmin agent has an open drift PR — proceed anyway?"

### Does NOT own

- **Live container management.** Restarting failed containers stays with `unless-stopped` + the per-project systemd units. The agent does not autonomously `docker compose up -d` anything.
- **Caddy config edits.** Public listener changes need human review. Agent proposes; human applies.
- **Secret rotation.** Out of scope for v1. Possible v2 if a real secret manager (Vault, etc.) gets introduced.
- **Cost optimization.** Not a finops bot. B2 spend and Hetzner spend are operator concerns.
- **Security response.** If an incident directory under `/opt/_host/incidents/` appears, the agent *notices and links it* but doesn't investigate. That's a human-led process.

---

## Operating loop

```
hourly:   light health probe (caddy, blog endpoint, n8n endpoint, B2 reachability)
          → emit a row to agent_decisions on anomaly only

daily:    coverage audit (scripts vs schedule, volumes vs script references,
          compose-file vs running-containers)
          → produce a delta report; if empty, log "clean"; if non-empty, open
            a draft patch against /opt/_host/README.md (or relevant compose file)

weekly:   reflection loop
          → read past week's agent_decisions rows + journal patterns
          → look for recurring incidents (same unit, same error, > N times)
          → propose: README updates, new systemd unit, or escalation note

monthly:  restore drill
          → pull most-recent host-*.tar.gz from B2 into /var/tmp/restore-drill/
          → extract, verify ghost SQL dump replays into a throwaway mysql container
          → write report to agent_decisions, delete drill directory
```

Each step produces an artifact (decision row + optional patch file). Nothing is applied without operator approval — patches are written to `/var/lib/sysadmin-agent/proposals/` as `.diff` files; operator runs `sysadmin-agent apply <id>` to land them.

---

## Tools the agent needs

| Tool | Why |
|---|---|
| Read-only shell with `docker`, `systemctl`, `journalctl`, `find`, `git log`, `cat` | Inspection |
| Read access to all `/opt/**` | Diffing docs vs state |
| Read access to `/etc/systemd/system/`, `/etc/caddy/`, `/usr/local/sbin/` | Same |
| Read access to `/root/.config/rclone/rclone.conf` (or just the file's existence + structure) | Capability audit; *not* the application key itself |
| B2 API read access via a separate "audit" key (listKeys, listBuckets, listFiles) | Credential scope audits; restore drills |
| Write access to `/var/lib/sysadmin-agent/proposals/` only | Patch proposals — no direct writes to live config |
| Postgres write to `agent_decisions` table | Decision trace, shared with Content/Marketer |
| Outbound HTTPS to `api.telegram.org` via `notify-telegram` helper (sendMessage only) | Failure-class push notifications |
| No `sudo`, no `docker compose up`, no `systemctl start/restart`, no rclone delete | Hard-coded absences |

This is the minimum capability surface. The agent's identity should be a dedicated user (e.g. `sysadmin-agent`) with these rights, not root with self-restraint.

---

## Integration with existing pieces

- **`backup.timer` + `backup.service`** — agent reads journal output, flags failures, notes upload size trends. Does not invoke directly.
- **`safe-reboot`** — agent registers itself as a pre-flight hook. If there are unmerged proposals or a recent unresolved incident, the script asks before proceeding. The agent never *initiates* a reboot.
- **`agent-platform-health.timer`** — agent treats this as a data source (per-hour signal), not a thing it manages.
- **`docker-prune.timer`** — agent watches that it ran; flags if not.
- **`agent_decisions` table** — shared decision trace. The Sysadmin agent's rows use `agent_role = 'sysadmin'`.

---

## Notifications — Telegram push

> **Decided 2026-07-02.** Motivating incident: the off-site B2 upload failed silently from ~2026-06-09 to 2026-07-02 (storage cap exceeded). Nothing on the box could push "backups are broken" to a human; discovery took a manual audit three weeks later. The proposals directory + a log line is the right channel for *drift*; it is the wrong channel for *failure*.
>
> **Implemented 2026-07-02** (helper + backup coverage, ahead of the agent): `/usr/local/sbin/notify-telegram`, config at `/etc/default/notify-telegram` (root:root 600 at install — **corrected 2026-07-23:** live mode is 640 root:**claude**, deliberately group-readable so agents running as `claude` can send, per the claude-sender doctrine in server-maintenance `docs/alerting/`; delivery proof is syslog's `sent:` line, never the helper's exit code, which is 0 by design even on failure; mirrors `DIRECTOR_TELEGRAM_*` from `/opt/ai-agent-platform/.env` — rotate both together), template unit `notify-telegram@.service`, `OnFailure=` on `backup.service`, and a warn-counting page at the end of `backup.sh`. Shared-channel convention: every message is prefixed `[AGENT]`, uppercased — one chat, many senders. The bot is the same one the Director listens on; this helper only ever sends.

**Mechanism.** A small shared helper, `/usr/local/sbin/notify-telegram`, wrapping a single Bot API call (`sendMessage`). Bot token + operator chat ID live in `/etc/default/notify-telegram` (root:root, mode 600) — same single-source-of-truth pattern as the env-var lesson below. The agent calls the helper, but so can plain systemd units (`OnFailure=notify-telegram@%n.service`), which means `backup.service` failures get push coverage *before* the agent exists. Build the helper first; it stands alone.

**What pushes vs. what logs.** Push is reserved for failure-class events:

- `backup.service` failure, or an off-site upload/prune WARNING in its journal output
- restore drill failure (monthly loop)
- recurring-incident escalation (weekly reflection loop)
- hourly health-probe anomaly that persists across two consecutive probes (debounced — one flapping endpoint is a row in `agent_decisions`, not a page)

Everything else — drift deltas, clean audits, new proposals — stays in the proposals directory and `agent_decisions`. The only non-failure push is a weekly one-message digest ("3 proposals open, 0 incidents, backups green"), so a silent bot is itself a signal.

**Constraints.**

- Hard cap on pushes per day (default 10); overflow collapses into a single "notification storm — see journal" message. Same runaway-loop spirit as the `agent_decisions` rate limit.
- Message bodies carry unit names, timestamps, and a one-line error class — never secrets, tokens, dump contents, or anything from `incidents/`. Telegram is an external service; treat every message as published.
- Send failures are logged and non-fatal. A Telegram outage must never block the caller — in particular it cannot abort `safe-reboot` or a backup run.
- Outbound-only: HTTPS to `api.telegram.org`, `sendMessage`, nothing else. No polling, no inbound commands. The bot is a pager, not a control channel — accepting commands from Telegram would be a new attack surface on a box that already had a cryptominer incident.

---

## Safety constraints

These are non-negotiable for v1.

1. **No autonomous writes to live config.** All changes via reviewed patches in `/var/lib/sysadmin-agent/proposals/`.
2. **No autonomous container management.** Containers are managed by systemd units and `unless-stopped` policies. The agent's only "action" on a container is reading its logs and labels.
3. **No credential generation or rotation.** Read-only on credential files; never writes.
4. **No interaction with the `/opt/_host/incidents/*/` directories beyond linking.** Forensic evidence is not the agent's domain.
5. **Hard rate limit on decisions per day** (e.g. 100 rows in `agent_decisions`) to catch runaway loops early.
6. **Reflection-loop output capped at one PR-equivalent per week.** Drift fixes should be batched, not drip-fed.
7. **Notifications are outbound-only and rate-capped.** No inbound command path from Telegram, ever (see Notifications section).

---

## Lessons from manual ops (informed by 2026-05-26/27 work)

What the design above is reacting to, concretely:

- **"Write-only is best" was wrong for this stack.** rclone+B2 needs `listBuckets` + `listFiles` to function. The right protection is *no `deleteFiles`*, not no read. The agent's credential audit should encode this: `writeFiles` ✅, `listBuckets` ✅, `listFiles` ✅, `readFiles` ✅, `deleteFiles` ❌, `writeBuckets` ❌.
  - **Amended 2026-07-02:** `deleteFiles` on the backup key is now *expected*, not a violation. B2 lifecycle rules can't prune this layout (unique filenames are never hidden, so hide-based rules never fire — this is how the bucket silently hit the account storage cap in June), so 7-day off-site retention is enforced by `rclone delete --min-age 7d --b2-hard-delete` inside `backup.sh`. The mitigation for a delete-capable key is the monthly restore drill + the separate read-only audit key, not scope denial. The audit should instead flag `writeBuckets`/`deleteBuckets`/`writeKeys` — capabilities nothing on the box legitimately uses.
- **Bootstrap-then-harden is a trap.** Don't design the agent to "start with Read+Write and downgrade." Land on the correct posture once.
- **Single source of truth for env vars.** The `BACKUP_OFFSITE_REMOTE` env var ended up in *two* places (systemd unit + would-be safe-reboot). The agent should detect this pattern and propose factoring into `/etc/default/<service>` files.
- **The README is the source of truth, but only if something reconciles it.** Without the agent, the README drifts. Don't try to fix this with "operator discipline" — that's how we got here.
- **Recurring incidents deserve different treatment than first occurrences.** The Ghost outage on 2026-05-26 was a *second* occurrence of the 2026-05-09 pattern. A first occurrence → add a systemd unit. A second occurrence with the *same* unit in place → escalate; the fix didn't work. The agent should distinguish these.

---

## Pre-build sweep — 2026-07-23

> Final pass before the build: every lesson from the sibling builds (Director,
> Scout, Writer, Wire Editor) and every box change since this doc's sections
> were written, checked against the spec. Sources: the Director devlog,
> NEWSROOM + writer docs, `_host/WORKFLOW.md`, the ledger, commit history in
> both repos, session transcripts, and live commands run 2026-07-23. The
> persona's skeleton survives untouched; the deltas below are what the spec
> was missing.

### The world moved under three sections of this doc

- **Box-native workflow (adopted 2026-07-19; `_host/WORKFLOW.md`, `read: full`).**
  There are no deploy Actions anymore — all three repos' deploy legs were
  deleted (`b4f8cfb`, `e0219be`, `344b55a`); push triggers nothing; CI
  verifies only. Consequences for this spec:
  - WORKFLOW.md joins the reconciliation corpus beside the `_host` README —
    it is documented *intent*, same precedence tier.
  - The coverage audit's GitHub surface changes: dead-deploy-workflow checks
    are history; the live checks are per-posture drift — dirty files in
    `predictor_prod` are a bug; uncommitted state in `/opt/uzelhub-web` is
    production with no undo point (flag trees dirty for days, not minutes);
    ai-agent-platform's review window is the gap before its next timer fire.
  - Credential follow-through: the `gha-deploy-20260706` keypair's consumers
    were retired with the deploy legs. An `authorized_keys` line whose
    consumer no longer exists is exactly this agent's kind of finding — flag
    for operator removal, don't assume.
  - Persona case study 3's fix shape ("three green runs") is now historical
    context; its lesson (never-succeeded ≠ pipeline) stands.
- **The 2026-07-20 predictor note is superseded** — see its inline amendment
  above: timers live 2026-07-22, the audit flips to verify-it-fires-and-pages.
- **notify-telegram config perms** — see the dated correction in
  §Notifications; the agent can send as `claude`, no privilege games needed.

### Identity (open question) now has hard data — verified 2026-07-23 as `claude`

Running as `claude` today, the loop is blocked in three of its four data
sources:

- **Journal-blind:** not in `systemd-journal`/`adm`, so `journalctl` returns
  nothing system-level. Recurring-incident detection and every "reads journal
  output" integration are dead until the agent's user gets the group
  (operator sudo, one line).
- **gh unauthenticated:** GitHub run history (provider-API precedence rank 2)
  404s anonymously. Device-flow login for the agent's user at build time.
- **rclone config is root-only** (`/root/.config/rclone/rclone.conf`): B2
  audits and the restore drill can't run as claude. Mint the read-only audit
  key at build and store it under the agent's own identity — don't share
  root's config.
- Already working as claude: docker (group), git over SSH, notify-telegram
  (640 root:claude, verified), and `calendar-mark --author sysadmin`
  (namespace-enforced, shipped) — `calendar-add` still lacks the author, so
  the persona's write exception 3 is half-plumbed.

Whatever identity is chosen, the unit file is the Director's proven template
(`director-listener.service`: `User=`, `Restart=on-failure`,
`OnFailure=notify-telegram@%n`, `EnvironmentFile=`) — and the counterexample
runs live today: `scout-pass.service` has no `User=` line, executes as root
every 05:45, and mints root-owned state files in a public repo (the
root-droppings law, on a timer).

### Build lessons inherited from the sibling builds

None of these were in this spec; all are proven in production on this box.

1. **Engine: anthropic SDK tool-loop, not the Agent SDK.** The devlog's
   producer-vs-orchestrator split (2026-06-29) applies: producers (Scout,
   Writer, content crew) get the batteries-included Agent SDK; agents that
   live on the spine — sequence-aware logging, cost caps, bounded read-only
   tools plus constrained write helpers — inherit the Director's loop. This
   agent is Director-shaped.
2. **Bound every tool's output at the pipe.** The grep-bomb (`d4af2c3`):
   never `capture_output=True` on a source that can be huge — read off the
   pipe with a byte ceiling and a wall-clock kill, clip per result, budget
   per turn. `journalctl` and `docker logs` are unbounded, and this agent
   greps them for a living. Inherit `_bounded_output()` wholesale.
3. **Inject the real clock.** The Director ran a day fast until
   `gather_state` was stamped (`b57a366`). This agent's entire job is cadence
   and staleness math; the timestamp goes into the state injection from day
   one.
4. **Cache-breakpoint the agentic transcript.** `1a86142`: one moving
   ephemeral breakpoint on the latest turn cut Director run cost 76%. Same
   loop shape, same fix.
5. **Refuse loudly on truncation; stream long calls.** Wire Editor
   (2026-07-18): thinking tokens ran ~4x the visible output; a call that
   stops on `max_tokens` must fail the run — a truncated audit never
   masquerades as an audit. Stream anything that could exceed 10 minutes.
6. **Model = house default Sonnet 5 behind an env var** (`SYSADMIN_MODEL`),
   priced in `pricing.py` at birth. The Director's benchmark logic applies
   unchanged: reconciliation is reasoning-with-tools, not pure coding.
7. **Survive a Postgres bounce.** `a870515`: reconnect on a dead socket; a DB
   bounce costs one retried loop, not a dead agent. Pairs with the existing
   SQLite-fallback open question.
8. **Helpers resolve paths at call time.** The `lead_mark` regression: an
   import-time default silently ignored a test override and wrote the real
   file. `ledger-append` and the proposals writer take their targets at the
   call.
9. **`agent_decisions.agent_name` stores the tool name in practice** (the
   Wire Editor's rows read `wire_triage`/`chief_shadow`, not the agent).
   Decide this agent's row identity deliberately and query accordingly.
10. **A pause is an env guard, not a timer edit.** The `SCOUT_PAUSED`
    pattern: check an env flag, exit 0 so `OnFailure` stays quiet, no root
    needed. Give this agent the same switch.
11. **Trust promotions ride a measured shadow, not a calendar.** The Wire
    Editor's gate-① concordance metric refines the persona's "advisory for 4
    weeks, then blocking" — promote the safe-reboot preflight (and any future
    authority) on measured agreement with operator decisions, not
    time served.
12. **Push is a publish.** This repo is public and this agent's ledger is
    tracked. Entries carry unit names and run IDs — never tokens, secrets,
    or session-transcript material (that stays in gitignored state dirs).

### First-audit targets, logged in advance (found during this sweep)

- **`anthropic-credit-check` is a loaded gun unloaded, today:** the script
  and path-encoded unit sources exist in `/opt/_host/scripts/` but nothing is
  installed — `systemctl` finds no such unit (verified 2026-07-23). The
  billing-class pager believed live since 07-21 isn't. Same sudo gate that
  held the predictor timers until 07-22.
- **`uzella-proxy.service` still has no `OnFailure=` pager** (verified
  2026-07-23) — a crash-loop that exhausts StartLimit pages nobody.
- **`scout-pass.service` missing `User=claude`** — see Identity above.
- **`config/director_registry.json` predictor note still reads "currently
  dormant; ADR-010 plans a restart"** (verified 2026-07-23) — three daily
  timers and an epoch-2 restart later.
- **`_host` README "Last verified: 2026-05-27"** — the standing armed drift
  from the 07-06 ledger entry; the first reconciliation run's job.
- Residue from the 2026-07-14 safe-reboot drill still open: safe-reboot's
  stop/status scope covers only the ghost pair; the gating backup's output
  isn't persisted (exit code + B2 object only); `/var/log/backup.log` is dead
  since ~07-05 but still logrotated.

---

## Open questions

These resolve once the agent runs against real data, not via more design.

- **Where does the agent live?** Likely `/opt/ai-agent-platform/agents/sysadmin_agent.py` for code parity with Content/Marketer. Decision pending. **Update 2026-07-23:** parity's other half is decided — engine per §Pre-build sweep item 1 (Director-shaped, anthropic tool-loop); `agents/sysadmin_agent.py` + `pipelines/sysadmin/` stays right for *layout* parity.
- **Single agent or sub-agent crew?** Could split into Inspector (read-only audit) + Drafter (patch proposals) + Reflector (weekly synthesis). Likely YAGNI for v1; revisit once the manual loop is captured.
- ~~**Notification channel.**~~ **Resolved 2026-07-02:** Telegram push for failure-class events, proposals directory for everything else — see [Notifications — Telegram push](#notifications--telegram-push). The `notify-telegram` helper is buildable now, ahead of the agent itself.
- **Postgres-on-agent-decisions vs. SQLite-local.** `agent_decisions` keeps schema parity with the rest of the crew. Cost: the agent depends on hvac-postgres being up, which is exactly the kind of thing it might be diagnosing. Mitigation: light health probes write to a fallback SQLite file under `/var/lib/sysadmin-agent/`.
- **What about a "snapshot" before any operator-initiated change?** Like `etckeeper` but for the whole `/opt`. Maybe later; the daily off-site backup partly covers this.

---

## Not in v1

- Cost monitoring / FinOps
- Multi-host fleet view (this is a single VPS)
- Active remediation
- Secret rotation
- Network/firewall management beyond reading UFW state
- Cross-agent coordination beyond shared `agent_decisions` table
- Two-way Telegram control (inbound commands / chat-ops) — the bot pages, it does not listen
