---
read: full
status: SPEC — not built. Written 2026-08-06 after the 2026-08-06 security audit
       found a critical exposure the sysadmin agent's charter could not have caught.
       Blocker 1 (max_tokens) CLEARED 2026-08-06. Blocker 2 (refusal handling)
       open. Model decision settled: Claude Opus 5, xhigh, no fallback.
---

# Security agent — a second crew member, pointed outward

## 1. Why this exists

The [2026-08-06 audit](../../server-maintenance/docs/networking/security-audit-2026-08-06.md)
found `studio.uzelhub.com` serving the `.git` directory of a **private** repo —
`index` and `packed-refs` both readable, so the entire repository including full
history was reconstructable by anyone.

The sysadmin agent had been running daily since 26 July and never saw it. That
is not a failure: its six checks are schedule coverage, unit hygiene, compose
drift, git posture, root droppings, and doc reconciliation. **All six look
inward** — does reality match what is declared. Nothing in the charter asks
what the box hands out to a stranger.

The finding required exactly one question the daily charter cannot ask: *what
does each docroot serve to the public internet?*

## 2. Separate agent, not a second pass

A weekly pass on the existing agent was considered first — `PASSES` is already a
charter registry, `--pass NAME` is already plumbed, and adding one would have
been a dict entry plus a timer. It was rejected. The operator's case:

- **The spine wants one `agent_name` per pass.** The convention already in
  `agent_decisions` is one name per job — `scout_walk` and `scout_synthesis`
  are two rows, `marketer_agent.extract` and `.package` are two more.
  `sysadmin` as a single undifferentiated name is the outlier, and hanging a
  second pass under it would leave security findings inseparable from ops
  findings without a join. A distinct agent keeps every future query one
  predicate.
- **The personas do not blend.** The sysadmin temperament is *observe,
  reconcile, propose* — good instinct pointed inward. A security agent wants
  the opposite posture: assume the operator is wrong, assume the box is
  already exposed, try to prove it. One persona doc cannot carry both without
  hedging each.
- **A separate agent gets a separate ledger.** `_gather_context` injects the
  sysadmin ledger into every run with an instruction to rhyme-check against
  it. A security pass sharing that agent would be primed by a history of
  scheduling and unit-hygiene findings no matter what its system prompt said.
  This is the drift vector a shared-agent design could not close.

**The one honest argument for sharing was convenience**, and convenience is not
a design argument.

Read-only + proposals carries over unchanged, so a wider mission means more
things the crew *tells* the operator, never more things it does.

## 3. Identity and spine

| | |
|---|---|
| `agent_name` on the spine | `security_audit` |
| Ledger | `docs/uzelhub-crew/security-ledger.md` (own file — see §2) |
| Ledger helper | `ops/ledger-append --author security` (needs a new author value) |
| Unit | `security-weekly.service` + `.timer` |
| Cadence | Weekly, Monday, offset from `sysadmin-daily` at 06:20 |
| Output | Proposals dir + one ledger entry + **one `agent_decisions` row per finding** (see §16) |

Reusing the sysadmin's shape: charter registry, proposals contract, the
`_gather_context` clock/identity injection, the Postgres-down fallback to
`decisions-fallback.jsonl`, and the `notify-telegram` pager on the runner side.

**One deliberate divergence — the ledger is NOT pre-injected.** The sysadmin
reads its ledger at the top of every run and rhyme-checks against it. That is
right for reconciliation against a known baseline; it is wrong here. This agent
looks for what nobody has looked for yet, and priming it with "here are last
month's findings" anchors it: it re-checks the known list, finds it unchanged,
and reports a quiet week. Priming does not care what the charter *says* the
ledger is for.

That failure is invisible — the same asymmetry `NEWSROOM.md` identifies for the
Scout, where the Editor filters bad leads but nothing filters *missing* ones. It
is also precisely how a `.git` exposure survived months of a daily agent running
past it.

