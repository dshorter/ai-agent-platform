# SysAdmin Agent — Ledger

> **What this is:** the sysadmin agent's system of record — dated, receipt-bearing
> findings that outlive any single run. Precedence position 3 (below live command
> output and provider APIs; above the `_host` README and repo prose) per the
> persona §"Your ledger, and precedence".
>
> **Write contract:** add-only, dated entries, receipts inline — and **newest
> entries go at the TOP** (immediately below this header). Immutability is
> semantic, not positional: prior entries are never altered; corrections are
> new dated entries citing what they correct. Newest-first matters because the
> agent's read_file tool returns a bounded PREFIX of the file (~40KB) — an
> append-at-bottom ledger would silently lose its newest entries first, the
> exact inversion of what a reconciliation loop needs. When the file nears the
> read budget, the weekly loop proposes a compaction: oldest entries distilled
> into the persona's case-study canon or an archive file, never silently
> dropped. Until the agent is built, sessions add entries on its behalf (as
> with the Director's devlog); once built, it writes via a constrained helper
> (`ledger-append`, the calendar-add pattern: validated shape, no edits to
> prior entries, rate-capped) — never freehand.
>
> **Read contract:** the agent reads this at the start of every reconciliation
> loop — this is where "memory is for pattern recognition" lives. New findings
> are checked for rhymes against entries here and the persona's canonical case
> studies before being reported as novel.

---

## 2026-07-13 (afternoon) — Every push to main was bouncing the stack; three-layer fix

**Symptom:** operator's Telegram turn to the Director failed with a disconnect
error; usage limit suspected. Actual: `psycopg AdminShutdown` then "the
connection is closed" — the listener's long-lived Postgres connection was dead
(listener log 18:34Z).

**Root cause (receipts):** the "Deploy to VPS" GitHub Action fires on *every*
push to ai-agent-platform main and ran `scripts/deploy.sh`, which did
`docker compose down` + `pull` + `up -d` — six deploys in the prior 24h, each
container recreate matching a run to the second (run 29259370247 at 14:46:21Z →
hvac-postgres recreate 14:46:35Z; run 29275842025 at 18:46:47Z → recreate
18:47:00Z; docker journal). ngrok bounced alongside; n8n survived only because
it is no longer in that compose file. Suspects cleared on evidence: no OOM
(`docker inspect`), `monitor.sh`'s panic branch never fired (0 hits in
/var/log/monitor.log), the hourly health timer runs at :48 — a minute late
both times. The bounce is the "surprise container bounce" the 07-12 leviathan
merge feared; the workflow was live all along.

