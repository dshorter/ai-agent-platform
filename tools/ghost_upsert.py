#!/usr/bin/env python3
"""Create-or-update a hand-authored Ghost post from a version-controlled file.

    .venv/bin/python -m tools.ghost_upsert POST.html            # dry run
    .venv/bin/python -m tools.ghost_upsert POST.html --apply    # write to Ghost
    .venv/bin/python -m tools.ghost_upsert POST.html --suggest  # + Marketer readout

Why this exists. The pipeline's `create_draft` is idempotent by *skipping* — it
returns the existing post rather than updating it, which is right for generated
corpus posts (never re-derive published work) and wrong for a piece a human
iterates on. Everything else about that path is good and is reused here: the
JWT client, and `?source=html`, whose HTML→lexical converter honours
`<!--kg-card-begin: html-->` markers. That is how arbitrary furniture — tables,
figures, callouts — survives ingest. Pasting the same markup into the Ghost
editor does not survive: the editor normalises to its own cards and drops
unknown divs and classes.

The file is the source of truth, not the database. Ghost keeps no history, so
an article that exists only in MySQL cannot be reviewed, diffed or restored —
the same reason the site-header injection is version-controlled in
config/ghost/.

File format — YAML front matter, then the body as HTML:

    ---
    title: What your agent can't tell you
    slug: what-your-agent-cant-tell-you
    tags: [agents, observability]
    meta_description: One morning brief, chased all the way down.
    ---
    <p>…</p>

Only `title` and `slug` are required. Updates are collision-checked against
`updated_at`, so a concurrent edit in the Ghost UI fails loudly instead of
being silently overwritten.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

from pipelines.blog_pipeline.ghost_publisher import GhostClient, GhostDraft


def _parse_front_matter(block: str) -> dict:
    """Minimal `key: value` reader — no YAML dependency.

    The project declares none and `pipelines/scout/leads.py` hand-parses its
    own ledger with stdlib, so this follows the house choice rather than
    pulling PyYAML in for four keys. Supports scalars and `[a, b]` lists;
    splits on the first colon so values may contain colons. Anything richer
    than that is a sign the front matter is doing too much.
    """
    meta: dict = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            meta[key] = [v for v in items if v]
        else:
            meta[key] = value.strip("'\"")
    return meta


@dataclass
class ParsedPost:
    meta: dict
    html: str

    @property
    def title(self) -> str:
        return self.meta["title"]

    @property
    def slug(self) -> str:
        return self.meta["slug"]


def parse(path: Path) -> ParsedPost:
    """Split YAML front matter from the HTML body."""
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise SystemExit(f"{path}: no YAML front matter (file must start with ---)")
    _, fm, body = raw.split("---", 2)
    meta = _parse_front_matter(fm)
    for required in ("title", "slug"):
        if not meta.get(required):
            raise SystemExit(f"{path}: front matter is missing '{required}'")
    return ParsedPost(meta=meta, html=body.strip())


def fetch_full(client: GhostClient, slug: str) -> dict | None:
    """The post with the fields an update needs — updated_at for collision safety."""
    resp = client._client.get(
        f"{client.admin_url}/ghost/api/admin/posts/slug/{slug}/",
        headers=client._headers(),
        params={"fields": "id,slug,status,url,updated_at,title"},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    posts = resp.json().get("posts", [])
    return posts[0] if posts else None


def update(client: GhostClient, post: dict, parsed: ParsedPost) -> dict:
    """PUT with updated_at, so a concurrent UI edit 409s rather than vanishing."""
    payload = {
        "posts": [
            {
                "id": post["id"],
                "updated_at": post["updated_at"],
                "title": parsed.title,
                "slug": parsed.slug,
                "html": parsed.html,
                "tags": [{"name": t} for t in parsed.meta.get("tags", [])],
                "meta_description": parsed.meta.get("meta_description"),
                "custom_excerpt": parsed.meta.get(
                    "custom_excerpt", parsed.meta.get("meta_description")
                ),
            }
        ]
    }
    resp = client._client.put(
        f"{client.admin_url}/ghost/api/admin/posts/{post['id']}/",
        headers=client._headers(),
        params={"source": "html"},
        json=payload,
    )
    if resp.status_code == 409:
        raise SystemExit(
            f"conflict: {parsed.slug} changed in Ghost since this file was written. "
            "Reconcile by hand — refusing to overwrite."
        )
    resp.raise_for_status()
    return resp.json()["posts"][0]


def suggest(parsed: ParsedPost) -> None:
    """Run the Marketer over this body and print what the doctrine produces.

    Read-only: nothing is written to Ghost and nothing here is auto-applied. The
    point is to exercise config/seo/blog.md against real content and to compare
    a hand-authored title against the one the rules would pick.
    """
    from anthropic import Anthropic

    from agents.content_agent import Draft
    from agents.marketer_agent import MarketerAgent

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("--suggest needs ANTHROPIC_API_KEY")

    marketer = MarketerAgent(Anthropic(api_key=key), sink="blog")
    draft = Draft(
        title=parsed.title,
        body=parsed.html,
        notes_for_marketer="Hand-authored long-form. Title is operator-approved.",
        input_tokens=0,
        output_tokens=0,
        raw_text=parsed.html,
    )
    descriptor, _ = marketer.extract_descriptor(draft)
    out = marketer.package(draft, descriptor, link_candidates=[], queue_depth=0)

    print("\n── Marketer readout (nothing applied) ──")
    print(f"  title       {out.title}  [{len(out.title)} chars]")
    print(f"  yours       {parsed.title}  [{len(parsed.title)} chars]")
    print(f"  slug        {out.slug}")
    print(f"  tags        {out.tags}")
    print(f"  meta        {out.meta_description}  [{len(out.meta_description)} chars]")
    print(f"  keyword     {descriptor.primary_keyword}")
    print(f"  topics      {descriptor.topics}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--apply", action="store_true", help="write to Ghost")
    ap.add_argument("--suggest", action="store_true", help="Marketer readout, applies nothing")
    args = ap.parse_args(argv)

    parsed = parse(args.file)
    print(f"{args.file}  →  {parsed.slug}")
    print(f"  title  {parsed.title}")
    print(f"  tags   {parsed.meta.get('tags', [])}")
    print(f"  body   {len(parsed.html):,} chars HTML")

    admin_url = os.environ.get("GHOST_ADMIN_URL", "http://localhost:2368")
    admin_key = os.environ.get("GHOST_ADMIN_API_KEY", "")
    if not admin_key:
        raise SystemExit("GHOST_ADMIN_API_KEY is not set (see /opt/ai-agent-platform/.env)")

    client = GhostClient(admin_url, admin_key)
    try:
        existing = fetch_full(client, parsed.slug)
        verb = "UPDATE" if existing else "CREATE"
        if existing:
            print(f"  exists  {existing['status']} — {existing.get('url','')}")

        if not args.apply:
            print(f"\nDRY RUN — would {verb}. Re-run with --apply to write.")
        else:
            if existing:
                post = update(client, existing, parsed)
            else:
                post = None
                res = client.create_draft(
                    GhostDraft(
                        title=parsed.title,
                        slug=parsed.slug,
                        html=parsed.html,
                        tags=parsed.meta.get("tags", []),
                        meta_description=parsed.meta.get("meta_description", ""),
                        custom_excerpt=parsed.meta.get("custom_excerpt"),
                    )
                )
                post = {"url": res.url, "status": "draft"}
            print(f"\n{verb} OK — {post.get('url','')} ({post.get('status','draft')})")

        if args.suggest:
            suggest(parsed)
    except httpx.HTTPStatusError as exc:
        raise SystemExit(f"Ghost API error {exc.response.status_code}: {exc.response.text[:300]}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
