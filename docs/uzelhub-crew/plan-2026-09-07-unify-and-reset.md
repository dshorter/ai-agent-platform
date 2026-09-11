---
read: full
status: COMPLETED HISTORICAL RUNBOOK — superseded for future construction by NEWSROOM-WORKPLAN.md, marked 2026-09-10. Written 2026-09-06; the September 7 window-3 handoff records the closed leg and the still-unapplied 006 cutover. Retain these steps as history, not next-session instructions.
---

# Plan — unify the specs, rename, reset the cycle, run it end to end

> **Completed leg; superseded for new work — 2026-09-10.** This was the
> next-session runbook prepared September 6. The
> [window 3 handoff](handoff-2026-09-07-window-3.md) records its outcome and
> the remaining live cutover work. Use [NEWSROOM-WORKPLAN.md](NEWSROOM-WORKPLAN.md)
> for the next leg. The reset and run commands below record past work; they
> are not instructions to reset today's state or resume prospecting.

<!-- MAP:START -->
- [How to run this session](#how-to-run-this-session)
- [Step 1 — rename the lead field register → type](#step-1--rename-the-lead-field-register--type)
- [Step 2 — thin the prompts to what the model needs; the spec holds the rule](#step-2--thin-the-prompts-to-what-the-model-needs-the-spec-holds-the-rule)
- [Step 3 — NEWSROOM becomes the map; AGENTS.md routes to the specs](#step-3--newsroom-becomes-the-map-agentsmd-routes-to-the-specs)
- [Step 4 — reset the cycle data (archive, never truncate)](#step-4--reset-the-cycle-data-archive-never-truncate)
- [Step 5 — a map of the box for the roam (small build)](#step-5--a-map-of-the-box-for-the-roam-small-build)
- [Step 6 — the end-to-end run, from the cursor](#step-6--the-end-to-end-run-from-the-cursor)
- [Step 7 — read-through of the 48-hour churn](#step-7--read-through-of-the-48-hour-churn)
- [Step 8 — after 5 and 6: one file reader, then the ledger in Postgres](#step-8--after-5-and-6-one-file-reader-then-the-ledger-in-postgres)
- [Not in this plan](#not-in-this-plan)
- [Checklist](#checklist)
<!-- MAP:END -->

## How to run this session

- **Read only these first:** AGENTS.md, docs/uzelhub-crew/GLOSSARY.md, the
  four spec-*.md files, and this plan. Do not open NEWSROOM.md, the ADRs or
  the dated findings unless a step points at a section. They are history,
  and they disagree with each other by design.
- **One job per window.** This plan is three windows: steps 1 to 3 (text),
  steps 4 to 6 (reset and run), steps 7 and 8 (read-through and build).
  Hand off between them with a short handoff doc: facts only, no theories.
- **Hand off at the second retraction.** If you have said "I was wrong"
  twice about the same thing, write the handoff and stop. The next window
  starts from the facts on disk.
- **A musing is not an order.** "Feels like we should" opens a discussion.
  Archive freely; delete, truncate or push only on an imperative.
- **Commit after every step, do not push.** The repo is public; a push is a
  publish and is the operator's call.
- **Spec beats code beats prose.** When a spec and the code disagree, fix one
  the same day and say which in the commit. Never add a dated correction to
  a spec; edit it.

## Step 1 — rename the lead field register → type

The word register is reserved for the tonal band (GLOSSARY). The content
type is type.

Sites. tests/test_register_vocabulary.py already enumerates them; it becomes
tests/test_type_vocabulary.py and asserts the five words at every site.
- agents/scout_agent.py: the synthesis prompt's "Registers:" line and the
  JSON schema key.
- agents/wire_editor_agent.py: both prompts and both schemas.
- pipelines/wire_editor/run.py: REGISTERS becomes TYPES; the coercion
  warning text.
- pipelines/writer/config.py: REGISTER_PROFILES becomes TYPE_PROFILES;
  pipelines/writer/run.py and agents/writer_agent.py (the assignment text,
  the summary keys, the "REGISTER: field note" prompt line becomes "TYPE:
  note").
- pipelines/scout/leads.py: format_lead writes `type:`; the header comment;
  any reader of `register`.
- pipelines/scout/lead_mark.py if it names the field; tools/leads_assay.py,
  tools/draft_review.py, tools/promote_draft.py.
- The git triage prompt's sentence "a different REGISTER" is rewritten to
  say stance.

Do not rename: voice/README.md's register entry; ADR text; dated findings.

The ledger: step 4 archives leads.yaml and starts a fresh one, so the 526
old entries are not migrated. If the operator wants them kept live instead,
one sed on the archived copy re-keys `register:` to `type:`.

Acceptance: the vocabulary test passes with five words at every site;
`grep -rn register agents/ pipelines/ tools/ tests/` returns only the voice
sense.

## Step 2 — thin the prompts to what the model needs; the spec holds the rule

For each prompt, keep the operative instructions and cut doctrine and
history. Where a rule lives in a spec, the prompt's line matches it or
cites it.
- **Wire Editor triage prompt:** replace "cluster… claim the strongest
  telling and spike the rest" with the arc/angles table from
  spec-wire-editor.md, including the "hold, folded into <id>" form. This is
  the one operator-rejected rule still live in a prompt: there since
  07-19, rejected 09-05, calendar item due 09-18.
- **Scout synthesis prompt:** keep the aperture, dedup, redaction and "types
  name what a lead is" lines; replace the register sentence about git jewels
  with the stance wording; name the registered roots (step 5 adds the
  index).
- **Writer note prompt:** the SHAPE block must equal spec-content-types
  §note; remove any "deepDive mandatory" wording; name the roots; leave the
  rest.
- **Scout triage prompts:** unchanged. The jewels were mined under them, and
  changing them is the one thing that would justify a re-walk.

Acceptance: a diff of each prompt against its spec section shows no
contradiction; the test suite passes (288 before this plan).

## Step 3 — NEWSROOM becomes the map; AGENTS.md routes to the specs

- NEWSROOM.md keeps the thesis, the three altitudes, the org chart, the
  pineapple essay, reuse-versus-fork, the one real fork, and open choices.
  Each section that now has a spec (Scout in detail, The Scout's sources,
  Model tiers, Writer in detail, Marketer & Editor, Content types, Editorial
  rules) is cut to a three-line pointer at the spec. The old text stays in
  git history, not in the file. Add one block at the top: "Current rules
  live in spec-*.md; this document is the design's reasoning and its
  history."
- AGENTS.md: the rows for GLOSSARY.md, the four specs and this plan, and
  the rewritable-spec convention, were added 2026-09-06. Verify they still
  match the files after the NEWSROOM cut. CLAUDE.md is a symlink to
  AGENTS.md; edit AGENTS.md only.
- Regenerate section maps with `python3 /opt/_host/scripts/doc-map.py
  <file> --write` on every read: full doc touched.
- Close the design review's critique 5 by pointing at the specs, instead of
  adding the corrections block it asked for.

## Step 4 — reset the cycle data (archive, never truncate)

Do not touch scout_jewel: 2,630 rows, all mined under the current triage
prompts, already archived at
pipelines/scout/state/archive/scout_jewel-20260906-204128.csv. Do not
re-walk. Do not move cursor.json (forward 418876).

```
cd /opt/ai-agent-platform
STAMP=$(date +%Y%m%d-%H%M%S)
cp pipelines/scout/state/leads.yaml   pipelines/scout/state/archive/leads-$STAMP.yaml
cp pipelines/scout/state/pitched.yaml pipelines/scout/state/archive/pitched-$STAMP.yaml
cp pipelines/scout/state/map.md       pipelines/scout/state/archive/map-$STAMP.md 2>/dev/null || true
.venv/bin/python - <<'PY'
from pathlib import Path
from pipelines.scout import leads
Path("pipelines/scout/state/leads.yaml").write_text(leads.HEADER)
PY
.venv/bin/python -m pipelines.scout.leads --rebuild-index
: > pipelines/scout/state/map.md
```
leads.HEADER is the ledger's contract header, which step 1 has already
changed to say type.

Acceptance: leads.yaml is the header only; pitched.yaml holds no ids;
archive/ has the three stamped copies; the scout_jewel count is unchanged.

## Step 5 — a map of the box for the roam (small build)

The roam only reaches where jewels point (96 of 104 calls on 09-06), and
exploratory reads failed 8 of 8 because the model guessed paths. Give it
coordinates:
- a generated index of readable text files under the registered roots
  (path, first heading, size, mtime), built at the start of each synthesis,
  capped at about 300 lines, excluding state directories, node_modules,
  .venv and anything the redaction gate would flag;
- injected into the synthesis context beside the map tail;
- measured before and after on one `--synthesize --dry-run --limit 250`
  (about $0.25): exploratory read_file and grep success rate, and how many
  leads cite a file.

Not in scope: registering _host or server-maintenance as roam roots. The
employer vocabulary lives in _host.

## Step 6 — the end-to-end run, from the cursor

1,066 un-walked rows sit past the forward cursor, about seven Haiku pages.
Run the daily verb once by hand. `--pass` idles when `SCOUT_PAUSED` is
set (pipelines/scout/__main__.py); an empty value reads as not paused, so
override it for this one shell rather than editing .env.

```
cd /opt/ai-agent-platform && set -a && . ./.env && set +a
SCOUT_PAUSED= .venv/bin/python -m pipelines.scout --pass 2>&1 | tee pipelines/scout/state/archive/pass-$(date +%Y%m%d-%H%M).out
```

Record, in ADR-002's run-record shape: rows walked, jewels found and
persisted, dropped anchors, map notes written, leads filed, cost, wall time,
how it terminated.

Then the downstream half, which has not run since early August:

```
.venv/bin/python -m pipelines.wire_editor --pass --dry-run      # read the shortlist first
.venv/bin/python -m pipelines.wire_editor --pass                # proposals artifact in state/
# read the artifact; apply one or two claims by hand:
.venv/bin/python -m pipelines.scout.lead_mark <id> --to claimed --by editor
.venv/bin/python -m pipelines.writer --list                     # what the note desk can draft
.venv/bin/python -m pipelines.writer --lead <id> --dry-run      # rehearse
.venv/bin/python -m pipelines.writer --lead <id>                # bank the draft
```

Acceptance: jewels persisted equals found minus dropped; map.md is
non-empty; every lead carries one of the five types; the wire artifact has
one proposal per new lead and uses the arc/angles form; the Writer banks a
draft and the lead reads drafted; the whole cycle costs under $1.

If synthesis returns zero leads, do not theorize. Read state/empty-calls,
record it, run the identical command once more (the empty forced pitch is
intermittent), and file both results.

## Step 7 — read-through of the 48-hour churn

pipelines/scout/run.py grew 469 lines between 09-05 and 09-06 under
diagnosis pressure, with one rule reverted and restored (A6). Read run.py,
jewels.py, walk.py and agents/scout_agent.py against spec-scout.md, in one
sitting. Fix drift where the code and the spec disagree; delete dead
branches; do not restructure. Report what changed and what was left.

## Step 8 — after 5 and 6: one file reader, then the ledger in Postgres

- One generic file reader with pluggable unit splitters (H2 section, dated
  ledger entry, YAML node, VTODO), anchored `path#anchor`, validated against
  the candidate set shown to the walker, with a one-paragraph stance
  description per splitter. Doc and ledger first. Not four bespoke readers.
- ADR-003's migration, with the columns named type and citations, and the
  pineapple rule as a grant.

## Not in this plan

A re-walk (only if a triage prompt or the kind vocabulary changes). The
Fable arm. An agent_decisions reader (blocked on the unit). Resuming the
timer (the operator's call after step 6 succeeds: delete SCOUT_PAUSED). Any
push.

## Checklist

- [x] type replaces register in code, tests and prompts; the vocabulary test is green
- [x] prompts match their specs; the arc/angles rule is live in the Wire Editor
- [x] NEWSROOM shrunk to reasoning and pointers; AGENTS.md routes to the specs; maps regenerated
- [x] leads, pitched and map archived and reset; jewels and cursor untouched
- [x] map of the box injected; exploration measured before and after
- [x] one pass, one Wire Editor pass, one Writer draft, all recorded
- [x] read-through done, drift fixed, nothing rewritten
- [x] a handoff written between windows
