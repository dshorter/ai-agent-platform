# ADR-001: Manual Writer Assignments Bypass the Leads Ledger

**Status:** Proposed
**Date:** 2026-09-03
**Deciders:** dshorter, Claude (Fable 5)
**Supersedes:** nothing. First ADR in this repo — see §Conventions at the foot.

## Context

### What is being asked for

The operator wants to run the newsroom's writing machinery on demand against a
subject **they have already chosen**: no prospecting, no discovery, no Scout.
The value being reached for is the Writer leg — the voice bottle, the roam, the
redaction scrub, the draft record — applied to a piece the operator decided to
write. In their words: *"The CLI is completely manual, where I've decided what
we're gonna do and I want to leverage the voice composition, etc., of the
pipeline to polish it."*

This is **not** the "pull as well as push" idea parked in NEWSROOM.md §Open
choices (commissioned prospecting — *"what do you have on X?"*). That one asks
the Scout to go looking on a topic and is analysed separately below, because
the two were conflated in the first pass at this question and they have
different risk profiles.

### What already exists

The Scout retool (2026-08-22, §§1–4) unwelded the walk from the leap for cost
reasons — re-mining the corpus cost ~$200 welded and ~$1 unwelded. That change
incidentally delivered most of the substrate an on-demand path needs:

| Verb | Moves a cursor? | Persists? | Gated by SCOUT_PAUSED? |
|---|---|---|---|
| `--pass` | yes, forward + backfill | jewels, leads | **yes** (ambient) |
| `--walk --from-seq N --pages M` | **no, by design** | jewels only | no (operator verb) |
| `--synthesize --since/--until/--kind` | no | leads | no (operator verb) |
| `--dry-run` (any) | no | nothing | n/a |
| `writer --lead <id> --dry-run` | n/a | nothing | n/a |

`run.py:290` states the cursor position explicitly: a reclaim sweep re-reads ore
the forward position has already covered, *"and letting it write that position
would rewind the Scout."* The pause switch deliberately gates only the ambient
pass, on the reasoning written into `__main__.py`: the reason to pause is
usually that you want to work the corpus by hand, which is what these verbs are
for.

**Consequence: the read-only chain is exercisable today with no new code.**
That matters immediately — the re-cut voice sample from 2026-08-08 is committed
and has never been verified against a real draft, precisely because the chain
could not be driven deliberately (`writer-ondemand-cli@operator`, still open).

### The blocker

`run_draft(config, lead_id, ...)` resolves its assignment through
`assignment.find_lead(config.leads_path, lead_id)` and the desk requires
`status: claimed`. So **a manual assignment today means writing a row into the
Scout's ledger** — and that row is then read by `leads.load_pitched()` as dedup
payload on the next ambient pass.

### Why that coupling is not free

Three costs, in increasing order of how easy they are to miss:

1. **Cost.** Per `scout-mining-economics.md`, a pass's cost is no longer a
   function of ore at all — it is dominated by the already-pitched dedup
   payload, which scales with the ledger. Every manual row therefore levies a
   permanent tax on every future ambient pass, and that tax never appears in
   the run that caused it.
2. **Provenance.** The lead record is `id, filed, status, register, agent_span,
   pitch, why_now, sources, redaction, model` (`leads.format_lead`). **Nothing
   records how a lead was produced.** Once filed, an operator-authored
   assignment is indistinguishable from something the Scout found — to the Wire
   Editor, to the Editor, and to any later measure of whether ambient
   prospecting works. This is the same class of problem the `spiked` vs
   `rejected` split was created to solve on 2026-08-03.
3. **Meaning.** The ledger *is* the Scout's product, and the Editor's queue over
   that product. Mixing "what the machine found that nobody has worked" with
   "what I decided to write" corrupts the only signal that says whether the
   ambient half is any good.

### Pineapple: not at risk on this path, and worth writing down why