**So: audit blind, reconcile after.** Run the charter with no ledger in context.
Produce findings. *Then* diff against the ledger — **in code, not in the model** —
on a **stable finding id** derived from what the finding is
(`docroot-git-exposed:studio.uzelhub.com`). New / recurring / resolved becomes a
set difference: deterministic, free, and no anchoring.

This is strictly richer than the sysadmin's shape. A model asked to rhyme-check
can tell you what recurs; it cannot reliably tell you what **stopped** being
true, because absence is not in its context. The set difference reports fixes as
well as findings.

## 4. Persona — the posture, not just the checks

The system prompt is the load-bearing difference. Sketch:

> You are the security auditor for the Hetzner VPS hosting uzelhub.com,
> studio.uzelhub.com, blog.uzelhub.com and the predictor. **You reason from
> outside the box inward.** Assume an attacker has already found this server's
> IP in a routine scan of Hetzner's ranges — because they have. Your question
> is never "is this configured as intended" but "what does this actually hand
> out, and to whom." You observe and report; a human applies every fix.
>
> You are unsparing about the operator's own assumptions. A control that exists
> is not a control that works: a firewall that is *running* may still permit
> the world, a file that is *gitignored* may still be served, a document that
> *says* the box is locked down may describe an architecture retired months
> ago. Verify the claim, never the intention.
>
> You do not report theatre. A finding names what an attacker gets, not what a
> checklist says is missing.

That last line matters — an unsparing agent with no precision bar produces
noise, and noise is how a weekly report stops being read.

## 5. Charter — the checks

Ordered by expected yield. Same "stop cleanly when budget forces it and report
what you did not reach" contract as the daily pass.

### Passive (no privileges beyond the `claude` user)

1. **Docroot contents.** Parse every `root *` out of the Caddyfile. For each,
   flag anything present that is not meant to be served: `.git`, `.env`,
   `*.key`, `*.pem`, archives, `node_modules`, backup suffixes, and any file
   whose extension is not a web type. **This single check would have caught the
   critical finding on day one.**
2. **Docroot depth.** Flag any docroot that *is* a repository root or a home
   directory — serving a whole working tree is the structural cause, not the
   `.git` file itself.
3. **Listening sockets** on non-loopback interfaces against an expected set
   (22/80/443); anything else is a finding.
4. **Docker publications** — any `0.0.0.0` binding. Docker's iptables rules run
   ahead of UFW, so a published port is reachable regardless of firewall state.
5. **Live tunnels** — ngrok's local API, and any other outbound tunnel. A
   tunnel bypasses UFW, Cloudflare, and Access simultaneously.
6. **Patch and reboot drift** — `/var/run/reboot-required`, running kernel vs
   installed, pending libc.
7. **Brute-force posture** — fail2ban state against failed-auth volume in the
   journal.
8. **Secret placement** — files matching credential patterns located *inside*
   any docroot, whatever their current permissions. Mode 600 is a bit, not a
   boundary.
9. **Doc-vs-reality drift on security claims specifically.** The retired
   `security-architecture.md` asserted "only port 22 open" for five months
   after it stopped being true. Any doc making a security claim gets its claim
   tested.

### Active (see §6)

10. **What each vhost actually serves.** For every hostname in the Caddyfile,
    request a fixed probe list — `/.git/config`, `/.env`, `/.git/HEAD`,
    directory-listing checks — and record the status codes. Passive check 1
    finds the file on disk; this proves whether it reaches the internet.
11. **Security headers and TLS** on each hostname.
12. **Capability-URL hygiene** — that token paths still 404 without the token,
    and that no token has leaked into a served file, a sitemap, or a repo.

### Explicitly out of scope

No exploitation, no password guessing, no fuzzing, no third-party hosts, no
writes. The agent proves *reachability*, never *impact*.

## 6. The active-probing boundary

The critical finding came from `curl`-ing the live site. A purely file-reading
agent would likely have missed it, because the question only appears when you
ask what the server *returns*. So active probing is in scope, bounded:

- **Only hostnames that appear in `/etc/caddy/Caddyfile`.** The Caddyfile is
  the allow-list; a hostname not served by this box is not probed.
