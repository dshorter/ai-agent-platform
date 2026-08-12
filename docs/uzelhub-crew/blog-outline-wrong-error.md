# Blog outline — "It said budget. It meant steps."

> **Status:** detailed outline, 2026-08-12. Post 1 of three. Same conditions as
> the sibling outline (`blog-outline-silent-clip.md`): outside the newsroom while
> the importance features are mid-tweak, bullet-oriented capture rather than
> voiced, prose only where the phrasing is load-bearing.
>
> **Series spine** (stated once, in whichever post ships first — currently carried
> by post 2): the agent couldn't say why it stopped; the system couldn't say it had
> degraded; the agent couldn't keep what it learned. Three failures of a system's
> ability to know things about itself.
>
> - **Post 1 — this one** (self-report vs telemetry)
> - Post 2 — the clip that told no one (silent capability loss)
> - Post 3 — we didn't need to build it (learned context)
>
> **Relationship to post 2:** this is the smaller, sharper piece and the one that
> can ship alone. It is *how* the post-2 failure was discovered, but its lesson is
> independent, so avoid making it a prologue. One cross-reference at the end is
> enough.

---

## Working titles

- **It said budget. It meant steps.** ← lead candidate
- The wrong error message
- Two percent of the way to the limit it named
- Testimony and telemetry

## The one-sentence thesis

An agent's account of *why* it stopped is testimony, not telemetry — and a
confidently wrong cause is worse than no cause, because it sends you to tune the
dial that wasn't the problem.

## Who it's for

Anyone whose agent reports on its own behavior — which is anyone whose agent
writes anything a human reads and acts on.

---

## 1. Cold open — the sentence, then the number

- The 07:00 brief landed on the phone opening with:

  > *"Budget's out mid-read — but I've got the live todo desk plus fresh commits,
  > and that's enough to call it."*

- Perfectly reasonable. Reads like a system being honest about a constraint.
- **It had spent $0.28 of a $15 cap.** One point nine percent.
- Beat. Then: nothing in that sentence was true except the feeling behind it.

## 2. What it actually hit

- The loop has a step cap: eight tool round-trips before it is forced to close.
  The trace records `iterations: 8`.
- It ran out of *turns*, not money.
- The distinction sounds pedantic and is not: the two point at opposite fixes.
  Acting on the sentence as written means raising the cost cap, which would have
  changed nothing whatsoever.

## 3. The one-line cause

- When the loop breaks, it hands the model a closing instruction. That instruction
  read:

  > *"Budget **or** step limit reached. Stop reading now and give Dan your best
  > answer with what you have — name any gap you couldn't close."*

- A disjunction, with no indication which half fired. The model resolved it by
  guessing, and guessed wrong.
- **The failure is one token wide.** No logic error, no bad data — a prompt that
  asked a question it already knew the answer to.

## 4. The nuance — most of that sentence was working correctly

- This is the section that keeps the post honest, and it came from the operator's
  own reaction: *the wrong error is bad; the graceful degradation is not — don't
  touch that.*
- What worked: the loop noticed it was cut off, stopped cleanly, gave a usable
  answer from partial information, and **named the gaps it couldn't close** — the
  uncommitted diff it hadn't re-checked, the backlog cross-check it never ran.
- That is exactly what you want from a bounded agent. It was preserved verbatim,
  and there are now tests asserting it stays preserved.
- **The defect was the label, not the behavior.** Worth being precise about,
  because the instinct on reading a wrong error message is to distrust the whole
  apparatus, and the apparatus was mostly right.

## 5. Three limits, not two

- The loop can break for three reasons, and they mean completely different things.

> **Table A — the three caps.** This is the post's core reference.
>
> | Fires when | What it means | What you'd do |
> |---|---|---|
> | step cap | 8 tool round-trips used | give it more turns, or cheaper reads |
> | cost cap | $15 spent | genuinely expensive — investigate |
> | output cap | 200k chars of tool output | it's reading huge files — fix the sources |

- One prompt covered all three. Whichever fired, the model was told the same
  ambiguous thing.

## 6. The mismatch nobody had noticed

- Marginal cost of an iteration, measured from two runs the same day: **about
  $0.036.** ($0.28 at eight steps versus $0.10 at three.)
- The cost cap is $15. That's roughly **400 iterations of headroom.**
- **The step cap binds at about 2% of the cost cap.** The generous budget that was
  configured is unreachable; the loop always dies on steps first, at a fiftieth of
  the spend that was authorized.
- Which is why "budget's out" was wrong in a deeper sense than a mislabel: **that
  budget has never once been the thing that stopped it.**

> **Diagram 1 — the unreachable budget.** A single horizontal bar, 0 to ~400
> iterations, marked "cost cap" at the far right. A hard stop drawn at 8, near the
> left edge, labelled "step cap — where every run actually ends." The whole point
> is the empty space between them. Caption: *the limit it named had never once been
> reached.*

