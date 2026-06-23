# Prompt Tuning Notes — Uzelhub Crew

A running log of Blog Director feedback on agent output. The point is to collect several observations before iterating prompts, so changes are informed by patterns rather than single drafts.

Each entry: what the agent did, whether to keep or change, and a description of the underlying voice/structure that produced it. The descriptions are deliberately non-evaluative — we're characterizing what's there so we can name it in prompts.

---

## Guiding principles (read before tuning)

These shape how feedback below should be interpreted.

- **The mission is to narrate the technical story.** Voice serves that, not the other way around. Essayistic openings are valued because they earn the technical material, not because we're trying to write essays.
- **Some posts need a didactic voice.** Walkthroughs, explainers, "how this works" pieces — they call for instruction-mode. The agent should choose register based on what the commits are actually telling, not default to one mode.
- **Story is the through-line for both registers.** Technical or non-technical, people remember stories. A didactic post can still have a narrative arc — what was tried, what failed, what the fix revealed. The thing to avoid is reference-manual prose: a list of facts with no question being answered and no protagonist (even if the protagonist is an idea).

### Why we log here instead of editing the prompt

This is the operating principle for *when* to tune, not just *what* to tune.

- **The good output came from the current prompt.** When something works, the prompt is already capable of producing it. The instinct to immediately codify "do more of that" is exactly how prompts bloat. The text we're praising is *evidence the prompt works as written*, not a problem to solve.
- **Verify across samples before naming a pattern.** One great opening could be a fluke of a particularly story-rich commit batch. Two or three across different batches is a pattern. The log accumulates samples; tuning waits for patterns.
- **Bloat deadens the very things we're trying to preserve.** Adding "remember to be taxonomic, deliver values through binaries, use a general → bridge → invitation shape" to the prompt would make those moves performative the moment they appeared. The agent loses the *noticing* that produced them.
- **This is more art than science.** Judgment calls — "is this a pattern yet?", "would naming this in the prompt help or freeze it?" — don't reduce to a checklist. The log is what makes the judgment possible.

---

## #1 — Opening paragraphs (KEEP)

**Source:** First successful single-batch run, 2026-04-25. Slug: `contract-first-pipeline-design-predictor-ingest-schema`.

**Excerpt:**

> There's a particular kind of discipline in software projects that's easy to describe and hard to practice: defining what your output looks like before you write the code that produces it. Most pipelines get built the other way — you fetch some data, see what comes back, and gradually calcify whatever shape it took into your data model. The schema becomes an artifact of history rather than an expression of intent.
>
> The first week of `predictor_ingest` went the other way. And looking at the commit sequence, it's worth understanding why.
>
> ## What This Thing Is

**Description of what this opening is doing:**

- Opens on a *practiced human experience*, not a technical setup. "Easy to describe and hard to practice" is something anyone has lived through — not just engineers. The reader is positioned as a peer who already knows this feeling, not as a student being taught.
- The thesis is delivered as observation, not argument. No "I'll show you why X" framing. The narrator just notices something and names it. This is closer to essayistic tech writing (long-form journalism, Gawande, Paul Graham) than to dev-blog or tutorial register.
- Establishes a contrast structure before the technical material arrives: there's a norm ("most pipelines get built the other way"), and then the specific project deviates from it. The reader is set up to look for the deviation.
- Word choice carries weight without flagging itself. "Calcify" is a precise metaphor — biological, slow, slightly unwelcome. "Artifact of history rather than an expression of intent" is a clean abstract pair. None of these phrases are reaching.
- The project name (`predictor_ingest`) drops in casually, possessively, without ceremony. The reader is treated as already knowing it matters, which is more inviting than introducing it formally.
- The transition to technical content ("And looking at the commit sequence, it's worth understanding why") is invitational — *come look with me* — rather than instructional.

**Three structural moves to name (these are the reproducible parts, not surface aesthetics):**

1. **Taxonomic essayistic.** Not "a discipline" but "*a particular kind of* discipline." The narrator names categories — they've thought about the work enough to type-classify it. That's what makes the voice feel earned. The pattern: notice something, then signal that you have a category for it before you describe the instance. This is the move underneath what reads as "essayistic register."

