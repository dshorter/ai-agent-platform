---
read: full
status: window handoff, written 2026-09-06 at the end of window 1 of plan-2026-09-07-unify-and-reset. Steps 1, 2 and 3 are done and committed. Facts only. Window 2 is steps 4 to 6 and starts from a fresh session.
---

# Handoff — window 1 (the text half) is done

Everything below is committed and unpushed. Nothing here is the authority on
anything; it is a map to the documents that are.

<!-- MAP:START -->
- [What the three commits did](#what-the-three-commits-did)
- [Facts window 2 needs](#facts-window-2-needs)
- [Two things found, neither fixed, both the operator's call](#two-things-found-neither-fixed-both-the-operators-call)
- [Two corrections to the plan itself](#two-corrections-to-the-plan-itself)
- [What window 2 does](#what-window-2-does)
<!-- MAP:END -->

## What the three commits did

| commit | step | what |
|---|---|---|
| `51ad9cd` | 1 | the lead's content type is `type`, not `register`, at every site |
| `4474daf` | 2 | each prompt matches its spec; the operator-rejected clustering rule is gone |
| `7981055` | 3 | NEWSROOM cut 762 → 455 lines; AGENTS.md routes to the specs |

Tests: **289 pass**, up one from 288. The added test is
`tests/test_type_vocabulary.py::test_the_word_register_is_not_the_content_type_anywhere`.

## Facts window 2 needs

- **`leads.yaml` is untouched and stale.** All 526 entries still carry
  `register:`; the code now reads `type:`. Step 4 archives and resets the
  ledger, so they are not migrated. Nothing runs unattended in the meantime —
  `SCOUT_PAUSED=1` is live at `.env` line 31.
- **Nothing else was touched.** `scout_jewel` is 2,630 rows (verified by query,
  not by inference). `cursor.json` is `{"seq": 418876}`. `pitched.yaml` is 66
  lines. `map.md` is empty. `archive/` holds only the 2026-09-06 20:41 copies
  from the previous session.
- **`leads.HEADER` now states the contract step 4 will write**: every lead
  carries `type:`, one of the five words, citing spec-content-types.md.
- **The wire artifact's shape changed.** It writes `type:` where it wrote
  `register:`, and `_queue_text` now includes each lead's `sources` line. No
  stored artifact depends on the old shape.
- **`docs/uzelhub-crew/sysadmin-ledger.md` was already modified when window 1
  opened and was left alone.** It carries an unresolved redaction finding
  at its line 46 — a home path, of the kind the gate refuses — which blocks
  any commit that includes the file. (Naming the string here would only move
  the leak into a second tracked file; the gate names it.) It is not this
  window's file; a dismissal is the operator's call.

## Two things found, neither fixed, both the operator's call

**1. The ore list and the roam list disagree.** `SCOUT_GIT_REPOS` mines five
repos; the roam's registered roots are three. `_host` and `server-maintenance`
are excluded from the roam on purpose — the employer vocabulary lives in
`_host`. Measured: **35 of the 2,630 jewels are anchored to repos `run_git`
refuses to open** — 21 `server-maintenance`, 14 `_host`. Two consequences, and
the second is the one that matters: the anchor is a dead end, and `source_ref`
is publishable text that travels to a lead's `sources` field, so `_host@<sha>`
would name a gated repo in publishable output. Filed as an open question in
AGENTS.md. **Settle which list moves before the next walk.** The synthesis
prompt now tells the model such a ref cannot be opened, which stops the dead-end
retry but does nothing about the leak.

**2. `stance` is overloaded again, one day after the glossary fixed it.**
GLOSSARY.md defines **stance** as what a source records relative to the event
(a transcript fights a problem; a commit records the decision afterwards). The
chief shadow's output schema in `agents/wire_editor_agent.py` also uses
`"stance"`, for `agree|differ`. Both are live. This was not renamed — the
glossary is the operator's, and picking the replacement word is a decision, not
a detail.

## Two corrections to the plan itself

- **Step 1's acceptance grep cannot hold as written.** It says
  `grep -rn register agents/ pipelines/ tools/ tests/` should return only the
  voice sense. The Director and the sysadmin use `register` as an ordinary verb
  at 16 sites (registered project roots, register the bot menu) and are right
  to. The new guard test scopes itself to the desks that carry a content type
  instead, and says why in its docstring.
- **`type` collides with the JSON-schema keyword.** `"type": "object"` and
  `"type": "ephemeral"` sit in the same files as the routing enums, so the
  vocabulary test's matcher now requires the pipe alternation. This is the one
  real cost of the rename and it is paid.

## What window 2 does

Steps 4, 5 and 6 of the plan, in order: archive and reset leads/pitched/map
(never truncate, never touch `scout_jewel` or the cursor); build the map of the
box for the roam and measure exploration before and after; then the end-to-end
run from the cursor — one Scout pass, one Wire Editor pass, one Writer draft,
recorded in ADR-002's run-record shape.

Read first: AGENTS.md, GLOSSARY.md, the four `spec-*.md`, the plan, and this
file. Not NEWSROOM, not the ADRs, not the dated findings unless a step points at
a section.