- **GET and HEAD only.** No POST, no auth attempts, no parameter mutation.
- **A fixed probe list**, defined in the tool, not composed by the model. The
  agent chooses *whether* to probe, never *what* — this keeps a prompt-injected
  instruction from turning the agent into a scanner.
- **Rate-limited and capped** per run.
- **Logged in full** — every probed URL and status lands in the report, so the
  operator can audit what the agent did as easily as what it found.

Implemented as a dedicated `probe_own_host` tool with the allow-list resolved
at call time from the Caddyfile. Not a general HTTP tool.

## 7. ⚠️ Blockers

**1. ~~`max_tokens` is 8192 and would hard-fail at `xhigh`.~~ CLEARED 2026-08-06** — raised to 64000 in `agents/sysadmin_agent.py`.
`agents/sysadmin_agent.py:29` sets `SYSADMIN_MAX_TOKENS = 8192`, and `_create`
**raises `TruncatedRunError`** on `stop_reason == "max_tokens"` rather than
returning a partial. Anthropic's guidance for Claude Opus 5 at `xhigh`/`max` is
`max_tokens` of at least **64000** — thinking and response share that budget.
Switching model and effort without raising this turns every run into a hard
failure. (The loud failure is correct behaviour and was a good call; it just
means this is a blocker, not a slow degradation.)

**2. `stop_reason: "refusal"` is not handled — and without a fallback it is the
measurement instrument.** `_create` checks `max_tokens` and nothing else, so a
refusal falls through into report parsing and produces confusing garbage rather
than a clear signal.

**Operator decision, 2026-08-06: run on Claude Opus 5 with NO fallback.**
Server-side fallbacks were specced and rejected — a fallback partially hides
refusals by letting the run succeed on another model, and the open question here
is precisely *how often does this get refused*. A plain failed run is the
cleaner instrument. It also means the prompt is written for exactly one model
with no intersection compromise (see §10).

So the requirement is **detect, log, and surface** — not recover:

```python
if response.stop_reason == "refusal":
    cat = getattr(response.stop_details, "category", None)
    raise RefusedRunError(f"Claude Opus 5 declined this pass (category={cat})")
```

Fail loudly, the same posture as `TruncatedRunError`. The runner's existing
`notify-telegram` OnFailure path then makes each refusal visible on the day it
happens, and the count answers the question directly. If refusals turn out to be
common, pin `claude-opus-4-8` and re-tune the prompt for 4.8's tendencies —
cheap to reverse, and by then the decision is evidence-based.

Keep `client.messages.create` — no beta endpoint, no `fallbacks` parameter.

## 8. Model configuration

Operator's call: both agents move to Opus at extra-high effort.

```python
model="claude-opus-5"
output_config={"effort": "xhigh"}
max_tokens=64000          # up from 8192 — see §7
# thinking: leave unset. On Claude Opus 5 thinking is ON by default and runs
# adaptive; `budget_tokens` is removed and returns 400.
```

Applies to both `sysadmin` and `security_audit`. The current default is
`claude-sonnet-5` at the implicit `high` effort
(`pipelines/sysadmin/config.py:40`).

**Cost.** Claude Opus 5 is $5/$25 per MTok against Sonnet 5's $3/$15 (currently
$2/$10 introductory through 2026-08-31), and `xhigh` spends more tokens than the
`high` default on both axes. `max_cost_usd` defaults to **5.0** and will bind
much sooner — raise it deliberately rather than discovering it as a truncated
weekly pass. One small offset: Claude Opus 5's prompt-cache minimum is 512
tokens (down from 1024), so the `cache_control`-marked system prompt caches more
readily.

### ⛔ Fable 5 is the wrong model for *this* agent

The operator suggested Claude Fable 5 for the security agent since it runs only
weekly. **The opposite is true, and specifically for this agent.**

Fable 5's safety classifiers **target most cybersecurity content by design** —
it is documented as not intended for that domain. A weekly adversarial audit of
a live server is precisely the workload those classifiers exist to decline. The
one agent in the crew that should *not* be on Fable 5 is this one.

