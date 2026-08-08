---
read: full
status: SPEC — not built. Written 2026-08-06 during the apex copy walk.
       Decision pending on the open questions in §9.
---

# Receipt refresher — deriving the agent-card numbers

The agent cards on `uzelhub.com/agents/` each carry a **receipt**: what that
agent has actually done, with real numbers. `uzelhub-web/marketing/README.md`
calls the receipt "the whole point of the page" — a claim of fact rather than
capability. They are the most credibility-bearing copy on the site.

They are also hand-authored prose, and they are the only numbers on the site
with no mechanical backstop. Every other figure — the stat strip, the ticker —
recomputes itself on each build. The receipts do not.

## 1. The problem, measured

Confirmed against `agent_decisions` on 2026-08-05:

| Card claims | Table says | Verdict |
|---|---|---|
| content-agent: 276 runs, 25 Apr–9 May | `content_agent` 276, same dates | exact |
| marketer-agent: 552 runs, 25 Apr–9 May | `.extract` 276 + `.package` 276 = 552 | exact |
| writer: 18 runs since 15 July | `writer_draft` 18, from 2026-07-15 | exact |
| director: **130** runs since 27 June | `director` **140**, from 2026-06-27 | **drifted +10** |
| sysadmin: "at 06:20 **every day** since 25 July" | 11 rows over 24 Jul–5 Aug (13 days) | **likely false** |
| wire-editor: "a **single pass** on 18 July" | `wire_triage` 7 runs through 3 Aug | **stale framing** |
| ask-assistant: "six instances" | only `ask.explorer` has ever run, once | **overstated** |

Three receipts match to the row, which is how we know the table is where these
numbers came from. The rest have decayed since they were written.

**The sysadmin line is the important one.** It is not stale, it is a claim of
*continuity* — "every day" — that nothing ever checked. That failure mode is
the argument for this whole document: a hand-written qualitative claim can
become false without anything moving.

## 2. Goals / non-goals

**Goals**

- Receipt numbers that cannot silently rot.
- Claims that stay true when the site is *not* rebuilt for a while.
- No new obligation on `generate.js` or on anything downstream of the copy.

**Non-goals**

- **Not a cron.** Operator-run, from the weekly calendar reminder
  (`apex-agent-receipts-weekly@ai-agent-platform`) or before a deploy.
- **Not live data.** The site is evidence of real life, not a status page.
- **Not full automation of the prose.** Only the numbers derive. The sentence
  around them stays authored — that sentence is what makes a receipt land.

## 3. Why precompute, and not derive in the generator

The numbers are resolved **before** `generate.js` runs, and written into
`data/agents.json` as ordinary strings. Three reasons, in order of weight:

1. **No cross-repo runtime coupling.** `agent_decisions` lives in Postgres on
   the `ai-agent-platform` side. If `generate.js` queried it, building the
   *private* web repo would depend on the *public* platform repo's live
   runtime state — two repos, different visibility, joined at build time.
   The refresher reaches across; the generator never does.
2. **A broken refresher cannot break the site.** `generate.js` keeps reading
   plain strings. If the DB is down or nobody runs the refresher, the build
   still produces a correct site carrying the last known-good figures.
   Stale-but-shipping beats broken.
3. **The generator's contract is untouched.** No token syntax in any field the
   generator or its downstream consumers read — no second escaping path, and
   the meta descriptions, ask-packs and syndication kit keep working without
   knowing anything changed. (An inline-token approach was tried for hero
   links on 2026-08-05 and reverted; see `VOICE-LEDGER.md` entry 5.)

The template *does* use tokens — but only in a field nothing but the refresher
reads. That is the distinction that makes it safe.

## 4. Receipt shapes

Two modes, chosen per agent.

### `rolling` — live agents

> `{n}` runs since `{since}`.  *…authored sentence continues…*

`{since}` is a real date, not "the last 30 days". This matters: naming the
date makes the claim a **floor**. If the site is not rebuilt for two months,
the true count since that date has only grown, so the page understates — the
safe direction. An unanchored phrase ("in the last 30 days") would instead
claim a recency it no longer has, which is a worse failure than the staleness
being fixed.

It also keeps the sentence shape already on the page, and reads like speech.

### `fixed` — dormant agents

Left exactly as authored. `content-agent` and `marketer-agent` last ran
9 May; any rolling window renders them **0 runs**, which is true and useless.
Their present sentences — *"276 runs between 25 April and 9 May. Idle
since."* — are already the honest and better form.

The refresher never touches a `fixed` receipt.

## 5. The window rule

```
since = max(today − windowDays, first_recorded_run(sources))
```

