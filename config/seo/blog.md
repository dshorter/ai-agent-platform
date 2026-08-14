# SEO doctrine — sink: blog

Agent-facing extract. Loaded into the Marketer's system prompt at runtime by
`agents/seo_doctrine.py`; never hand-copied into a prompt string.

The human source of truth is `/opt/_host/SEO.md` (local to the box, not in this
repo). This file carries only the **operational rules an agent needs to do its
job** — no strategy, no indexing posture, no corpus reasoning. This repo is
public; a push is a publish.

Edit this file to change how the Marketer packages a post. No code change
required. A new sink is authored by dropping `config/seo/<sink>.md`.

## Canonical model

- This sink is **blog.uzelhub.com**, served by Ghost. It is its own canonical.
- The apex is **uzelhub.com**. It is a separate host and the authority host for
  the operation. Never describe the blog as living under a path on the apex —
  there is no `/blog` path there.
- Field notes on the apex are apex-canonical. A blog piece that retells a field
  note carries `rel=canonical` back to that note. A blog piece with its own
  distinct intent does not — it is self-canonical.
- Copies syndicated to third-party platforms declare the canonical of whichever
  host owns the original, never the platform's own URL.

## Titles

- 50-60 characters. This is measured, not a guess: the median title length
  across the top 40 posts by reactions on dev.to is 57.
- Lead with the problem or the insight — the opening words carry the hook.
- **Name the technology rather than talking around it.** A reader scanning a
  feed needs one concrete noun they already recognise to know the post is for
  them. Leading with the insight and naming the stack are not in tension; a
  title that does neither is the failure mode.
- No clickbait. This audience respects directness, and an inflated title is
  paid for on the next post.

## Meta descriptions

- 150-160 characters.
- Summarise the core insight, not the topic.
- A soft hook or call to action, never a hard sell.
- Write it; never let it be a truncation of the first paragraph.

## Tags

- **3-4 topic tags per post. Topic only.**
- Every public tag spawns its own archive page on the site. Few and reused
  beats many and unique — a tag applied to one post is an archive page with one
  entry on it.
- Do not emit audience tags, funnel tags, or status tags. If a tag would not
  make sense as the title of a page listing every post that carries it, it is
  not a tag.
- Prefer a tag that already exists in the corpus over a new near-synonym.

## Internal linking

- Link to prior posts in this corpus where a genuine relationship exists, and
  only from the ranked candidates supplied in the request. Never invent a slug.
- Anchor text describes the destination. Never "click here", never a bare URL.
- Zero links is a valid answer. A forced link is worse than none, and a link to
  a post that does not yet exist is a hard 404 for every reader who follows it.
