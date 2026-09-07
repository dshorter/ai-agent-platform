"""The file reader — the box's own prose as ore, one reader with splitters.

The third source, and the first that is not a stream of events. A transcript is
rows and git is commits; a doc is a document, so the unit a jewel anchors to has
to be CHOSEN. That choice is the splitter, and it is the only thing that varies
between the sources this module serves:

    doc     one H2 section of a markdown file — doctrine and dated findings, cut
            where the writer already cut them.
    ledger  one dated entry (`## 2026-09-02 — …`), where the date in the heading
            is the date of the material and the file's own date is not.

Both split on the same H2 machinery, which is the point: `## ` is where this
estate's prose is already sectioned. Two further splitters are named in the plan
— a YAML node for the survey, a VTODO for the calendar — and are deliberately
NOT built here. They have no caller yet, and jewels.py carries the scar of a
read side written before its arguments were known. Each is a row in `SPLITTERS`
and a paragraph in `STANCES` on the day something calls it.

**What this shares with git_ore is the whole design.** Rows carry `ref` and
`date`, `page_as_prompt` tags every unit `[ref=…]`, and `persist()` validates
each cited ref against the page it actually showed. Schema 1.4.0 gave up the
foreign key for five of six sources on precisely that understanding, so a reader
that does not hand back a candidate set is not a reader.

**The roots are a boundary, not a default.** `read_units` refuses a path outside
the registered roam roots. `_host` and `server-maintenance` are excluded on
purpose — the employer vocabulary lives in `_host` — and a `source_ref` is
publishable text that travels to a lead's `sources` field, so a path from a
gated repo would name that repo in publishable output even when its content
never left the box. The refusal is AGENTS.md §Open questions enforced in the one
place that can enforce it, not a convenience.

**Dates.** A ledger entry states its own. A doc does not, so the file's last
commit date stands in: when the doctrine was last touched, which spreads doc
jewels across the ore's real chronology instead of piling every one of them on
the day of the walk. mtime is the fallback for an untracked file — it is second
choice because a fresh clone would make every date the date of the clone.
"""
from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from pipelines.director.registry import load_registry
from pipelines.director.tools import looks_secret
from pipelines.scout.box_index import MAX_FILE_BYTES, SKIP_DIRS

# Mirrors walk.ROW_CLIP_CHARS and git_ore.COMMIT_CLIP_CHARS: enough to catch a
# jewel, small enough that a page of units stays a cheap call. The whole section
# is one read_file away for anything that needs it.
UNIT_CLIP_CHARS = 1200

# NOT MEASURED, unlike git_ore.DEFAULT_PAGE, and the difference is worth stating
# rather than hiding behind a confident-looking constant. 50 commits measured at
# 13 jewels and ~1,005 output tokens against a 4,096 ceiling. A prose section is
# longer than a commit message and denser in doctrine, so the yield per unit
# should be higher and the safe page smaller. 30 is a starting estimate with
# headroom; the first live walk is what turns it into a number. The truncation
# guard makes a wrong guess loud rather than silent, which is what earns the
# right to guess at all.
DEFAULT_PAGE = 30

_H2 = re.compile(r"^##\s+(.*?)\s*$")
_LEDGER_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
_MAP_START, _MAP_END = "<!-- MAP:START -->", "<!-- MAP:END -->"
# A directory scan for ledgers matches on the name. An explicitly named file is
# taken as given — and a spec handed to the ledger splitter yields nothing
# anyway, because its sections carry no date.
_LEDGER_HINT = "ledger"


def slug(text: str) -> str:
    """The anchor, by the same rule /opt/_host/scripts/doc-map.py uses.

    Deliberately the same: the MAP block at the top of every `read: full` doc
    already links its sections by this slug, so a jewel's `#anchor` and the
    document's own table of contents name the section identically. A reader that
    invented its own scheme would produce refs that look like the map's and are
    not.
    """
    return re.sub(r"[^\w\s-]", "", text.strip().lower()).replace(" ", "-")


def _sections(text: str) -> list[tuple[str, str]]:
    """(heading, body) per H2, with the preamble riding under the H1.

    Frontmatter and the generated MAP block are dropped: one is metadata about
    the file and the other is a table of contents, and neither is material.
    Fenced code is passed through untouched — a `## ` inside a fence is example
    text, not a section boundary, and this estate's docs are full of both.
    """
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                start = i + 1
                break

    out: list[tuple[str, str]] = []
    heading: str | None = None
    body: list[str] = []
    in_map = in_fence = False

    def flush() -> None:
        if heading is not None and "\n".join(body).strip():
            out.append((heading, "\n".join(body).strip()))

    for line in lines[start:]:
        stripped = line.strip()
        if stripped == _MAP_START:
            in_map = True
            continue
        if stripped == _MAP_END:
            in_map = False
            continue
        if in_map:
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            if heading is None and line.startswith("# "):
                heading, body = line[2:].strip(), []
                continue
            match = _H2.match(line)
            if match:
                flush()
                heading, body = match.group(1), []
                continue
        body.append(line)
    flush()
    return out


def split_doc(sections: list[tuple[str, str]], file_date: str) -> list[tuple[str, str, str, str]]:
    """Every section is a unit, dated by the file. (anchor, date, title, body)"""
    return [(slug(head), file_date, head, body) for head, body in sections]