The pineapple rule is **enforced by omission, deterministically.**
`leads.load_pitched()` is a hand-rolled parser matching exactly two patterns —
the `id` line and the `pitch` block. There is no pattern for `status`. Verdicts
are not filtered downstream and not discouraged in a prompt; they are never read
off disk, so they do not exist in the Scout's process. Breaking the rule
requires adding a regex, which is a visible act in a diff rather than a quiet
erosion. `leads.py` calls this "enforced in code, not just prose."

It is also correctly **scoped**. `writer/assignment.py` reads whole leads,
status included, and says why: *"The pineapple rule protects the prospector's
aperture, not the rewrite desk's inputs."*

Therefore, on a Writer-only manual path the rule is **structurally** out of
reach rather than protected by discipline: `load_pitched` is called only by
Scout synthesis, and a manual draft never invokes it. This ADR does not weaken
the rule and does not rely on anyone remembering it.

**One correction to NEWSROOM.md, owed regardless of this decision.** §Open
choices clears commissioned prospecting as "pineapple-compatible: a commission
scopes one errand, it doesn't narrow the ambient aperture." That is true of the
*roam* and false of the *ledger* — a commissioned lead enters the dedup payload
and therefore does suppress the identical ambient pitch later. The clearance was
argued about aperture; the coupling is about coverage. That gap is inherited,
not introduced here, and wants an amendment when commissioned prospecting is
actually built.

## Decision

**A manual Writer assignment is read from a file the operator writes, and never
enters `leads.yaml`.**

1. Split resolution from drafting. `run_draft` takes a **lead dict**; the caller
   resolves it — from the ledger by id, or from an assignment file. The binding
   today is one line, so this is a small refactor rather than a fork.
2. Add an assignment source at a convention path, matching the estate's existing
   convention-drop pattern (`voice/<profile>/`, `data/ask/<slug>.md`,
   `img/notes/<slug>.*`): **`pipelines/writer/state/assignments/<slug>.md`**,
   gitignored with the rest of `writer/state/`.
3. The assignment carries the same fields an assignment needs — `register`,
   `pitch`, `why_now`, `sources` — and **no lifecycle fields**. There is no
   `status`, because there is no queue: the operator has already decided.
4. The draft record banks as it does today under `writer/state/`, carrying
   `source: manual` so the draft's own provenance is unambiguous even though the
   ledger is untouched.
5. **The redaction scrub is not conditional on provenance.** It lives in the
   draft path, not the ledger path, so a file assignment keeps it for free —
   and that is load-bearing, because the Writer roams the box to research and
   can reach session logs even when the operator wrote the pitch. Gate ② stays
   exactly where it is. Recorded explicitly so nobody later removes it on the
   grounds that a human supplied the subject.

### What this does NOT decide

- **Commissioned prospecting** (`--synthesize --about "<topic>"`) is untouched
  and still open. It has the ledger coupling described above and should not be
  built until that is settled.
- **Whether `leads.yaml` gains a `source:` field.** Not needed by this decision,
  because nothing manual reaches the ledger. It becomes necessary the moment
  commissioned prospecting is built, and is the recommended keystone for that
  work.

## Alternatives Considered

**A. Add a manual row to `leads.yaml` with `source: manual`.** Rejected. Keeps
one lifecycle and one place to look, which is genuinely attractive, but it pays
all three costs above — permanent dedup tax, and a ledger that no longer answers
"is ambient prospecting working" — to buy tidiness on a path that has no queue
to manage. If manual volume ever grows enough to *need* a queue, this ADR should
be revisited rather than worked around.

**B. Relax the `status: claimed` requirement so any lead can be drafted.**
Rejected. It removes gate ① for every lead, not just manual ones, and gate ①
is the Editor's disposal step. The problem is the ledger being the only input,
not the claim being enforced.

**C. Use `--dry-run` and hand-copy the output.** This is what is possible today
and it is genuinely enough for *rehearsal* — verifying the voice bottle, for
instance. Rejected as the standing answer because nothing is banked: no draft
record, no roam trace, no scrub receipt, so a real piece produced this way
leaves no provenance at all.

## Consequences

