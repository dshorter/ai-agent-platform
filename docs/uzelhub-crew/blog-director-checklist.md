# Blog Director's Review Checklist — Uzelhub Crew Drafts

A short list of *attentions* the Blog Director runs through when reviewing a draft in Ghost. Not gates. Not a rubric to score. Notice what's there and log notable moments to [prompt-tuning.md](prompt-tuning.md).

The agent's prompt holds **principles** (durable: voice, audience, craft). This checklist holds **attentions** (per-draft: what stood out, what was missed). Mixing them bloats the prompt.

---

## Per-draft attentions

Walk through these in order. Spend ~30 seconds on each unless something draws you in.

### 1. Voice — does it sound like Dan?

- Precise but not sterile. Playful but not flippant. Honest about process.
- Not: tutorial register, marketing register, AI-flavored hedge-speak.
- *Notable?* Log to prompt-tuning.md under voice — both wins and misses.

### 2. Story — did the agent find the actual narrative?

- Did it earn its arc? A walkthrough is fine if the commits are a walkthrough — but is there a question being answered, a tension being resolved, an idea being followed?
- Was there an arc *in the commits* the agent walked past? (E.g. an attempt → pivot, a constraint → consequence, a polish/delight moment, a problem → diagnosis → fix.)
- Examples of arcs to keep an eye out for — non-exhaustive, none privileged:
  - *attempt → failure → pivot*
  - *constraint → design choice → consequence*
  - *problem → diagnosis → fix*
  - *walkthrough → revealed insight*
  - *delight or polish moment* (per the predictor's own delight/polish docs)
- *Notable?* Log to prompt-tuning.md — name the arc shape if you can.

### 3. Human stake — does the opening earn the technical material?

- Does the reader have a reason to care before the jargon arrives?
- Tech people are still people. The opening doesn't have to be essayistic, but it does have to *invite*.
- *Notable?* Log a quote-and-description in prompt-tuning.md (see entry #1 for the format).

### 4. SEO surfaces — title, meta, tags, slug

- Title: 50–60 chars, leads with insight or problem, not the technology.
- Meta: 150–160 chars, summarizes the *core insight*, not just the topic.
- Tags: 3–5, mix of broad/specific/conceptual.
- Slug: readable, not a hash of the title.
- *Notable?* Log only if something is wrong systematically (e.g. titles always start with the technology).

### 5. Length and shape

- 600–1200 words is the target. Off by a lot? Worth noting.
- Does the structure (sections, transitions) match the content's natural rhythm, or feel imposed?

### 6. Sanity

- No leaked agent-internal text (e.g. NOTES FOR MARKETER, system prompt fragments).
- No hallucinated details about the project.
- Code blocks/identifiers match the actual repo.

### 7. Cross-sample — what's the same/different from prior drafts?

If a comparable artifact existed in earlier drafts (similar opening shape, similar diagram type, similar arc), name what's the same and what's different — and which structural move produces the variation. Don't analyze in a vacuum once samples exist. *Notable?* Log to prompt-tuning.md framed as a diff, not as a one-off.

---

## What to log, and where

**prompt-tuning.md** — anything that suggests a pattern across drafts: a voice register that worked, an arc the agent keeps missing, an opening shape that should be preserved. One entry per observation; reviewed periodically.

**Don't log** — single-draft idiosyncrasies that won't repeat. The point of logging is to find patterns, not to keep a per-post audit trail.

---

## Approve / iterate / discard

- **Approve** — moves to the published queue (drip throttle, Sprint One+).
- **Iterate** — request a redraft. If iterating because of a *prompt-level* issue (voice drift, missed arcs across many posts), tune the prompt instead of redrafting one post.
- **Discard** — the commits weren't a story worth telling. Filter the source batch in `commit_batcher.py` so we don't draft from this kind of input again.
