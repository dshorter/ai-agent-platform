---
read: full
status: CURRENT SPEC, rewritable — the rewrite desk as built (the note path) and as designed (the rest), as of 2026-09-06. For day-to-day reading it supersedes writer-persona.md; the persona stays as the voice of the design and its [OPEN] agenda.
---

# The Writer — current spec

<!-- MAP:START -->
- [The assignment](#the-assignment)
- [Voice: the bottle](#voice-the-bottle)
- [Shape, for a note](#shape-for-a-note)
- [Roam: convergent](#roam-convergent)
- [Redaction, and where drafts live](#redaction-and-where-drafts-live)
- [Lifecycle](#lifecycle)
- [Seat](#seat)
- [Never](#never)
- [State of the desk](#state-of-the-desk)
<!-- MAP:END -->

**Job.** A claimed lead in, a draft out. One lead, one piece, one type.
Stateless: every assignment starts cold. The only thing at the desk is the
voice bottle, and a profile is wardrobe, not memory.

## The assignment

A lead from the ledger with status claimed, or drafted for a redraft. Never
a raw idea (the Scout's), never a routing question (the Editor's), never
HTML (the generator's). A dry run rehearses on a lead of any status and
persists nothing. Verb: `python -m pipelines.writer --lead <id>`
(`--dry-run`; `--list` shows the claimed leads the note desk can draft).

The type selects everything else:

| type | path | profile | output |
|---|---|---|---|
| note | pipelines/writer | man-page-dry (harvested) | a notes.json-shaped entry: slug, kicker, date, title, tagline, metaDescription, bullets, optional image and context, sections, citations |
| blog | the content agent | narrative, harvested from published Ghost posts only | a titled post body plus notes for the Marketer |
| newsletter | not built | newspaper broadsheet, to be seeded | headline, deck, digest item |
| ticker | not built, perhaps never | none | a claimed pitch may already be the line |
| paper | none | formal | none; only the Scout's abstract exists |

The type-to-profile map is data, one row per built path. A new path is a
row plus a profile directory.

## Voice: the bottle

The Writer has no voice of its own. voice/<profile>/samples carry the voice;
moves.md is deliberately thin. Rules from voice/README.md that bind the desk:
- samples outrank the prompt, so a SHAPE change re-cuts every sample in the
  same commit;
- one sample is a stencil; keep several that agree on structure and differ
  in rhythm, at least one with no wit at all;
- an empty samples directory refuses to load, on purpose;
- wit is watched for, never commissioned.

## Shape, for a note

Lives in the prompt, not the bottle, and must equal spec-content-types.md
§note: three beats (problem, solution, lessons), one screen, body 840
characters ±5 percent, receipts as list entries carrying the full receipt,
at most four lexicon keys in context, title, tagline and metaDescription
required, `deepDive` only when a deep dive exists, no table.

## Roam: convergent

The same hands as the Scout (read_transcript, read_file, grep, run_git,
inside the registered roots), pointed the opposite way: pull exactly the
threads the lead cites until the draft can be written from receipts. Up to
`WRITER_ROAM_ITERATIONS` rounds (default 6; 9 was recommended after the
first story), tool output capped, then the draft is forced. Never invent a
detail, a date or a number; pull the thread further or write around it.
Tuning owed: name the roots in the prompt, and keep the drafts directory out
of the toolbox.

## Redaction, and where drafts live

Paraphrase and point; never reproduce secret material. A draft parks at
pipelines/writer/state/drafts/<lead-id>.json, gitignored, holding the
assignment, the citations, the roam trace, the reasoning summary when the
seat produced one, and a copyDraft stamp written by the pipeline, never by
the model. It crosses into uzelhub-web's notes.json only after the scrub and
the Editor's approval, through tools/promote_draft.py, which refuses a draft
without title, tagline and metaDescription.

## Lifecycle

The pipeline marks the lead drafted (by writer) when a draft lands. The
Editor approves or rejects; rejected is the one verdict that is feedback
about the Writer, and it is the bottle's maturity metric. Redrafts are
allowed from drafted. Publishing stamps published.

## Seat

Sonnet 5 (`WRITER_MODEL`), Opus 5 on refusal with one tool-less retry,
adaptive thinking with a summarized display, a 20,000-token output ceiling
with a truncation guard, `WRITER_MAX_COST_USD` default $2. Quality rides on
the exemplars, not on the seat.

## Never

Publish. Touch HTML. Route, second-guess the type, or spike an assignment
(flag misgivings in the handoff). Learn taste from verdicts. Write its own
stamp.

## State of the desk

Last ran 2026-07-31; 12 drafts on disk. It has not seen a git-anchored lead.
Open, from the persona: a send-back move; which well wins when a seeded and a
harvested sample disagree; the scrub pre-flight, a mechanical scan before
gate ②.