2. **Values delivered through binaries.** "An artifact of history rather than an expression of intent" is a *statement of values*, not just nice prose. The writer says what they think is good. Readers trust voices that do this; they distrust voices that only describe. The pattern: when introducing a contrast, make the second half normative (what *should* be) rather than just descriptive.

3. **Macro-shape: general → bridge → invitation → section header.** The first paragraph names no project at all — it's pure category-level observation. The second paragraph pivots in one sentence ("The first week of `predictor_ingest` went the other way") and invites in the next ("And looking at the commit sequence, it's worth understanding why"). Then the section header arrives. The shape is what lets the technical material land without ceremony — by the time the project is named, the reader is already inside the question.

**Why it works:**
The opening earns the technical material by establishing human stakes first. The reader isn't shown code or jargon until they've already agreed there's something interesting to investigate. Tech people are still people; this register acknowledges that without dumbing the content down.

**Implication for the prompt:**
The Content agent's existing `CONTENT_SYSTEM_PROMPT` is already producing this register. Whatever combination of "precise but not sterile / playful but not flippant / honest about process" plus the audience description is making it land. Don't perturb the opening guidance until we've seen if other parts of the post hold the same register.

---

## #2 — Mermaid diagram self-selection (LOG, sample 1 of N)

**Source:** Second batch run, 2026-04-26. Slug: `building-llm-extraction-layer-schema-contract`. First post emitted under the **Path 3 nudge** (~25 tokens added to `CONTENT_SYSTEM_PROMPT` granting permission to use `flowchart TD` where structure would clarify; see "Backlog — diagram support" below).

**What the agent did:**

- Diagrammed the parse-and-validate flow specifically: `A[LLM Response String] → B{Contains markdown fences?} → ... → G[ExtractionError]`. Eight nodes, two decision diamonds, six process boxes, labeled edges (Yes/No, Valid JSON/Parse error, Pass/Fail), two arms converging on the error node.
- Did NOT diagram other parts of the post (the prose-driven sections about evidence requirements, prompt construction, dual-mode input, custom exception). Self-selected to skip rather than decorate.
- Stayed in TD as instructed; no drift to LR or sequence.
- Used semantically appropriate node shapes — `{}` for decisions, `[]` for transformations.

**Three structural moves to name (the reproducible parts, not the surface fact that "it drew a diagram"):**

1. **Selected for branching topology.** The diagrammed section is the one place in the post where the prose has to describe a flow that branches and reconverges. The agent picked exactly that — not the sections where prose handles linear reasoning fine. This is the right discrimination: diagram what prose obscures, not what prose handles.
2. **Used node shape as semantic signal, not decoration.** Diamonds for choice points, rectangles for state transitions. The shapes carry meaning; a reader scanning the diagram learns the type-distinction without reading every label. This is what makes the diagram add information rather than restate prose.
3. **Self-restricted scope.** Eight nodes, one diagram, one post. The agent did not also diagram the test-coverage section (it could have — there are categories and edges) or the dual-mode input (it could have — there are two arms). It picked the *most* structural moment and stopped. The not-diagramming is as load-bearing as the diagramming.

