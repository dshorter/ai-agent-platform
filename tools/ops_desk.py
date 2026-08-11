#!/usr/bin/env python3
"""Assemble the ops desk — one served root behind one capability URL.

The admin pages were each earning their own token-bearing route. That doesn't
scale past about three: every new page is another Caddyfile edit, another
reload, another URL to keep out of a repo. So they move under one directory,
one handle, one token.

    /opt/ai-agent-platform/ops/desk/
      index.html      this entry point (generated)
      todos.html   -> ops/views/todos.html
      notes/       -> pipelines/writer/state/review/   (desk + queue)

Nothing here is copied — the entries are symlinks onto the real generated
files, so `calendar-views` and `draft_review.py` keep their existing output
contracts and this stays a pure assembly step.

**The generated page never contains the token.** Every link is relative, so
the same files serve correctly under any capability path — rotation stays a
one-reload story with nothing to regenerate. Caddy is operator-only (sudo):
this prints the config to paste, and applies nothing.

    .venv/bin/python tools/ops_desk.py                # assemble + print the snippet
    .venv/bin/python tools/ops_desk.py --token-only   # just mint a fresh token
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
DESK = _REPO / "ops" / "desk"

# (link name in the desk, target relative to the desk dir, label, blurb)
ENTRIES = [
    ("todos.html", "../views/todos.html", "To-do list",
     "Overdue, due today, next seven days. Projected from the ops calendar — "
     "current as of the last write, not a lazy poll."),
    ("notes", "../../pipelines/writer/state/review", "Draft review desk",
     "Field-note and newsletter drafts awaiting a verdict. Thumb up to queue; "
     "the drip schedule is computed as you go."),
]

# Pages reachable inside a linked directory, listed on the entry point so the
# desk is one hop from anything.
SUBPAGES = [("notes/queue.html", "Publication queue",
             "Read-only. What is live, what is waiting, and the id each "
             "server-side command takes."),
            # Built by ops/apex-sandbox into desk/apex/ — a real directory, not
            # a symlink, so assemble() leaves it alone. Absent until first build.
            ("apex/", "Apex copy walk",
             "A throwaway rebuild of uzelhub.com, every page in reading order "
             "with prev/next at the thumb. For dictating final copy — nothing "
             "here is live, and the chrome names the data key behind each page.")]

CSS = """
html{font-size:106.25%}  /* 17px base — matches apex; every rem follows */
:root{--bg:#f6f6f4;--card:#fff;--fg:#17181c;--dim:#64666e;--line:#e4e4e1;--acc:#2f5d8a;
--sans:Inter,ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif;
--serif:Charter,"Iowan Old Style",Georgia,serif}
@media(prefers-color-scheme:dark){:root{--bg:#14151a;--card:#1b1d23;--fg:#e6e6e2;
--dim:#93959d;--line:#2a2d35;--acc:#82b4e2}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:1rem/1.6 var(--sans);
-webkit-text-size-adjust:100%}
.wrap{max-width:34rem;margin:0 auto;padding:3rem 1.2rem 4rem}
h1{font-family:var(--serif);font-size:1.6rem;margin:0 0 .3rem;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:.87rem;margin:0 0 2rem}
a.item{display:block;text-decoration:none;color:inherit;background:var(--card);
border:1px solid var(--line);border-radius:12px;padding:1rem 1.2rem;margin-bottom:.8rem;
transition:.13s}
a.item:hover{border-color:var(--acc);transform:translateY(-1px)}
a.item:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.t{font-weight:640;font-size:1.02rem;display:flex;justify-content:space-between;
align-items:baseline;gap:1rem}
.t .go{color:var(--acc);font-size:.85rem;font-weight:500;flex:none}
.b{color:var(--dim);font-size:.85rem;margin-top:.25rem;line-height:1.5}
.foot{margin-top:2rem;padding-top:1rem;border-top:1px solid var(--line);
color:var(--dim);font-size:.76rem;line-height:1.6}
@media(prefers-reduced-motion:reduce){a.item{transition:none}
a.item:hover{transform:none}}
"""


def render(items: list[tuple[str, str, str]]) -> str:
    cards = "".join(
        f'<a class="item" href="{href}"><span class="t">{label}'
        f'<span class="go">open &rarr;</span></span>'
        f'<span class="b">{blurb}</span></a>'
        for href, label, blurb in items
    )
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta name="referrer" content="no-referrer">
<title>Ops desk</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body><div class="wrap">
<h1>Ops desk</h1>
<p class="sub">Everything behind one capability URL.</p>
{cards}
<p class="foot">Read-and-decide surfaces. Each hands back a command to run on
the box &mdash; none of them write. Links are relative, so this page keeps
working after a token rotation.</p>
</div></body></html>
"""


def assemble(desk: Path) -> list[str]:
    """Symlink the real generated files into the served root."""
    desk.mkdir(parents=True, exist_ok=True)
    notes = []
    for name, target, _label, _blurb in ENTRIES:
        link = desk / name
        resolved = (desk / target).resolve()
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(Path(target))
        notes.append(f"  {name:<12} -> {target}" + ("" if resolved.exists() else "   [target missing — generate it]"))
    return notes


def caddy_snippet(token: str) -> str:
    # The redir matters: `handle /desk-X/*` does not match the bare
    # /desk-X, so without it the entry point 404s unless you happen to
    # type the trailing slash. handle_path strips the prefix for us.
    return f"""    redir /desk-{token} /desk-{token}/ permanent
    handle_path /desk-{token}/* {{
        header X-Robots-Tag "noindex"
        header Referrer-Policy "no-referrer"
        header Cache-Control "no-cache, max-age=0"
        root * /opt/ai-agent-platform/ops/desk
        file_server
    }}"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desk", default=str(DESK))
    ap.add_argument("--token-only", action="store_true", help="mint a token and exit")
    args = ap.parse_args(argv)

    token = secrets.token_hex(16)
    if args.token_only:
        print(token)
        return 0

    desk = Path(args.desk)
    links = assemble(desk)

    items = [(href, label, blurb) for href, _t, label, blurb in
             [(n, t, l, b) for n, t, l, b in ENTRIES]]
    # Directory entries open their index; name the page, not the folder.
    items = [(h if h.endswith(".html") else f"{h}/", l, b) for h, l, b in items]
    items += SUBPAGES

    (desk / "index.html").write_text(render(items), encoding="utf-8")

    print(f"assembled {desk}")
    for n in links:
        print(n)
    print(f"  index.html   (generated, {len(items)} entries)")
    print("\nCaddy — paste inside the uzelhub.com { } block in /etc/caddy/Caddyfile,")
    print("then:  sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy\n")
    print(caddy_snippet(token))
    print(f"\n  Entry point:  https://uzelhub.com/desk-{token}/")
    print("\nThe token lives ONLY in the Caddyfile — never in a repo, a page, or a sitemap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
