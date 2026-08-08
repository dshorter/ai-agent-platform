# Security Agent — Ledger

> **What this is:** the security agent's system of record — dated,
> receipt-bearing findings that outlive any single pass. A finding lives here
> once it has been *confirmed reachable*, not once it has been suspected.
>
> **Write contract:** add-only, dated entries, receipts inline — and **newest
> entries go at the TOP** (immediately below this header), for the same reason
> as the sysadmin ledger: `read_file` returns a bounded PREFIX of the file, so
> an append-at-bottom ledger silently loses its newest entries first. Prior
> entries are never altered; a finding that gets fixed is recorded as a **status
> line on a new dated entry**, never by editing the original. Until the agent is
> built, sessions add entries on its behalf; once built it writes through the
> constrained `ledger-append` helper, never freehand.
>
> **Read contract — DELIBERATELY DIFFERENT from the sysadmin ledger.** The
> sysadmin reads its ledger at the *start* of every loop and rhyme-checks
> against it. **This ledger is not injected into the pass at all.** The security
> agent audits blind, and the ledger is reconciled *afterwards, in code*, on the
> stable finding id below. The reason is in `docs/security-agent.md` §3: an
> agent primed with last month's findings re-checks the known list, finds it
> unchanged, and reports a quiet week — and a security false negative is
> invisible. Blind audit, mechanical diff.
>
> **Stable finding id.** Every finding carries an `id:` derived from *what it
> is*, not when it was found — `docroot-git-exposed:studio.uzelhub.com`. The
> weekly diff is a set difference over these ids, which is what makes
> new / recurring / **resolved** all fall out for free. Never renumber; never
> reword an id to read better.
>
> **Severity is recorded, never used as a reporting filter.** See
> `docs/security-agent.md` §9.3 — on Claude Opus 5 a "only report high-severity"
> instruction is followed literally and suppresses real findings. Everything
> found gets an entry; ranking happens at read time.

---

## 2026-08-06 — Entry zero: full manual audit, seeding the baseline

**Author:** operator + session (agent not yet built). **Method:** manual audit,
full report at `server-maintenance/docs/networking/security-audit-2026-08-06.md`.

**Why this exists:** the daily sysadmin agent had run since 26 July without
seeing any of these, because all six of its checks look *inward* — reality
against declared state. None asks what the box hands to a stranger. This audit
is the worked example of the register expected, and its findings are the
baseline the first real pass will diff against.

---

### `docroot-git-exposed:studio.uzelhub.com` — CRITICAL — **RESOLVED 2026-08-06**

`studio.uzelhub.com` served `/opt/uzelhub-web`, the repository root, so `.git`
was fetchable over the public internet. Confirmed reachable: `.git/config`,
`.git/HEAD`, `.git/index` and `.git/packed-refs` all returned 200.

**What an attacker gets:** with `index` and `packed-refs` readable, every object
is enumerable and fetchable — a complete clone of a **private** repository
*including full history*, which carries everything ever committed and later
removed. `.git/config` additionally disclosed the GitHub remote.

**Fixed during the audit** — `chmod 750 /opt/uzelhub-web/.git`. Caddy runs as
`caddy`, not `claude`, so dropping world-read is sufficient. Verified 403; git
operations unaffected; all four sites still 200.

**Not fully closed:** permissions are the wrong layer — a future `chmod -R`
reopens it. The durable fix is a dotfile 404 rule in the studio block, which
requires an operator Caddy edit and has not been applied. **This id should
recur as MEDIUM until that rule lands.**

### `secret-in-docroot:services/uzella-proxy/.env` — HIGH — OPEN

`/opt/uzelhub-web/services/uzella-proxy/.env` sits *inside* the studio docroot
and holds `ANTHROPIC_API_KEY`, `CONTACT_DB_URL`, `CONTACT_IP_SALT`, `ASK_DB_URL`.

**What an attacker gets:** nothing today — it returns 403, but only because the
file happens to be mode 600 and Caddy cannot read it. **One permission bit is
the entire control.** A single `chmod 644`, or any recursive chmod over that
tree, publishes a live Anthropic API key.

