# The Ops Calendar — format, guardrails, service (spec)

> **Status:** updated 2026-07-17. The append path (`calendar-add`, including
> VEVENT and VTODO), the lifecycle verb (`calendar-mark`), and the derived
> views (`calendar-views` — todos.ics projection + todos.html list) are all
> built and proven; the subscription/serving routes (Caddy) remain spec.
> Design doctrine: RFC 5545 is the application — git is history, the helpers
> are the write API, agents and phone clients are readers. No calendar server
> exists or is wanted.

## The file

`ops/calendar.ics` — one VCALENDAR, `X-WR-TIMEZONE:America/New_York`, timed
events floating local. Freehand edits are **operator-only**; agents write
exclusively through the helpers below. Every write is git-committed with
author attribution.

## Namespaces (the whole security model)

The UID suffix is the ownership boundary, enforced in helper code — never by
prompt discipline:

| Author | UID suffix | May create | May lifecycle |
|---|---|---|---|
| operator | `@ai-agent-platform` | any | any (human hands, but still only via constrained transforms) |
| director | `@director.ai-agent-platform` | own suffix only | own suffix only |
| sysadmin *(planned)* | `@sysadmin.ai-agent-platform` | own suffix only | own suffix only |

**No author, ever, lifecycles another namespace's items.** Cross-namespace
needs are expressed as a *new* item in your own namespace (e.g. the sysadmin
scheduling a follow-up to a director event), or as a proposal to the operator.

## Verbs

### `calendar-add` (BUILT — `ops/calendar-add`)

Appends ONE validated `VEVENT`. Enforces: namespace suffix by author,
duplicate-UID refusal, field validation + ICS escaping/folding, daily rate
cap (refuse loudly, never loop). `--alarm=-PT1H` (equals-form — the value
starts with a dash).

### `calendar-mark` (SPEC)

The only mutation verb. Applies exactly one lifecycle transform to exactly
one item, matched by UID, within the author's namespace:

- **On a `VEVENT`:** set `STATUS:CANCELLED` (RFC 5545: VEVENTs may be
  TENTATIVE / CONFIRMED / CANCELLED — *there is no COMPLETED for events*).
  Cancelled events stay in the file; subscribed clients hide or strike them.
- **On a `VTODO`:** set `STATUS:COMPLETED` + `COMPLETED:<utc-stamp>`
  (and optionally `PERCENT-COMPLETE:100`).
- **Every mark also:** increments `SEQUENCE` (creates it at 1 if absent) and
  refreshes `DTSTAMP` — this is how subscribed clients learn an item changed.

- **On a `VTODO`, `--action defer`:** set a new `DUE` (BUILT 2026-08-30). The
  third transform, added because there was previously **no way to change a due
  date** through sanctioned tooling — add only appends, mark only did
  lifecycle — so a slipped date could be fixed only by cancel-and-recreate
  (re-keying the UID and dropping `RELATED-TO`) or by an operator editing the
  file freehand. That gap is why the list reached 2026-08-30 with 42 of 44
  todos overdue: moving a date was harder than ignoring it.

  A reschedule verb can make a rotten list look healthy, so every defer keeps
  a receipt in-band: `X-ORIGINAL-DUE` (the first due date the item ever had,
  written once and never rewritten), `X-DEFER-COUNT`, and `X-DEFER-REASON`.
  Lateness is promoted rather than erased — "due 09-14, deferred 3x, originally
  07-19" is better signal than a six-week-stale date, and a high defer count
  marks an item to kill rather than move again. Refuses on a `VEVENT`, on a
  CANCELLED/COMPLETED item (reopening is a decision, not a reschedule), and on
  a no-op date.

  **`--plan <file>` (operator only)** applies a reviewed batch — lines of
  `<uid> <YYYYMMDD> [reason]`, `#` comments ignored. All-or-nothing: every line
  must validate or nothing is written, so a typo cannot half-rebase the file.
  It needs one free write to start rather than one per move, but still stamps
  each moved component, so a large re-base deliberately spends the rest of the
  day's budget. Operator-only because a bulk defer carries the same authority
  as the freehand edit it replaces.

