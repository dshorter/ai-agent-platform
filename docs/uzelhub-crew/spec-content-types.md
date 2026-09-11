---
read: full
status: CURRENT SPEC, rewritable — type/shape rules, with the operator's independent destination policy added 2026-09-09. Destination recommendation/override wiring is pending NR-09 in NEWSROOM-WORKPLAN.md. Supersedes NEWSROOM.md §Content types and §Editorial rules for day-to-day reading. Where SEO.md states policy, SEO.md wins and this repeats it. No corrections stack here; edit in place and date the commit.
---

# Content types — the Editor's routing table

<!-- MAP:START -->
- [The table](#the-table)
- [Content type and destination](#content-type-and-destination)
- [Rules that cross all types](#rules-that-cross-all-types)
- [Shape, per type](#shape-per-type)
- [What each desk does with the type](#what-each-desk-does-with-the-type)
<!-- MAP:END -->

Five types. A piece has exactly one. The Editor confirms or overrides the
proposed type at gate ①; this does not select its syndication destinations.
The Scout labels a lead with the type it would become and never goes looking
for one (the pineapple rule). A new type is a new row here plus a voice
profile and a sink, never a new agent.

## The table

| type | for | own-site sink and canonical | register (voice profile) | audience |
|---|---|---|---|---|
| **ticker** | the box's activity, in verbs; a rolling pulse | the site-wide masthead, a text pack compiled at generate time; v1 source is the survey | terse verb crawl (no profile; a pitch is most of a line) | everyone |
| **newsletter** | the week's digest: the Director's weekly report made public | apex /newsletter/, self-canonical, generator-native | newspaper broadsheet (profile to be seeded; nothing on the box has spoken it) | prospects, followers |
| **note** | field notes: the platform's self-awareness first, war stories second | apex /notes/, self-canonical; data/notes.json rendered by generate.js | man-page dry (profile man-page-dry, harvested) | prospects who want receipts |
| **blog** | narrative for developers; deep dives; the predictor commit-history blog | Ghost, Ghost-canonical, grows by subfolders | narrative (harvested from published posts only) | developers, followers |
| **paper** | a white paper or case study: deep, rigorous technical proof | unplaced, deliberately | formal, technical | evaluators, decision-makers |

## Content type and destination

**Operator decision, 2026-09-09:** content type and syndication destination
are independent. Type governs the editorial form, voice and creation/rendering
requirements. A destination is where an approved piece is delivered. The
own-site sink table above does not prohibit any type from external syndication.

Retain the Scout's recommendation with human override: it proposes the type
and destination set separately; the operator accepts or changes them at gate
①. Preserve the proposal and the operator's chosen values independently.
The Wire Editor may advise; its proposal does not erase either attribution.
Operator overrides remain downstream of the Scout's taste firewall.

A field note remains a field note on DEV or Hashnode. A longer article can go
to the same destinations. A piece does not need to be expanded, relabeled or
given a companion of another type to qualify for syndication. Existing adapter
coverage is an implementation fact, never a hard type-to-destination policy.

Destination packaging may adapt formatting and supported metadata. It must
preserve the approved claims and voice; substantive variants must be covered
by gate ②. A real platform constraint is reported explicitly, with the affected
delivery unresolved until handled, never silently dropped or called complete.
Each syndicated copy identifies the piece's actual original under SEO.md.

**Implementation gap:** the inspected Scout output and lead store record type,
but no separate destination recommendation. Wiring that recommendation, human
override and the independent delivery path is NR-09 in NEWSROOM-WORKPLAN.md.
This policy does not claim those paths already work, or require every unbuilt
content-creation path to exist before the first MVP.

## Rules that cross all types

- **One canonical home per story.** A note is apex-canonical and complete on
  its own. A blog piece is either a deep dive (distinct intent,
  self-canonical, indexed) or, rarely, a retelling with canonical back to the
  note.
- **Apex types are generator-native.** Ticker, newsletter and notes are data
  rendered by generate.js. Ghost is only the blog's sink. No agent touches
  HTML.
- **Redaction and gate ②.** Nothing derived from a session log publishes
  without a hard secret and PII scrub and the Editor's approval, whatever the
  type.
- **Employer gate.** Day-job material publishes technique-forward and
  application-anonymous. Applied at routing; a lead can pass the scrub and
  still fail this.
- **Wit is watched for, never added**, in every type except the ticker. The
  Clemens lean, measured by the Kodiak test: wit that crystallizes a fact.
  Never instruct a writer to add it.
- **Cadence** (SEO.md §Cadence): notes at one or two a week with a three-day
  minimum gap, enforced by release.js. The ticker rolls on each regenerate.
  The newsletter is weekly.
- **Dates.** On the apex, `published` is the real release day, stamped by
  release.js, never backdated. The blog corpus is deliberately backdated and
  bans wall-clock words.

## Shape, per type

**ticker.** One tip-length line with a verb: "Regenerated the site." Verbs,
not victories; the moment it crows it is dead. A challenge appears only as
its resolution verb, linking to the note that carries the truth. Pure verb
crawl, no wit.

**newsletter.** Headline, deck, digest item, in newspaper voice: active,
present tense. Two columns wide, one on a phone. Waits on the Director's
weekly pass and a seeded profile.

**note.** SEO.md §The field-note contract is the authority.
- Three beats: the problem, the solution, the lessons learned. One screen.
- Body 840 characters ±5 percent (798 to 882), sections plus bullets,
  enforced by release.js. The tolerance is slack, not a target.
- Enumerable receipts (commits, read histories, fix steps) go in list
  entries carrying the full receipt, never buried in a sentence.
- An optional Quick-context block cites at most four keys from
  marketing/data/lexicon.json; a term not in the lexicon is introduced
  inline.
- Title, tagline and metaDescription are required, written in register, and
  held by the Writer.
- `deepDive` is opportunistic. Link a blog deep dive when one exists, and
  publish the deep dive first so the button never 404s. A note without one
  is complete.
- A note that wants a table is not a note; the schema escapes every value.

**blog.** 600 to 1,200 words: the story behind the commits, the decision,
what was learned, what changed and why. Perfect tense, no "this week". A
mermaid flowchart only where prose would obscure structure. Per-item text and
packaging belong to the Marketer agent. A deep dive is self-canonical and
indexed; it never points its canonical back at the note.

**paper.** Not written by anyone yet. What the Scout may pitch is an abstract
with references: a claim rigorous enough to defend, plus the pointers that
would evidence it. The Writer has no paper path. The sink stays unplaced
until one is chosen.

## What each desk does with the type

| | Scout | Wire Editor | Writer |
|---|---|---|---|
| ticker | pitches | claims, spikes, holds | no desk yet; a claimed pitch may be the line |
| newsletter | pitches | same | no desk yet |
| note | pitches | same | drafts, profile man-page-dry |
| blog | pitches | same | the content agent, its own path to Ghost |
| paper | pitches an abstract | same | none |

Five words in the Scout's vocabulary, five in the Wire Editor's, one in the
Writer's. Adding a Writer path is a row in the type-to-profile map plus a
profile directory, not new code.