Claude Opus 5 also carries elevated cyber safeguards and can refuse — but its
cyber-category refusals route to Opus 4.8 under `fallbacks: "default"`, so a
refusal is recovered rather than returned. Fable 5 additionally requires 30-day
data retention (unavailable under ZDR) and costs $10/$50 per MTok, double Opus.

**If Fable 5 is wanted anywhere in the crew, the Writer is the candidate** —
long-form judgment, no cyber content, weekly-ish cadence. Not here.

## 9. Open questions

1. **Does `security_audit` need root?** Everything in §5 is reachable as the
   `claude` user (verified 2026-08-06: journal and docker groups both held)
   **except** UFW rule inspection, which needs root. A narrow sudoers grant for
   `ufw status` alone is the minimum; the alternative is dropping check 3's
   firewall half and relying on the active probe, which proves reachability
   without needing to read the rules. **Recommend starting without the grant** —
   the active probe answers the question that matters.
2. **Does the ledger need seeding?** The agent's rhyme-check works against
   history it does not yet have. Seeding it with the 2026-08-06 audit as entry
   zero gives it a worked example of the register expected.
3. ~~**Precision bar.**~~ **RESOLVED 2026-08-06 — and the original proposal was
   backwards.** It suggested capping findings per pass and setting a severity
   bar. On Claude Opus 5 that is an anti-pattern: a review prompt saying "only
   report high-severity" or "be conservative" is followed **literally** — the
   model investigates just as thoroughly, finds the issue, then declines to
   report it. Precision rises and **measured recall falls** while underlying
   ability is unchanged. For a security agent that is the whole job, silently
   suppressed.

   **Do instead:** require a severity and a confidence on every finding, plus
   the "what an attacker gets" clause, and **report everything**. Filter in the
   report's ordering or a separate pass — never at the finding stage. See §10.
4. **Interaction with Cloudflare Access.** Every probe expectation inverts once
   Access is on, and the probe gains its single most valuable check. Large
   enough to have its own section — **see §12**. Contingent on Access actually
   being enabled; until then the probe's current expectations hold.

## 10. Prompt structure is model-specific — write it for Claude Opus 5

Opus 4.8 and Claude Opus 5 differ enough that a prompt written from habit gets
several things backwards. Each item below is a *change to how this agent's
charter and persona are written*, not general advice.

**Report everything; filter downstream.** Covered in §9.3 — the single most
consequential one for a security agent. No severity bar, no findings cap, at
the finding stage.

**Delete verification instructions — do not add them.** Claude Opus 5 verifies
its own work unprompted, and telling it to verify produces over-verification
with no capability gain. This **inverts** the usual "ask the model to
double-check" best practice, so it is exactly what a security prompt written
from instinct gets wrong. The sysadmin persona's *"you refuse to call a thing
healthy on its own say-so"* is a temperament statement and stays; an
instruction to *"verify each finding before reporting"* does not.

**Add length discipline, in both registers.** Claude Opus 5 writes longer
user-facing responses *and* longer files on disk. The weekly report is exactly
the artifact that bloats. Lowering `effort` does **not** reliably shorten
visible output — it has to be prompted:

> Match the length of the report to what was found. Cover the substance; do not
> pad with filler sections, redundant summaries, or boilerplate. A clean week is
> a short report.

**Add scope discipline.** Claude Opus 5 can widen a task and apply its own
judgment about what the task should be. For a read-only auditor, "decided to
just fix it" is the worst available failure:

> Deliver the audit at the scope asked. You observe and report; you never
> remediate, and you never change system state. If you conclude a fix is
> obvious, say so in a sentence in the proposal and stop there.

**Do not add subagent-delegation guidance.** Claude Opus 5 reaches for
subagents readily — the opposite of Opus 4.8, which under-reached and needed
prompting. Any "delegate more" language written for the 4.8 era should stay out
of this agent.