**Good.** The Scout's ambient state — both cursors, the dedup payload, the
ledger, the cost curve — is untouched by any amount of manual drafting. The
pineapple rule needs no new protection. The voice bottle becomes exercisable
deliberately, which unblocks the stalled 2026-08-08 verification. Manual work no
longer inflates the queue the Editor triages.

**Costs and risks.** Two places now answer "what is being written" — the ledger
and the assignments directory — and someone reading only one gets a partial
view; this is accepted because they are genuinely different things, but it wants
a line in NEWSROOM.md so it is discoverable. A manual piece gets no ledger
lifecycle, so `drafted → approved → published` stamps do not apply to it, and if
manual pieces ever need publication tracking that is unbuilt. And the register
map is one row deep today (`REGISTER_PROFILES = {"note": "man-page-dry"}`), so
the manual desk can polish a **field note** and nothing else — a blog or
newsletter register is a data row to add, not code, but it does not exist yet.

**Reversible?** Yes, cheaply. Nothing is written to shared state, so abandoning
this leaves no residue to migrate.

## Prior Art

Surveyed 2026-09-03 by fetching page content (not search snippets) for three
systems in this shape. Two academic pipelines and one production content
operation. What follows is what they actually do, and where it agrees or
disagrees with the estate's own findings.

### The manual path is the production answer, not a compromise

Louis-François Bouchard's content pipeline — the only genuinely *shipping*
content operation in the set — **has no automated discovery at all**: *"I still
choose the topic. I still look at the current work that already exists. I still
write the brain dump."* Topics come from papers, conversations and interest,
never from algorithmic prospecting. Agents cover research, drafting, media and
translation; the human keeps topic selection, direction, taste and final
validation.

That is a direct external match for what this ADR proposes, and it reframes the
estate's design: **the Scout's ambient prospecting is the unusual, ambitious
half — the manual desk is what production practice actually converges on.**
Building the manual path is not a retreat from the automated one.

### Two human gates, in the same two places, arrived at independently

