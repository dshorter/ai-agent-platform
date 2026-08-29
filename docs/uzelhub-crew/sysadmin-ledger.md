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










## 2026-08-29 — daily pass FAILED (APIStatusError) — no audit performed

`sysadmin-daily.service` exited non-zero before producing a report, so no proposals artifact exists for this date and no audit of live state was made.

- Error class: `APIStatusError`
- Detail: `journalctl -u sysadmin-daily.service --since 2026-08-29`

Rhyme-check this against other `pass FAILED` entries before treating it as a one-off — this failure class has recurred with different literal errors each time.

## 2026-08-24 — Same 3 proposals reissued unapplied across ≥5 daily cycles, 08-13→08-24

Three findings — check-anthropic-credit unwired (ledger 2026-08-13), monitor.sh's
dead bare-compose fallback (ledger 2026-08-16), server-maintenance.service missing
OnFailure= (ledger 2026-07-31 item b) — have now been independently re-derived and
re-proposed, with near-identical diffs, in at least the 08-13, 08-16, 08-19, 08-21,
and 08-24 daily passes (08-19/08-21 payloads recovered via `journalctl -g
run_blog_pipeline`, which incidentally matched their `tool.end` records — the same
excavation method the 08-16 and 08-17 entries used, because the ledger itself has
no record of any of these five runs' proposals between 08-17 and today). None of
the three has been applied. This is the 07-31 ledger entry's predicted failure mode
("daily-pass proposals outliving 3 cycles unapplied") now confirmed at 5 cycles
minimum, for the same three items, 11 days running — not new drift, but the
clearest evidence yet that re-proposing identical diffs daily does not substitute
for either (a) an operator apply pass or (b) the weekly compaction this ledger's
own write contract calls for. Until one of those happens, expect this entry's own
three items in the 09-24 rhyme-check too.

## 2026-08-17 — n8n orphaned from compose since Apr; 08-16 23:35 pass invisible to ledger

Two receipts worth keeping past this run:

1. **n8n compose-orphan, dated.** `git -C /opt/ai-agent-platform log -- docker-compose.yml` shows `b50778a` (2026-04-22, "retire n8n") dropped the `n8n:` block; `docker inspect n8n` shows the container was created 2026-04-25T16:03:38Z and has run continuously since on `RestartPolicy=unless-stopped` alone — not managed by ai-agent-platform's compose file (doesn't define it) or server-maintenance's (defines it, doesn't run it). `/opt/_host/README.md`'s "Last verified: 2026-05-27" postdates the retirement commit by five weeks yet the project table still lists n8n as compose-managed under ai-agent-platform. Proposed dated correction (not drafted as one of this pass's 3 diffs — batching for a future pass or operator edit): amend the `ai-agent-platform/` row and the "Recently resolved" section to note n8n's actual status (compose-orphaned since 2026-04-22, alive only via Docker restart policy), dated 2026-08-17.