**Enumerate what, not how.** Prompts written for older models are often too
prescriptive for Claude Opus 5 and reduce output quality. The distinction that
matters here: §5's numbered checks are a **coverage contract** — they exist so
the checks actually run — and stay enumerated. Do not script the *method*
inside each check; state what must be true and let the agent choose how to
establish it.

**Corrections.** Claude Opus 5 narrates its own earlier mistakes at length. In a
weekly report that reads as thrash — scope corrections to ones that change the
operator's decision.

### Consequence for the sysadmin agent

The same shifts apply to `sysadmin` once it moves to Claude Opus 5. Its daily
charter has no severity bar and no verification instruction, so it is clean on
the two that matter — but its persona and report contract should get the same
length and scope discipline pass rather than being moved model-first and tuned
later.

## 11. Telegram — alerts out, Director in

Settled 2026-08-06 across a design conversation that started at a full slash-command
surface and collapsed to almost nothing. Recording the collapse, because the
discarded designs are the useful part.

### Already working — the outbound half

Every sysadmin pass calls `_notify(_pass_summary(...))`, so a summary line lands
in Telegram whether the pass is clean or has findings, plus
`notify-telegram@<unit>` for hard failures. The security agent inherits this
unchanged. **Nothing to build.**

### Rejected — a read surface

The first design gave each agent `/sysadmin findings`, `/sysadmin 3`,
`/sysadmin skipped` and so on, reading sections straight out of the report.
Workable — the parsers (`_FINDINGS_SECTION`, `_LEDGER_SECTION`) and the message
chunker already exist — but superseded, see below.

### Rejected — a conversational mode

`/sysadmin <question>` would **re-run an Opus 5 xhigh agent to answer questions
about work it already did** — paying for a fresh reasoning pass to retrieve what
is sitting in a file, and returning an answer that might not even match the
report. Expensive and non-deterministic.

### Settled — the Director is the read path

Both agents emit artifacts. The Director already has `read_file`, `grep` and
read-only git, scoped to registered project roots — and `/opt/ai-agent-platform`
**is** one of the three registered roots (verified 2026-08-06), so the proposals
dir and both ledgers are already inside its reach.

So follow-up is bare text to the Director, which is already the default. This is
better than a read surface on three grounds:

- **It preserves the crew's own separation.** The Director card states *the agent
  that decides is not the agent that produces, so nothing here marks its own
  homework.* An auditor that also explains its own findings collapses that; the
  Director reading the report is a genuine second pair of eyes.
- **The cost shape is right.** The Director is Sonnet 5 — a cheap fast model
  reading a file, instead of Opus 5 at xhigh re-deriving it.
- **It reasons across artifacts** — a security finding beside a sysadmin finding
  beside fresh git state. A per-agent read command cannot.

**The one gap: capability yes, pointer no.** The Director's prompt says "you can
read the projects yourself" and never mentions the crew's own artifacts. It will
find a report only if handed a path, and will not connect a Telegram alert to
the report behind it. **Fix: a few lines in the Director's system prompt naming
where crew artifacts land.** Small change; it is what makes this architecture
work at all.

### The final surface

```
alerts     →  push                     (already works)
follow-up  →  bare text to Director    (works; needs the prompt pointer)
trigger    →  /sysadmin, /security     (one command each)
```

**Why the trigger stays a command:** it is an action, and the Director is
read-only *by design* — "you have no write tools by design" is the property that
makes it safe to talk to. Giving it a run-a-pass tool trades that away for
convenience.

**Why the trigger is fire-and-acknowledge:** a pass takes ~4 minutes today
(06:20 → 06:24) and will take longer at Opus 5 xhigh. The listener is
single-threaded on a 30-second long-poll with a 45-second HTTP timeout, so an
inline pass freezes the bot and blows the timeout. `/sysadmin` launches detached
and replies immediately; the existing `_notify` push closes the loop.

**Launch without a privilege grant:** the `claude` user cannot start a system
unit (no polkit rules, no passwordless sudoers). Launch the pass as a detached
subprocess from the listener — both processes already run as `claude`. The
alternative, a narrow sudoers entry for `systemctl start`, buys systemd tracking
at the cost of a grant; `_notify` already covers the normal paths from inside.

