#!/usr/bin/env python3
"""Syndicate a version-controlled blog post to dev.to, canonical pointing home.

    .venv/bin/python -m tools.devto_syndicate content/blog/POST.html            # dry run
    .venv/bin/python -m tools.devto_syndicate content/blog/POST.html --apply    # create/update the dev.to draft
    .venv/bin/python -m tools.devto_syndicate content/blog/POST.html --apply --publish

Why this exists. Syndication used to mean the field-note kits under
`uzelhub-web/syndication/<slug>/`, which are cut from `notes.json` and sized for
the apex. Field notes are apex content; the blog is what goes out. Those kits
still serve LinkedIn and X and are untouched by this.

The source of truth is the same file `tools.ghost_upsert` publishes — one
article, one file, two sinks. Reading Ghost back over its API instead would
make the rendered database the authority, and Ghost keeps no history, so a
syndicated copy could silently drift from what review approved.

Canonical goes to `blog.uzelhub.com`, NOT the apex. A canonical asserts "same
page", and a deep dive is not the same page as the 840-character field note that
links to it — pointing one at the other is a false claim search engines are
entitled to ignore. The consequence is deliberate: syndication builds the blog's
authority, and the apex keeps its own through the notes that link outward.

Two things this filters that a naive port would leak:

- **Internal tier tags.** Ghost marks them with a leading `#` (`#deep-dive`
  slugifies to `hash-deep-dive` and drives `routes.yaml`). They are routing
  machinery, meaningless to a dev.to reader, and are dropped here. dev.to caps
  tags at four and silently discards the rest; we refuse loudly instead.
- **Ghost card markers.** `<!--kg-card-begin: html-->` and the `uz-*` furniture
  classes are Ghost's, not portable, and are rendered down to plain markdown.

Posts are created as DRAFTS unless `--publish` is passed — the same posture
`ghost_publisher.create_draft` takes, so a human sees it on the platform before
the world does. Re-running updates the same article rather than creating a
duplicate; the id map lives in `state/devto.json`, which is gitignored.

Requires DEVTO_API_KEY (dev.to → Settings → Extensions → DEV Community API Keys).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

BLOG = "https://blog.uzelhub.com"
API = "https://dev.to/api/articles"
MAX_TAGS = 4

VOID = {"img", "br", "hr", "meta", "input"}
BLOCK = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "figure",
    "figcaption", "div", "table", "thead", "tbody", "tr", "th", "td",
    "ul", "ol", "li", "pre", "section",
}


class Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag: str, attrs: dict | None = None):
        self.tag = tag
        self.attrs = attrs or {}
        self.children: list = []

    def cls(self) -> str:
        return self.attrs.get("class", "")


class Tree(HTMLParser):
    """Minimal DOM. Ghost bodies are well-formed HTML fragments, so a stack
    that tolerates unclosed inline tags is enough — no lxml dependency."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].children.append(data)


def inline(node) -> str:
    """Render a node's contents as inline markdown."""
    if isinstance(node, str):
        return re.sub(r"\s+", " ", node)
    out = []
    for child in node.children:
        if isinstance(child, str):
            out.append(re.sub(r"\s+", " ", child))
            continue
        t = child.tag
        if t in ("strong", "b"):
            out.append(f"**{inline(child).strip()}**")
        elif t in ("em", "i"):
            out.append(f"*{inline(child).strip()}*")
        elif t == "code":
            out.append(f"`{inline(child).strip()}`")
        elif t == "a":
            href = child.attrs.get("href", "")
            if href.startswith("/"):
                href = BLOG + href
            out.append(f"[{inline(child).strip()}]({href})")
        elif t == "br":
            out.append("\n")
        else:
            out.append(inline(child))
    return "".join(out)


def cells(row) -> list[str]:
    return [
        inline(c).strip()
        for c in row.children
        if not isinstance(c, str) and c.tag in ("th", "td")
    ]


def render_table(node) -> str:
    rows = []
    for part in node.children:
        if isinstance(part, str):
            continue
        if part.tag == "tr":
            rows.append(part)
        elif part.tag in ("thead", "tbody"):
            rows += [r for r in part.children if not isinstance(r, str) and r.tag == "tr"]
    if not rows:
        return ""
    head = cells(rows[0])
    body = [cells(r) for r in rows[1:]]
    width = max([len(head)] + [len(r) for r in body]) if body else len(head)
    head += [""] * (width - len(head))
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * width]
    for r in body:
        r += [""] * (width - len(r))
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def render(node, out: list[str]) -> None:
    for child in node.children:
        if isinstance(child, str):
            text = re.sub(r"\s+", " ", child).strip()
            if text:
                out.append(text)
            continue
        t, cls = child.tag, child.cls()
        if t == "table":
            out.append(render_table(child))
        elif t in ("div", "section"):
            render(child, out)          # uz-act / uz-stat wrappers carry no meaning here
        elif t == "figure":
            render(child, out)
        elif t == "img":
            src = child.attrs.get("src", "")
            if src.startswith("/"):
                src = BLOG + src
            out.append(f"![{child.attrs.get('alt', '')}]({src})")
        elif t == "figcaption":
            text = inline(child).strip()
            if text:
                out.append(f"*{text}*")
        elif t == "blockquote":
            text = inline(child).strip()
            out.append("\n".join(f"> {ln}" for ln in text.split("\n")))
        elif re.fullmatch(r"h[1-6]", t):
            out.append("#" * int(t[1]) + " " + inline(child).strip())
        elif t == "span":
            # The act label ("Act one") sits beside its own h2; give it a line.
            text = inline(child).strip()
            if text:
                out.append(f"**{text}**")
        elif t in ("ul", "ol"):
            items = [c for c in child.children if not isinstance(c, str) and c.tag == "li"]
            for i, li in enumerate(items, 1):
                bullet = f"{i}." if t == "ol" else "-"
                out.append(f"{bullet} {inline(li).strip()}")
        elif t == "p":
            text = inline(child).strip()
            if not text:
                continue
            if "uz-pull" in cls:
                out.append("\n".join(f"> {ln}" for ln in text.split("\n")))
            elif "uz-stat-fig" in cls:
                out.append(f"**{text}**")
            else:
                out.append(text)
        elif t == "pre":
            out.append("```\n" + inline(child).strip() + "\n```")
        else:
            text = inline(child).strip()
            if text:
                out.append(text)


