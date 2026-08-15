"""
One-time (idempotent, re-runnable) sweep of Ghost drafts: render every
<pre class="mermaid"> HTML card to a PNG and swap the card for an image.

Why: mermaid renders client-side via a Ghost code-injection script. That
works in a normal browser and nowhere else — RSS readers and reader mode
strip scripts today, and email clients would too. A PNG renders everywhere.

  Corrected 2026-08-14: this used to read "every newsletter send would show
  raw diagram source," which implied sends were happening. They were not and
  still are not — Ghost has 0 members and has sent 0 emails, ever. RSS and
  reader mode were always the live reasons; email is the anticipated one.
  The sweep was right either way, for reasons that did not depend on email.

Token-free: the
diagram source is already written; rendering is mechanical (mermaid-cli,
local chromium — draft content never leaves the box).

Usage (from repo root, inside .venv):
    python -m pipelines.blog_pipeline.mermaid_sweep            # dry run
    python -m pipelines.blog_pipeline.mermaid_sweep --apply    # write to Ghost

Dry run renders everything to state/mermaid-sweep/ and touches nothing in
Ghost. Apply uploads each PNG via the Admin API images endpoint and swaps
the lexical html card for an image card, preserving updated_at collision
checks. Only status:draft posts are ever touched. Extracted .mmd sources
are kept alongside the PNGs (gitignored — drafts are unpublished and the
repo is public). Failures leave the card untouched and are reported.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from .ghost_publisher import GhostClient

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = Path(__file__).resolve().parent / "state" / "mermaid-sweep"
MMDC = REPO_ROOT / "tools" / "mermaid-render" / "node_modules" / ".bin" / "mmdc"
PUPPETEER_CONFIG = REPO_ROOT / "tools" / "mermaid-render" / "puppeteer-config.json"

CARD_RE = re.compile(r'^<pre class="mermaid">(.*)</pre>$', re.DOTALL)

# First word of the source → honest generic alt text (token-free; a
# descriptive-alt model pass can upgrade these later if it ever matters).
ALT_BY_TYPE = {
    "flowchart": "Flow diagram",
    "graph": "Flow diagram",
    "sequencediagram": "Sequence diagram",
    "statediagram": "State diagram",
    "classdiagram": "Class diagram",
    "erdiagram": "Entity-relationship diagram",
    "gantt": "Gantt chart",
    "pie": "Pie chart",
    "timeline": "Timeline diagram",
}


def load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


def mermaid_source(node: dict) -> str | None:
    """Extract unescaped mermaid source from a lexical html card, if it is one."""
    if node.get("type") != "html":
        return None
    m = CARD_RE.match((node.get("html") or "").strip())
    return html.unescape(m.group(1)) if m else None


def alt_text(source: str) -> str:
    # Frontmatter title wins: ---\ntitle: X\n---
    fm = re.match(r"\s*---\s*\n(.*?)\n\s*---", source, re.DOTALL)
    if fm:
        t = re.search(r"^title:\s*(.+)$", fm.group(1), re.MULTILINE)
        if t:
            return t.group(1).strip()
    first = re.sub(r"[^a-z]", "", source.strip().split()[0].lower()) if source.strip() else ""
    return ALT_BY_TYPE.get(first, "Diagram")


def png_dimensions(png: bytes) -> tuple[int, int]:
    w, h = struct.unpack(">II", png[16:24])
    return w, h


def render(source: str, out_png: Path) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False) as f:
        f.write(source)
        mmd = f.name
    try:
        proc = subprocess.run(
            [str(MMDC), "-p", str(PUPPETEER_CONFIG), "-i", mmd, "-o", str(out_png),
             "-b", "white", "--scale", "2"],
            capture_output=True, text=True, timeout=120,
        )
        return proc.returncode == 0 and out_png.exists()
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.unlink(mmd)


def upload_image(client: GhostClient, png_path: Path) -> str:
    token_headers = {
        "Authorization": f"Ghost {client._token()}",
        "Accept-Version": client.api_version,
    }
    with open(png_path, "rb") as f:
        resp = client._client.post(
            f"{client.admin_url}/ghost/api/admin/images/upload/",
            headers=token_headers,
            files={"file": (png_path.name, f, "image/png")},
        )
    resp.raise_for_status()
    return resp.json()["images"][0]["url"]


def image_card(src: str, width: int, height: int, alt: str) -> dict:
    return {
        "type": "image", "version": 1, "src": src,
        "width": width, "height": height,
        "title": "", "alt": alt, "caption": "",
        "cardWidth": "regular", "href": "",
    }


def iter_drafts(client: GhostClient):
    page = 1
    while True:
        resp = client._client.get(
            f"{client.admin_url}/ghost/api/admin/posts/",
            headers=client._headers(),
            params={"filter": "status:draft", "formats": "lexical", "limit": "50",
                    "page": str(page), "fields": "id,slug,status,updated_at"},
        )
        resp.raise_for_status()
        data = resp.json()
        yield from data["posts"]
        if data["meta"]["pagination"]["next"] is None:
            return
        page += 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="write changes to Ghost (default is a render-only dry run)")
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after N drafts that contain mermaid (0 = all)")
    args = ap.parse_args(argv)

    load_env()
    client = GhostClient(os.environ["GHOST_ADMIN_URL"], os.environ["GHOST_ADMIN_API_KEY"])
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    drafts = swapped = failures = 0
    failed: list[str] = []
    try:
        for post in iter_drafts(client):
            doc = json.loads(post["lexical"]) if post.get("lexical") else None
            if not doc:
                continue
            children = doc["root"]["children"]
            hits = [(i, src) for i, node in enumerate(children)
                    if (src := mermaid_source(node)) is not None]
            if not hits:
                continue
            drafts += 1
            slug_dir = STATE_DIR / post["slug"]
            slug_dir.mkdir(parents=True, exist_ok=True)
            changed = False
            for n, (idx, src) in enumerate(hits, start=1):
                (slug_dir / f"{n}.mmd").write_text(src)
                out_png = slug_dir / f"{n}.png"
                if not render(src, out_png):
                    failures += 1
                    failed.append(f"{post['slug']}#{n}")
                    print(f"RENDER FAILED  {post['slug']} diagram {n} (card left as-is)")
                    continue
                if args.apply:
                    url = upload_image(client, out_png)
                    w, h = png_dimensions(out_png.read_bytes())
                    children[idx] = image_card(url, w, h, alt_text(src))
                    changed = True
                print(f"{'swapped' if args.apply else 'rendered'}  {post['slug']} diagram {n}")
            if args.apply and changed:
                resp = client._client.put(
                    f"{client.admin_url}/ghost/api/admin/posts/{post['id']}/",
                    headers=client._headers(),
                    json={"posts": [{"lexical": json.dumps(doc),
                                     "updated_at": post["updated_at"]}]},
                )
                resp.raise_for_status()
                swapped += 1
            if args.limit and drafts >= args.limit:
                break
    finally:
        client.close()

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"\n[{mode}] drafts with mermaid: {drafts}; "
          f"{'updated: ' + str(swapped) + '; ' if args.apply else ''}"
          f"render failures: {failures}")
    if failed:
        print("failed diagrams:", ", ".join(failed))
    return 1 if failures and args.apply else 0


if __name__ == "__main__":
    sys.exit(main())
