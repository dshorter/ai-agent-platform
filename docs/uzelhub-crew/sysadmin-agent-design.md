# Sysadmin Agent — Design

> **Status:** Draft — informed by manual ops work through 2026-05-27
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

## Safety constraints

These are non-negotiable for v1.

1. **No autonomous writes to live config.** All changes via reviewed patches in `/var/lib/sysadmin-agent/proposals/`.
2. **No autonomous container management.** Containers are managed by systemd units and `unless-stopped` policies. The agent's only "action" on a container is reading its logs and labels.
3. **No credential generation or rotation.** Read-only on credential files; never writes.
4. **No interaction with the `/opt/_host/incidents/*/` directories beyond linking.** Forensic evidence is not the agent's domain.
5. **Hard rate limit on decisions per day** (e.g. 100 rows in `agent_decisions`) to catch runaway loops early.
6. **Reflection-loop output capped at one PR-equivalent per week.** Drift fixes should be batched, not drip-fed.

---

## Lessons from manual ops (informed by 2026-05-26/27 work)

What the design above is reacting to, concretely:

- **"Write-only is best" was wrong for this stack.** rclone+B2 needs `listBuckets` + `listFiles` to function. The right protection is *no `deleteFiles`*, not no read. The agent's credential audit should encode this: `writeFiles` ✅, `listBuckets` ✅, `listFiles` ✅, `readFiles` ✅, `deleteFiles` ❌, `writeBuckets` ❌.
- **Bootstrap-then-harden is a trap.** Don't design the agent to "start with Read+Write and downgrade." Land on the correct posture once.
- **Single source of truth for env vars.** The `BACKUP_OFFSITE_REMOTE` env var ended up in *two* places (systemd unit + would-be safe-reboot). The agent should detect this pattern and propose factoring into `/etc/default/<service>` files.
- **The README is the source of truth, but only if something reconciles it.** Without the agent, the README drifts. Don't try to fix this with "operator discipline" — that's how we got here.
- **Recurring incidents deserve different treatment than first occurrences.** The Ghost outage on 2026-05-26 was a *second* occurrence of the 2026-05-09 pattern. A first occurrence → add a systemd unit. A second occurrence with the *same* unit in place → escalate; the fix didn't work. The agent should distinguish these.

---

## Open questions

These resolve once the agent runs against real data, not via more design.

- **Where does the agent live?** Likely `/opt/ai-agent-platform/agents/sysadmin_agent.py` for code parity with Content/Marketer. Decision pending.
- **Single agent or sub-agent crew?** Could split into Inspector (read-only audit) + Drafter (patch proposals) + Reflector (weekly synthesis). Likely YAGNI for v1; revisit once the manual loop is captured.
- **Notification channel.** Email? Drop into n8n? Append to a `proposals.md` the operator reads? The cheapest answer is the proposals directory + a summary line in `agent-platform-health` output. Start there.
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