Gitignored and never committed. Fix is to move it out of the docroot entirely.

### `patch-drift:kernel+libc` — HIGH — OPEN

Running kernel 6.8.0-134 with 6.8.0-136 and -137 installed and waiting, plus
pending `libc6`. `/var/run/reboot-required` set. Uptime 3 weeks 3 days.

**What an attacker gets:** whatever the unpatched kernel and libc concede.
`safe-reboot.sh` exists and the 2026-07-14 reboot was clean, so the remedy is
proven and unused.

### `working-files-served:studio.uzelhub.com` — MEDIUM — OPEN

Serving the repo root also serves non-page files: `/uzella.zip`,
`/mktg-notes.txt`, `/editing-notes.md`, `/BACKLOG.md`, and the uzella-proxy
source. `VOICE.md` itself flags `mktg-notes.txt` as needing a scrub before the
repo could go public — it is already public here.

**Structural cause is the same as the critical finding:** the docroot *is* a
working tree. Studio already 404s `/marketing/*`, so the pattern exists.

### `doctrine-files-served:uzelhub.com` — MEDIUM — OPEN

The apex docroot is `/opt/uzelhub-web/marketing`, so `VOICE.md`,
`VOICE-LEDGER.md`, `CHARTER.md`, `TODO.md`, `CONCEPT-INVENTORY.md`,
`promotion-survey.yaml` and `data/products.json` (5 `copyDraft` review notes) are
all live.

**What an attacker gets:** the marketing strategy, the autopsy of retired copy,
and a candid section on which work is *not* publicly verifiable. Written
expecting privacy.

### `no-bruteforce-guard:sshd` — MEDIUM — OPEN

27,726 failed SSH attempts in 7 days (~4,000/day); `fail2ban` inactive.

**What an attacker gets:** no access — password auth is off, which is why this
is medium and not high. The cost is log volume and journal noise that buries
real events.

### `security-doc-stale:security-architecture.md` — MEDIUM — OPEN

`server-maintenance/docs/networking/security-architecture.md` (dated
2025-01-13) asserts "Only Port 22 Open", "Zero ports exposed except SSH", and
"Attackers can't port scan your VPS". All three stopped being true on
**2026-03-15**, when Caddy was installed and the box began serving public HTTPS.

**What an attacker gets:** nothing directly. Logged because it caused a live
misdiagnosis during this very audit — the operator reasonably believed the box
was locked down, and the document was the reason. **A stale security claim is a
finding.**

### `vestigial-tunnel:ngrok` — LOW — OPEN

`https://agents-platform.ngrok.io` still registered, pointing at a `web-server`
container in `Created` state; returns 502.

**What an attacker gets:** nothing today. It is an unlatched door, not an open
one — a tunnel bypasses UFW, Cloudflare, and any future Access policy
simultaneously, and the target is one `docker start` from serving. Subscription
has been dropped; `docker stop ngrok` is the definitive close.

### `origin-reachable-by-ip` — INFO — ACCEPTED

UFW permits 80/443 from anywhere — correct for a public web server, since
Cloudflare connects from arbitrary addresses. DNS does not leak the origin (all
four hostnames resolve to Cloudflare only), but Hetzner ranges are swept
continuously, so obscurity is not the control.

**Accepted, with a live compensating control:** the desk's capability URL is
currently the auth. **This becomes a real finding the moment that path is
shortened** — see `docs/security-agent.md` §9.4. Closing it means restricting
80/443 to Cloudflare CIDRs or moving behind a Cloudflare Tunnel.

---

### What passed, recorded so a later pass doesn't re-derive it

SSH hardening (passwords off, keyboard-interactive off, root
`prohibit-password`, pubkey only — why 27k failures are noise). Every container
bound to loopback, **no `0.0.0.0` publications**, so the Docker-bypasses-UFW
hole is absent. UFW active and enabled, default-deny, exactly three ports.
Secrets never committed. `.git` not exposed on apex, predictor, blog or the
desk — studio was unique in serving a repo root. TLS at Cloudflare and Caddy on
all four hostnames.