**What this evidences (and what it doesn't):**

- The Path 3 hypothesis ("Sonnet self-selects intelligently when given permission") is **supported by this sample**. Not yet a confirmed pattern.
- Syntax was clean on first try — parsed by mermaid v11 with no warnings or red error boxes.
- TD was honored without re-prompting.

**Caveats:**

- One sample. Need at least two more before calling Path 3 a pattern. Specifically watching: over-eager diagramming (>60% of posts), drift to LR/sequence/etc., diagrams that decorate without informing, bad-syntax errors.
- Render-side: the diagram spans two screen-heights in Ghost's reading column. TD's cost is vertical scroll. The trade-off plays out as: TD = scroll (preferred — labels stay readable), LR = compressed labels on narrow viewports (with default `useMaxWidth: true`). If LR is ever needed, mitigation is `useMaxWidth: false` + `overflow-x: auto` wrapper — untested, hypothesis-only.

**Implication for the prompt:**
Leave the nudge as-is. Accumulate two to three more samples across batches with different topologies (a state machine, a pipeline with parallelism, a post with no structural moment) before doing anything. Do **not** codify "diagram structural moments" further — the noticing is currently organic and naming the rule more specifically would push it toward performance.

---

## Backlog — corpus-level analysis (Sprint One+)

After the first full backlog crawl produces ~20–50 raw drafts, run two corpus-level analyses as part of the **batch intake** step (alongside the existing internal-link candidate ranking):

1. **Story-arc classification.** Tag each draft with the kind of arc it tells (e.g. *problem → diagnosis → fix*, *constraint → design choice → consequence*, *attempt → failure → pivot*, *walkthrough → revealed insight*). Pairs with the "guiding principles" above — gives us a way to see which arcs the Content agent is finding naturally and which it's missing.
2. **Internal-link candidate ranking** (already planned, currently passes `candidates=[]`). Wire the cohesion-graph descriptors into a ranking call so the marketer can pick relevant prior posts.

Both belong in the intake step because they need the full corpus to be useful, and they share the same descriptor data. Doing them together avoids two passes over the corpus.

---

## Backlog — diagram support (mermaid)

A technical blog without diagrams is subpar. The question is how to add them without bloating the Content agent's prompt or deadening its organic judgment. Three paths, recommended order: try #3 first, escalate to #2 if data warrants, never do #1.

### Path 1 — Heavy addition to Content agent prompt (REJECTED)

Add 200-400 tokens of mermaid syntax + when-to-draw guidance + format constraints + accessibility rules directly to `CONTENT_SYSTEM_PROMPT`. Charges every Content call for a feature most posts won't use; once "draw a diagram when structure exists" is in the prompt, the agent will start finding "structure" everywhere (the noticing-deadens-when-named pattern). Don't do this.

### Path 2 — Separate Diagrammer agent (Sprint One+ if needed)

A new agent that runs after the Content agent on the finished draft. Its prompt is *only* about diagram judgment + mermaid syntax + TD-with-subgraph constraints + accessibility description. Content agent prompt stays untouched. Probably Haiku — structure-detection from finished prose is more constrained than prose generation.

Properties: composable, tunable independently, kill-switchable, doesn't compete for token budget with voice guidance. This is the architecturally correct answer for an agent crew. Build only if Path 3 shows the model needs a dedicated judgment layer.

### Path 3 — Minimal nudge experiment (Sprint Zero, after backlog crawl)

Add ~25 tokens to `CONTENT_SYSTEM_PROMPT`:

> Where structure would clarify, you may include a mermaid diagram in `flowchart TD` format.

Sonnet already knows mermaid syntax. The hypothesis: the model self-selects intelligently when given permission. Run on a handful of batches, evaluate:
- Does it diagram the right posts (structural ones) and skip the prose-driven ones?
- Is the syntax clean (no red error boxes)?
- Does it stay within TD or drift to LR/sequence/etc.?
- Does the diagram add information or just decorate?

If yes across the board, this is the answer. If it over-uses or produces noise, the data justifies Path 2.

### Shared infrastructure (needed for any path)

These are real-but-solvable problems regardless of which path we pick:

- **Rendering.** Ghost doesn't render mermaid natively. Lowest-friction route: load mermaid JS site-wide via Ghost's global code injection, agent emits `<pre class="mermaid">…</pre>` blocks. Per-post cost is just the JS already-cached on second load.
- **Verifiability.** Syntax errors render as red error boxes in production. For a first pass, the Blog Director catches them in Ghost review (it's already a checklist item). Pre-flight rendering (mermaid-cli or headless Chromium) is a Sprint One+ option if errors prove common.
- **Body conversion.** The current `_body_to_html` is paragraph-only. Whatever markdown→HTML upgrade we do has to preserve fenced code blocks (mermaid blocks live inside ```` ```mermaid ```` fences in markdown).
- **Accessibility.** A bare mermaid block has no alt text. Brief prose description above or below the diagram. In Path 2/3, this is part of the agent's instruction.

### Decision criteria

Move from Path 3 to Path 2 if the nudge experiment shows any of:
- Diagrams appearing on >60% of posts (over-eager)
- Syntax errors on >10% of attempts
- Diagrams that add no information (decorative)
- Inability to stay in TD when prompted to