2. **A completed daily pass (2026-08-16 23:35 EDT, artifact `/var/lib/sysadmin-agent/proposals/2026-08-16-daily-2.md`) produced real findings and two drafted proposals — and left no trace in the ledger.** Discovered only because `journalctl -g blog_pipeline` incidentally matched its `tool.end` payload; the ledger's own newest entry (also dated 2026-08-16) describes a different, earlier same-day session. Both of that run's proposals (install anthropic-credit-check; fix monitor.sh) are still unapplied today and are re-proposed verbatim in this pass's P1/P2. Whether that run's own ledger-write was attempted-and-refused (2026-08-14/15's title-cap failure mode) or simply never issued is not determinable from what I can read this pass. Until the daily-pass pipeline either (a) verifies its ledger-append succeeded before considering the run complete, or (b) the weekly compaction pass folds still-open per-day proposals files into the ledger regardless of whether the daily run remembered to, this exact gap — real work, done, invisible to the next day's rhyme-check — will keep recurring under different literal timestamps. This is the third documented instance of the pattern (2026-07-31 ledger entry, 2026-08-15 ledger entry, this one).

## 2026-08-16 — monitor.sh bare 'docker compose up -d' unscheduled - rediscovered blocked finding

Both `/opt/ai-agent-platform/scripts/monitor.sh` and `/opt/server-maintenance/scripts/monitor.sh` (identical) contain a bare `docker compose up -d` fallback (line 27) in an "n8n is down" recovery branch — no service names, the exact footgun the persona's compose-overlap mechanic names by rule. Confirmed unscheduled today: `crontab -l` (claude) empty, no matching unit in `/etc/systemd/system`. First surfaced in the 2026-07-27 daily pass; a follow-up write attempt on 2026-08-14 produced a full receipt-bearing ledger entry that `ledger-append` refused for exceeding the 90-char title cap (recorded 2026-08-15), so it silently dropped out of the ledger for two days and had to be independently re-derived by this pass (2026-08-16) via a journal excavation, not the ledger itself. Additionally new this pass: the fallback is now provably broken, not just risky — `/opt/ai-agent-platform/docker-compose.yml` no longer defines an `n8n` service (confirmed via `grep` + `docker inspect n8n`'s compose labels still pointing at this file), so the bare `up -d` it would run can't even revive the thing it's checking for. Proposal P2 this pass replaces the fallback with a page. Rhymes with case study #3 (never-loaded deploys, the finding itself) and case study #4 (the blocked reminder, its ledger-write history) simultaneously — worth remembering as the box's clearest example of both patterns compounding on the same artifact.

## 2026-08-16 — daily pass FAILED (BadRequestError) — no audit performed

`sysadmin-daily.service` exited non-zero before producing a report, so no proposals artifact exists for this date and no audit of live state was made.

- Error class: `BadRequestError`
- Detail: `journalctl -u sysadmin-daily.service --since 2026-08-16`

Rhyme-check this against other `pass FAILED` entries before treating it as a one-off — this failure class has recurred with different literal errors each time.

## 2026-08-15 — ledger-append silently refused an entry on 2026-08-14 (title cap)

