# Director — Engineering Ledger

> A human-curated log of hardening decisions and safeguards for the Director. **One entry = one
> decision worth not relearning** — the failure, the fix, and the reusable lesson.
>
> Distinct from the Director's *own* runtime ledger (the auto-written "building blocks" of rework
> slice 4): same spirit — keep the keepers — but this one is written by us, about the machinery.

---

## 2026-06-29 — Three-layer tool-output guardrail (the grep-bomb)

**Failure.** A live Telegram turn ("let's try another read test") gave the agentic loop a vague
instruction with no named document. Taking it literally, the loop ran `grep` across
`predictor_ingest/data/raw` — scraped HTML with **single lines up to 731,548 characters**. Two things
broke at once: `subprocess.run(capture_output=True)` buffered the *entire* multi-gigabyte match stream
into memory (an **OOM, exit 137**, when reproduced locally), and the matches that did come back produced
a **3.77M-token prompt → `400 invalid_request_error` ("prompt is too long")** on the next round-trip.
(The 400 was rejected at validation, so it was **not billed** — only the normal pre-bomb calls were.)

**Why one fix isn't enough.** A per-result character clip runs *after* the subprocess has already
buffered everything — too late for the OOM. A pipe-level read bound stops the OOM but one 40k result ×
many calls × many iterations can still creep toward the context limit. So: defense in depth.

**The three layers** (`pipelines/director/tools.py`, `agents/director_agent.py`):

1. **Bound at the pipe.** `_bounded_output()` reads a subprocess's stdout directly off the pipe — at
   most **600 KB within a 15 s wall-clock deadline**, then kills the child. Used by `grep` and
   `run_git`. This is the root fix: never let `capture_output=True` buffer an unbounded stream first.
2. **Per-result ceiling.** Every tool result is clipped in `dispatch()` to **`MAX_TOOL_RESULT_CHARS`
   (40 k)**, with a **300-char per-line clip** for minified/bundled/scraped lines. `read_file` reads a
   bounded prefix (not the whole file) with a NUL-byte binary check.
3. **Per-turn budget.** The loop sums tool output and stops at **`DIRECTOR_MAX_TOOL_CHARS` (200 k)**,
   so many individually-bounded results still can't accumulate past the context window.

The iteration cap (`DIRECTOR_MAX_ITERATIONS = 8`) and cost cap (`config.max_cost_usd`) are the other
two bounds on a run; these three layers are specifically about *output size*.

**Reusable lesson.** **Never `capture_output=True` on a tool that can touch large or untrusted data.**
Bound at the pipe for memory *and* with a wall-clock deadline for time; a clip applied after the call
returns protects neither. (Also: a vague instruction to an agent with read tools means "search
everything" — name the file, or rely on recent-history to carry the reference.)

**Refs.** commit `d4af2c3`; verified by direct toolbox probes (grep over predictor_ingest → 16 k chars
in 0.1 s; giant-HTML read + full `git log -p` both clip to 40 k) and a full `--selftest` loop.

---

## Open hardening items

- **No automated test suite yet.** `pyproject.toml` declares `pytest` but it isn't installed and there
  are zero test files. The toolbox guards (`_within_roots`, `_looks_secret`, `_GIT_READONLY`, the
  output bounds) are pure functions — prime fast unit-test candidates, and the grep-bomb is exactly the
  kind of regression they'd catch. Worth a hardening micro-slice: install pytest + `tests/test_director_tools.py`.
- **Listener is not a service.** Still a detached `nohup` process (logs → `director.listener.log`), not
  systemd — slice 6.
