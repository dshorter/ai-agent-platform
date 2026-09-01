---
read: reference
status: snapshot taken 2026-09-01 — a dated state-of-play, NOT live state; re-derive before acting on any count
---

# Publishing pipeline — where it stands, 2026-09-01

Written on picking the pipeline back up after ~3 weeks. The style work that
occupied mid-August is **done**; nothing below is blocked on writing quality.
Counts verified against the live blog, `notes.json`, `site.json` and
`ops/calendar.ics` on the date above — they go stale, so re-derive.

## The one-line read

The pipeline is not waiting on build work. **The automated drip has been held
since 2026-07-18 (45 days), and the operation kept publishing through it by
hand** — one note, released manually 2026-08-15. So the cost of the hold is not
that nothing shipped; it is that shipping reverted to being rate-limited by one
person's attention, which is precisely what the drip exists to remove.

## Streams

| Stream | Host | Live | Contract rate | Held by |
| --- | --- | --- | --- | --- |
| Field notes | apex | 3 | 1–2 / week, 3-day min gap | identity profiles |
| Deep dives | blog | 1 | opportunistic — no fixed rate | *nothing* |
| Chapters | blog | 0 of ~25 | 2–3 / week over ~3 months | none written; `routes.yaml` |
| Corpus | blog | 0 of 270 | batch, published `noindex, follow` | `routes.yaml`, then the stamp |
| Syndication (dev.to) | dev.to | 0 | per released note | API key + profile URL |

## Two tracks, two gates

They are independent. Neither waits on the other, and treating them as one
queue is what made the whole thing look stuck.

### Track 1 — the apex note drip

**Gate: `identity-profiles-setup`** — operator, ~30 minutes, due 2026-09-02,
deferred once with the note *"it is the only real gate left on publishing."*

`marketing/data/site.json` → `identity.profiles` currently holds `github` and
three empty strings: `linkedin`, `x`, `devto`. Empty fields are
convention-gated (SEO.md §Syndication): they are omitted rather than emitted
blank, so the byline hub at `/about.html` presently points at one profile.
LinkedIn refresh comes first, then the bios point back at the apex.

This is upstream of lifting the hold (`resume-release-drip-post-sonnet`, due
2026-09-08) because a findable person behind the byline is what the drip is
*for*. Nothing else blocks the notes.

### Track 2 — the blog project (Option B)

**Gate: `routes.yaml`** — a decision, not a task, and the window is closing for
free.

SEO.md §Routing carries a PROPOSED tier-by-internal-tag / route-by-collection
config that has never been applied; Ghost is still on factory-default routes.
`routes.yaml` defines URLs, so changing it *after* the corpus ships is a 301
migration across ~290 posts. With one post live today it costs nothing.
**Decide before the first corpus publish, not after.**

Behind that gate, in order:

1. **Chapters — 0 of ~25 written.** These are the entire indexed layer of the
   blog project. Hand-written, nothing automated, and the corpus underneath is
   evidence they cite. No chapters means no indexed tier, which means the
   quarantine has nothing to pass equity to.
2. **The corpus stamp.** Mechanism now exists — `tools/corpus_quarantine.py`,
   dry-run verified 2026-09-01 against the live blog: 272 posts read, the 2
   indexed-tier posts excluded, 270 would be stamped, nothing written.
   Applying is a bulk Ghost write and therefore the operator's call. The tool
   cannot publish and cannot mail (no `status`, no `newsletter_id` in its
   payload); it only sets the quarantine posture.
3. **The clock.** It starts at *first publish*, not today. An unpublished
   corpus costs nothing; a permanently quarantined one loses the link equity it
   was published to pass upward. Months fine, indefinite not.

### Off to the side — syndication

`tools/devto_syndicate.py` has been built and committed since 2026-08-17 and
has never fired: no `DEVTO_API_KEY` in `.env`, no `profiles.devto` URL. It
reads the same version-controlled `content/blog/<slug>.html` that
`ghost_upsert.py` publishes. Cheap to switch on, and it needs volume to be
worth testing — which is Track 2's problem, not its own.

## Shipped 2026-09-01

Deck-clearing, so none of the above is waiting on housekeeping:

- **The redaction gate is diff-aware** (`9a5ce31`). It was blocking commits over
  content already in the public tree — the detector's own fixtures re-blocked
  their file every time a rule was added. The hook now compares against HEAD's
  copy of the same file and only blocks what the commit *adds*. Settles
  AGENTS.md's path-scoping open question without scoping dismissals.
- **Five parked changes committed**, all previously stuck behind that gate: the
  calendar-UID redaction fixtures, the Writer's reasoning trace, the Scout
  fallback model, the Ghost injection spacing fix, the Director ledger entry.
- **Sonnet 5 pricing corrected** (`706580e`). Anthropic made the $2/$10
  promotional rate permanent; `pricing.py` holds it with a comment against
  "restoring" $3/$15, and the reminder VEVENT is cancelled.
- **`corpus_quarantine.py`** built and tested (`d06a834`).
- **A ledger claim corrected, then the correction corrected** — see the
  2026-08-21 entry in `docs/director/director-ledger.md`.
