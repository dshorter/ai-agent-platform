---
read: full
status: living sketch (opened 2026-07-08); §Scout settled 2026-07-10, shipped 2026-07-12 — the build settled four open choices, synced 2026-07-14; SEO POLICY MOVED OUT 2026-08-13 to /opt/_host/SEO.md (responsibility model split out to seo-duties.md 2026-08-16; where they disagree SEO.md wins); open items flagged inline
---

# The Newsroom — content architecture (living sketch, ongoing)

> Formerly "The Reporter Flywheel" — renamed 2026-07-08 once the doc outgrew
> both words (it's the whole content operation now — roles, content types, SEO —
> not one agent or one loop). The flywheel is one mechanism inside it.

> **Status:** concept sketch, opened 2026-07-08. NOT a build plan — a captured
> line of thinking, kept because the box's founding grievance is *insight
> evaporation* and this reasoning shouldn't live only in a morning chat.
> Everything below is an **open choice**, not a blocker (per the "separate
> ideals from implementation" doctrine). Seed idea committed 2026-07-07 as
> `5d60175` (the one-line parked version); this doc is its expansion.

**Map** — the whole shape at a glance (regenerate with `_host/scripts/doc-map.py NEWSROOM.md --write` after editing headings; **read this doc in full** — the Scout spec alone spans four of these):

<!-- MAP:START -->
- [The thesis](#the-thesis)
- [The three-altitude pipeline (each altitude has a different author)](#the-three-altitude-pipeline-each-altitude-has-a-different-author)
- [The org chart — three roles, one genuinely new agent](#the-org-chart--three-roles-one-genuinely-new-agent)
- [Scout, in detail](#scout-in-detail)
- [The Scout learns navigation, not taste (the pineapple rule)](#the-scout-learns-navigation-not-taste-the-pineapple-rule)
- [The Scout's sources — session logs first, read by cursor](#the-scouts-sources--session-logs-first-read-by-cursor)
- [Model tiers — cheap walk, premium synthesis (Fable 5 on the leap)](#model-tiers--cheap-walk-premium-synthesis-fable-5-on-the-leap)
- [Reuse vs fork — the ghost crew stays on ghost](#reuse-vs-fork--the-ghost-crew-stays-on-ghost)
- [SEO duties — moved to a leaf](#seo-duties--moved-to-a-leaf)
- [Writer, in detail — and the voice bottle](#writer-in-detail--and-the-voice-bottle)
- [Marketer & Editor — mostly already here](#marketer--editor--mostly-already-here)
- [Content types = the Editor's routing dimension](#content-types--the-editors-routing-dimension)
- [Editorial rules — the cadence, the ticker filter, the three registers](#editorial-rules--the-cadence-the-ticker-filter-the-three-registers)
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
| [**Scout**](#scout-in-detail) | Wander logs/docs/repos/`agent_decisions`; file leads on the leads ledger (the unpromoted story queue) | nobody, autonomously | **shipped 2026-07-12** (`c749c31`) — daily 05:45 pass, filing since day one |
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

## Scout, in detail

**Two sub-verbs, only one new:**
- **Discover** (walk the whole box, surface unpromoted candidates) — new;
  nobody does self-directed prospecting.
- **Assess** (is there a story, what's the angle) — the **marketer already
  does this**. `marketer_agent.extract_descriptor()` pulls structured meaning
  out of a draft; `package()` shapes it for a channel with internal-link
  selection. Don't rebuild "assess" — **reuse the marketer's extraction
  *technique*, NOT the marketer agent** (see "Reuse vs fork" below: the agent
  bakes in a Ghost-authoritative canonical model that inverts for notes).
  Pointed *outward* at raw box material instead of a finished draft. Clean
  boundary: the marketer assesses *one known thing for a channel*; the Scout
  assesses *the unknown many for existence.* Same verb, opposite scope — and
  the shared technique inherits the marketer's cost split (extraction on
  **Haiku**, judgment on **Sonnet**), which is exactly what cheap whole-box
  prospecting wants.

**Story-worthiness heuristic — cross-agent span (and it's queryable):** the
richest stories are emergent, living *at the seams between agents* — the
content agent handing to the marketer, the Director reasoning over the
marketer's survey, one agent refusing based on what another wrote. This is not
a vibe: `agent_decisions` carries `workflow_sequence_id`, `parent_decision_id`,
`step_number` — a "story where two agents interact" is literally **a sequence
whose rows span more than one `agent_name`.** The Scout should **rank a lead by
how many distinct agents its sequence touches.** (The calendar saga scores high
— Director ↔ operator ↔ its own prior reasoning; the backup story lower —
one domain, one actor — yet it shipped first only because it was *handed* to
the walker. A cross-agent-aware Scout would have surfaced the saga itself.)
**This heuristic is a hint that adds weight, never a filter that subtracts
candidates** — weight the agent-seams higher for attention, but never stop
surfacing the lone-actor story (the backup note was single-actor and shipped
first). See "The Scout learns navigation, not taste" for why nothing is ever
allowed to close the Scout's aperture.

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

## The Scout's sources — session logs first, read by cursor

The Scout grazes several sources (git, docs, `agent_decisions`, the ledger),
but its **primary ore is the Claude Code session logs** — the transcripts of
the human-AI sessions that build the box. This was the original flywheel idea
(commit `5d60175`, "grazing the session logs"), and it's the richest by far:
the *reasoning*, the corrections, the aha-moments — where the jewels live. It's
also the direct **evidence for the thesis** — the logs literally *are* the
100%-human-AI-collaboration the site claims. Recursive by nature: the session
that designed this newsroom is itself future ticker / newsletter / note material.

**Shape — a sequence table, not loose files.** Ingest the JSONL (the Codex
reader already works; adapt to Claude Code's format) into a table —
`session_id, date, turn, role, type (query | progress | final), text` — plus a
**light-cleaned** copy of the human turns (fix dictation/spelling only, preserve
meaning) **with the raw kept alongside**. Never let the tidy version become the
only version; an LLM "cleanup" can quietly rewrite intent.

**⚑ Redaction guardrail (absolute).** These logs contain everything —
credentials spoken aloud, the recovery-key screenshot, the B2 key, internal
paths, IPs, personal email, the security posture stated plainly. The Scout may
**read freely**; **nothing derived from a session log publishes without a hard
secret/PII/security scrub AND the Editor's approval.** Here read-freely /
propose-writes stops being nice-to-have and becomes non-negotiable.

**Why a table, not files — the cursor.** The table is a *cursor substrate*. A
persisted high-water-mark (last-processed `date, session_id, turn`) lets the
Scout:
- **page a bounded chunk per run** — context stays small and doesn't drift or
  overflow (the real risk of reading too much at once);
- **resume exactly where it left off** — stop when context fills, come back;
- **advance by story-arc when one is complete**, else by page — loop a full arc
  as a unit, then move the cursor past it.

Use **keyset pagination** (`WHERE (date, session_id, turn) > cursor`), not
OFFSET — the log is append-only and ordered, so a watermark is stable where an
offset would drift (à la a paged DB reader).

**Scope the cursor to the logs, and nowhere else.** Its only job is *coverage*:
guaranteeing the append-only log gets fully read at least once — best owned by
the ingestion / a completeness pass, not baked into the Scout's judgment. It's
external, inspectable, warm-bootable; reset it to re-scan; it encodes read
position only, never taste. For **every other source** — git, docs,
`agent_decisions`, the ledger — the Scout is **cursor-free and temporally
bidirectional.** Investigation is non-linear: a decision made in March explains
a bug in July, so a smart Scout must jump back and forth in time as it tracks a
thread. A forward cursor there would *close the Scout's temporal aperture* —
exactly what the pineapple rule forbids. **Coverage is linear (cursor);
investigation is not (free roam).** One cursor across all sources is both clumsy
and aperture-closing — don't. The coverage sweep itself is just the Scout's own
**forward-only walk of newly-imported logs** — read the new chunk in order, miss
nothing, advance the watermark. That's the whole of the cursor's job; it isn't a
separate agent.

**Arc notes: a free-text scratchpad column, not a schema.** Give every log
record a free-text `scratchpad` column the Scout may scribble in during the
forward walk — "connects to the backup saga," "possible arc: calendar
authority." Deliberately *not* a rigid `arc_id` or an over-structured JSON field:
that's schema-on-write before we know the shape (the nickel-jar move). Fuzzy
prose is enough — LLM-native, inspectable, and it lets arcs stay *latent* until
something actually needs them, at which point you extract structure on read into
something *new* — never retrofit-parse the scratchpad, since that quietly
re-imposes a schema (and probably a one-to-many).

It's the Scout's own **opaque** space: it may use whatever internal format helps
it think — prose, its own tags, a dab of ad-hoc JSON — but the contract is that
**nothing downstream ever reads it as structured data.** It's all scratch as far
as the system is concerned, and that opacity is exactly what keeps the schema
(and the nickel jar) from sneaking back. The scratchpad is the arc substrate;
nothing more is needed yet.

**Jewels heuristic.** Mine for the *durable* material — named principles,
corrections/reversals, reframes, decisions-with-reasons — not the play-by-play
of which command ran. Same "story lives at the seams / emergence" nose the
Scout already has, pointed at transcripts: the best moments are the corrections
(the pineapple catch, reuse-vs-fork, the STATUS-values fix earlier tonight).

**Parked — a batch arc-finder, only if the scratchpad isn't enough.**
Arc-detection lives in the scratchpad first: the Scout notes connections inline
as it walks. IF that proves too shallow, a *separate* batch process (ghost-crew
nature — scheduled, whole-corpus, non-interactive) could later read all the
scratchpads and assemble/rank complete arcs across sessions. But that's a
speculative later consumer, not a first-pass build — the scratchpad-on-walk is
v1, and the batch arc-finder earns its existence only if the inline notes fall
short. Don't build it on spec.

## Model tiers — cheap walk, premium synthesis (Fable 5 on the leap)

The Scout is **not one model call** — it's two stages with opposite needs, so
"Opus vs Sonnet for the Scout" is the wrong granularity. Tier it (this is the
marketer's Haiku-triage / Sonnet-judgment split, inherited):

- **Walk / triage / dedup** — read big swaths of the box, filter, coverage
  bookkeeping. *High token volume, low IQ demand.* → **Haiku 4.5** ($1/$5) or
  Sonnet. You're paying per token to skim; keep it cheap.
- **Creative synthesis** — the "link 16 things because maybe" leap over the
  triaged candidates. *Low token volume, maximum IQ demand.* → **Fable 5**
  ($10/$50), the most capable model. The model question applies **only** to
  this stage.

**Why spend top-tier on synthesis — the asymmetry:** this stage is the creative
*ceiling of the whole newsroom*. The Editor filters the Scout's **bad** leads
(false positives are cheap — spiked), but **nothing filters the Scout's
*missing* leads** — the Editor can only reject what was surfaced, never conjure
the story a duller model failed to see. False negatives are invisible and
uncounted, so the synthesis model sets the ceiling on *what stories ever
exist*. That's a stronger reason to spend than anywhere else in the pipeline
(the Writer's quality rides on voice exemplars; the Editor's routing is
near-mechanical).

Two things make it cheap to spend here: it's **ambient** (weekly-ish, no user
waiting — a slow deliberate model is fine) and **low-token** (synthesis reasons
over already-triaged candidates, not the raw box). At that volume the ladder is
pennies per pass — Sonnet $3/$15 → Opus $5/$25 → Fable $10/$50 — and the whole
Director has spent ~$3.31 in its life. Cost is not the binding constraint.

**Why Fable, not Opus:** by this operation's own benchmark logic (the devlog's
reason for Director→Sonnet 5: it matches Opus 4.8 on knowledge-work and
reasoning-with-tools, trailing only on pure coding), **Opus 4.8 is the
weakest-justified choice** — 1.67× Sonnet's price for a rounding-error gain on
non-coding work. Synthesis is divergent associative reasoning over a huge
heterogeneous context — Fable 5's stated sweet spot. So the real fork is
**Sonnet 5 (cheap, near-Opus) vs Fable 5 (top ceiling, still trivially cheap
here)**; Opus is the mushy middle to skip. This is the one seat in the whole
operation where raw IQ converts *directly* into stories-that-would-otherwise-
never-exist — so **Fable 5 on the synthesis call is the plan**, the one place we
break from the house Sonnet default.

**Settle it with data, not this argument:** make the synthesis model an env var
(like `DIRECTOR_MODEL`), run one ambient pass each through Sonnet and Fable,
read the two lead-lists side by side; the `agent_decisions` cost spine prices
them automatically. At pennies per pass, let lead *quality* decide. If Sonnet's
leads are as good, you've saved nothing worth measuring and kept it simpler.

**Caveat to handle if Fable:** always-on thinking (minutes-long turns — fine for
ambient work) and a safety-refusal classifier. Neither bites here
(story-prospecting isn't cyber/bio), but wire the same `stop_reason: "refusal"`
handling the Director needs, and consider a server-side fallback to Opus 4.8.

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

## Writer, in detail — and the voice bottle

The Writer is the content agent choosing a **voice profile** per assignment.
Critical correction to the first-pass plan: *harvest is not enough.* The
commit/devlog/ledger corpus is **one** voice (terse, epigrammatic,
receipts-forward). The voice wanted for a note, a marketing headline, or a
future surface may not exist anywhere to harvest — **you cannot mine a voice
the box has never spoken.**

So the bottle is not one jar — it is **voice profiles**, each drawing from two
wells:
- **Harvested** exemplars, where the voice is already demonstrated (→ an
  "operator's log" profile from commits/devlog/ledger).
- **Seeded** exemplars, where the voice is *aspirational* — samples the
  operator drops in, or that are drafted and operator-approved, for a register
  nothing has written yet.

**Mechanism = convention-path drop** (matching `data/ask/<slug>.md` and
`img/notes/<slug>.*`): a `voice/<profile>/` holding `samples/` (exemplars,
harvested or seeded) and a short `moves.md` (the named-move list). The Writer
picks a profile per assignment; a new voice is authored by dropping samples,
no code. Caution from the operator's standing rule: **samples carry the voice;
name the moves sparingly** — over-specifying moves in-prompt deadens them, the
exemplars do the real work. Bottle **per register**: apex notes run man-page
dry (the codified register exception), commits epigrammatic, blog narrative —
one house, three volumes.

Voice attribution, for the label on the bottle: the register is a
*collaboration* — model provides phrasing, operator provides discipline
(name-the-move, receipts-before-rhyme, honesty-as-posture, log-don't-edit),
the box provides material. None alone writes like this — which is *why* it must
be bottled: "the current model on a good night" is not a durable dependency,
and this operation swaps model brains routinely.

**The bootstrap is not the process (operator, 2026-07-18).** The first
story's cycle — four Writer runs, live voice calibration, an Editor splice —
was *voice refinement*, not the standing workflow: each hand-tuned draft
exists to enrich the bottle (moves named, exemplars banked) precisely so the
next story needs less of it. Steady state is one Writer draft against a
matured bottle, a light Editor pass, approve. Judge pipeline maturity by the
trend in hands-on minutes per story, not by the first story's cost.

## Marketer & Editor — mostly already here

- **Marketer:** unchanged, and stays **dedicated to the Ghost blog** (see
  "Reuse vs fork"). Its extraction *technique* is what the Scout reuses via a
  shared lib — **not** the marketer agent itself, which bakes in a
  Ghost-authoritative canonical model. (Per-surface SEO assignment resolved
  2026-08-03 — the Writer holds the notes' per-item text; a "newsroom
  marketer" seat opens when the notes corpus earns a link graph. See [seo-duties.md](seo-duties.md).)
- **Editor:** operator today → the Director's designed weekly editorial pass.
  **Topology settled 2026-07-18: the triage half of that pass is a hired
  desk, the Wire Editor** (publishing-automation-plan.md Phase 2) — reads
  the ledger, proposes claim/spike/register shortlists; operator applies via
  `lead_mark`; Director stays Editor-in-chief and its morning brief stays an
  ops organ (at most a one-line queue stat, never pitches — the two hats
  are different altitudes and must not re-conflate). **The Editor-in-chief
  shadows gate ① from day one** — suggested verdicts alongside the Wire
  Editor's proposals, operator disposes; concordance over real cycles is
  the maturity metric that eventually hands the Director the routing pen
  (plan doc §Gate-① shadow mode). Gate ② — scrub + approval to publish —
  is the operator's permanently.
  The routing desk's ledger turned out to be the Scout's leads file
  (`pipelines/scout/state/leads.yaml`; lifecycle since 2026-07-18:
  `new → claimed → drafted → approved → published`, `spiked` from
  new|claimed, **`rejected` from drafted** (added 2026-08-03 — until then there
  was no verdict for "the draft isn't good enough", so the review desk's
  thumbs-down emitted an illegal transition and was refused every time;
  `spiked` and `rejected` stay distinct because only the second is a signal
  about the *Writer*, and that is the metric that says whether the voice bottle
  is maturing), all transitions via the `lead_mark` verb with dated stamps —
  publishing-automation-plan.md Phase 1) —
  the build chose the ledger pattern over the survey's `featured:` field, which
  stays the *marketing-promotion* queue, a different desk. Producer-vs-
  orchestrator stays intact: Scout and Writer are producers (Agent SDK, like
  their siblings); the Director approves and routes but never writes.

## Content types = the Editor's routing dimension

Sinks aren't interchangeable — each content *type* carries its own {purpose,
canonical model, voice, audience}. **This taxonomy IS the Editor's routing
table (its rows)**, and it's the axis the reuse-vs-fork principle scales
across: a new type is a new **sink profile** (canonical + voice + corpus)
plugged into the shared mechanics — never a new agent. This is *why* we forked
the ghost crew off rather than genericizing it: content types diverge, the
extraction technique doesn't.

| Type | Primarily for | Sink / canonical | Voice | Audience |
|---|---|---|---|---|
| **Ticker** | the box's *activity*, in verbs — a rolling pulse under the header | site-wide masthead (fixed second row, since 2026-07-19; was apex-home), generate-time text pack | terse verb crawl | everyone — "running right now" |
| **Weekly newsletter** | the Director's weekly report, made public — the week's digest | apex `/newsletter/`, self-canonical | newspaper broadsheet | prospects / followers |
| **Field notes** | the ecosystem's **self-awareness** (4C / platform-is-the-product); war stories second | apex `/notes/`, self-canonical | man-page dry | prospects — "see the receipts" |
| **Blog** | predictor-ingest commit history; grows by **subfolders** (Ghost = one instance, one blog) | Ghost, Ghost-canonical | narrative | developers / followers |
| **White papers / case studies** | deep, rigorous technical proof | *unplaced — future sink* | formal / technical | evaluators / decision-makers |

Two guardrails:
- **Field notes are self-awareness first, war-stories second** — but that lens
  is a *routing* filter the **Editor** applies, NOT a discovery filter the
  Scout applies. The Scout walks wide; the Editor sorts by type. Per-sink
  lenses narrow *routing*, never *prospecting* (the pineapple rule again).
- **White papers are genuinely different** — audience AND depth, not just
  voice. Sink unplaced (apex `/papers/` via generate.js? Ghost? its own
  thing?), deliberately unsolved for now.
- **Field-note shape (Editor's standing order, 2026-07-16, set while routing
  the first story through the Writer):** three beats — the problem, the
  solution, the lessons learned — one screen, with a Clemens lean: wit
  wherever it crystallizes a fact, engaging and factual at once (the
  Kodiak-diary measure — riveting *because* every detail is true).
  Receipts stay; play-by-play goes. Long-form depth is the blog leg's job
  (a retelling that links back to the note), so detail is banked, not lost.
  **Amended 2026-08-13 — the blog leg is a DEEP DIVE, not a retelling**
  (self-canonical and indexed; see [seo-duties.md](seo-duties.md) for why the word mattered), and
  the standing order now carries a number: **a note's body caps at ~840
  characters** — three tweets, a captain's log — with the `deepDive` link
  **mandatory**, not optional. The cap *quantifies this 2026-07-16 order*
  rather than replacing it: "one screen" and "long-form is the blog leg's job"
  already said it, and the drafts had drifted to 3-4× anyway. A note that wants
  a table is not a note — the schema escapes all values, so furniture cannot
  render, which is a feature that keeps the generator decision-free. The two
  live notes predate the cap and are grandfathered until trimmed. Contract in
  SEO.md §The field-note contract.
  **Amended 2026-07-17** (from reviewing an external rewrite of the first
  published note — its scannability was right, its stripped receipts were
  not): a note may open with a **Quick-context block** — a `context` field
  citing keys in the shared lexicon (`marketing/data/lexicon.json`, one
  canonical definition per house term); the generator renders only the
  cited terms, and notes without the field render unchanged, so published
  pages stay frozen. Enumerable receipts (commits, read histories, fix
  steps) render as list body entries (`{"list": []}` / `{"numbered": []}`)
  carrying the full receipt — scannability never at the receipts' expense.
  Receipts remain non-negotiable; the published copy of a stamped note is
  never retro-edited — shape improvements fold forward into the next note.

## Editorial rules — the cadence, the ticker filter, the three registers

The three apex content types form **a real newsroom's cadence**, by durability:
**ticker** = the pulse (near-real-time), **newsletter** = the weekly edition
(digest), **field notes** = the features (event-driven, durable). Pulse →
digest → feature. All three draw from the same source (the box narrating
itself); they differ by cadence, register, and durability — three sink
profiles, one set of mechanics.

**Day-job-derived material — technique-forward, application-anonymous
(operator, 2026-07-18).** The ingested work-machine sessions are legitimate
ore, and their stories publish under one hard rule on top of the usual
scrub + Editor approval: the employer's application is never named,
described, or identifiable. What publishes is the *method* arc —
spreadsheet-to-archetypes, feature-to-technique mapping, agentic API
discovery, plain-language-to-test — which the operator judges tellable
compellingly with zero application specifics. Employer confidentiality is
a distinct gate from credential/PII redaction; a lead can pass the scrub
and still fail this. The Editor applies it at routing time.

**All generator-native, not Ghost.** The newsletter and ticker are built the
same way as field notes (data → generate.js → index + page-per-entry), NOT in
Ghost. Ghost stays the narrative-blog sink. Embedding Ghost content into the
static generator would couple it to a live CMS API and break the
zero-dependency / git-is-truth model — the clumsy shoehorn to avoid. (If the
newsletter is ever *emailed* to subscribers, that's a delivery leg — Ghost or a
relay — not a reason to move the content's home into Ghost.)

**The ticker — "live" is euphemistic; it's a text pack compiled on generate.**
**(v1 SHIPPED 2026-07-19 — home-hero crawl, all running non-hidden survey
nodes in survey order, deliberately deterministic: a random sample would
break the CI regenerate-diff gate, so "rotation" arrives when the survey
re-walks. Pure CSS marquee, hover-pause, reduced-motion fallback. The
dedicated ticker table below remains the open v2 question.)**
No real-time infra: a rolling set of recent items refreshed on each regenerate
(driven by a cron) is indistinguishable from "live" for a crawl. **v1 source: a
rotating sample of the inventory** (the survey — already generated, so *zero new
plumbing*). That's a *status pulse* (what's on the box, live/paused) rather than
*activity verbs* (what happened); both are legit ticker registers, and the
status pulse directly animates the hero's "running right now." Activity-verb
feeds (`agent_decisions`, git) come later. Sample and rotate — don't crawl all
55; a fresh handful per regenerate keeps it varied and the pack small. Editorial
rules, which are what keep it honest:
- **Verbs, not victories.** Each item is a punchy, tip-length line — a success
  blurb, a process, or a **method verb** ("Regenerated the site," "Ran the
  weekly backup," "Shipped two cut sheets"). Process/method verbs are
  load-bearing; pure wins are seasoning. The moment it crows, it's dead and
  reads as spin.
- **Challenges enter only as their resolution-verb, linking to the full note.**
  A bare "backups are not working" reads as a live alarm and strips the context
  that makes it honest. So a challenge never appears raw — it appears as the
  action taken, with depth one tap away: *"Made backup silence page a phone →
  read the field note."* The ticker is the pulse; the notes carry the
  warts-and-all truth; together they're honest, and the ticker points to the
  depth rather than pretending it doesn't exist. This is the guardrail against
  an all-wins ticker smelling like spin.

**The newsletter — the Director's weekly report, made public.** It IS the
already-designed weekly editorial pass (devlog: "compile the week from the
accumulated harvest → synthesize → route"), just wearing a public face.
- **Newspaper broadsheet look**, but **responsive**: two columns on wide
  screens, collapsing to one on mobile (we live on the phone). Keep the
  masthead, headline hierarchy, and hairline rules; let the columns flex.
- **Editor tuned to newspaper-style headlines** — a voice profile: active
  voice, present tense, punchy head with a deck underneath. Seed it with real
  newspaper-headline exemplars (per the voice-bottle: samples carry the voice).

**Three registers as a system:** ticker = terse verb crawl, newsletter =
newspaper editorial, field notes = man-page technical. Not three formats that
happen to coexist — the *visual range of an actual newsroom*, which makes the
metaphor real instead of decorative.

**House wit rule (operator, 2026-07-17) — every content type except the
ticker.** When composing, stay on the lookout for sharp, clever wit —
opportunistic, never a requirement, never forced when the material doesn't
offer it. The measure stays the Clemens lean / Kodiak diary (wit that
crystallizes a fact); this rule extends it from the field-note register to
the whole house — newsletter, blog, notes, papers — the ticker alone stays
pure verb crawl. Provenance worth keeping: the snark in an external rewrite
of the first note ("Revolutionary, we know") traced back to an explicit
"add some gen-Z comments" instruction — well executed, wrong ask.
Commissioned wit produces snark; opportunistic wit produces the Clemens
lean. Never instruct a writer to *add* wit — instruct it to *watch for* it.

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
- Synthesis-stage model: **A/B underway** — week 1 (07-13..19) on Fable 5,
  week 2 on Sonnet 5 (`SCOUT_SYNTHESIS_MODEL` flip, calendar TODO), side-by-side
  readout due 07-26; the Editor judges, not the contestant (see "Model tiers").
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