def parse_source(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        sys.exit(f"{path}: no YAML front matter — is this a ghost_upsert source file?")
    _, fm_text, body = raw.split("---", 2)
    fm: dict = {}
    for line in fm_text.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            fm[key.strip()] = [
                v.strip().strip('"').strip("'")
                for v in value[1:-1].split(",")
                if v.strip()
            ]
        else:
            fm[key.strip()] = value
    body = re.sub(r"<!--\s*kg-card-(begin|end):[^>]*-->", "", body)
    return fm, body


def to_markdown(body: str) -> str:
    tree = Tree()
    tree.feed(body)
    out: list[str] = []
    render(tree.root, out)
    return "\n\n".join(b for b in out if b.strip())


def footer(canonical: str) -> str:
    """Visible attribution, carrying one link to each host.

    The canonical tag is the search-engine signal; this is the human one, and
    the two do different jobs — a reader who liked the piece needs somewhere to
    click. Both hosts appear on purpose: the blog because it is the source, the
    apex because syndication is the only structured authority flow it has, and
    a blog-only footer would quietly cut it out of its own promotion."""
    return (
        f"---\n\n*Originally published at [blog.uzelhub.com]({canonical}). "
        "The systems these come from are at [uzelhub.com](https://uzelhub.com).*"
    )


def public_tags(raw: list[str]) -> list[str]:
    """Ghost internal tags start with '#'. They are routing, not topic."""
    tags = [t for t in raw if not t.startswith("#")]
    if len(tags) > MAX_TAGS:
        sys.exit(
            f"{len(tags)} public tags ({', '.join(tags)}) — dev.to accepts at most "
            f"{MAX_TAGS} and silently drops the rest. Trim the front matter."
        )
    return tags


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", type=Path, help="content/blog/<slug>.html")
    ap.add_argument("--apply", action="store_true", help="write to dev.to")
    ap.add_argument("--publish", action="store_true", help="publish rather than draft")
    ap.add_argument("--cover", default="", help="main_image URL (defaults to first figure)")
    ap.add_argument("--state", type=Path, default=Path("state/devto.json"))
    args = ap.parse_args()

    fm, body = parse_source(args.source)
    for required in ("title", "slug"):
        if not fm.get(required):
            sys.exit(f"{args.source}: front matter is missing '{required}'")

    canonical = f"{BLOG}/{fm['slug']}/"
    markdown = to_markdown(body) + "\n\n" + footer(canonical)
    tags = public_tags(fm.get("tags", []))
    first_image = re.search(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    cover = args.cover or (first_image.group(1) if first_image else "")

    article = {
        "title": fm["title"],
        "body_markdown": markdown,
        "published": bool(args.publish),
        "canonical_url": canonical,
        "description": fm.get("meta_description", ""),
        "tags": ", ".join(tags),
    }
    if cover:
        article["main_image"] = cover

    dropped = [t for t in fm.get("tags", []) if t.startswith("#")]
    print(f"source     {args.source}")
    print(f"title      {article['title']}")
    print(f"canonical  {canonical}")
    print(f"tags       {article['tags'] or '(none)'}" + (f"   dropped internal: {', '.join(dropped)}" if dropped else ""))
    print(f"cover      {cover or '(none — dev.to cards without one read as empty in the feed)'}")
    print(f"body       {len(markdown):,} chars markdown")
    print(f"status     {'PUBLISH' if args.publish else 'draft'}")

    if not args.apply:
        print("\ndry run — nothing sent. Re-run with --apply.")
        print("--- first 400 chars ---")
        print(markdown[:400])
        return

    key = os.environ.get("DEVTO_API_KEY", "").strip()
    if not key:
        sys.exit("DEVTO_API_KEY is not set — refusing to run rather than half-publish.")

    import httpx

    state = {}
    if args.state.exists():
        state = json.loads(args.state.read_text())
    existing = state.get(fm["slug"])
    headers = {"api-key": key, "Content-Type": "application/json"}

    with httpx.Client(timeout=30.0) as client:
        if existing:
            resp = client.put(f"{API}/{existing}", headers=headers, json={"article": article})
            verb = "updated"
        else:
            resp = client.post(API, headers=headers, json={"article": article})
            verb = "created"
        if resp.status_code >= 400:
            sys.exit(f"dev.to {resp.status_code}: {resp.text[:400]}")
        post = resp.json()

    state[fm["slug"]] = post["id"]
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    print(f"\n{verb}: {post.get('url') or post.get('id')}")


if __name__ == "__main__":
    main()
