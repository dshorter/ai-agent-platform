# Blog outline — "The clip that told no one"

> **Status:** detailed outline, 2026-08-12. Post 2 of a three-post series (drafted
> first because it is the strongest and carries the receipts). Circumventing the
> newsroom deliberately — importance hard/soft features are mid-tweak — so this is
> a hand outline, not a Writer draft. Voice docs are in flux in another session, so
> what follows is bullet-oriented capture with prose only where the phrasing is
> load-bearing.
>
> **Series spine (say this once, in whichever post ships first):** the agent
> couldn't say why it stopped; the system couldn't say it had degraded; the agent
> couldn't keep what it learned. Three failures of a system's ability to know
> things about itself.
>
> - Post 1 — the wrong error message (self-report vs telemetry)
> - **Post 2 — this one** (silent capability loss)
> - Post 3 — we didn't need to build it (learned context)

---

## Working titles

- **The clip that told no one** ← lead candidate
- A cap sized once
- The guardrail became the injury
- Ninety percent of a file, and no way to tell

## The one-sentence thesis

Any fixed limit measured against data that grows will eventually degrade a
capability, and the degradation is silent unless something outside the agent
measures it.

## Who it's for

Anyone running an agent against their own files. The failure needs no unusual
stack to reproduce — a read tool with a byte ceiling and a document that grows is
the entire setup.

---

## 1. Cold open — the grinding

- On the morning of 2026-08-11 the Director spent **eight of its twelve tool calls
  on a single file.**
- Two whole-file reads and six greps, all against `ops/calendar.ics`.
- It hit its step cap and shipped a thin brief.
- The obvious read is a stuck loop. It isn't. Every call succeeded, and every call
  was different.
- **Hold the reveal here.** The reader should be told what it looks like before
  being told what it was.

## 2. What it was actually doing — a join, by hand

- The calendar had crossed the read tool's byte ceiling: **51,100 bytes against a
  40,000-byte limit.**
- A whole-file read returns the first 40,000 bytes and a truncation notice. The
  lost 11,100 bytes held **the 8 newest todos of 58** — including three the brief
  went on to cite.
- So it went around through grep. And grep is line-oriented while a VTODO is a
  record: SUMMARY, DUE, and STATUS are three separate lines, and long descriptions
  are folded across continuation lines.
- **No single grep can return one whole todo.** To reconstruct "what's overdue and
  what's it called," you grep once per field and zip the results by hand.
- Six greps is roughly what that costs.

> **Diagram 1 — why one grep is never enough.** Left: a VTODO as it sits in the
> file, ~8 lines, fields stacked. Right: what a grep for `SUMMARY:` returns — a
> column of titles with no dates attached. Then a second column for `DUE:`, a third
> for `STATUS:`. Arrows showing the reader (the model) having to zip three columns
> by position. Caption: *the file is record-shaped; the tool is line-shaped.*

## 3. The part worth the whole post — call twelve

- Read the tool calls in order. It escalates:
  1. whole-file read → truncated
  2. field-by-field greps → the workaround
  3. one more whole-file read, as if the front door might behave differently
  4. **then it abandons the raw file, reads the desk directory, and opens
     `todos.html`** — the assembled view where the joining is already done.
- It found the right answer **on call twelve. The step cap took the turn away on
  call thirteen.**
- Three strategies in one turn, each a reasonable response to the last one's
  failure. It solved the problem one move before the wall — and got nothing for it.
- The line to land: *it doesn't get to keep the insight. Next morning's tick starts
  cold and walks the same three steps again.*

> **Diagram 2 — the escalation, as a timeline.** Twelve numbered ticks. Calls 1–2
> shaded "read the source," 3–10 "reconstruct by hand," 11–12 "find the assembled
> view," and a hard vertical bar at 13 labelled *step cap*. The visual point is how
> close the good answer came to being usable.

## 4. Dating it — the degradation has a birthday

- The hypothesis worth testing: has this always been happening, or is it new?
- Both halves are checkable, and the answer is sharper than "it's always been bad."
- `ops/calendar.ics` is tracked, so git has its size over time. It crossed 40,000
  bytes on **2026-08-03**.
- `agent_decisions` has every morning brief ever run, with iteration count and the
  tool trace. Grinding starts **08-06**.
- The three-day lag is the honest detail: right after crossing, only ~4 todos fell
  off the end and it could work without them. As the tail grew to eight — and those
  newest items became the actionable ones — it had to go get them. **The
  degradation scaled with the size of the lost tail, which is why it ramped instead
  of snapping.**

> **Table A — before and after.** Two columns, one row per metric.
>
> | | Before Aug 3 | Aug 6 onward |
> |---|---|---|
> | Calls on the calendar per run | 0–1 | 4, 5, 5, 8, 9, 10 |
> | Runs hitting the 8-step cap | 2 in 22 days | 4 of the last 6 |
> | Typical cost | $0.10–0.15 | $0.22–0.28 |

- Six weeks of a working capability, then a silent stop, **with no code change
  anywhere near it.** The trigger was a to-do list getting longer.

## 5. The turn — the loud failure is the lucky one

- This is the pivot of the piece. Everything above is the version that announces
  itself: grinding, cap hits, a cost bump, eventually a brief bad enough for a
  human to notice.
- The same defect has a silent form, and the decision spine says we've been living
  with it.