Hard limits, in code: never delete a component; never touch `UID`, `DTSTART`,
or `SUMMARY` (that's a re-key/rewrite — make a new item instead); never edit
anything outside the matched component; own rate cap; git commit with
attribution, e.g. `calendar: mark done <uid> (director, via calendar-mark)`.

**Named acceptance test — PASSED 2026-07-06 (`fe543ee`):** the Director
itself, conversationally, marked
`github-ssh-key-refresh-20260704@director.ai-agent-platform` CANCELLED — after
warming up on its own smoke event (`8d9838c`) and volunteering, unprompted,
the RFC correction that "mark done" must be `cancel` on a VEVENT. The
"live specimen of state-drift-by-missing-verb" is no longer live; the verb
exists and its author has used it. Original criterion preserved below for the
record: *the build isn't done until the Director itself marks the golden todo
CANCELLED — completed on the back end 2026-07-06 (receipts in
docs/director/devlog.md) but untouchable on the calendar because this verb
didn't exist.*

### `calendar-add --todo` (BUILT — `ops/calendar-add --todo`, 2026-07-11)

To-do–shaped items (like the GitHub key refresh was) are `VTODO`, not
`VEVENT` — that's the component with a real completion lifecycle (`DUE`,
`STATUS:COMPLETED`, `PERCENT-COMPLETE`). Same validation, same namespaces,
same alarms; the one difference is the deadline field: `--due YYYYMMDD` (all-day,
emits `DUE;VALUE=DATE:`) or `--due YYYYMMDDTHHMMSS` (timed, emits `DUE:`) in
place of `--date`/`--start`/`--end`. New VTODOs are created
`STATUS:NEEDS-ACTION`; `calendar-mark --action complete` (VTODO-only) and
`--action cancel` both work on them unchanged — verified interop 2026-07-11
(a smoke VTODO created with `--todo` was marked `COMPLETED` via
`calendar-mark` with `SEQUENCE`/`COMPLETED`/`PERCENT-COMPLETE` set correctly).

**Subtasks — `RELATED-TO`:** `--related-to <uid>` chains a new VTODO to an
existing component's UID, emitting `RELATED-TO;RELTYPE=<type>:<uid>`.
`--reltype` is `PARENT` (default), `CHILD`, or `SIBLING`. The target UID must
already exist in the calendar — `calendar-add` refuses a dangling reference
or a self-reference — but the target can be in *any* namespace; `RELATED-TO`
is a descriptive link, not a grant of write access. Only settable at creation
(one per component; `calendar-add` never edits an existing item to add a
second relation later). `--todo`-only for now — not offered on `VEVENT`.
Existing to-do-flavored VEVENTs stay as they are (immutability); new to-dos
use VTODO.

## The subscription route (SPEC — operator applies; Caddy is operator-only)

Purpose: the operator's real phone calendar *subscribes* to the ops calendar.
Agent writes → git → served file → native alarms on the wrist. Zero calendar
software; the format is the interface.

```caddy
# Inside an existing HTTPS site block (apex or blog — either works).
# <TOKEN> = openssl rand -hex 16, generated AT APPLY TIME and living ONLY in
# the Caddyfile — a capability URL. Do not commit the real token to any repo.
handle /ops-cal-<TOKEN>.ics {
    header Content-Type "text/calendar; charset=utf-8"
    header X-Robots-Tag "noindex"
    header Cache-Control "no-cache, max-age=0"
    root * /opt/ai-agent-platform/ops
    rewrite * /calendar.ics
    file_server
}
```

Client setup: iOS → Settings → Calendar → Accounts → Add Subscribed Calendar
→ the full https URL. (Google Calendar's "From URL" also works but polls on a
lazy schedule — hours to a day; iOS refreshes more eagerly.)

Security posture, stated honestly:

- **Auth = the unguessable path** (capability URL). Rotation = new token in
  the Caddyfile, one reload, re-subscribe. Right-sized for a single-operator
  box; if that ever feels thin, `basic_auth` is the next notch.
- Event descriptions mention internal paths and operational details — the URL
  must never appear in a repo, a sitemap, or a page. `X-Robots-Tag` is
  belt-and-suspenders, not the protection.
- Behind Cloudflare, `no-cache` from origin is respected for proxied content;
  if a stale copy ever persists, purge the single URL rather than everything.

## Derived views (BUILT — `ops/calendar-views`, 2026-07-17)

The client gap this closes: **Google Calendar and Apple Calendar silently
drop VTODOs from URL-subscribed feeds**, and neither offers a todo-list view
of a subscribed calendar — the todos publish fine and render nowhere. The
spec had the right component all along; the read stopped at the client. So
the calendar stays the single source of truth and grows two read-only,
decision-free projections in `ops/views/` (gitignored — derived, regenerated
wholesale, never edited):

- **`todos.ics`** — every open VTODO projected as a VEVENT on its `DUE` date
  (all-day, or a 1-hour block for timed DUEs; `☐ ` summary prefix;
  `todo-view.` UID prefix so both feeds subscribe side by side without UID
  collisions; VALARMs carried over; completed/cancelled drop out on next
  regeneration). Subscribed as its own URL it gets its own color and toggle —
  Google's **Schedule view with only this calendar visible is the todo list**
  Google won't otherwise provide.
- **`todos.html`** — the actual list: overdue / due today / next 7 days /
  later buckets, namespace badges from the UID suffix, `RELATED-TO` subtask
  links, descriptions behind a tap, completions from the last 14 days struck
  through. No lag behind a lazy poll — it is current as of the last write.

Regeneration: `calendar-add` and `calendar-mark` both call `calendar-views`
after every successful write (best-effort — a view failure warns, never
refuses the write that already landed). Run it by hand after an operator
freehand edit. Date buckets are computed at generation time, so between
writes the HTML's "overdue" line can lag the calendar date; if that ever
matters in practice, a daily timer invoking `calendar-views` fixes it — not
pre-built, per don't-build-on-spec.

Serving (SPEC — operator applies, same capability-URL posture as the
subscription route; tokens minted at apply time, never committed):

```caddy
handle /ops-todos-<TOKEN>.ics {
    header Content-Type "text/calendar; charset=utf-8"
    header X-Robots-Tag "noindex"
    header Cache-Control "no-cache, max-age=0"
    root * /opt/ai-agent-platform/ops/views
    rewrite * /todos.ics
    file_server
}
handle /ops-todos-<TOKEN>.html {
    header X-Robots-Tag "noindex"
    header Cache-Control "no-cache, max-age=0"
    root * /opt/ai-agent-platform/ops/views
    rewrite * /todos.html
    file_server
}
```

One token can serve both handles; rotation is the same one-reload story as
the calendar URL. The HTML page carries `noindex` in its own meta as well.
Known client caveat, stated honestly: Google polls URL subscriptions on a
lazy schedule (hours to a day), so a completed todo can linger checked-off
in Google until the next poll; the HTML view has no such lag.

## Failure posture

Helpers refuse loudly and exit non-zero; they never retry-loop. A refused
write is a *message to the author* (wrong namespace, duplicate UID, rate cap,
malformed field) — the author says so in its reply rather than working around
it. The calendar file is never left half-written: helpers build the full
component text first, then splice in one write.

## What this deliberately is not

- Not a scheduler daemon: `RRULE` + the reading clients do recurrence.
- Not a notification service: `VALARM` + the subscribing client do alarms;
  failure-class paging stays with `notify-telegram` (different channel,
  different contract).
- Not a shared mutable database: add-only + single-transform lifecycle +
  namespaces. If richer coordination is ever needed, that's `agent_decisions`
  territory, not more ICS verbs.