**Fixes, three layers:**
1. `deploy.sh` rewritten (`957e27f`): `sudo -u claude git pull --ff-only`
   (root SSH tripped git's dubious-ownership guard) + `up -d --no-deps
   postgres ngrok` — named services per the _host overlap rule, no down, no
   blind pull. Verified live: run 29277507091 completed 13s, postgres
   `StartedAt` unchanged. Docs/calendar pushes are now docker no-ops.
2. Listener reconnects on a dead DB socket (`a870515`) — a DB bounce now
   costs one retried turn, not a dead Director.
3. `director-listener.service` installed + enabled (15:12 EDT, User=claude,
   Restart=on-failure, OnFailure pager) — **closes the 07-06 entry's armed
   drift risk** "Director listener runs in an abandoned SSH session scope
   with hand-sourced .env (needs a systemd unit)". Logs now in
   `journalctl -u director-listener`.

**Related, found in the same review:** the Director had no clock — nothing in
the prompt or injected state carries a date, so it inferred one and ran a day
fast (declared the Scout's 07-13 leads "not run today"; reframed a 07-14
VTODO as due-today). Fixed by stamping `gather_state()` with the real clock.
Root-droppings law honored throughout (re-chowns after each root git op).

## 2026-07-07 (evening) — Root droppings, occurrences #2 and #3: it's a law, not an incident

The 2026-07-06 root-droppings entry re-fired twice tonight, during the apex
cutover Phase 0 — different files, same physics:

- **#2, Caddy log:** `caddy validate` run from a root shell doesn't just parse —
  it *instantiates* the config, pre-creating `/var/log/caddy/studio.uzelhub.com.log`
  as root:root 600. The real reload, running as user `caddy`, then failed with
  `permission denied`. Fix: `chown caddy:caddy` the file; reload succeeded.
  Prevention folded into `marketing/CUTOVER.md` Phase 2.3 (pre-touch + chown
  the apex log before the flip's validate). **Receipts:** systemctl status
  ExecReload 2026-07-07 ~20:50 (status=1 → status=0 after chown).
- **#3, git object store:** root-ssh commits in `/opt/uzelhub-web` left
  root-owned fan-out dirs in `.git/objects/`; the claude user's commit of the
  runbook corrections failed with `insufficient permission for adding an
  object`. Fix: `chown -R claude:claude /opt/uzelhub-web` (operator-run,
  ~21:55). **Receipts:** commit `bf4289c` landing immediately after.

**Pattern, now three-for-three:** any root session that *touches* an
agent-or-service-owned tree (write, commit, or even a validating read that
instantiates) leaves ownership droppings that break the unprivileged owner
*later*, at a distance, mid-task. The 07-06 rule upgrades from repo-specific
to box-wide: **root work in any non-root workspace ends with a re-chown of
that workspace, same change, not cleanup** — and validation commands count
as writes.

## 2026-07-06 (evening) — Root-session droppings broke an agent's write path

First live use of `calendar_add` by the Director failed: `PermissionError`
on `ops/calendar.ics`. **Cause:** engineering sessions running as root had
rewritten that file — and `.git/index` — inside the claude-owned
ai-agent-platform repo. Ownership drift from privileged hands in an
unprivileged agent's workspace: the write path the Director was granted on
paper was physically root-locked by the people who granted it. **Fix:**
`chown -R claude:claude /opt/ai-agent-platform`; verified zero root-owned
files remain and claude can write the file + git plumbing. **Rule derived:**
when root touches an agent-owned tree, ownership restoration is part of the
change, not cleanup — and root-session git operations in agent-owned repos
re-pollute `.git`, so they end with a re-chown. **Receipts:** Director
listener log 2026-07-06T20:45 turn (its own correct triage: perms bug ≠
missing verb); chown ~21:05. The Director's smoke-test UID
(`test-smoke-20260707@…`) was never consumed — its retry is the end-to-end
proof.

## 2026-07-06 — Ledger opened; inherited state

Seeded at persona second-draft time. The four canonical case studies
(persona §Canonical case studies) are the founding entries by reference:
backup silence (receipts: journalctl backup.service June 2026, notes page),
the B2 key that lied (receipt: b2_authorize_account 2026-07-03), the
never-loaded deploys (receipts: gh run history, secrets set 2026-07-06,
runs 28804147192 / 28804149127 / 28804224536), the blocked-reminder saga
(receipt: docs/director/devlog.md §"The calendar saga — verified record").

Known-good state as of this entry, for future drift comparison:

- Backups: staging `/var/backups/host` (root, 700); off-site nightly ~03:30,
  8-day script prune, Object Lock pending console toggle; warn-count Telegram
  paging live; restore drill monthly from 2026-08-01 (ops/calendar.ics).
- Credentials: B2 key bucket-scoped (verified via API 2026-07-03); GitHub
  deploy key `gha-deploy-20260706` (authorized_keys line 3), secrets on all
  three repos; gh CLI on device-flow OAuth (no scheduled expiry).
- Known drift risks left armed: Director listener runs in an abandoned SSH
  session scope with hand-sourced .env (needs a systemd unit); `_host` README
  "Last verified" header predates the July corrections; off-site bundles
  unencrypted; typo'd /opt dirs still present.
