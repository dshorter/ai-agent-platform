---
read: full
status: REASONING AND HISTORY, not the current rule — seven sections cut to spec pointers 2026-09-06 (762 lines to 427). Current rules consolidated in NEWSROOM-SPEC.md on 2026-09-10; former desk pointers retained as history; vocabulary in GLOSSARY.md. Living sketch opened 2026-07-08; §Scout settled 2026-07-10, shipped 2026-07-12 — the build settled four open choices, synced 2026-07-14; SEO POLICY MOVED OUT 2026-08-13 to /opt/_host/SEO.md (responsibility model split out to seo-duties.md 2026-08-16; where they disagree SEO.md wins); open items flagged inline
---

# The Newsroom — content architecture (living sketch, ongoing)

> **Specification consolidated, 2026-09-10:** [NEWSROOM-SPEC.md](NEWSROOM-SPEC.md)
> now holds the current system requirements, including the former four desk
> specs and the proposed UI contract. Earlier pointers/authority statements
> below are retained history. [NEWSROOM-WORKPLAN.md](NEWSROOM-WORKPLAN.md)
> continues to own construction status and sequence.

> **Navigation added 2026-09-10:** the [documentation index](README.md#newsroom-start-here)
> links the recent critique, merge rationale, proposed UI specification and
> paused-Scout audit. Read [NEWSROOM-WORKPLAN.md](NEWSROOM-WORKPLAN.md) for
> the current construction leg and decision status. This document remains the
> design's reasoning and history.

> Formerly "The Reporter Flywheel" — renamed 2026-07-08 once the doc outgrew
> both words (it's the whole content operation now — roles, content types, SEO —
> not one agent or one loop). The flywheel is one mechanism inside it.

> **Status:** concept sketch, opened 2026-07-08. NOT a build plan — a captured
> line of thinking, kept because the box's founding grievance is *insight
> evaporation* and this reasoning shouldn't live only in a morning chat.
> Everything below is an **open choice**, not a blocker (per the "separate
> ideals from implementation" doctrine). Seed idea committed 2026-07-07 as
> `5d60175` (the one-line parked version); this doc is its expansion.

> ## Read this for *why*, never for the current rule
>
> **The current rules live in the four rewritable specs** —
> [spec-content-types.md](spec-content-types.md), [spec-scout.md](spec-scout.md),
> [spec-wire-editor.md](spec-wire-editor.md), [spec-writer.md](spec-writer.md) —
> and the vocabulary in [GLOSSARY.md](GLOSSARY.md). Those are edited in place and
> hold no correction strata. **This document is the design's reasoning and its
> history**: why a thing was decided, what it was decided against, and what was
> later found to be wrong. Where this document and a spec disagree, the spec is
> current and this one is the record of how it got there.
>
> Seven sections that now have a spec were cut to pointers on 2026-09-06. Each
> pointer names the reasoning that was in it, so nothing is silently lost; the
> full text is in git history.

**Map** — the whole shape at a glance (regenerate with `_host/scripts/doc-map.py NEWSROOM.md --write` after editing headings):

<!-- MAP:START -->
- [The thesis](#the-thesis)
- [The three-altitude pipeline (each altitude has a different author)](#the-three-altitude-pipeline-each-altitude-has-a-different-author)
- [The org chart — three roles, one genuinely new agent](#the-org-chart--three-roles-one-genuinely-new-agent)
- [Scout — moved to a spec](#scout--moved-to-a-spec)
- [The Scout learns navigation, not taste (the pineapple rule)](#the-scout-learns-navigation-not-taste-the-pineapple-rule)
- [The Scout's sources — moved to a spec](#the-scouts-sources--moved-to-a-spec)
- [Measured behaviour — moved to a leaf](#measured-behaviour--moved-to-a-leaf)
- [Model tiers — moved to a spec](#model-tiers--moved-to-a-spec)
- [Reuse vs fork — the ghost crew stays on ghost](#reuse-vs-fork--the-ghost-crew-stays-on-ghost)
- [SEO duties — moved to a leaf](#seo-duties--moved-to-a-leaf)
- [Writer — moved to a spec](#writer--moved-to-a-spec)
- [Marketer & Editor — moved to a spec](#marketer--editor--moved-to-a-spec)
- [Content types — moved to a spec](#content-types--moved-to-a-spec)
- [Editorial rules — moved to a spec](#editorial-rules--moved-to-a-spec)
- [The one real fork — where the Scout stops (v1 vs mature)](#the-one-real-fork--where-the-scout-stops-v1-vs-mature)
- [Open choices (none are blockers)](#open-choices-none-are-blockers)
<!-- MAP:END -->

## The thesis

The box already narrates its own work — commits, the Director's devlog, the
sysadmin ledger, `agent_decisions`. The flywheel puts a **curator on the
narration stream** and makes the narration itself the product's content:
box narrates → curate → publish. It is "the platform *is* the product story
uzelhub is telling" (the Director's own line) turned into a pipeline.

**One full revolution has already run, by hand** — the specimen: a backup
incident → sysadmin-ledger case study → survey node `ops.backup-june-silence`
→ authored `data/notes.json` entry → the live `/notes/silent-backup-failure`
page on the apex. The flywheel is not speculative; it is the *automation of a
trail with a complete, human-walked specimen.*

## The three-altitude pipeline (each altitude has a different author)

1. **The walk** — `promotion-survey.yaml`. Agentic, dated, re-walked
   *wholesale* (never patched), honoring the id-stability contract. Its
   product is the **diff**: `featured: []` nodes are the unpromoted story
   queue. Stories are first-class (`kind: narrative` sits beside `system`).
2. **The authoring** — `data/notes.json`. Authored prose stored as structured
   data (title, tagline, bullets, JSON-prose `sections`), each entry carrying
   a `copyDraft` provenance/approval stamp. **The human-approval gate is
   encoded as data**, not a permission prompt — same discipline as the
   Director's missing write tool, different costume.
3. **The render** — `generate.js`. The *only* deterministic layer
   ("decision-free pipeline"): a note object → page + index + sitemap +
   canonical + breadcrumb; an image at `img/notes/<slug>.*` auto-wires by
   convention. Tested, CI-gated. **No agent ever touches HTML.**

## The org chart — three roles, one genuinely new agent

| Role | Job | Who | Status |
|---|---|---|---|
| [**Scout**](#scout--moved-to-a-spec) | Wander logs/docs/repos/`agent_decisions`; file leads on the leads ledger (the unpromoted story queue) | nobody, autonomously | **shipped 2026-07-12** (`c749c31`) — daily 05:45 pass, filing since day one |
| **Writer** | Turn a claimed lead into copy in the right register — a `notes.json` entry *or* a blog draft, `copyDraft` stamped | the **content agent** (276 runs) + the new **note desk** | **note leg shipped 2026-07-14** — voice bottle + convergent roam (`pipelines/writer/`, persona: `writer-persona.md`); blog leg = the content agent, unchanged |
| **Wire Editor** | Triage the new-lead queue into a claim/spike/hold shortlist; carry the Editor-in-chief's shadow verdicts (gate-① concordance) | its own desk agent (Sonnet seat); proposals-only, never the pen | **hired + built 2026-07-18** (`pipelines/wire_editor/`, plan doc Phase 2) |
| **Editor** | Dispose the Wire Editor's shortlist (gate ①); scrub + approve drafts (gate ②, permanent) | **operator** today; Director inherits gate ① on sustained shadow concordance | **live, as operator** — gate ② never migrates |

Drilling into the pipeline *reduced* the new-build surface: the Writer half
was already on the payroll (content agent), the Editor half was already
designed (Director). What's genuinely new is narrower than "a reporter" — it
is a **Scout that maintains the survey queue.**

**Read this doc as two layers, and keep them distinct** (it's what keeps the
design wipeable):
- **Responsibility model** — which *concern* belongs to which *role*
  (find→Scout, write→Writer, package/SEO→marketer-technique, route→Editor).
  Largely settled. This is concept→role.
- **Process topology** — how roles map onto actual *processes* (one Scout that
  also writes vs Scout + separate Writer; shared lib vs duplicate; one agent or
  three). Deliberately OPEN — the v1-vs-mature forks below. This is role→agent.

We are assigning duties at the *role* layer; the *agent* layer stays wet. No new
concepts were invented this whole design — the work is assignment, not
rearrangement (though assigning SEO correctly forced it to decompose into the
layers below: a real separation won't sit still until you split the concept
under it).

## Scout — moved to a spec

**[spec-scout.md](spec-scout.md)** (`read: full`) — what the Scout is and does
today: the two seats and their budgets, the seven sources and which have
readers, the walk, synthesis, filing, the invariants and what is still open.

What this section held and the spec does not: the *derivation*. The Scout's two
sub-verbs (discover is new, assess is the marketer's `extract_descriptor`
pointed outward at the unknown many rather than at one known thing), and why
cross-agent span is a queryable heuristic rather than a vibe — `agent_decisions`
carries `workflow_sequence_id`, so "a story where two agents interact" is a
sequence spanning more than one `agent_name`. Span was always a weight that adds
attention, never a filter that subtracts candidates; that it counts strings and
not agents was measured 2026-09-06
([agent-span-counts-strings-2026-09-06.md](agent-span-counts-strings-2026-09-06.md)).
Cut to a pointer 2026-09-06; the text is in git history.

## The Scout learns navigation, not taste (the pineapple rule)

The Scout is **stateful** where every other producer is stateless — a
concept-level property, not an implementation detail: sourcing *accumulates*,
production doesn't. So the Scout has its own flywheel. But there are two
completely different things called "Scout learning," and only one is safe:

- **Navigational learning — YES.** The *craft of looking*: where things live,
  which sources run rich, how to search efficiently, the ecosystem map,
  cross-referencing skill. Makes the Scout a better explorer; biases *nothing*
  about what counts as a story.
- **Taste learning — NO.** Absorbing what the Editor promotes/spikes and
  drifting toward it. That is a reward signal, and reward signals *narrow* —
  the "new-Instagram-likes-pineapple → the world is pineapple → apples are
  heresy" trap. It would starve the wild "link 16 things because maybe" leaps,
  which are often the *best* stories precisely because no pattern predicted them.

**Principle: the Scout generates wide, the Editor selects narrow — do NOT close
the loop between them, or the generator collapses into the selector's taste.**
The Editor spiking a lead is not feedback *to the Scout*; it is just this one
lead not making the cut, and the next pass must be no less reckless. (Note: the
*opposite* is ideal where ground truth is the reward — medicine, cryptography,
fraud — converge hard toward provably-correct. Our search space has infinite
good answers, not one right one; so we stay explore-heavy.)

**The inversion:** the Editor gate is precisely what *licenses* the Scout's
recklessness — because something downstream filters, throwing 16-way
connections at the wall is *cheap*. Fuse Scout and Editor and it would have to
self-censor. The separation wanted for cleanliness is *also* what unleashes the
creativity. Same cut, two payoffs.

**What the flywheel accumulates — all navigation, no taste:**
- **The map** — topology, source richness, where narratives hide.
- **Coverage memory** — what it has already pitched, for dedup. Hard line:
  remember the *specific pitch* to avoid re-surfacing the identical thing;
  NEVER generalize a verdict into "avoid this kind." Dedup is memory; taste is
  contamination.
- **Raw material** — the more of the box it has seen, the more it has to
  connect. Here accumulation *fuels* creativity instead of narrowing it.

Memory is **external, inspectable, warm-bootable** state (a ledger file, not
weights) — a rut is a five-minute trim, not a retrain, and you can see what it
hoarded before deciding it's stuck. Corollary: the monoculture failure mode is
*iatrogenic* — remove the Editor-reward loop and the Scout has no narrowing
force, so it stays wide by default. A completeness-critic counterweight drops
from load-bearing to belt-and-suspenders.

## The Scout's sources — moved to a spec

**[spec-scout.md](spec-scout.md) §Sources and readers** (`read: full`) — the
seven source types, which have a reader and which are roam-only, the three
registered roots, and the anchor each source cites.

What this section held and the spec does not: the reasoning behind the cursor
substrate (keyset pagination over a sequence table, so coverage is linear while
investigation stays temporally bidirectional — one cursor across all sources
would close the Scout's temporal aperture, which is the pineapple rule again),
and the opaque free-text scratchpad, deliberately not an `arc_id`, that nothing
downstream may read as structured data.

It also held the **2026-09-04 correction to "session logs are the richest ore"**
— that the word was carrying two properties at once, and that the `NOT NULL`
foreign key, not the wording, was what actually made every lead transcript-only.
That correction now lives where it can be read whole:
[jewels-are-transcript-only-2026-09-03.md](jewels-are-transcript-only-2026-09-03.md)
for the mechanism, [newsroom-design-review-2026-09-04.md](newsroom-design-review-2026-09-04.md)
for the review, and **stance** in [GLOSSARY.md](GLOSSARY.md) for the word that
replaced the overloaded one. Cut to a pointer 2026-09-06; the text is in git
history.

## Measured behaviour — moved to a leaf

**[scout-mining-economics.md](scout-mining-economics.md)** (`read: full`) — what
the Scout measurably *does* with ore, as opposed to what this doc specifies it is
for. Measured against the live corpus 2026-08-19..21. Read it before tuning any
Scout knob, because three of its findings are counterintuitive:

- output is homeostatic at ~13 leads a pass regardless of input, so **more ore
  per pass means thinner mining, not more leads** (conversion runs 0.18 leads
  per jewel on a full plate, 1.00 on a small one);
- **jewels are never persisted** — ~1,645 were extracted and discarded, and
  73.3% of the corpus is cited by no lead;
- cost is no longer a function of ore at all; it is dominated by the
  already-pitched dedup payload, which scales with the ledger.

What is being done about it: **[scout-retool.md](scout-retool.md)** (`read: full`,
spec, not built) — persist the jewel layer, unweld walk from synthesis, size the
plate by row budget, add a backfill cursor. A retool, not a fifth agent.

## Model tiers — moved to a spec

**[spec-scout.md](spec-scout.md) §Seats and budgets** (`read: full`) — the two
seats, their models, depth, output ceilings and measured cost, and the cost fuse
on every verb.

What this section held and the spec does not: the **asymmetry argument** for
spending on synthesis, which is the part worth keeping. The Editor filters the
Scout's bad leads, but nothing filters its *missing* ones — an editor can only
reject what was surfaced, never conjure the story a duller model failed to see.
False negatives are invisible and uncounted, so the synthesis seat sets the
ceiling on what stories ever exist. **That argument is untouched by what
followed, and it has still never been tested.**

What followed: its cost premises were measured on 2026-09-03 and were wrong by
two orders of magnitude — 39 Fable synthesis calls averaged $1.3274 against
$0.75 for all 106 walk calls combined, 187× per call, growing 4× in six weeks
because the dedup payload rides in that prompt and scales with the ledger.
"Ambient, weekly-ish" had been overtaken by the daily timer. The default moved
to Sonnet 5 to **invert the burden, not to refute the quality argument**; the
A/B due 2026-07-26 is still owed, and is an open question in AGENTS.md. A second
correction, 2026-09-05: the output-budget hazard belongs to the *seat*, not to
Fable — a Sonnet 5 call burned all 20,000 tokens and emitted nothing, reading as
"0 leads" for $0.43 until a guard made it loud
([silent-instruments-2026-08-29.md](silent-instruments-2026-08-29.md) is the
family). Cut to a pointer 2026-09-06; the text is in git history.

## Reuse vs fork — the ghost crew stays on ghost

The existing blog pipeline (`content_agent` → `marketer_agent` → Ghost, wired
in `runner.py`: "content → extract → package → ghost") is **left alone,
dedicated to the predictor/commit-history blog.** Not out of caution — because
those agents bake in blog-specific assumptions that are *wrong* for the
flywheel's surfaces:

- The marketer's `MarketerOutput` struct is generic SEO metadata, but its
  *brain* is Ghost-shaped: its prompt encodes "Ghost is authoritative,
  canonical points to Ghost," and its internal links rank against the **blog
  corpus** (`LinkCandidate.post_id`).
- For apex **notes**, the canonical model *inverts*: notes are apex-canonical;
  a blog retelling points *back to the note*. Reusing the marketer as-is would
  import a backwards canonical assumption and links ranked against the wrong
  corpus.

**Decision:** build the flywheel fresh (Scout + notes Writer + a flywheel SEO
pass with its own canonical model), but **fork ≠ copy-paste** — factor the
voice/sink-*agnostic* mechanics into a shared lib both worlds import: the
`MarketerOutput` metadata *shape*, the Haiku-triage extraction *technique*, the
overlap-scored link *algorithm*. Principle: **separate by what changes (input,
voice, canonical model, corpus), share by what's stable (the extraction
technique, the SEO-metadata shape).**

## SEO duties — moved to a leaf

**[seo-duties.md](seo-duties.md)** (`read: full`) — the responsibility model:
the five layers, who holds per-item text per surface, the unowned charter, and
the deep-dive-vs-retelling fork. Extracted 2026-08-16; this doc was 729 lines
and the section had become mostly pointer plus amendment history.

Policy itself lives in **`/opt/_host/SEO.md`** — the two-host rule, indexing
tiers, Ghost routing and tags, the field-note size contract, syndication
canonicals. Where any of the three disagree, SEO.md is right.

## Writer — moved to a spec

**[spec-writer.md](spec-writer.md)** (`read: full`) — the assignment, the
type-to-profile map, the note's shape, the convergent roam, where drafts park,
the lifecycle and the seat. [writer-persona.md](writer-persona.md) stays as the
voice of the design and its open agenda.

What this section held and the spec does not: why the bottle is **profiles, not
one jar** — *you cannot mine a voice the box has never spoken*, so a profile
draws from two wells, harvested where the voice is already demonstrated and
seeded where it is aspirational. And why it must be bottled at all: the voice is
a collaboration (model phrasing, operator discipline, the box's material) and
"the current model on a good night" is not a durable dependency for an operation
that swaps model brains routinely. Also the operator's 2026-07-18 note that **the
bootstrap is not the process** — the first story's four runs and live
calibration were voice refinement, banked into the bottle precisely so the next
story needs less of it; judge maturity by the trend in hands-on minutes per
story, not by the first story's cost. Cut to a pointer 2026-09-06; the text is
in git history.

## Marketer & Editor — moved to a spec

**[spec-wire-editor.md](spec-wire-editor.md)** (`read: full`) — the triage
desk's pass, its verdicts, the clustering rule, the policy it routes by, the
chief's shadow and the concordance metric. The Marketer is unchanged and stays
dedicated to the Ghost blog; per-surface SEO assignment is in
[seo-duties.md](seo-duties.md).

What this section held and the spec does not: that the routing desk's ledger
turned out to be **the Scout's own leads file** rather than the survey's
`featured:` field, which stays the marketing-promotion queue — a different desk.
And why `spiked` and `rejected` stay distinct (added 2026-08-03, when the review
desk's thumbs-down had no legal transition and was refused every time): only
`rejected` is a signal about the *Writer*, and that is the metric that says
whether the voice bottle is maturing. Producer-versus-orchestrator holds — the
Scout and the Writer are producers; the Director approves and routes but never
writes. Cut to a pointer 2026-09-06; the text is in git history.

## Content types — moved to a spec

**[spec-content-types.md](spec-content-types.md)** (`read: full`) — the five
types, their sinks and canonicals, voice profiles and audiences; the rules that
cross all types; the shape of each; and what each desk does with the type. Where
it and `/opt/_host/SEO.md` disagree, SEO.md wins.

What this section held and the spec does not: that **the taxonomy IS the
Editor's routing table**, and that it is the axis the reuse-versus-fork
principle scales across — a new type is a new sink profile plugged into shared
mechanics, never a new agent, which is precisely why the ghost crew was forked
rather than genericized. And the guardrail that outlives every amendment:
*self-awareness first, war stories second is a **routing** filter the Editor
applies, never a **discovery** filter the Scout applies.* Per-sink lenses narrow
routing, never prospecting.

Two amendments in that text are now wrong, and the spec is right: the note's
`deepDive` was written as **mandatory** and was corrected to opportunistic by the
operator on 2026-08-17 (SEO.md §The field-note contract), and the body cap
carries a tolerance — 840 characters ±5%. Cut to a pointer 2026-09-06; the text
is in git history.

## Editorial rules — moved to a spec

**[spec-content-types.md](spec-content-types.md)** (`read: full`) — the cadence,
the shape of each type, the wit rule and the employer gate. Cadence policy
itself is `/opt/_host/SEO.md` §Cadence.

What this section held and the spec does not: that the three apex types are **a
real newsroom's cadence by durability** — ticker the pulse, newsletter the weekly
edition, field notes the features; pulse → digest → feature, one set of mechanics
behind three sink profiles, which is what makes the metaphor real rather than
decorative. The ticker's two honesty rules and their reasoning: **verbs, not
victories** (the moment it crows it reads as spin), and a challenge never appears
raw but only as its resolution verb, linking to the note that carries the warts —
the ticker points at the depth instead of pretending it does not exist. The
employer gate (operator, 2026-07-18): work-machine sessions are legitimate ore,
what publishes is the method arc with the application never named or
identifiable, it is a distinct gate from the credential scrub, it is applied at
routing, and a lead can pass the scrub and still fail it. And the house wit rule
(operator, 2026-07-17): **never instruct a writer to add wit — instruct it to
watch for it**, because commissioned wit produces snark and opportunistic wit
produces the Clemens lean. Cut to a pointer 2026-09-06; the text is in git
history.

## The one real fork — where the Scout stops (v1 vs mature)

- **v1 — Scout writes the draft.** One agent walks *and* files a `copyDraft`
  stamped for review; operator is editor. Minimal; a literal automation of the
  trail that already ran once.
- **Mature — Scout files a lead only.** It flips the survey node + writes a
  one-line pitch (surveyId, why-now, source pointers, suggested register); the
  content agent writes; the Director routes. Clean single-responsibility,
  reuses the one Writer (one voice bar) — but three handoffs where v1 has zero.

**Recommendation (separate ideals from implementation):** the *ideal* is three
roles; **ship v1 as one Scout + operator-editor, decompose when volume forces
it.** The split is an open choice to make after watching the Scout run — not a
problem being deferred.

**Settled — by the build, in the other direction (synced 2026-07-14).** The
Scout that shipped (`c749c31`, 2026-07-12) files leads only: pitch, why-now,
sources, suggested register — no copy. The lead was simply the natural output
unit of walk+synthesis, so the build landed on the *mature* side of this fork
without ever holding the meeting — the recommended v1 was skipped, not chosen
against. The cost surfaced immediately and honestly: a queue of pitches with no
Writer behind it (the 07-17 routing TODO). The fork is closed; what it leaves
behind is the real next build — the Writer leg, claimed lead → copy (see
`writer-persona.md`).

## Open choices (none are blockers)

**Settled since — by the build, not the whiteboard** (synced 2026-07-14; the
Scout shipping answered four of these before anyone re-opened this doc):

- *Source streams:* session logs by cursor (the ore); `agent_decisions`
  sequences in the synthesis context; repos, docs, ledger, calendar, survey by
  free roam — a catalog, no rotation, no quotas.
- *Pass cadence:* daily, 05:45 systemd timer — not weekly — at least through
  the A/B; revisit once the queue's fill rate has met an actual Editor.
- *The curation queue:* the ledger pattern won —
  `pipelines/scout/state/leads.yaml`, gitignored (origin is public; a push is a
  publish). The survey's `featured: []` stays the marketing-promotion queue.
- *Scout-writes-draft vs files-lead:* files-lead (see §The one real fork).

Still open:

- ~~Link-vs-copy SEO shape for the blog leg~~ — **closed 2026-08-13**: the blog
  leg is a distinct-intent, self-canonical **deep dive**, not a retelling (see
  [seo-duties.md](seo-duties.md)). Notes stay apex-canonical and link out to it.
- **No internal-tag producer exists** (added 2026-08-13). SEO.md tiers content
  with Ghost *internal* tags — no archive page, absent from the sitemap, usable
  as a `routes.yaml` filter. But `ghost_publisher.py` emits `{"name": tag}` and
  nothing else, so the thing that publishes cannot create the tier the policy
  depends on. A build, not an edit; blocks the routing plan, not the corpus.
- **The Marketer's link instruction and its data disagree** (added 2026-08-13).
  Its doctrine asks for a link back to the apex, but `internal_links` may only
  be chosen from `LinkCandidate`, which carries a blog `post_id`. Moot today —
  candidates are hardcoded `[]` because Phase 2.1 was never built, which is why
  0 of 270 corpus posts carry a single internal link. Fixing the ranker without
  fixing the corpus mismatch would produce confidently wrong links.
- Whether the "assess" muscle is literally shared code with the marketer or a
  parallel implementation.
- Where the white-paper / case-study type lives (apex `/papers/` via
  generate.js, Ghost, or its own surface).
- Ghost subfolder / tag-routing mechanics for new blog topics (Ghost hardwires
  one instance = one blog).
- Synthesis-stage model: **still owed, not underway** (corrected 2026-09-06;
  this entry read "A/B underway" for 40 days after its own readout was due).
  The design was one week on Fable 5 and one on Sonnet 5 with a side-by-side
  readout on 07-26, the Editor judging and not the contestant. It never ran.
  What happened instead: cost was measured on 09-03 and the default moved to
  Sonnet 5, which inverts the burden without answering the quality question.
  ADR-002 §6b has since replaced the arm's design — run both arms as
  `--synthesize --dry-run` over the same stored jewels, so the first arm's
  leads never enter the second arm's dedup memory. Current state:
  [spec-scout.md](spec-scout.md) §Seats and budgets. Open question:
  ../../AGENTS.md.
- **A dedicated ticker table** (added 2026-07-13, once the Scout started filing
  ticker-register leads): the ticker is a *rolling* pulse, so accumulating items
  need lifecycle management — when one rolls on, how long it stays, when it
  rolls off. The interval is unknown right now; the shape (a table/data file the
  generator samples from, superseding the v1 survey-sample source) firms up once
  a few passes of ticker leads exist to look at.
- **Pull as well as push** (added 2026-07-13): after the Scout has accumulated
  state (leads, scratchpad arcs, the map), a *query* mode — "what do you have
  on X?" — i.e. commissioned prospecting: a targeted roam + synthesis over its
  own material on demand. Distinct from the spiked /scout-as-chat idea (ranking
  "most promising" stays Editor judgment) and pineapple-compatible: a commission
  scopes one errand, it doesn't narrow the ambient aperture.
  **Qualified 2026-09-06.** ADR-001 splits this: it holds for a commissioned
  *roam*, which reads ore and narrows nothing, and fails for a commissioned
  read of the *ledger*, which is where dispositions live — that is the path by
  which a verdict would reach the Scout. The compatibility is a property of
  what the commission may read, not of commissioning itself.