def split_ledger(sections: list[tuple[str, str]], file_date: str) -> list[tuple[str, str, str, str]]:
    """Only dated sections are entries, and each carries its own date.

    An undated section in a ledger is its preamble or its conventions block —
    prose about the ledger rather than a record of what the machine did. Skipping
    it is also what makes the splitter safe to point at a directory: a spec file
    swept up by mistake produces no units at all rather than doctrine mislabelled
    as unattended machine work.
    """
    out = []
    for head, body in sections:
        match = _LEDGER_DATE.match(head)
        if match:
            out.append((slug(head), match.group(1), head, body))
    return out


SPLITTERS = {"doc": split_doc, "ledger": split_ledger}

# One paragraph per splitter, and it goes into the triage prompt as the ore's
# stance — what this source records relative to the event (GLOSSARY §stance).
# The seam between two stances on one event is the richest material in the pile,
# so telling the walker which one it is holding is not decoration.
STANCES = {
    "doc": (
        "This ore is DOCTRINE, or a derived account of it. A doc records what "
        "the estate decided to believe, written to be read later and revised in "
        "place — the settled version, with the argument that produced it usually "
        "gone. It is the opposite end from a session log, which records a problem "
        "while it is being fought. Mine the claim and the reason given for it; "
        "a doc that corrects an earlier doc, or states a rule whose cost it "
        "admits, is the richest kind here."
    ),
    "ledger": (
        "This ore is a RECORD OF WHAT THE MACHINE DID UNATTENDED. A ledger entry "
        "is written by or about an automated pass, after the fact, with nobody "
        "watching at the time — findings, failures, things reissued and never "
        "applied. It carries what the estate learned about itself when no human "
        "was in the loop, which is exactly the material a session log structurally "
        "cannot hold. Mine the finding and its consequence; an entry that repeats "
        "an earlier entry is itself the finding."
    ),
}


def _root_of(target: Path, roots: list[Path]) -> Path:
    for root in roots:
        if target == root or root in target.parents:
            return root
    raise ValueError(
        f"{target} is outside the registered roam roots "
        f"({', '.join(r.name for r in roots)}). A source_ref is publishable "
        f"text; a path from a gated repo names that repo in a lead's sources "
        f"even when its content never leaves the box."
    )


def _files(target: Path, kind: str) -> list[Path]:
    if target.is_file():
        return [target]
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        )
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            if kind == "ledger" and _LEDGER_HINT not in name.lower():
                continue
            found.append(Path(dirpath) / name)
    return found


def _file_date(path: Path, root: Path, st: os.stat_result) -> str:
    """The file's last commit date, or its mtime when git has nothing to say."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%ad", "--date=short",
             "--", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        stamp = done.stdout.strip()
        if done.returncode == 0 and len(stamp) == 10:
            return stamp
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")


def read_units(
    paths: list[Path] | list[str],
    kind: str,
    roots: list[Path] | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = DEFAULT_PAGE,
) -> list[dict]:
    """A bounded, chronological page of prose units. Rows are candidate-set shaped.

    `paths` are files or directories, each of which must resolve inside a
    registered root. `kind` picks the splitter and, downstream, the jewel's
    `source_type`.
    """
    if kind not in SPLITTERS:
        raise ValueError(
            f"no splitter for {kind!r} — built: {', '.join(sorted(SPLITTERS))}"
        )
    resolved_roots = [
        Path(r).resolve()
        for r in (roots if roots is not None else [p.path for p in load_registry()])
    ]
    split = SPLITTERS[kind]
    rows: list[dict] = []
    seen: set[str] = set()
    for raw in paths:
        target = Path(raw).resolve()
        root = _root_of(target, resolved_roots)
        for path in _files(target, kind):
            if path.is_symlink() or looks_secret(path):
                continue
            try:
                st = path.stat()
            except OSError:
                continue
            if st.st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            prefix = f"{root.name}/{path.relative_to(root)}"
            file_date = _file_date(path, root, st)
            for ordinal, (anchor, when, title, body) in enumerate(
                split(_sections(text), file_date)
            ):
                ref = f"{prefix}#{anchor}"
                if ref in seen:
                    continue  # two overlapping --path arguments, one unit
                if since and when < since:
                    continue
                if until and when > until:
                    continue
                seen.add(ref)
                rows.append({
                    "ref": ref,
                    "date": when,
                    "path": str(path),
                    "ordinal": ordinal,
                    "title": title,
                    "text": body,
                })
    # One chronological page across everything named, and DOCUMENT ORDER inside
    # a file. git sorts by (date, ref) because a sha carries no order, but every
    # section of one doc shares that doc's date, so the same key would shuffle a
    # document into alphabetical-by-heading — a page where the section that
    # answers the previous section can arrive before it. The ordinal is what
    # keeps a page both stable between runs and readable as the writer wrote it.
    rows.sort(key=lambda r: (r["date"], r["path"], r["ordinal"]))
    return rows[:limit]


def page_as_prompt(rows: list[dict]) -> str:
    """The page the walker is shown, and the set it is held to.

    The date sits OUTSIDE the bracket, exactly as git_ore learned to put it
    there: the first live git walk tagged `[ref=X 2025-10-01]` and every jewel
    came back citing the whole tag body, so the guard dropped all of them and the
    page cost full price for nothing.
    """
    out = []
    for row in rows:
        text = row["text"]
        if len(text) > UNIT_CLIP_CHARS:
            text = text[:UNIT_CLIP_CHARS] + " …(clipped)"
        out.append(f"[ref={row['ref']}] written {row['date']}\n{row['title']}\n{text}")
    return "\n\n".join(out)
