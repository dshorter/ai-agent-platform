---
read: reference
status: house vocabulary, opened 2026-09-06 — one word per concept; retired synonyms listed so older docs stay readable. Voice-bottle terms stay in voice/README.md. Where a code identifier still uses a retired word, plan-2026-09-07-unify-and-reset.md names the rename.
---

# Glossary — the newsroom's words

Look terms up; nobody reads this front to back.

**The one rule.** Every concept gets one word. A doc, a prompt or a code
comment that needs the concept uses that word. When a word here disagrees
with NEWSROOM.md, an ADR or a dated finding, this file is current and the
other is history.

---

## The content axis

**type** — what a piece IS: ticker, newsletter, note, blog, paper. The
Editor's routing dimension; the rows of spec-content-types.md. The Scout
labels a lead with the type it would become; it never goes looking for one.
*Code today: the lead field `register` and the `REGISTERS` sets — renamed to
`type` by the plan.* Retired synonyms: register (in this sense), product,
surface, sink profile, leg, "the three registers".

**register** — the tonal band a surface writes in, fixed per type
(voice/README.md): ticker terse verb crawl, newsletter newspaper broadsheet,
note man-page dry, blog narrative, paper formal. A property OF a type, never
the type itself.

**profile** — one named voice, one directory: voice/<profile>/samples plus
moves.md. A type selects a profile (note → man-page-dry). Bottle, sample,
exemplar, move, harvested, seeded and SHAPE are defined in voice/README.md.

**sink** — where a type's published copy lives and which copy is canonical:
apex /notes/, apex /newsletter/, the masthead text pack, Ghost, or unplaced
(paper). A destination, never a name for the type.

**deep dive / retelling** — the two kinds of blog piece a note can link to.
A deep dive has distinct intent, is self-canonical and indexed (the normal
case). A retelling is the same story on a second surface, canonical back to
the note, and rare. Policy in SEO.md §Indexing policy.

## The ore and what is mined from it

**the box** — this server and its repos: the thing that narrates its own
building, and so both the subject and the source of every story.

**source** — a kind of ore the Scout can mine and retain: transcript, git,
doc, ledger, calendar, survey, agent_decisions. The jewel column is
`source_type`. Not the same thing as a lead's citations.

**stance** — what a source records relative to the event. A transcript
records a problem while it is being fought (present tense, unresolved). A
commit records what was decided and why, afterwards. A ledger entry records
what the machine did unattended. A doc records doctrine or a derived account.
The seam between two stances on one event is the richest material. *The one
new word in this file; it replaces "register" in the sense ADR-002 and the
git triage prompt used.*

**ore** — raw material before mining: transcript rows in scout_session_log,
commits, files.

**reader** — the module that turns one source into pages the walker can
triage and into anchors persist() can validate. Today: transcripts (ingest
plus the walk), git (git_ore.py) and files (file_ore.py, doc and ledger).
Readers add retention, not access; the roam already reaches every source.

**splitter** — the rule that cuts one file into units a jewel can anchor to:
an H2 section for a doc, a dated `## 2026-09-02 — …` entry for a ledger. It
owns the unit, its anchor and its date, and it carries the source's stance
paragraph — which is what makes the file sources one triage prompt instead of
one per kind. Two are built; a calendar VTODO and a survey YAML node are named
and not built.

**page** — the bounded chunk one triage call reads: 150 transcript rows,
each clipped to 1,200 characters; a git page is sized by yield (50 commits,
measured); a file page is 30 units, estimated and not yet measured.

**plate** — the total rows one daily pass may walk (`SCOUT_PASS_ROW_BUDGET`,
150). Bigger plates mine thinner.

**walk** — the cheap coverage pass over ore in cursor order; each page is one
**triage** call. Produces jewels, scratchpad notes and map notes. Never
synthesis.

**cursor** — a read position on the transcript log: `forward` (the coverage
high-water mark, never retreats) and `backfill` (a re-mine position). A
return address, not a leash: the roam may go anywhere and comes back to it.

**jewel** — one durable finding: a kind, a one-sentence note, an anchor, a
source_type, a source date. A row in scout_jewel. Carries no disposition,
ever.

**kind** — a jewel's kind: principle, correction, reframe, decision, aha.
(The walker has emitted four others; whether the set is closed is a decision
the plan lists.)

