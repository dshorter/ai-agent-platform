---
read: reference
status: glossary, opened 2026-08-16 — the vocabulary was in use across 8 files and defined in none
---

# The voice bottle — glossary

Look terms up; nobody reads this front to back. The vocabulary below appears in
`bottle.py`, `writer_agent.py`, `writer-persona.md`, `NEWSROOM.md` and both
profiles' `moves.md`, and until now had no single definition. Where a term is
already used in one of those files, the definition here follows that usage
rather than inventing a better one.

---

**bottle** (the voice bottle) — the whole mechanism: `voice/<profile>/`
directories holding samples and a move list, loaded at runtime by
`pipelines/writer/bottle.py` and appended to the Writer's prompt. Named for
bottling a voice that would otherwise exist only as "the current model on a
good night," which is not a durable dependency in an operation that swaps model
brains routinely. The canonical framing, from `writer-persona.md`: *a voice
profile is not memory, it is wardrobe.*

**profile** — one named register, one directory. Today: `man-page-dry` (apex
field notes) and `doorway-warm` (hooks, excerpts, per-platform titles — bodies
never). A new profile is authored by dropping a directory. No code change.

**sample** — a file in `voice/<profile>/samples/`. A real piece of writing in
that voice. Samples carry the voice; this is the load-bearing claim of the
whole design.

**exemplar** — the same sample once it is inside the prompt. `bottle.py` renders
each as `EXEMPLAR n (filename) — study how it moves:`. Sample is the artifact on
disk, exemplar is its role at runtime; the words are otherwise interchangeable
and both appear in the codebase.

**move** — a named rhetorical technique: the dry verdict, receipts before rhyme,
breathe, smart stranger, the Clemens lean. Handles for discussion, not
instructions to follow.

**moves.md** — the per-profile list of moves, kept **deliberately thin**. The
standing rule is *samples carry the voice, name the moves sparingly.*

**deadened** — what happens to a move when it is described instead of shown. The
model then aims at the description and satisfies it every time, producing
something that reads as an attempt at the move rather than the move. A
description also cannot express *absence* — an exemplar shows the paragraphs
where the move did not fire, and that restraint is most of the craft. Receipt,
from NEWSROOM: the snark in an external rewrite of the first field note traced
to an explicit "add some gen-Z comments" instruction. **Commissioned wit
produces snark; opportunistic wit produces the Clemens lean. Never instruct a
writer to _add_ wit — instruct it to _watch for_ it.**

**the Clemens lean** — dry, Twain-grade wit, welcome wherever it crystallizes a
fact, never forced when the material does not offer it. Twain's *sensibility*
applied to the desk and the inbox, never his scenery: no steamboats, silt,
barns, frontier or blacksmiths unless the post is actually about one.

**the Kodiak measure** — the test for whether wit is earned. Someone who met a
mother Kodiak bear on a trail writes an entry that is riveting *because* every
detail is true. An aphorism rides on receipts; it never floats free of them.

**register** — the tonal band a surface writes in, fixed per content type:
ticker terse verb crawl, newsletter newspaper broadsheet, field notes man-page
dry, blog narrative. One house, several volumes.

**harvested / seeded** — the two origins of a sample. *Harvested* from writing
the box has already done (commits, devlog, ledger). *Seeded* where the voice is
aspirational and nothing has spoken it yet — the operator drops samples in, or
drafts are approved into the bottle. You cannot mine a voice the box has never
spoken.

**SHAPE** — the structural order, and it lives in the **prompt**
(`writer_agent.py`), not the bottle: three beats, one screen, receipts as lists.
Keeping shape in the prompt and voice in the bottle is the intended split.

---

## Three traps, all observed

**Samples outrank the prompt.** Where a sample and a written rule disagree, the
model follows the sample. A sample carries section count, paragraph rhythm and
total length whether or not anyone chose them. So SHAPE changes require
re-cutting every sample in the same commit — see the dated note at the top of
`man-page-dry/moves.md` for the three weeks this cost.

**One sample is a stencil, not a voice.** With a single exemplar there is
nothing to generalise across, so everything transfers — including where the wit
landed and how much of it there was, which turns opportunistic wit into a slot
to fill. Several samples that agree on structure and differ in rhythm give you
a chosen stencil for shape and a real voice for sentences. Include at least one
sample with no wit at all, or the model learns it is mandatory.

**An empty `samples/` directory hard-fails.** `bottle.py` raises
`FileNotFoundError` rather than running voiceless — a moves list alone deadens
the voice, so a profile without exemplars is refused. `doorway-warm/samples/`
is empty as of 2026-08-16 and cannot currently load.