HLER (human-in-the-loop economic research) runs eight stages — data audit,
profiling, questioning, collection, analysis, writing, self-critique, review —
with **exactly two human gates**: selecting the research question among
generated candidates, and approving the finished paper for publication. Those
are structurally our gate ① (the Editor disposing the Wire Editor's shortlist)
and gate ② (scrub and approve to publish). Independent convergence on gate
*placement* is reasonable evidence the topology is right.

### Nobody else guards the backward edge

This is the finding worth having.

- **HLER has backward flow and does not examine it.** *"If none of the
  candidates are satisfactory, the researcher can request a new generation round
  with modified constraints, making this a genuine iterative loop."* The paper
  discusses multiple-testing and p-hacking risks but contains no analysis of
  whether repeated human selection narrows the hypothesis space.
- **Denario has a critique loop and does not examine it either.** Its
  `idea_maker` generates *"based on input text and feedback from the
  `idea_hater` agent"*; `idea_hater` reviews for feasibility, value and
  relevance. No discussion of diversity, novelty loss or convergence appears.

So the pineapple rule is **not** a solved problem we re-derived. It addresses a
gap that peer systems in this exact shape leave open, which means there is no
standard answer to copy and enforcement-by-omission stands on its own merits.

### The distinction that keeps Denario from being a counterexample

Denario's loop is **bounded and within-run**: three iterations in the fast
implementation, and a structured `5 ideas → critique → improve 2 → critique →
select` sequence in the planned one. Nothing accumulates across runs.

The pineapple rule prohibits **across-run taste accumulation** — the Editor's
verdicts biasing the *next* pass. A bounded within-run critic is a different
mechanism and does not violate it.

**This opens a design option the estate has not considered:** the Scout's
synthesis stage could run an internal critic — generate wide, critique, revise,
select — entirely within one pass, and stay pineapple-compatible so long as no
critique survives the process boundary. Worth its own ADR if pursued; noted here
so the option is on record rather than lost.

Bouchard reaches the same instinct from the other end: his reviewer evaluates
against the guideline *"using fresh context (avoiding inherited bias)."*
Deliberately withholding context is an established technique, not local paranoia.

### Where prior art conflicts with house doctrine — doctrine wins

Two places, both worth recording so nobody "improves" the design toward them
later without knowing they were considered.

**1. Word budgets as a drafting input.** Bouchard's stage 2 is a human-written
*"article guideline"* defining *"the sections, the hook, a word budget for each
part, the key definitions, the transitions, the examples, and every place where
the article needs a diagram"* — about an hour of work he rates as the
highest-value human input in the pipeline. Richer than this ADR's assignment
(register, pitch, why_now, sources), and superficially attractive given the
840-character field-note cap.

**Rejected on standing doctrine.** The operator's rule is that length caps are a
gate checked once *after* drafting, never a per-clause input — measuring
mid-stride makes the walk awkward. `release.js` enforces the cap by refusing to
stamp an out-of-range note, which is exactly a post-hoc gate. Adopting per-section
budgets would invert a decision already made from experience. The *non-length*
parts of the guideline (key definitions, examples, where a diagram earns its
place) carry no such conflict and are reasonable future assignment fields.

**2. Decomposed voice profiles.** Bouchard runs **six** modular voice profiles —
structure, mechanics, terminology, tonality, article format, character — against
our one-profile-one-directory bottle.

**Partly rejected, and his own text argues our side.** The same piece says
few-shot examples beat rules: *"Two or three strong pieces that actually sound
right teach rhythm and editorial judgment better than abstract rules."* That is
the voice bottle's central claim in someone else's words — independent
confirmation that samples carry the voice. Six *named rule categories* pulls the
other way, and the estate has a specific finding about that direction:
describing a move deadens it, because the model then aims at the description and
satisfies it every time, and a description cannot express the absence that is
most of the craft. We keep thin moves and rich samples.

### Convergences worth noting in passing

- **Plain files between stages.** Bouchard: *"Plain Markdown files connect
  stages, allowing inspection and correction mid-pipeline without full
  restarts."* Same doctrine as the estate's external, inspectable,
  warm-bootable state — and the same shape as this ADR's assignment file.
- **Fixed iteration counts** rather than loop-until-satisfied: three research
  rounds, three editor passes, three title rounds. The estate's equivalent
  discipline is bounded pages per walk and an explicit row budget.

### What was NOT verified

Denario's full architecture came from the HTML rendering; the 272-page PDF
exceeded the fetch limit. No production newsroom-shaped system with *ambient*
prospecting plus human gates was found — the closest matches either prospect
without publishing (research pipelines) or publish without prospecting
(Bouchard). If such a system exists it was not surfaced by this survey.

**Sources:** [HLER](https://arxiv.org/html/2603.07444v1) ·
[Denario](https://arxiv.org/html/2510.26887v1) ·
[Bouchard's content pipeline](https://www.louisbouchard.ai/ai-agent-content-pipeline/)

## Related Documents

- `docs/uzelhub-crew/NEWSROOM.md` (`read: full`) — §Writer and the voice bottle,
  §Open choices ("pull as well as push"), the pineapple rule
- `docs/uzelhub-crew/scout-retool.md` — the walk/leap unweld this depends on
- `docs/uzelhub-crew/scout-mining-economics.md` — the dedup-payload cost finding
- `voice/README.md` — bottle vocabulary (sample, exemplar, move, deadened)
- `pipelines/scout/leads.py` — pineapple enforcement by omission
- `pipelines/writer/assignment.py` — why the Writer may read status
- Calendar: `writer-ondemand-cli@operator.ai-agent-platform`

## Conventions

This is the first ADR in `ai-agent-platform`. Format follows
`/opt/predictor_ingest/docs/architecture/` — numbered `adr-NNN-slug.md`, with
Status / Date / Deciders, then Context, Decision, Alternatives Considered,
Consequences. Numbering is per-repo and starts at 001 here; the predictor's
series is unrelated and continues on its own.
