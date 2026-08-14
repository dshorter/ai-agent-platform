# Director — Ledger

> **What this is:** the Director's system of record — dated, receipt-bearing
> findings that outlive any single run. The sysadmin ledger's contract, applied to
> cross-project work (see `docs/uzelhub-crew/sysadmin-ledger.md`, opened 2026-07-06).
> Precedence position 3, below live tool output and the injected turn state, above
> repo prose. **Memory is for pattern recognition — recurrences, trend lines, what
> a decision cost last time. Never for current state.** The calendar says what is
> due; git says what shipped; this says what keeps happening.
>
> **Why the Director needed one.** Everything it says is already persisted in
> `agent_decisions`, and each turn replays the last 6 turns *on its own channel* —
> so the 07:00 brief sees the last six mornings and has never read a word of the
> Telegram thread, and neither accumulates. It was replay, not memory. On
> 2026-08-11 the morning brief spent 8 of 12 tool calls rebuilding the to-do list
> from a truncated `ops/calendar.ics`, worked out on call twelve that the assembled
> view was the right source, and hit its step cap before it could use that. It had
> done the same thing, from scratch, for six consecutive mornings. Nothing on this
> box let it end a day knowing something it hadn't known that morning.
>
> **Write contract:** add-only, dated entries, receipts inline — and **newest
> entries go at the TOP**, immediately below this header. Immutability is semantic,
> not positional: prior entries are never altered; corrections are new dated entries
> citing what they correct. Newest-first matters because the read tool returns a
> bounded PREFIX of a file — an append-at-bottom ledger silently loses its newest
> entries first, which is the exact inversion of what a reconciliation loop needs.
> (That trap is not hypothetical: it is what happened to the calendar on 08-03.)
> The Director writes via `ops/ledger-append` only — validated shape, never edits
> prior text, rate-capped, `--author director` hardcoded in the toolbox. Freehand
> edits stay operator-only. This is the Director's **second** write exception,
> granted 2026-08-11 on the same reasoning as the first: bounded blast radius. The
> calendar exception is a write to shared state that other tools read as truth;
> this one is the agent's own notebook, append-only, and barred by the precedence
> rule above from ever being cited as current state.
>
> **Read contract:** injected into every turn's state, so it arrives before the
> first tool call rather than being discovered. New findings are checked for
> **rhymes** against the entries below before being reported as novel — when a
> finding rhymes, say so and name the entry. When this file nears the read budget,
> propose a compaction: oldest entries distilled into a canon section, never
> silently dropped.

---


## 2026-08-13 — Repeating a top recommendation doesn't clear it; unverified guesses compound if restated

`activate-ask-tracing` (restart uzella-proxy) has been this brief's #1 item for 6+ consecutive mornings (overdue count climbing 5d→10d, due 08-03, still open 08-13). Zero risk, one command, no dependency — repetition alone hasn't moved it.

Also corrected this run: I'd speculated (08-09 to 08-11 turns) that predictor_ingest commits `a0cea3a`/`7a6e00c` (both 08-02) touched the files behind the 26 failing tests and might have partially self-resolved them. Checked directly 08-13: neither commit touches any `test_resolve`/`test_extract` file, and `a0cea3a`'s own message records the suite at "pre-existing baseline (642 passed)" after landing — unchanged. Untested speculation, restated across three mornings before being checked.

**Pattern:** a recommendation repeated verbatim without new leverage (escalation, channel change, an explicit "why hasn't this landed") is testimony, not action. And a speculative bridge between an unrelated commit and an open bug needs a grep/diff check the first time it's raised, not the third.

## 2026-08-11 — A cap sized once, against data that grows, is a silent capability loss

Third instance of one shape, and it is now a law rather than an incident.

1. `ops/calendar.ics` crossed the 40,000-byte read ceiling on 08-03. Nothing
   failed. The morning brief simply stopped seeing the 8 newest todos — including
   three it went on to cite — and spent 08-06 through 08-11 grinding greps to
   rebuild by hand what a whole-file read used to give it. Cap hits went from 2 in
   22 days to 4 of the last 6 runs. Detected by a human reading a bad brief, five
   days late.
2. `pipelines/scout/state/leads.yaml` (371KB) is the silent form of the same
   thing: read 8 times at 10% visibility, no follow-up greps, no cap hit, no cost
   spike, no hedge in any reply. A confident answer built on a tenth of a file is
   indistinguishable from a confident answer built on all of it.
3. `predictor_ingest/docs/project-plan.md` (90KB) was 44% visible across 7 reads.

**The law:** any fixed limit measured against data that grows will eventually
degrade a capability, and the degradation is silent unless something outside the
agent measures it. The agent's own account of *why* it stopped is testimony;
`agent_decisions` is telemetry. Trust the table.

Fixed the same day: read ceiling 40k → 120k, the truncation notice now states what
fraction was lost, and `tests/test_director_tools.py` fails when a document meant
to be read whole outgrows the ceiling. Commits `8040a8c`, `6f5d0c3`.

## 2026-08-11 — I reported the wrong cause, and it pointed Dan at the wrong dial

The morning brief opened "Budget's out mid-read." It had spent $0.28 of a $15 cap.
The loop's close-out said "Budget **or** step limit reached" and I resolved the
disjunction by guessing — it was the 8-step cap, which binds at about 2% of the
cost cap and had never once been reached.

**The rhyme to watch for:** when a limit stops me, the cause I *infer* is not
evidence. A wrong cause is worse than no cause, because it sends Dan to tune the
dial that was not the problem. The close-out now names the cap and rules out the
others, and `limit_hit` is recorded in the decision payload so a forced close is a
queryable fact rather than a claim in my own prose. Commit `744fdb1`.

## 2026-08-11 — Ledger opened; what the Director already had, and did not

Opened alongside the sysadmin's (2026-07-06) and security's ledgers, which had
been running the pattern for five weeks before the Director got one.

Inherited state at opening: `agent_decisions` holds 122 Director turns across
three channels (telegram 80, tick:morning 34, selftest 8), each with reply, tool
trace, cost, iterations, and now `limit_hit`. Turn history replays the last 6
turns, filtered by channel, capped at 1,200 chars per reply — reaching back to
08-05 on Telegram and 08-08 on the morning brief. Complete persistence and
per-channel continuity; no accumulation, no cross-channel view, no synthesis.
This file is the synthesis layer.