`sysadmin-daily.service`'s 2026-08-14 run generated a full receipt-bearing
"Ledger entry" section (the monitor.sh bare-compose finding) and the
pipeline's own `ledger-append` call rejected it: `ledger-append refused:
REFUSED: title exceeds 90 chars` (`journalctl -u sysadmin-daily.service
--since 2026-08-14`). The refusal is visible only in the unit journal — it
never surfaced in that day's proposals artifact summary line, and nothing
paged it. Net effect: a durable finding that should have entered the
ledger instead existed for one day in a per-day proposals file and had to
be independently re-derived by this pass before the prior attempt was even
discovered. Rhymes with case study #4 (the blocked reminder) — a valid
write blocked by validation, invisible until someone goes looking — and is
the specific failure mode the 2026-07-31 ledger entry's own proposed
remediation ("give ledger-append a 'still open' bump") anticipated but
which was never built or applied. Until `ledger-append`'s length validation
either truncates-and-warns or the caller enforces a title budget before
calling it, any finding whose natural title exceeds 90 chars is a
finding that silently fails to outlive its run.

## 2026-08-13 — check-anthropic-credit — built 2026-07-21, zero fires as of 2026-08-13

Confirmed via `find /etc/systemd/system -iname '*credit*'`/`-iname '*billing*'` (both empty) and `systemctl list-timers --all` (26 timers, none matching): the billing-exhaustion probe written after the 2026-07-21 -$0.40 outage has never been wired to a timer or service unit. The script is complete, tested-shaped (`--dry-run` flag), and documents its own scheduling assumption ("probe cadence bounds detection latency") without that cadence existing. `/opt/_host/README.md` doesn't mention it, so this isn't even a doc-vs-reality mismatch — it's an absence on both sides. Rhymes with case study #3 (never-loaded deploys): the pattern on this box is that a fix gets written in response to an incident, and the wiring step that makes it fire is the one that doesn't happen. Proposal P1 this pass installs it; if it's not applied, the next occurrence of the 2026-07-21 outage class will again have zero proactive signal.

## 2026-08-03 — uzelhub-web is back on main and clean — the 07-28 finding is closed

The daily pass flagged this from 2026-07-28 onward and it recurred unclosed for
six days: /opt/uzelhub-web sitting on content/voice-rework, 11 commits ahead of
a main frozen at 2026-07-21, working tree dirty. Because the apex docroot IS
that working tree, the dirty files were simultaneously the live site and the
only copy of them.

Resolved 2026-08-03. The day's work was committed in two commits (b6390d9 the
ask endpoint's decision trace, 2186983 the Agents section plus the Agent Crew
retirement), the branch was pushed, PR #48 merged to main as 3e31928, and the
box was moved onto main and fast-forwarded.

Two things worth keeping from how it was done, both about the specific hazard of
a working tree that is also a docroot:

1. The tree comparison came BEFORE the checkout. origin/main's tree was verified
   byte-identical to the branch tip first, which made switching branches a
   guaranteed content no-op on a live docroot. GitHub used a merge commit rather
   than a fast-forward, so this was worth checking rather than assuming — a merge
   commit of a fast-forwardable branch keeps the tree, but that is a property to
   confirm, not to trust.
2. CI's exact gate was run locally before committing: regenerate, then
   git diff --exit-code over marketing + packs excluding sitemap.xml. The
   workflow only triggers on push to main, so a failure would have landed AFTER
   the merge, on the branch that is production.

Still open and operator-only: uzella-proxy needs a restart before the new ask
decision-tracing records anything (the running process predates it), and
/products/agent-crew.html now 404s where it wants a 301 to /agents/ — a
Caddyfile edit, tracked as redirect-retired-agent-crew@ai-agent-platform.

## 2026-07-31 — Daily-pass proposals are outliving 3 cycles unapplied, and the ledger doesn't know it

2026-07-31: My own 2026-07-28 daily-pass artifact (`/var/lib/sysadmin-agent/proposals/2026-07-28-daily.md`, via `journalctl -u sysadmin-daily.service`) found: (a) `/opt/predictor_prod` root-owned droppings (occurrence #4 in the root-droppings law), (b) `uzella-proxy.service`/`server-maintenance.service` missing `OnFailure=`, (c) `monitor.sh` running on a trigger invisible to the claude user, (d) `uzelhub-web` off `main` on `content/voice-rework`. Re-checking live on 2026-07-31: (a) is fixed (`find /opt/predictor_prod -user root` clean — good, proposal P1 was applied). (b), (c), (d) are **all still unapplied**, and (d) has worsened (branch now also 22 files dirty, 11 commits ahead of a `main` that hasn't moved since 2026-07-21). Root cause of the blind spot: the ledger (this file) has not been appended to since 2026-07-13, so daily-pass findings after that date live only in per-day proposal files under `/var/lib/sysadmin-agent/proposals/`, which the read contract doesn't route through the rhyme-check step. A finding can recur for a week and still get reported as fresh, or worse, an applied fix (predictor_prod chown) can go unconfirmed as applied because nothing marks proposals as closed. Separately, `sysadmin-daily.service` failed loudly and correctly on 2026-07-29 (`TruncatedRunError`, `journalctl -u sysadmin-daily.service --since 2026-07-29`) — the failure-handling design works, but it means that day's proposals file (`2026-07-29-daily.md`) never existed, a silent one-day gap in the very audit trail this entry depends on. **Proposed remediation (for the weekly pass, not mine to apply unilaterally):** either (1) fold each daily proposals file's still-open items into this ledger on some cadence (weekly compaction, per this file's own write contract), or (2) give `ledger-append` (once built) a "still open as of <date>" bump so unapplied proposals accrue visible age instead of resetting to "novel" each morning.

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