### Open — the Director's own memory

Everything the Director says persists to `agent_decisions.decision_payload`
keyed by channel, which is what makes the six-turn replay possible. **Durable,
but not curated.** The crew's *producers* have ledgers — deliberate, append-only,
human-readable records of what mattered. The *interpreter* has undifferentiated
rows: a sharp read on a security finding sits in the same soup as "I'm here.
What do you need?"

The obvious fix is wrong: the Director cannot decide what is ledger-worthy —
that is grading its own output, and from the inside a confidently-phrased
banality is indistinguishable from a real connection. **The model is the worst
available judge of this.**

**Proposal: `/keep`** — append the last Director reply to a director ledger,
**authored by the operator**, through the existing constrained `ledger-append`
helper. Preserves the Director's read-only property (the operator writes, not
the agent), reuses the established write-exception path, and puts curation where
the only reliable judge is.

The payoff is larger than an archive: the sysadmin's ledger is its long-term
memory, injected every run. The Director has only a rolling six-turn window that
forgets by design. A curated ledger is the Director's **missing memory**, not a
filing cabinet.

## 12. The probe under Cloudflare Access

**Status: contingent.** Access is not enabled yet (see the 2026-08-06 audit's
INFO finding and `security-ledger.md` → `origin-reachable-by-ip`). Until it is,
§5's probe expectations hold unchanged. This section is what changes on the day
it lands — written now because the change is not a tweak, it inverts the
probe's whole reading.

### Every expectation inverts

Today a 403 or 404 on `/.git/config` is a pass and a 200 is a finding. Under
Access, an unauthenticated request to a protected path returns a **302 to the
Cloudflare login**. The agent then sees 302 across everything behind the
protected path and can no longer distinguish three very different states:

- Access is protecting this path ✅
- the path does not exist ✅
- Caddy is 404ing it ✅

All three collapse into one non-200. **A probe that only asks "is it 200?" goes
blind the day Access is enabled** — not broken, worse: silently uninformative
while still reporting green.

### The finding becomes an absence

A path that *should* sit behind Access returning 200 rather than a login
redirect means Access is not covering it. So the probe must carry a list of
what is meant to be protected and assert the redirect is **present**. Missing
redirect = misconfiguration.

### The reverse check is the valuable one

The classic Access mistake is scoping the policy too broadly — a rule on
`uzelhub.com/*` rather than the desk path puts the **entire marketing site**
behind a login. Googlebot receives a login page, the site falls out of search,
and every visitor hits a wall.

**A login redirect on a public marketing page is a CRITICAL finding**, and it
is the best single argument for the probe existing at all — because *this
failure is invisible to the person most likely to look.* The operator is
logged in. Their browser sails through. The site looks perfect to them while it
is dark to everyone else. Only an unauthenticated request catches it, and the
agent is the only unauthenticated party that checks weekly.

### Edge-versus-origin is the real instrument

The agent runs *on the box*, which gives it two vantage points on the same URL.
The **delta between them** is the signal — neither alone is:

```
curl https://host/path            → out to Cloudflare and back → sees Access
curl 127.0.0.1 -H "Host: host"    → bypasses Cloudflare        → sees origin raw
```

| Edge | Origin | Reading |
|---|---|---|
| 302 login | 403 / 404 | Properly protected at both layers ✅ |
| 302 login | 200 | **Access enforced at the edge only** — origin still serves it to anyone who finds the IP |
| 200 | 200 | Not protected at all |
| 302 login | *(a public page)* | **Over-scoped policy — silent SEO outage** |

Row two is the edge-enforcement gap identified during the 2026-08-06 audit.
This turns it from a standing caveat into a weekly assertion, and upgrades
`origin-reachable-by-ip` in the ledger from ACCEPTED-with-a-note to a checked
condition — the ledger entry already says it converts to a real finding the
moment the capability path is shortened.

### Ruled out: giving the agent an Access service token

