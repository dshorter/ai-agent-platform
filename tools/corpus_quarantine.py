#!/usr/bin/env python3
"""Corpus quarantine — stamp (or lift) `noindex, follow` across the corpus.

The Option B publishing model (SEO.md §Indexing policy) puts ~25 hand-written
chapters in the index and publishes the ~266-post corpus underneath them
carrying:

    <meta name="robots" content="noindex, follow">

`follow` is not optional. The corpus passes link equity up to the chapters the
entire time it is quarantined, and that is the whole point of publishing it
rather than sitting on it. The flip to indexed later is `--lift`, which nulls
the same field in batches — no rewrite, no redirect, no migration.

    tools/corpus_quarantine.py                 # dry run: what would change
    tools/corpus_quarantine.py --apply         # stamp the meta tag
    tools/corpus_quarantine.py --lift          # dry run of the un-quarantine
    tools/corpus_quarantine.py --lift --apply  # null the field, in batches
    tools/corpus_quarantine.py --limit 5 --apply   # a small first batch

Dry run is the default because this writes to every post on the blog.

WHAT THIS DOES NOT DO — deliberately:

  * **It never publishes.** `status` is not in any payload it sends. Stamping
    a draft leaves it a draft. Quarantine posture and publication are two
    decisions, and welding them was how a 290-post migration would sneak in
    behind a one-line flag.
  * **It never attaches a newsletter.** Ghost gates an email send on
    `newsletter_id`, which is NULL on all 272 posts. Nothing here sets it, so
    no batch of this tool can mail the corpus to anyone.
  * **It does not touch `codeinjection_head` content it did not write.** A post
    whose injection holds something else is reported and skipped, never merged
    or clobbered.

BEFORE THE FIRST REAL PUBLISH, `routes.yaml` MUST BE SETTLED (SEO.md §Routing).
URLs come from the route config; changing it after the corpus ships is a 301
migration across ~290 posts. With one post live it is free. This tool does not
publish, so it is safe to run against drafts beforehand — but do not read a
clean run here as "the corpus is ready to go live".
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from pipelines.blog_pipeline.ghost_publisher import GhostClient  # noqa: E402

ROBOTS_META = '<meta name="robots" content="noindex, follow">'

# Posts that are NOT the corpus. The chapters and deep dives are the indexed
# tier; quarantining them would empty the index by construction. Slugs are the
# handle because the internal-tag tier split in SEO.md is still PROPOSED — when
# it lands, this becomes a tag filter and the list goes away.
NOT_CORPUS_SLUGS = {"coming-soon", "what-your-agent-cant-tell-you"}


def fetch_all(client: GhostClient) -> list[dict]:
    """Every post, drafts included. Ghost pages at 100; walk to the end rather
    than trusting a single big limit."""
    posts, page = [], 1
    while True:
        resp = client._client.get(
            f"{client.admin_url}/ghost/api/admin/posts/",
            headers=client._headers(),
            params={
                "fields": "id,slug,title,status,updated_at,codeinjection_head",
                "limit": 100,
                "page": page,
                "formats": "",
            },
        )
        resp.raise_for_status()
        body = resp.json()
        posts.extend(body.get("posts", []))
        pagination = body.get("meta", {}).get("pagination", {})
        if not pagination.get("next"):
            return posts
        page = pagination["next"]


def classify(post: dict, lift: bool) -> str:
    """One of: skip-not-corpus, skip-foreign-injection, already, change."""
    if post["slug"] in NOT_CORPUS_SLUGS:
        return "skip-not-corpus"
    head = (post.get("codeinjection_head") or "").strip()
    if head and head != ROBOTS_META:
        return "skip-foreign-injection"
    if lift:
        return "already" if not head else "change"
    return "already" if head == ROBOTS_META else "change"


def payload_for(post: dict, lift: bool) -> dict:
    """The whole write, as data — one field plus the collision guard.

    Kept separate from the request so a test can assert on the keys directly.
    What is absent is the point: no status (a stamp must not publish), no
    newsletter (a stamp must not mail), no body fields."""
    return {
        "posts": [
            {
                "id": post["id"],
                "updated_at": post["updated_at"],
                "codeinjection_head": None if lift else ROBOTS_META,
            }
        ]
    }


def write(client: GhostClient, post: dict, lift: bool) -> None:
    """PUT with updated_at, so a concurrent UI edit 409s rather than vanishing."""
    payload = payload_for(post, lift)
    resp = client._client.put(
        f"{client.admin_url}/ghost/api/admin/posts/{post['id']}/",
        headers=client._headers(),
        json=payload,
    )
    if resp.status_code == 409:
        raise SystemExit(
            f"conflict: {post['slug']} changed in Ghost since it was read. "
            "Re-run to pick up the new version — refusing to overwrite."
        )
    resp.raise_for_status()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="actually write (default is a dry run)")
    ap.add_argument("--lift", action="store_true",
                    help="the inverse: null the field, un-quarantining the batch")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N changes — for a small first batch")
    args = ap.parse_args(argv)

    admin_url = os.environ.get("GHOST_ADMIN_URL", "")
    admin_key = os.environ.get("GHOST_ADMIN_API_KEY", "")
    if not admin_url or not admin_key:
        print("GHOST_ADMIN_URL / GHOST_ADMIN_API_KEY not set (see .env)",
              file=sys.stderr)
        return 2

    client = GhostClient(admin_url, admin_key)
    try:
        posts = fetch_all(client)
    except Exception as exc:  # noqa: BLE001 — report the failure, don't half-run
        print(f"could not read the blog: {exc}", file=sys.stderr)
        client.close()
        return 1

    verb = "lift" if args.lift else "stamp"
    buckets: dict[str, list[dict]] = {}
    for post in posts:
        buckets.setdefault(classify(post, args.lift), []).append(post)

    changes = buckets.get("change", [])
    if args.limit:
        changes = changes[: args.limit]

    for post in buckets.get("skip-foreign-injection", []):
        print(f"  SKIP {post['slug']} — carries a different code injection")

    print(f"\ncorpus-quarantine ({verb}): {len(posts)} post(s) on the blog")
    print(f"  {len(buckets.get('already', []))} already in the target state")
    print(f"  {len(buckets.get('skip-not-corpus', []))} not corpus (indexed tier)")
    print(f"  {len(buckets.get('skip-foreign-injection', []))} skipped, foreign injection")
    print(f"  {len(changes)} to {verb}"
          + (f" (of {len(buckets.get('change', []))}, --limit)" if args.limit else ""))

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply.")
        for post in changes[:10]:
            print(f"  would {verb}: {post['slug']} [{post['status']}]")
        if len(changes) > 10:
            print(f"  ... and {len(changes) - 10} more")
        client.close()
        return 0

    done, failed = 0, 0
    for post in changes:
        try:
            write(client, post, args.lift)
            done += 1
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAILED {post['slug']}: {exc}", file=sys.stderr)
    client.close()

    print(f"\n{verb}ed {done} post(s); {failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