## 7. Where the 8 came from

- Worth checking rather than assuming, and git answers it: set on 2026-06-29, in
  the same commit that first built the agentic loop, and **never touched since.**
- That commit's own verification run used 3 iterations. So 8 was "roughly 2.5× what
  we just observed" — a sane opening guess, not a measured limit.
- The contrast that makes the point: its neighbour in the same file, the
  output-volume cap, carries a documented incident in its comment — a 3.77M-token
  prompt that 400'd. **The step cap has no story behind it.** One was set in
  response to a failure; the other was set because a number was needed.
- Six weeks later it was the binding constraint on the quality of a daily brief,
  and nobody had revisited it.

## 8. One constant, two callers, opposite needs

- The same number governed two paths with nothing in common:
  - the **listener** — a human waiting on Telegram; eight round-trips is already
    about 70 seconds, which is the edge of tolerable for a chat reply
  - the **tick** — unattended at 07:00, nobody waiting, running under a 600-second
    systemd allowance
- The unattended path was being sized by the chat path's constraint.
- What the cap actually bought on the tick wasn't protection from a bad outcome. It
  **converted one bad outcome into a different one**: instead of a slightly slower,
  slightly pricier brief, the result was a thin brief plus a false explanation — and
  nobody was waiting to benefit from the speed.

> **Diagram 2 — two lanes, one dial.** Two horizontal lanes sharing a single knob
> drawn between them. Top lane: a person with a phone, a 70-second clock, "8 is
> right here." Bottom lane: a timer icon, an empty chair, a 600-second allowance,
> "8 is arbitrary here." Simple, and it makes the fix self-evident.

## 9. What changed

> **Table B — the fix set.**
>
> | Change | Why |
> |---|---|
> | Close-out names the cap that fired and rules out the others | The model shouldn't have to guess what stopped it |
> | `limit_hit` recorded in the decision payload | A forced close becomes a queryable fact, not a claim in prose |
> | Step budget split: 8 for chat, 20 for unattended ticks | Two callers, two latency budgets |
> | The "name any gap you couldn't close" instruction, untouched | It worked; tests now pin it |

- Cheap to state, and worth stating: the tick's larger budget costs nothing on a
  normal day — the fixed run finished in 3 — and only pays out on days when
  something is wrong, which are the days the brief is worth most.

## 10. The principle — and the prompt fix that would have failed

- The tempting instinct is to ask the agent for more self-reporting: *tell me when
  you couldn't check everything.*
- **It already did.** The close-out asked it to name the gap, and it named the gap.
  What failed was attribution, not silence. **Adding more testimony to a system
  whose testimony was the broken part does not help.**
- The version that does work is narrower, and the distinction generalizes:
  - **Ask an agent to report what it was *told*, not what it must *infer*.**
  - It receives a truncation notice — that's knowledge. It does not receive a
    reason for the loop ending — that's an inference about its own machinery.
- And the durable answer isn't a prompt at all. Iteration counts, tool paths, and
  file sizes were sitting in the decision log the whole time. **A table can't
  confabulate.** The run that misreported itself could not have misreported those.

## 11. Close

- Candidate landing: the system was honest, cooperative, and wrong — and those are
  not in tension. It reported faithfully on the only thing it could see, which was
  that it had been stopped. What it couldn't see was which wall it hit, and nothing
  in its design had ever told it.
- Optional single line pointing at post 2: the same day's trace answered a second
  question nobody had asked — *why did it need eight steps in the first place?*

---

## Receipts to have open while drafting

- The 08-11 morning brief reply, verbatim opening sentence.
- Its trace: 12 tool calls, `iterations: 8`, $0.2798, 69.3s.
- The fixed run for the marginal-cost arithmetic: 3 iterations, $0.0999.
- `.env`: `PIPELINE_MAX_COST_USD=15`.
- `git log -S DIRECTOR_MAX_ITERATIONS` → the 2026-06-29 commit and its message
  (the verification run at 3 iterations is quoted in it).
- The neighbouring constant's comment, naming the 3.77M-token grep-bomb.
- `TimeoutStartSec=600` in the tick's systemd unit.
- Commit `744fdb1` (named caps, `limit_hit`, split budget).

## Notes for whoever drafts it

- Keep it short. This is the tight one — the whole argument fits in the cold open
  plus sections 5, 6, and 10.
- Do not let it become an attack on the agent. The operator's reaction is the right
  register: *the misattribution is a bug; the graceful close is a feature, and I
  don't want it touched.* That balance is the piece's credibility.
- Resist the "AI hallucinated" framing. It didn't invent anything — it was handed a
  disjunction and asked to report a cause. Given that prompt, a wrong answer half
  the time is the expected outcome, not a model failure.
- Do not name the capability URL or any token.