Probing *behind* Access requires an Access service token. **Do not.** It is a
credential the agent would hold, which breaks the read-only, credential-free
property that makes an adversarial agent safe to run, and it would let a
prompt-injected instruction reach protected surfaces.

**The agent verifies the boundary, never the contents.** Checking that the
desk's pages are intact is a different job with a different trust profile, and
it does not belong to an agent whose charter is "assume the operator is wrong."

## 13. DRAFT — the report contract

**Status: draft, for reaction.** This is the gap that would have bitten the
build: §3's reconcile-after design needs every finding to carry a stable id,
and nothing was requiring the agent to emit one.

Shape deliberately **mirrors the ledger's**, so promoting a finding to a ledger
entry is close to a copy and the diff keys on the same heading in both files.

````
## Status: CLEAN or FINDINGS

## Findings

### `<id>` — <SEVERITY> — <confidence>
**Reachable:** what you ran and what came back — the receipt, verbatim.
**What an attacker gets:** one sentence, concrete. Not "information
disclosure" — what they hold afterwards.
<optional detail>

## Checks passed
- `<check-id>` — one clause on what was verified

## Checks not reached
- `<check-id>` — why (budget, tool refusal, needs a privilege)

## Ledger entry
<title line>
<body>
````

**Finding id rules — the load-bearing part:**

- Lowercase kebab, `class:target` — `docroot-git-exposed:studio.uzelhub.com`.
- Derived from **what the finding is**, never from when it was found or the
  order it appeared. Ids are the diff key; a date or an index in one makes
  every pass look like a new finding.
- **Never renumber. Never reword an id to read better.** A reworded id reads
  as "old one resolved, new one appeared" — a silent double error.
- One id per distinct condition per target. The same class on two hostnames is
  two findings, because they get fixed separately.

**`Checks passed` is not padding.** Without it, a later pass cannot tell
"checked and fine" from "never checked" — and the whole reason this agent
exists is that a check nobody ran looks exactly like a check that passed.

**Severity and confidence are recorded, never used to filter.** See §9.3 —
everything found gets an entry; ranking happens at read time.

## 14. DRAFT — the persona

**Status: draft, for reaction.** Replaces the §4 sketch. Written for Claude
Opus 5 per §10 — note what is deliberately *absent*: no instruction to verify
its own work, no subagent guidance, no severity bar.

> You are the security auditor for the Hetzner VPS hosting uzelhub.com,
> studio.uzelhub.com, blog.uzelhub.com and the predictor. You run weekly.
> **You reason from outside the box inward.** Assume an attacker has already
> found this server's IP in a routine sweep of Hetzner's ranges — because they
> have. Your question is never "is this configured as intended" but "what does
> this actually hand out, and to whom."
>
> **You observe and report. You never remediate and never change system
> state.** If a fix is obvious, say so in one sentence in the proposal and stop
> there. A human applies every change. Deliver the audit at the scope asked —
> do not widen it, and do not decide the task should have been something else.
>
> You are unsparing about the operator's own assumptions, including the ones
> written down. A control that exists is not a control that works: a firewall
> that is *running* may still permit the world, a file that is *gitignored* may
> still be served, a document that *says* the box is locked down may describe an
> architecture retired months ago. Verify the claim, never the intention. A
> stale security claim is itself a finding.
>
> **Report everything you find.** Attach a severity and a confidence to each
> finding and let the reader rank them. Do not suppress a finding because it
> seems minor, because you are unsure, or because it feels like noise — a
> filter at your end is invisible, and the failure this whole role exists to
> prevent is the check that quietly stopped happening. Surfacing something that
> later gets dismissed is cheap. Silently dropping a real one is not.
>
> A finding names **what an attacker gets**, not what a checklist says is
> missing. "No security headers" is theatre. "Any unauthenticated request
> retrieves the full git history of a private repository" is a finding.
> Absence of proof is not proof of absence: if you could not establish
> reachability, say that plainly rather than reporting it either way.
>
> Match the length of the report to what you found. A clean week is a short
> report. Do not pad with filler sections, restated summaries, or boilerplate.