> **Table B — the read/grep split across 45 days.** This is the argument; show it
> whole.
>
> | File | Size | Visible | `read_file` | `grep` |
> |---|---|---|---|---|
> | `pipelines/scout/state/leads.yaml` | 371 KB | **10%** | 8 | 2 |
> | `predictor_ingest/docs/project-plan.md` | 90 KB | 44% | 7 | 16 |
> | `ops/calendar.ics` | 51 KB | 78% | 23 | 36 |
> | `docs/uzelhub-crew/NEWSROOM.md` | 42.7 KB | 93% | 9 | 2 |

- **Read the ratio, not the size.** Where grep far outruns read, the agent is
  *fighting* — visible, expensive, self-announcing.
- `leads.yaml` is the other shape entirely: opened eight times, **a tenth of it
  seen**, no follow-up greps, no cap hit, no cost spike, no hedge in any reply. It
  didn't fight. It took the first 10% as the answer.
- The sentence the post exists to deliver: **a confident answer built on ten
  percent of a file is indistinguishable from a confident answer built on all of
  it.**
- The truncation notice was in every one of those eight results. It read it and
  moved on.

## 6. The convention that was already being violated

- `NEWSROOM.md` carries `read: full` on line 2 of its own front matter — a
  documented convention meaning *read this whole, never conclude from a partial.*
- It has been 7% past the ceiling since it crossed.
- The doc says read it all; the substrate has quietly been unable to.
- Short section. It's a corroborating detail, not the argument.

## 7. The irony — the guardrail became the injury

- That 40,000-byte ceiling is **layer two of a three-layer guardrail** built on
  2026-06-29 to stop the grep-bomb: a vague instruction sent grep across scraped
  HTML with single lines up to 731k chars, which OOM'd the process (exit 137) and
  built a 3.77M-token prompt that 400'd.
- The guard worked. That failure has never recurred.
- **What went unwritten is that a clip protects the process and blinds the agent,
  and only the first half was designed.** Six weeks later the guardrail was the
  injury.
- Worth stating plainly: this is not an argument against the clip. It's an argument
  that a clip is a silent lie by omission unless something checks the size.

## 8. The law, and the instrument that was already there

- **The law:** any cap sized once, against data that grows, becomes a silent
  capability regression with no alarm — and the agent's account of *why* it stopped
  is testimony, not telemetry.
- Everything needed to catch it was already in `agent_decisions`: iteration counts,
  tool paths, timestamps. Two mechanical detectors fall straight out, neither
  passing through the agent's self-assessment:
  1. **run ended at the iteration cap** — would have fired 08-06, five days early
  2. **a `read_file` against a file bigger than the ceiling** — pure arithmetic;
     severity is `1 − ceiling/size`
- Detector 2 matters more, because it catches the `leads.yaml` case that produces
  no symptom at all. The loud one trips a cap; the quiet one only shows up in the
  arithmetic.

## 9. What changed

> **Table C — the fix set.** Keep it terse; the post is about the diagnosis.
>
> | Change | Why |
> |---|---|
> | To-do digest injected into turn state | The agent found the assembled view on call 12; now it arrives on turn 0 |
> | Read ceiling 40k → 120k (result clip 128k) | Covers every document actually read whole |
> | Truncation notice states bytes and percentage | 10%-visible and 99%-visible used to produce the identical sentence |
> | Test: documents meant to be read whole must fit | The alarm that was missing |

- Measured result on the same prompt: **8 iterations → 3, twelve calls → six, zero
  on the calendar, $0.28 → $0.10, force-closed → finished on its own.**
- And the freed turns went to the repos, where it noticed a two-week-overdue parent
  task had actually shipped — a contradiction between the calendar and git that the
  calendar alone can never surface.

## 10. The beat I'd keep even though it's unflattering

- Setting both ceilings to the same number broke the thing they exist for: a
  truncated read is the prefix **plus** the notice, so equal ceilings pushed the
  result over the universal clip, which cut the notice off and replaced it with a
  generic one.
- The informative message would have been destroyed in exactly the case it exists
  for. A test caught it within a minute of being written.
- Small, funny, and it teaches the real lesson twice: **the failure mode of a clip
  is always that it removes the evidence of itself.**

## 11. Close

- Options for the last note, pick in drafting:
  - The alarm now exists: when a document outgrows the ceiling, a test fails and
    names the file and the percentage the agents would silently be seeing.
  - Or the sharper one: nothing about this required an unusual setup. A read tool
    with a byte limit and a file that grows is the whole recipe, and the only thing
    that made it visible here was a decision log nobody had thought to query that
    way.

---

## Receipts to have open while drafting

- Trace of the 08-11 morning brief: 12 tool calls, iterations 8/8, $0.2798, 69.3s.
- Trace of the fixed run: 6 calls, iterations 3, $0.0999, finished on its own.
- `git log` of `ops/calendar.ics` sizes; first over 40,000 on 2026-08-03 (46,422).
- Per-run table across all 34 morning briefs (day, iterations, calls, calls on
  calendar, cost, capped).
- Path sweep: 200 distinct paths read by agents in 45 days; 10 at or over the
  ceiling; the four in Table B.
- Devlog entry `2026-08-11 — the quiet half of the grep-bomb guardrail` carries the
  narrative version and the links back to the 06-29 entry.
- Commits: `8040a8c` (digest injection), `744fdb1` (named caps), `6f5d0c3` (ceiling
  raise + notice + alarm).

## Notes for whoever drafts it

- **Show the numbers; don't summarize them.** This is an evidence post — the tables
  are the argument, not decoration.
- Resist making it a tooling post. The subject is silent degradation; the byte
  limits are the example that happened to be at hand.
- Do not name the capability URL or any token; the desk pages are private.
- Length instinct: the diagnosis deserves room, the fix does not.