`windowDays` defaults to **31**.

The clamp is the part that matters. `sysadmin` first ran 24 July with 11 runs.
A flat today−31 yields *"11 runs since 6 July"* — reading as roughly one run
every three days, and implying three idle weeks that never happened. Clamped,
it yields *"11 runs since 24 July"*, which is both more accurate and more
flattering. Same data.

Without the clamp, every young agent is libelled by its own receipt.

## 6. Data model — `data/agents.json`

Per agent, one optional block. `generate.js` reads **only** `receipt`.

```json
{
  "slug": "director",
  "receipt": "140 runs since 6 July. Holds a chat line open all day for questions, and files a written brief every morning at seven.",
  "receiptSpec": {
    "mode": "rolling",
    "windowDays": 31,
    "sources": ["director"],
    "template": "{n} runs since {since}. Holds a chat line open all day for questions, and files a written brief every morning at seven."
  }
}
```

- **`receipt`** — materialised output. Committed, like a lockfile. The only
  field the generator sees.
- **`receiptSpec`** — the recipe. Never read at build time.
- **`sources`** — one or more `agent_name` values, **summed**. Card slugs do
  not map 1:1 to row keys:

  | Card | `agent_name` key(s) |
  |---|---|
  | director | `director` |
  | sysadmin | `sysadmin` |
  | writer | `writer_draft` |
  | wire-editor | `wire_triage` |
  | marketer-agent | `marketer_agent.extract` + `marketer_agent.package` |
  | content-agent | `content_agent` |
  | scout | `scout_walk` + `scout_synthesis` — **but see §9** |
  | ask-assistant | `ask.*` — **see §9** |

- **`template`** — tokens `{n}` (count) and `{since}` (date, formatted to
  match the existing copy: `6 July`, day-month, no year).

Agents with no `receiptSpec` are `fixed` by definition.

## 7. The refresher

```
uzelhub-web/scripts/refresh-receipts        # writes marketing/data/agents.json
uzelhub-web/scripts/refresh-receipts --dry-run   # prints the diff, writes nothing
```

Lives in `uzelhub-web` because it writes that repo's data and the marketing
site owns its own content. Reads the platform's DB read-only.

**Behaviour**

1. One query, grouped by `agent_name`, returning count and first/last
   timestamp per key.
2. For each agent with `mode: rolling`, compute `n` and `since` per §5,
   render `template`, write to `receipt`.
3. Print a unified diff of every receipt that changed.
4. Never touch `mode: fixed`.

**Failure posture** — if the DB is unreachable, exit non-zero and write
nothing. A partial refresh is worse than a stale one. `agents.json` is left
byte-identical and the site still builds.

**Clobber warning** — hand-editing a `rolling` `receipt` is lost on the next
run. Wording changes go in `template`. The `--dry-run` diff is the guard.

## 8. Sequencing

The weekly reminder currently reads "check receipts against reality, edit
agents.json, then regenerate." Once this exists it becomes:

```
uzelhub-web/scripts/refresh-receipts --dry-run   # read the diff
uzelhub-web/scripts/refresh-receipts             # apply
node marketing/generate.js                       # publish
```

The reminder stays a reminder. Nothing on the box runs this.

## 9. Open questions — decide before building

1. **Scout's lead count is not in this table.** *"Has filed 248 leads since
   12 July"* comes from `pipelines/scout/state/leads.yaml`, which now holds
   **269**. Either the refresher grows a second source kind (`file:` as well
   as `db:`), or scout's lead figure stays hand-maintained. Recommend
   deferring — one file source is not a source *system*.
2. **Low-frequency agents may not want a number at all.** `wire_triage` has 7
   rows since 18 July, `chief_shadow` 4. *"4 runs since 6 July"* is a weaker
   receipt than the qualitative sentence those cards carry now. Candidate for
   `fixed` even though they are live.
3. **ask-assistant's claim is structural, not temporal.** "Six instances, one
   per product" tracks `products.json` length, not run counts — and only one
   instance has ever run. Needs a copy decision before any derivation
   decision.
4. **Rows are decisions, not runs.** The schema has `run_id` into
   `pipeline_runs`. For the three exact matches, one row = one run. Unverified
   for `sysadmin` — if `count(distinct run_id)` differs, the query in §7 must
   use it instead of `count(*)`.
5. **Is this worth building at all?** With scout deferred and the
   low-frequency cards possibly `fixed`, this may refresh as few as three
   numbers. Against `don't-build-on-spec`, three is thin. The counter-argument
   is §1's sysadmin line: the failure it prevents is a *false claim*, not a
   stale one.