## 15. Testing

Unit tests ship with the code, not after. Higher-level coverage below.

**Already built** (`tests/test_sysadmin_stop_reasons.py`, 8 tests): both
stop-reason guards, the missing-`stop_details` path, that the two errors are
distinguishable by a pager, and that cost prices at the served model.

**The one that matters most — a regression fixture for the finding that
created this agent.** A fixture Caddyfile plus a fake docroot containing a
`.git`, asserting check 1 fires. The whole agent exists because that went
unseen; a test that proves it would now be caught is the honest measure of
whether the build worked.

**Probe allow-list — security-critical, must be adversarial.** Assert the probe
refuses a hostname absent from the Caddyfile, refuses a non-GET/HEAD method,
and refuses a URL composed at runtime rather than drawn from the fixed list.
This is the boundary that keeps a prompt-injected instruction from turning the
agent into a scanner, so it gets tested like one.

**Reconcile classification.** Golden report + golden ledger → assert
new / recurring / **resolved**. Resolved is the case most likely to rot,
because it is inferred from absence.

**Report parser.** A report missing ids, or carrying a reworded id, must fail
loudly rather than silently producing a spurious resolved+new pair.

## 16. One spine row per finding — and the reconcile moves to SQL

**Corrects §3 and §13.** Earlier drafts specced "one `agent_decisions` row per
pass." That was wrong, and it was wrong from reading the sysadmin's current
behaviour as if it were the contract rather than one agent's choice.

**The schema says otherwise, explicitly.** `workflow_sequence_id` is commented
*"Groups all decisions in one run"* and `parent_decision_id` is a
self-referencing FK — neither means anything unless a run writes many rows. The
table is `agent_decisions`, not `agent_runs`.

**And multi-row is already the norm here.** Measured 2026-08-06:

| agent | sequences | rows | rows per run |
|---|---|---|---|
| `content_agent` | 6 | 276 | **46** |
| `marketer_agent.package` | 6 | 276 | **46** |
| `ghost.create_draft` | 6 | 270 | **45** |
| `scout_walk` | 29 | 83 | ~3 |
| `director` | 144 | 144 | 1 |

The Director is 1:1 because a conversational turn genuinely *is* one decision.
The sysadmin's one-row-per-pass is the outlier, not the pattern, and the
plumbing already exists — `log_manager.task_sequence` / `tool_sequence`, which
already carry `workflow_sequence_id`, `parent_decision_id` and `step_number`.

### What this changes

**A finding is a decision.** One row each, sharing the pass's
`workflow_sequence_id`, with the stable id and severity in the payload. A
refusal is also a decision — write a row for it rather than raising with no
trace, or refusals stay countable only by scrolling Telegram.

**The reconcile step becomes a query, not a diff.** §3 specced parsing two
markdown files and taking a set difference. With findings on the spine:

- **new** — id absent from the previous sequence
- **recurring** — id present in both
- **resolved** — id in the previous sequence, absent now
- **first seen** — `min(decision_timestamp)` for that id, free
- **age** — how long a finding has been open, free

No parser, nothing to rot, and no risk of a markdown format change silently
breaking the classification.

**The ledger keeps its own job** and does not become redundant. The spine holds
the structured facts; the ledger holds the narrative — the receipts, the "what
an attacker gets" prose, the reasoning a human needs six months later. Same
split the sysadmin already has between its spine row and its ledger entry. §13's
report contract stands unchanged: it is what a *human* reads, and the id in the
heading is what ties the prose to the row.

### Open

- **`decision_type` value.** The schema comments the existing set as
  `'invoke' | 'route' | 'classify'`. A finding is none of those. Adding
  `'finding'` and `'refused'` is the honest move; confirm nothing downstream
  switches exhaustively on that column first.
- **Parenting.** Findings as children of one pass-level row (`parent_decision_id`)
  gives a natural "the pass, and what it found" tree, and makes the pass row
  the place to hang cost and status. Worth doing if the helper makes it cheap.
