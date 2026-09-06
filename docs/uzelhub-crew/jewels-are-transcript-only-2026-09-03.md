---
read: full
status: findings from 2026-09-03; schema fixed same day (1.4.0), the reader work is open
---

# The jewel layer could only hold one of six sources

A verification question with an obvious expected answer turned up a hard
constraint nobody had decided, one layer below where the design docs discuss it.

## How the question emerged

It was not a bug report. Twice in passing, while tracing the lead-to-Writer
handoff, I described session logs as the Scout's **primary ore** — accurate,
since `NEWSROOM.md` says exactly that and calls them "the richest by far."

The operator stopped on the word *primary*:

> "You mentioned in passing at least twice that the session logs are the primary
> source for the scout. If you are just measuring the results, that's fine. But
> in terms of execution, all the possible sources should have equal weight…
> I just wanted to be sure we weren't accidentally weighting the scout to favor
> session logs."

The distinction being drawn — **description versus execution** — is the whole
finding. "Session logs are richest" is an observation. If it had leaked into the
mechanism it would be a preference, and preferences narrow apertures, which is
the thing the pineapple rule exists to prevent one seat over.

The expected answer was "coincidental, you're fine."

## What the layers actually said

Checking the code rather than the doc produced three different answers at three
depths.

**Prompt level — no preference.** `scout_agent.py` describes the roam as "a
catalog of sources, no rotation, no quotas," and lists `read_transcript`,
`read_file` / `grep` and `run_git` flat, with no ranking. The only weighting
anywhere is `agent_span`, and it is guarded exactly as it should be: "span never
disqualifies a lone-actor story; keep surfacing those too," echoed in
`sources.py` — "Span is a WEIGHT handed to synthesis, never a filter."

**Coverage level — a deliberate, documented asymmetry.** Session logs have a
cursor and get linear guaranteed coverage; every other source is cursor-free and
temporally bidirectional. `NEWSROOM.md` defends this directly: *"Coverage is
linear (cursor); investigation is not (free roam)."* This is a difference in the
KIND of privilege, not a ranking — logs cannot be skipped, the others cannot be
exhausted. No problem here.

**Persistence level — a hard constraint nobody decided.** `004_scout_jewel.sql`:

```sql
seq BIGINT NOT NULL REFERENCES scout_session_log(seq),
```

Not a runtime check. A NOT NULL foreign key. **A jewel could not exist without
pointing at a transcript row.** Material mined from git history, the design
docs, the sysadmin ledger, the ops calendar, the marketing survey or
`agent_decisions` could inform a jewel's note, but could never *be* one — there
was no field in which to say where it came from.

## The cause behind the cause

The FK is an anti-hallucination control and it is correct. `persist()` builds a
seq allowlist from the page the walker was actually shown and drops anything
off-page, "so a hallucinated seq is dropped here." A fabricated citation cannot
land. Keep that.

The problem is its **side effect**: the schema's only provenance field was a
transcript position. So the control quietly answered a second question it was
never asked — *what may a jewel be about* — and answered it "transcripts only."

That is the shape `AGENTS.md` was written to catch: a locally-correct fix that
turns out to have decided an architectural boundary. The router's own founding
example is the same shape. Nobody was careless; the constraint simply had two
consequences and only one of them was in view.

**And the retool tightened it.** Before `004`, jewels lived in a local Python
list and died with the process — the preference was soft, at prompt level.
Persisting the jewel layer made it durable, and `--synthesize` now selects from
`scout_jewel`. So a soft preference became the substrate every future leap reads
from, as a side effect of a change made for cost reasons.

**The irony worth keeping.** `004`'s own header calls the table "a PUBLISHED
INTERFACE, not Scout-private scratch," and names its anticipated consumers:
*"a directed hunt on a named topic, a monthly arc digest."* A directed hunt is
precisely the commissioned-prospecting pathway. Against a transcript-only jewel
layer it would have been blind to five of six sources **while believing it had
searched the box** — the exact failure mode of a silent instrument.

## What was NOT lost

The natural next fear is a corpus of dropped jewels. Measured, it is much
better than that:

| | |
|---|---|
| Turns ingested (`scout_session_log`) | **14,852** (2026-01-21 → 2026-09-02) |
| Jewels persisted (`scout_jewel`) | **58**, from a single date (2026-07-12) |
| Walks that produced them | **2** |
| Ore those walks covered | **seq 3–144 — 142 turns** |
| Share of the corpus ever mined into the layer | **0.96%** |
| Distinct `source_type` values present | **1** |

**Read that ratio correctly — 58 against 14,852 is a coverage number, not a
yield number.** Only 142 turns have ever been mined into this layer, across two
walks: roughly one 150-row page. Against the measured historical rate (~1,645
jewels across 35 passes, ≈47 per pass) 58 jewels from about one page is normal,
if anything slightly rich. The layer is not sparse because jewels are rare; it
is sparse because **99% of the corpus has never been walked into it.** `004`
landed 2026-08-22 and `SCOUT_PAUSED=1` has been set since 2026-08-19, so the
full re-mine the retool made affordable (~95 pages, ~$1) has never been run.

> **SUPERSEDED 2026-09-05 — the table above is the state on 09-03 and is kept
> as the record of how thin the layer was.** Both gaps it describes are now
> closed. The git reader landed and mined 1,080 commits into 642 jewels
> ($0.53); the full transcript re-mine this section says had never been run ran
> the same day — 101 pages, 15,126 rows, 1,930 jewels persisted ($2.89). The
> layer now holds **2,630 jewels across two source types** spanning 2026-01-24
> to 2026-09-05, against 58 from a single date when this was written.
>
> The open empirical question this section poses — whether the other five
> sources are rich or barren — is answered for **one** of them. Git is rich:
> 642 jewels from 1,080 commits, weighted toward `decision` and `principle`,
> which is the resolved register the transcripts structurally lack. Four sources
> remain unmeasured.

**And the single `source_type` value proves nothing about the other five.** All
58 rows are transcript-anchored — necessarily, because until 1.4.0 the table
could not store anything else. The absence of git, doc, ledger, calendar,
survey and `agent_decisions` jewels is a **selection effect, not a measurement**:
an instrument that can only record one value tells you nothing when it records
that value. Whether those sources are rich or barren is still an open empirical
question, and it stays open until a reader exists to ask it.

**So this was caught in the cheap window.** There is almost nothing to migrate
and no legacy of transcript-only jewels to live with. Had the finding arrived
after the full mine, the corpus would have had to be re-mined against the new
schema. It arrived before. That is luck, not process, and worth saying so.

The loss to date is therefore mostly **jewels never formed** rather than jewels
formed and discarded — the walker was told "your jewels cite seqs," so it had no
way to express a git or ledger finding as a jewel and would rarely have tried.

## Fixed — schema 1.4.0, applied 2026-09-03

`005_jewel_source.sql`, applied to `ai_agent_platform` after a `pg_dump` of the
table (the cluster is `pg_dumpall`-only with no per-table restore point, so a
backup came first):

- `source_type VARCHAR(24) NOT NULL DEFAULT 'transcript'` — the DEFAULT labels
  the 58 existing rows correctly, so no backfill was needed
- `source_ref TEXT` — the pointer for non-transcript jewels
- `seq` keeps its FK but drops NOT NULL
- `CHECK jewel_anchor_matches_type` — exactly one anchor, matching the declared
  type, so the two provenance models cannot blur into "sometimes both"
- `UNIQUE (seq, kind, note)` replaced by a unique index on
  `(source_type, COALESCE(seq::text, source_ref), kind, note)`. **This one
  matters:** Postgres treats NULLs as distinct, so a nullable `seq` under the old
  constraint would have made every non-transcript jewel trivially unique and
  silently destroyed the idempotency `004` depends on, for five of six sources.

Verified in place: 58 rows preserved and labelled `transcript`; a `git`-anchored
jewel inserts; the CHECK rejects both mismatches (transcript with no seq, git
with a seq); a duplicate non-transcript insert is a no-op. Test rows removed.

**What the fix gives up, stated rather than discovered.** A git sha or a file
path has no table to reference, so non-transcript rows get no FK and the
DB-level anti-hallucination guarantee now covers transcript rows only.
`persist()` must supply the equivalent check — validating `source_ref` against
the candidate set actually shown to the walker, exactly as the seq allowlist
does. **Until that code exists the schema is ahead of the pipeline**, which is
recorded in the migration header too.