**anchor** — the jewel's pointer back to its ore: `seq` for a transcript row,
`source_ref` otherwise (`repo@sha` for git, `repo/path#anchor` for a doc or
ledger unit). Validated against the page the walker was shown; an anchor it
was not shown is dropped and counted.

**scratchpad** — free-text arc breadcrumbs the walker appends to transcript
rows. The Scout's own opaque space; nothing downstream parses it.

**map** — map.md: navigation notes (where rich material lives, which sources
run rich). Navigation, never taste. Its tail rides in the synthesis context.

## The leap and its product

**synthesis** (the leap) — the premium call over a selection of jewels plus
the cross-agent decision sequences, the map tail and the dedup memory. Roams,
then pitches. Its output is leads.

**selection** — the jewels handed to one synthesis, chosen by date window,
kind, source type, mining run or limit. A pass selects the jewels its own
walk found.

**roam** — bounded tool use over the box during synthesis or drafting:
read_transcript, read_file, grep, run_git, inside the registered roots.
Divergent for the Scout (anything might be a story), convergent for the
Writer (pull exactly the cited threads).

**lead** — the Scout's product and the Editor's queue item: an id (a slug,
never renamed), filed date, status, type, agent_span, pitch, why_now,
citations, the model that pitched it, and a redaction flag.

**pitch** — a lead's two-to-four-sentence abstract. **why_now** — one
sentence on timeliness or durability.

**citations** — a lead's pointers to its evidence: session and turns,
repo@sha, a file, a decision sequence. *Lead field today: `sources` — a second
rename, taken with the ADR-003 migration.* Publishable text, so gated
material needs an opaque form.

**agent_span** — how many distinct agent names the cited decision sequence
touches. A weight, never a filter. It counts strings, not agents, until the
unit is settled (agent-span-counts-strings-2026-09-06.md).

**dedup memory** — the id plus a **digest** (the first sentence, at most 240
characters) of every lead ever pitched, so the Scout never re-pitches the
identical story. Append-only, never pruned, status-blind by construction.

**status** — a lead's position: new → claimed → drafted → approved →
published; spiked from new or claimed; rejected from drafted. Forward-only,
one dated stamp per move, only through lead_mark.

## The desks

**Scout** mines and pitches. **Wire Editor** triages the new queue into
proposals. **Editor-in-chief** is the Director's editorial hat, shadowing the
Wire Editor. **Editor** is the operator, who disposes gate ① and owns gate ②
forever. **Writer** turns a claimed lead into a draft. **Marketer** holds the
Ghost blog's per-item text and packaging; it is not a newsroom desk.

**verdict** — a Wire Editor proposal on one new lead: claim (with the type
confirmed or corrected), spike, or hold. Proposals never touch the ledger.

**arc / angles** — an arc is one story developing over time (many source
dates). Angles are several leads on one discrete event (one source date).
Angles fold into the strongest telling; an arc is never folded. One date
across two stances is corroboration and is kept whole.

**gate ①** — routing: claim, spike, hold. The operator today; may migrate to
the Director on concordance. **gate ②** — scrub and approval to publish. The
operator, permanently.

**shadow** — the Editor-in-chief's agree or differ per proposal.
**concordance** — its agreement rate with the operator's actual verdicts,
scored on human marks only.

**employer gate** — day-job material publishes technique-forward and
application-anonymous. A flag applied at routing, never a spike reason.

**the pineapple rule** — the Scout learns navigation, never taste. No Editor
verdict reaches it, structurally: no disposition columns on jewels, no status
in the dedup memory, no verdict in any prompt.

**spine** — agent_decisions: one row per model invocation, with its cost.
The cost and decision trace for every desk.

**pass** — the daily timer verb: walk from the forward cursor within the
plate, top up from backfill, synthesize over that walk's jewels, file the
leads.

## Reading a lead out loud

A lead is ABOUT the box, so its content sounds like a status report on the
architecture. Say "the lead says" or "the lead's sequence spans four
agents". A four-agent lead is not four agents running; a webhook inside a
lead is subject matter, not a component. Three clarifications across two
sessions were this confusion and nothing else.

## Retired words

**product**, **surface**, **leg**, **sink profile** (say type). **register**
for a type or for a stance. "Jewels cite seqs" (they cite anchors).
"Primary ore" (say the transcript source; nothing is primary). "Mode 1 /
mode 2" for synthesis failures (say the ceiling failure and the empty
forced pitch).
