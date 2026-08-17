---
read: full
status: extracted from NEWSROOM.md 2026-08-16 (it was 729 lines and this section had become mostly pointer plus amendment history). Responsibility model only — policy lives in /opt/_host/SEO.md.
---

# SEO duties — a distributed concern, not a fourth agent

<!-- MAP:START -->
- [The five layers](#the-five-layers)
- [Who holds layer 2, per surface](#who-holds-layer-2-per-surface)
- [The unowned charter, and the guardrail](#the-unowned-charter-and-the-guardrail)
- [Deep dive vs retelling — say which branch](#deep-dive-vs-retelling--say-which-branch)
<!-- MAP:END -->

> **Leaf of [NEWSROOM.md](NEWSROOM.md)**, which holds the content architecture
> this sits inside. Policy — what the rules actually *are* — lives in
> **`/opt/_host/SEO.md`** (`read: full`). This doc answers *who owns which
> layer*; that one answers *what the layer says*. Where they disagree, SEO.md
> is right and this is stale.

> **Source of truth moved 2026-08-13.** SEO *decisions* now live in
> **`/opt/_host/SEO.md`** (`read: full`) — the two-host rule, indexing tiers,
> Ghost routing and tag policy, the field-note size contract, syndication
> canonicals. That doc exists because four surfaces were each deciding these
> independently and disagreeing. **This section keeps the responsibility model
> — who owns which layer — and points there for what the policy actually is.**
> Where the two disagree, SEO.md is right and this section is stale.

## The five layers

SEO is ~70% already owned; what's unowned is the strategic layer. **Five**
layers *(this line read "four" until 2026-08-13; the list below always had
five)*, only one of which is "descriptions on content":

1. **Structural / on-page** — canonical, OG, sitemap, robots, breadcrumbs, meta
   rendering. Already the deterministic `generate.js` layer (`d79daf7`).
   Automatic, decision-free, tested. ~~Solved.~~ **Amended 2026-08-13:
   *mostly* solved, which is a different claim.** An audit found `og:type`
   hardcoded `website` on notes (should be `article`), no `og:image` path ever
   exercised, and no RSS feed on the apex at all. The mechanism is sound; the
   coverage isn't complete. Live list in SEO.md §Fixture checklist.
2. **Per-item text** — title, meta description, tags. The marketer's job. The
   "same language" every piece normalizes to. Lowest-stakes, but its **uniform
   output contract is exactly what makes SEO factorable as a shared service.**
3. **Technical directives** — canonical placement, 301-vs-302, status codes.
   NOT descriptions; machine instructions; *highest*-stakes (a broken canonical
   or a 302-that-should-be-301 sinks a page regardless of copy — cf. the www
   defection and the atomic-flip constraint). Ownership: infra + Editor routing.
   **Policy owned by SEO.md since 2026-08-13** — indexing tiers, Ghost
   `routes.yaml` collections and the internal-vs-public tag split all landed
   here and were previously unowned in practice. Note the timing constraint:
   routes.yaml defines URLs, so the collection prefixes must be decided *before*
   the corpus publishes or it becomes a 301 migration across ~290 posts.
4. **Link graph** — internal links, topic clusters, anchor text. Relationships
   between pages (survey `see:` field + marketer `internal_links`). Grows into
   a real asset as the notes corpus accumulates.
5. **Off-page** — backlinks, Search Console submit/monitor. Currently manual
   operator aftercare; eventual Editor/Director duty. **Added 2026-08-13:**
   crawler access belongs here too and nobody owned it — a zone-level
   Cloudflare managed `robots.txt` is live on *both* hosts and disallows
   ClaudeBot, GPTBot, Google-Extended, CCBot and five others, with
   `Content-Signal: ai-train=no`. Neither generator knows it exists. Both
   properties are currently invisible to AI answer engines. Status in SEO.md.

## Who holds layer 2, per surface

*Resolved 2026-08-03; operator delegated "whichever is simpler".* "Per-item text — the marketer's job" above is a
ROLE statement, and it was getting read as an AGENT one — a conflation,
because the marketer *agent* is dedicated to the Ghost blog and bakes in a
Ghost-authoritative canonical model (NEWSROOM.md §Reuse vs fork) that inverts for apex
notes. The assignment, per surface:
- **Blog:** the marketer agent, unchanged.
- **Notes:** the **Writer** — already true in code, now stated as doctrine:
  title, tagline and metaDescription are REQUIRED fields of every draft
  (`tools/promote_draft.py` refuses without them), written in-register and
  reviewed at gate ② with the rest of the copy. Nothing to build.
- **The "newsroom marketer" seat is real but future.** Its first genuine
  duty is layer 4 — internal links / topic clusters over the notes corpus —
  which at two live notes has nothing to select from. *(Amended 2026-08-13:
  **that reason no longer holds.** The field-note contract makes `deepDive`
  mandatory, so a link graph now forms by construction rather than waiting on
  corpus volume. The seat may still be premature — but if it stays parked it
  should be parked for a current reason, not an outgrown one.)* Build it from the
  shared-lib mechanics (NEWSROOM.md §Reuse vs fork) once the corpus is big enough that
  link selection matters, not before (the batch-arc-finder rule: don't
  build it on spec). Pointing the blog marketer at both surfaces was
  considered and declined — retooling its canonical model per-sink is the
  *larger* structural change, not the smaller one it looks like.

## The unowned charter, and the guardrail

 the Editor is the SEO strategist,
because link-vs-copy routing *is* canonical placement. A content flywheel is a
cannibalization machine if unguarded, so: **every story has exactly one
canonical home** (notes apex-canonical and self-contained; a blog piece is
either distinct-intent or carries `rel=canonical` back to the note).

## Deep dive vs retelling — say which branch

*Amended 2026-08-13, because the fork was a trap.* That
sentence and the field-note standing order below (NEWSROOM.md §Content types) are each
correct and combine into a wrong outcome: one offers the fork, the other calls
the blog leg "a retelling," so anyone building the first long-form piece
canonicals it back to the note — and it never ranks, leaving the indexed tier
empty by construction. They are two different content types and must stop
sharing a word:

- **Deep dive** — the substance a field note is too small to hold.
  **Distinct-intent, self-canonical, indexed.** This is what a note's
  `deepDive` field points at, and it is the normal case.
- **Retelling** — the same story on a second surface. Carries `rel=canonical`
  back to the note, not indexed on its own. Rare, and mostly not wanted.

The note links *out*; the deep dive does **not** point its canonical back.
Full statement in SEO.md §Indexing policy.

