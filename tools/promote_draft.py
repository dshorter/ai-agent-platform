#!/usr/bin/env python3
"""Promote an approved draft into the release queue.

The crossover step that was still hand-carried: a Writer draft lives in
gitignored state; a note lives in uzelhub-web's `data/notes.json`. This
moves the `note` payload across and leaves it WITHOUT a `published` date —
which is exactly what "queued" means (PUBLISHING.md: a note is public iff
it carries a published ISO date, and only release.js stamps one).

So promotion is not publication. It puts the note in line; the drip valve
(release.js) still decides when it goes live, and the cadence guard still
enforces the 1-2/week doctrine.

    .venv/bin/python tools/promote_draft.py <slug>
    .venv/bin/python tools/promote_draft.py <slug> --dry-run
    .venv/bin/python tools/promote_draft.py --list

Ledger: stamps the source lead `approved` via lead_mark — the sanctioned
mutation verb, never freehand YAML. `--no-stamp` skips it.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

DRAFTS_DIR = Path(os.environ.get("WRITER_DRAFTS_DIR", _REPO / "pipelines" / "writer" / "state" / "drafts"))
NOTES_PATH = Path(os.environ.get("UZELHUB_NOTES_PATH", "/opt/uzelhub-web/marketing/data/notes.json"))

# The fields generate.js needs to render a note page and its SEO surface.
REQUIRED = ("slug", "kicker", "title", "tagline", "metaDescription", "sections")


def load_drafts(drafts_dir: Path) -> list[dict]:
    """Every real draft in the state dir. Skips .bak snapshots and the
    non-JSON companions (arc briefs, blog skeletons)."""
    out = []
    for p in sorted(drafts_dir.glob("*.json")):
        if p.name.endswith(".bak") or ".bak." in p.name:
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  ! {p.name}: unparsable ({e})", file=sys.stderr)
            continue
        if isinstance(data.get("note"), dict) and data["note"].get("slug"):
            data["_path"] = str(p)
            out.append(data)
    return out


def load_notes(notes_path: Path) -> list[dict]:
    return json.loads(notes_path.read_text(encoding="utf-8"))


def write_notes(notes_path: Path, notes: list[dict]) -> None:
    # Match release.js byte-for-byte: JSON.stringify(notes, null, 2) + '\n',
    # which does not escape non-ASCII. ensure_ascii=True would rewrite every
    # em dash in the file and produce a churn diff on first write.
    notes_path.write_text(
        json.dumps(notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def stamp_approved(lead_id: str, repo: Path) -> tuple[bool, str]:
    """Ledger transition through the only sanctioned verb."""
    venv_py = repo / ".venv" / "bin" / "python"
    py = str(venv_py) if venv_py.exists() else sys.executable
    proc = subprocess.run(
        [py, "-m", "pipelines.scout.lead_mark", lead_id, "--to", "approved", "--by", "editor"],
        cwd=str(repo), capture_output=True, text=True,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="*", help="one or more note slugs to promote")
    ap.add_argument("--list", action="store_true", help="show promotable drafts and exit")
    ap.add_argument("--dry-run", action="store_true", help="validate and report; write nothing")
    ap.add_argument("--no-stamp", action="store_true", help="skip the ledger `approved` stamp")
    ap.add_argument("--drafts-dir", default=str(DRAFTS_DIR))
    ap.add_argument("--notes-path", default=str(NOTES_PATH))
    args = ap.parse_args(argv)

    drafts_dir, notes_path = Path(args.drafts_dir), Path(args.notes_path)
    if not drafts_dir.is_dir():
        print(f"no drafts dir: {drafts_dir}", file=sys.stderr)
        return 1
    if not notes_path.exists():
        print(f"no notes.json: {notes_path}", file=sys.stderr)
        return 1

    drafts = load_drafts(drafts_dir)
    notes = load_notes(notes_path)
    existing = {n.get("slug") for n in notes}

    if args.list or not args.slug:
        if not drafts:
            print(f"no drafts in {drafts_dir}")
            return 0
        for d in drafts:
            slug = d["note"]["slug"]
            state = "already in notes.json" if slug in existing else "promotable"
            reg = d.get("lead", {}).get("register", "?")
            print(f"  {slug:<48} [{reg}] {state}")
        return 0

    # Validate the whole batch before writing anything. A half-applied batch is
    # worse than a refused one: notes.json would carry some of your verdicts and
    # the ledger the rest, and you'd have to diff them to find out which.
    plan, problems = [], []
    seen = set(existing)
    for slug in args.slug:
        match = next((d for d in drafts if d["note"]["slug"] == slug), None)
        if not match:
            problems.append(f"  {slug}: no such draft (see --list)")
            continue
        if slug in seen:
            problems.append(f"  {slug}: already in notes.json — promotion is once-only")
            continue
        missing = [f for f in REQUIRED if not match["note"].get(f)]
        if missing:
            problems.append(f"  {slug}: missing required fields: {', '.join(missing)}")
            continue
        seen.add(slug)
        plan.append(match)

    if problems:
        print(f"refusing the batch — {len(problems)} of {len(args.slug)} would fail:", file=sys.stderr)
        for p in problems:
            print(p, file=sys.stderr)
        print("\nNothing was written. Fix or drop those slugs and re-run.", file=sys.stderr)
        return 1

    for match in plan:
        slug = match["note"]["slug"]
        register = match.get("lead", {}).get("register", "note")
        if register != "note":
            print(f"warning: {slug} has register '{register}', not 'note' — notes.json is the field-note sink", file=sys.stderr)

    if args.dry_run:
        for match in plan:
            note = match["note"]
            print(f"[dry-run] would queue '{note['slug']}' "
                  f"(sections={len(note.get('sections', []))} bullets={len(note.get('bullets', []))})")
            if not args.no_stamp:
                print(f"[dry-run]   stamp lead {match.get('lead', {}).get('id')} -> approved")
        print(f"[dry-run] {len(plan)} would be appended to {notes_path}; nothing written")
        return 0

    for match in plan:
        note = dict(match["note"])
        # Queued, not published. release.js owns the stamp; that separation is
        # what keeps the drip a valve instead of a memory exercise.
        note.pop("published", None)
        notes.append(note)
    write_notes(notes_path, notes)
    print(f"queued {len(plan)} in {notes_path} (no published dates — none are live):")
    for match in plan:
        print(f"  {match['note']['slug']}")

    if not args.no_stamp:
        print()
        for match in plan:
            lead_id = match.get("lead", {}).get("id")
            if not lead_id:
                continue
            ok, out = stamp_approved(lead_id, _REPO)
            print(f"  ledger: {lead_id} -> approved" if ok else f"  ledger stamp FAILED ({lead_id}): {out}")

    print("\nNext: release the head of the queue when the drip allows —")
    print("  node marketing/release.js --next           # in /opt/uzelhub-web")
    return 0


if __name__ == "__main__":
    sys.exit(main())
