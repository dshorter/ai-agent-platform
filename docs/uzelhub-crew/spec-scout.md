---
read: full
status: CURRENT SPEC, rewritable — what the Scout is and does as of 2026-09-06. For day-to-day reading it supersedes the Scout sections of NEWSROOM.md, scout-retool.md §§1-4 and the operative parts of ADR-002; those stay as history and reasoning. Where this and the code disagree, fix one the same day and say which in the commit.
---

# The Scout — current spec

<!-- MAP:START -->
- [Seats and budgets](#seats-and-budgets)
- [Sources and readers](#sources-and-readers)
- [The walk](#the-walk)
- [Synthesis](#synthesis)
- [Filing](#filing)
- [Redaction, absolute](#redaction-absolute)
- [Verbs and schedule](#verbs-and-schedule)
- [Invariants](#invariants)
- [Open](#open)
<!-- MAP:END -->

**Job.** Mine jewels from the box's ore, surface leads for the Editor, keep
no taste. Two stages with opposite needs, on two seats.

## Seats and budgets

| | walk (triage) | synthesis (the leap) |
|---|---|---|
| model | Haiku 4.5 (`SCOUT_WALK_MODEL`) | Sonnet 5 (`SCOUT_SYNTHESIS_MODEL`); Opus 5 on refusal (`SCOUT_SYNTHESIS_FALLBACK`) |
| depth | none | `SCOUT_SYNTHESIS_EFFORT`, default high; the only depth control on this seat |
| output | 4,096, a sanity ceiling | streamed; ceiling `SCOUT_SYNTHESIS_MAX_TOKENS` (64,000) |
| cost | about $0.037 per 150-row page | about $0.25 per run since 09-06 (was $1.50 before streaming and the digest) |
| ceiling | `SCOUT_MAX_COST_USD`, default $2, on every walking leg — `--walk`, `--walk --source git`, and both of a pass's legs; checked between pages, so a fuse rather than a brake | none. A synthesis is one call and there is no between-pages to check at; what bounds it is `SCOUT_SYNTHESIS_MAX_TOKENS` on the way out and the digested dedup memory on the way in |

Fable 5 on synthesis is one env var away. Whether it is worth five times
Sonnet has never been measured; that arm is still owed.

## Sources and readers

Seven source types: transcript, git, doc, ledger, calendar, survey,
agent_decisions. A reader gives a source retention (jewels); the roam gives
every source access.

| source | reader | anchor | how it is walked |
|---|---|---|---|
| transcript | ingest into scout_session_log, then the walk | `seq` | by cursor, pages of 150 rows |
| git | git_ore.py over `SCOUT_GIT_REPOS` (five repos) | `repo@sha` | `--walk --source git` over an explicit range; use `--since 2026-01-21` to match the transcript era |
| doc, ledger | `file_ore.py` — ONE reader, a splitter per kind: an H2 section for a doc, a dated `## 2026-09-02 — …` entry for a ledger | `repo/path#anchor`, the same slug the doc's own MAP block uses | `--walk --source doc\|ledger --path <file or dir>`; refuses a path outside the three roam roots, because a `source_ref` is publishable text |
| calendar, survey | none; roam only | `path#anchor` (planned) | not walked. Their splitters — a VTODO, a YAML node — are one row in `file_ore.SPLITTERS` and one stance paragraph each, added when something calls them and not before |
| agent_decisions | none, blocked | sequence id | the mineable unit is unsettled (step_number is 1 on every row; names are dotted); settle it before any reader |

The roam reaches only the registered roots: ai-agent-platform, uzelhub-web,
predictor_ingest. It cannot read _host or server-maintenance. Since
2026-09-06 an index of what exists under those roots rides in the synthesis
context (`box_index.py`): path, size, mtime and first heading for up to 300
readable text files, excluding generated trees, credential-shaped names, and
any line the redaction gate would flag. Before it, exploratory reads outside
jewel coordinates failed 8 of 8; the roam had no way to tell a refusal from
an absent file. Gated
day-job material gets an opaque `source_ref` resolved through a mapping that
never leaves the box; its home is _host and it is not built.

## The walk

- Pages of 150 rows (`SCOUT_PAGE_ROWS`), each row clipped to 1,200
  characters; the full text stays in the database.
- A pass walks at most the plate (`SCOUT_PASS_ROW_BUDGET`, 150 rows): fresh
  ore from the forward cursor first, then backfill with whatever is left,
  stopping where forward stood. Bigger plates mine thinner, because output
  is homeostatic.
- The forward cursor never retreats and advances only after the page's
  jewels are persisted. `--walk` moves no cursor.
- Per page the walker returns jewels (kind, note, anchor), scratchpad
  breadcrumbs (transcripts only) and map notes. Anchors must come from the
  page it was shown; persist() drops the rest and counts them (0.8 percent
  on transcripts, none on git).
- Kinds: principle, correction, reframe, decision, aha. The walker has
  emitted four more (observation, finding, note, verification; 11 rows).
  Whether the set is closed is a decision owed.
- Jewels accumulate: a re-walk is a new run, never a correction. Exact
  re-findings are idempotent.
- Aperture, absolute: when unsure, include; no taste; never judge what
  deserves publishing.

## Synthesis

- Selection: jewels by `--since`, `--until`, `--kind`, `--source-type`,
  `--of-run`, `--limit`, in source-date order across all sources. A pass
  selects its own walk's jewels; both paths hand synthesis the same shape.
- Context: the selected jewels, the cross-agent decision sequences, the tail
  of the map (4,000 characters), the box index (what files exist under the
  roots; navigation, never taste), and the dedup memory as digests (id plus
  first sentence, at most 240 characters; status-blind).
- Roam: up to `SCOUT_ROAM_ITERATIONS` (6) rounds of read_transcript,
  read_file, grep, run_git, with tool output capped; then the pitch is forced
  with tools disabled. On refusal, one tool-less retry on the fallback. A
  truncated answer raises. An empty answer is captured to state/empty-calls
  before anything else happens.
- Output, strict JSON: leads with slug, pitch (two to four sentences),
  why_now, citations, type, agent_span.
- **Policy settled 2026-09-09, wiring pending NR-09:** retain the Scout's
  recommendations with human override. Recommend type and destinations
  independently, as specified in spec-content-types.md §Content type and
  destination. The current JSON/store path above has no separate destination
  field; do not describe it as implemented. Recommendations remain advisory;
  operator choices and verdicts do not feed back into the Scout.
- Aperture: generate wide, err reckless; false positives are cheap, missed
  leads are invisible. Span adds weight, never filters. Dedup skips only an
  essentially identical pitch. Types name what a lead is, never what to look
  for. No Editor verdict ever reaches this stage.
- Known behaviour: about 10 to 13 leads per run regardless of input. The
  forced pitch intermittently returns nothing (once in six runs on 09-06;
  the capture is now in place). The source mix changes what leads anchor to
  and which type they land in, not how many.

## Filing

Leads append to the ledger with status new, the model, the filed date and
`redaction: required`. The Scout never edits or removes a lead. The dedup
memory is rebuilt from the ledger. Slugs are never renamed. The ledger is a
gitignored file today and moves to Postgres under ADR-003, where the
pineapple rule becomes a grant.

## Redaction, absolute

The ore contains credentials, keys, paths and personal data. A pitch
paraphrases and points; it never reproduces secret material. Citations are
publishable text, so a gated source needs an opaque anchor before it is ever
mined.

## Verbs and schedule

| verb | does | moves a cursor | cost |
|---|---|---|---|
| `--ingest` | session logs into scout_session_log | no | trivial |
| `--walk` (`--source transcript\|git\|doc\|ledger`; `--from-seq`, `--pages`, `--since`, `--until`, `--path`) | mine and persist jewels | no | Haiku pages |
| `--synthesize` (selection flags, `--dry-run`) | leads from stored jewels | no | one synthesis |
| `--pass` | walk within the plate, backfill the remainder, synthesize over that walk, file | forward and backfill | both |

The daily timer runs `--pass` at 05:45 and is gated by `SCOUT_PAUSED`, set
since 2026-08-19. Controlled comparisons run `--synthesize --dry-run` on both
arms so the first arm's leads never enter the second arm's dedup memory.

## Invariants

The pineapple rule: no disposition on jewels, no status in the dedup memory,
no verdict in any prompt. The aperture rules in both triage prompts. The
forward cursor never moves backward. Raw transcript text is never
overwritten. Lead slugs are never renamed. A cost ceiling on every walking leg.

## Open

The remaining two splitters (a calendar VTODO, a survey YAML node), which have
no caller yet. The file page size: 30 units is an estimate with headroom, not
the measurement `git_ore.DEFAULT_PAGE` carries — the first live doc walk is what
settles it. The kind
vocabulary. Multi-run selections over the same ore (near-duplicate jewels).
The agent_decisions unit. ADR-002's coverage ledger (not built; the two
cursors do its job for transcripts). The cause of the empty forced pitch.
The Fable-versus-Sonnet arm.