The pineapple ban is untouched. `source_type` and `source_ref` are provenance —
where a jewel came from — never disposition. Still no `lead_id`, no
`became_lead`, no status, no score.

## Open — the reader work

The schema now permits what the pipeline cannot yet produce. Opening the other
five sources means, per source: what counts as a mineable unit, what
`source_ref` addresses it, what date it carries, and how the walker is shown a
bounded candidate set it can be held to.

| Source | Candidate unit | `source_ref` | Date |
|---|---|---|---|
| git | a commit | sha | commit date |
| doc | a section or line range | `path#Lstart-Lend` | file mtime, or the doc's own dated status line |
| ledger | a dated entry | `path#anchor` | the entry's date |
| calendar | a VTODO/VEVENT | UID | DUE / DTSTART |
| survey | a node | node id | walk date |
| agent_decisions | a sequence | `workflow_sequence_id` | `MAX(decision_timestamp)` |

Three things to settle before building any of it:

1. **The bounded-page discipline has to survive.** The transcript walk works
   because the walker sees one bounded page and is held to its seqs. Each new
   reader needs the same shape — a candidate set, an allowlist, a budget — or
   the anti-hallucination property is lost along with the FK.
2. **Coverage stays linear only for the logs.** Adding readers must not add
   cursors. `NEWSROOM.md` is explicit that one cursor across all sources is
   "both clumsy and aperture-closing." Other sources stay free-roam.
3. **Mine once, afterwards.** The full corpus mine has not been run. It should
   happen *after* the readers land, not before, so the ~$1 pass fills the layer
   from everything rather than from transcripts alone and then needs redoing.

> **MEASURED 2026-09-05 — the ~$1 figure is wrong by about 4x, and it is
> repeated across three documents.** The first real full-corpus walk came in at
> **$0.037 per 150-row page**, so ~101 pages is **about $3.75**, not a dollar.
> The estimate was derived from `$0.0105` a page, which was measured on the
> *thin* August pages (a few dozen rows of fresh ore) and then applied to full
> 150-row pages. The right number was always going to be ~3.5x higher, because
> the page is ~3.5x the input.
>
> Nothing in the reasoning changes: $3.75 to fill the jewel layer once, against
> ~$200 welded, is still exactly the point the retool was making, and the 200x
> argument is untouched. What changes is that "about a dollar" must not be
> quoted as a budget — the same cheap-sample error also made the git mine's
> estimate 3x low, so it is a habit rather than a one-off.


## What generalises

- **A constraint can answer a question it was not asked.** The seq FK was
  designed to stop fabricated citations and ended up deciding what a jewel may
  be about. When a control is added, it is worth asking what *else* it now
  forbids.
- **Making something durable makes its assumptions durable too.** The transcript
  preference was survivable while jewels died with the process. Persisting them
  promoted a soft bias into the substrate — and the change was made for cost
  reasons, with nobody looking at aperture.
- **"Description versus execution" is a reusable audit question.** The operator's
  framing — is this just how we *talk* about it, or is it in the *mechanism* —
  found a real constraint that reading the docs would never have surfaced, since
  the docs correctly describe a preference the schema had silently hardened.
- **Check the layer below the one the docs discuss.** All three narrative layers
  here were honest. The constraint was in the DDL.

## Related

- `database/ai_agent_platform/004_scout_jewel.sql` — the original, including the
  "published interface" framing that makes the gap sharp
- `database/ai_agent_platform/005_jewel_source.sql` — the fix
- `docs/uzelhub-crew/scout-retool.md` §1 — why the jewel layer was persisted
- `docs/uzelhub-crew/scout-mining-economics.md` — the ~1,645 discarded jewels
  that motivated `004`
- `docs/uzelhub-crew/silent-instruments-2026-08-29.md` — the same family: an
  instrument that reports confidently while blind
- `docs/architecture/adr-001-manual-writer-assignments.md` §Prior art — the
  directed-hunt pathway this would otherwise have crippled
- `AGENTS.md` §Shared surfaces — the cluster's no-per-table-restore constraint
