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
