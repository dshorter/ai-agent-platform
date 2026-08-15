#!/usr/bin/env python3
"""Push the version-controlled site-header injection into Ghost.

    .venv/bin/python -m tools.ghost_inject            # dry run, shows the diff
    .venv/bin/python -m tools.ghost_inject --apply    # write to Ghost
    .venv/bin/python -m tools.ghost_inject --backup-only

Why this exists. `config/ghost/code-injection-head.html` carries the CSS that
long-form posts depend on for their furniture — act headers, pull quotes, stat
blocks, takeaways. Ghost keeps it in a settings row in MySQL **with no history**,
so the file is the source of truth and the database is a deployment target. Until
2026-08-15 the only documented way to install it was pasting into Settings →
Code injection → Site header, which is exactly the hand-edit-a-live-config shape
we stopped doing elsewhere: no backup, no validation, no verification, and no
record of what the previous value was.

So: same contract as the sudo scripts. Back up what is there, validate before
writing, verify after, and refuse loudly rather than half-apply.

The provenance comment at the top of the file is stripped before upload — it
documents the file for whoever opens the repo, and shipping it would put ~1.2KB
of build notes into the <head> of every page on the blog.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

import httpx
import jwt

_REPO = Path(__file__).resolve().parent.parent
SOURCE = _REPO / "config" / "ghost" / "code-injection-head.html"
BACKUP_DIR = _REPO / "config" / "ghost" / "backups"
KEY = "codeinjection_head"


def payload_from(path: Path) -> str:
    """The file minus its provenance comment — what actually ships."""
    text = path.read_text(encoding="utf-8")
    body = re.sub(r"^\s*<!--.*?-->\s*", "", text, count=1, flags=re.S)
    if "<style>" not in body:
        raise SystemExit(f"REFUSED: {path} has no <style> block after the comment")
    if "<script" in body.lower():
        raise SystemExit("REFUSED: source contains a <script> tag; this channel is CSS only")
    return body.strip() + "\n"


def client() -> tuple[httpx.Client, str, dict]:
    key = os.environ.get("GHOST_ADMIN_API_KEY", "")
    url = os.environ.get("GHOST_ADMIN_URL", "").rstrip("/")
    if not key or not url:
        raise SystemExit("GHOST_ADMIN_API_KEY / GHOST_ADMIN_URL not set (see .env)")
    kid, secret = key.split(":")
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    token = jwt.encode({"iat": now, "exp": now + 300, "aud": "/admin/"},
                       bytes.fromhex(secret), algorithm="HS256", headers={"kid": kid})
    return httpx.Client(timeout=30), url, {"Authorization": f"Ghost {token}"}


def read_live(c, url, headers) -> str:
    r = c.get(f"{url}/ghost/api/admin/settings/", headers=headers)
    r.raise_for_status()
    return {s["key"]: s["value"] for s in r.json()["settings"]}.get(KEY) or ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write to Ghost")
    ap.add_argument("--backup-only", action="store_true", help="save the live value and exit")
    a = ap.parse_args(argv)

    desired = payload_from(SOURCE)
    c, url, headers = client()
    live = read_live(c, url, headers)

    print(f"source  {SOURCE.relative_to(_REPO)}  →  {len(desired):,} chars (comment stripped)")
    print(f"live    {KEY}  →  {len(live):,} chars"
          + ("  (empty — nothing installed)" if not live else ""))

    # Always preserve what is about to be replaced; Ghost keeps no history.
    if live:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = BACKUP_DIR / f"{KEY}.{stamp}.html"
        dest.write_text(live, encoding="utf-8")
        print(f"backup  {dest.relative_to(_REPO)}")
    elif a.backup_only:
        print("backup  nothing to back up")

    if a.backup_only:
        return 0

    if live.strip() == desired.strip():
        print("\nalready in sync — nothing to do.")
        return 0

    if not a.apply:
        print("\nDRY RUN — would REPLACE the live value. Re-run with --apply.")
        return 0

    r = c.put(f"{url}/ghost/api/admin/settings/", headers=headers,
              json={"settings": [{"key": KEY, "value": desired}]})
    if r.status_code == 501:
        # Ghost restricts settings writes to staff tokens; a custom integration
        # key can create posts but not edit site settings. Verified 2026-08-15.
        # Fall back to the documented paste, but make it a two-step with a
        # machine check on the other side rather than a hope.
        out = BACKUP_DIR / "PASTE-INTO-SITE-HEADER.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(desired, encoding="utf-8")
        print(f"\nGhost refused the write (501): settings are staff-token only, and this\n"
              f"is an integration key. The API cannot install this — a human must.\n\n"
              f"  1. copy   {out.relative_to(_REPO)}   ({len(desired):,} chars)\n"
              f"  2. paste  Ghost → Settings → Code injection → Site header → Save\n"
              f"  3. verify .venv/bin/python -m tools.ghost_inject   (says 'already in sync')\n",
              file=sys.stderr)
        return 2
    if r.status_code >= 400:
        print(f"\nFAILED {r.status_code}: {r.text[:300]}", file=sys.stderr)
        return 1

    # Verify by reading it back rather than trusting the write.
    back = read_live(c, url, headers)
    if back.strip() != desired.strip():
        print(f"\nMISMATCH after write — live is {len(back):,} chars, expected "
              f"{len(desired):,}. The backup above holds the prior value.", file=sys.stderr)
        return 1
    print(f"\nAPPLIED and verified — {len(back):,} chars live at {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
