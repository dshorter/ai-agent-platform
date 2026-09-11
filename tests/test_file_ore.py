"""The file reader — one reader, two splitters, and the contracts both owe.

A reader's job is not "produce text". It is to produce the CANDIDATE SET the
walker is held to: schema 1.4.0 gave up the foreign key for five of six sources
on the understanding that `persist()` validates every cited ref against the page
it was shown, so a ref this module emits and a ref `resolve_anchor` accepts have
to be the same string. Most of what is asserted here is that contract, from both
ends.

The rest is the two splitters' one real difference — where the date comes from —
and the boundary that keeps a gated repo's paths out of publishable text.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout import file_ore  # noqa: E402
from pipelines.scout.jewels import candidate_index, resolve_anchor  # noqa: E402

DOC = """\
---
read: full
status: fixture
---

# The design

Why it exists at all.

<!-- MAP:START -->
- [First](#first)
<!-- MAP:END -->

## First rule, absolute

When unsure, include.

## Second rule

```
## not a heading, it is inside a fence
```

Still the second rule.
"""

LEDGER = """\
# SysAdmin Agent — Ledger

How to read this file.

## 2026-09-02 — the pass found the same thing again

Third cycle unapplied.

## 2026-08-30 — daily pass FAILED

No audit performed.
"""


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "ai-agent-platform"
    (root / "docs").mkdir(parents=True)
    return root


def _units(root: Path, target: Path, kind: str) -> list[dict]:
    return file_ore.read_units([target], kind, roots=[root], limit=100)


# --- the doc splitter -------------------------------------------------------


def test_doc_units_are_h2_sections_with_the_preamble_under_the_h1(tmp_path):
    root = _root(tmp_path)
    (root / "docs" / "design.md").write_text(DOC)

    units = _units(root, root / "docs" / "design.md", "doc")

    assert [u["title"] for u in units] == [
        "The design", "First rule, absolute", "Second rule",
    ]
    assert "Why it exists at all." in units[0]["text"]


def test_frontmatter_and_the_generated_map_are_not_material(tmp_path):
    """One is metadata about the file, the other a table of contents."""
    root = _root(tmp_path)
    (root / "docs" / "design.md").write_text(DOC)

    blob = " ".join(u["text"] for u in _units(root, root / "docs" / "design.md", "doc"))

    assert "status: fixture" not in blob
    assert "MAP:START" not in blob
    assert "[First](#first)" not in blob


def test_a_heading_inside_a_fence_does_not_cut_a_section(tmp_path):
    """This estate's docs are full of `## ` inside code blocks — a fence-blind
    splitter would file example text as doctrine under its own anchor."""
    root = _root(tmp_path)
    (root / "docs" / "design.md").write_text(DOC)

    units = _units(root, root / "docs" / "design.md", "doc")
    second = [u for u in units if u["title"] == "Second rule"][0]

    assert "not a heading" in second["text"]
    assert "Still the second rule." in second["text"]


def test_the_anchor_is_the_maps_own_slug(tmp_path):
    """`#first-rule-absolute`, the same slug /opt/_host/scripts/doc-map.py
    writes into the MAP block, so a jewel's anchor and the document's own table
    of contents name the section identically."""
    root = _root(tmp_path)
    (root / "docs" / "design.md").write_text(DOC)

    refs = [u["ref"] for u in _units(root, root / "docs" / "design.md", "doc")]

    assert "ai-agent-platform/docs/design.md#first-rule-absolute" in refs


# --- the ledger splitter ----------------------------------------------------


def test_ledger_entries_carry_their_own_date_not_the_files(tmp_path):
    root = _root(tmp_path)
    (root / "docs" / "sysadmin-ledger.md").write_text(LEDGER)

    units = _units(root, root / "docs" / "sysadmin-ledger.md", "ledger")

    assert {u["date"] for u in units} == {"2026-09-02", "2026-08-30"}


def test_an_undated_section_is_not_an_entry(tmp_path):
    """A ledger's preamble is prose about the ledger, not a record of what the
    machine did — and this is also what makes the splitter safe to point at a
    directory, since a spec swept up by mistake yields nothing at all."""
    root = _root(tmp_path)
    (root / "docs" / "sysadmin-ledger.md").write_text(LEDGER)
    (root / "docs" / "spec-ledger.md").write_text("# Spec\n\n## Seats\n\nProse.\n")

    titles = [u["title"] for u in _units(root, root / "docs", "ledger")]

    assert all(t.startswith("2026-") for t in titles), titles
    assert "Seats" not in titles


def test_a_directory_scan_for_ledgers_matches_on_the_name(tmp_path):
    root = _root(tmp_path)
    (root / "docs" / "sysadmin-ledger.md").write_text(LEDGER)
    (root / "docs" / "design.md").write_text(DOC)

    paths = {u["path"] for u in _units(root, root / "docs", "ledger")}

    assert paths == {str(root / "docs" / "sysadmin-ledger.md")}


# --- the contracts ----------------------------------------------------------


def test_every_ref_the_reader_emits_is_one_persist_would_accept(tmp_path):
    """Both ends of the anti-hallucination check, in one assertion. If these
    ever disagree, a walk pays full price and persists nothing."""
    root = _root(tmp_path)
    (root / "docs" / "design.md").write_text(DOC)

    rows = _units(root, root / "docs" / "design.md", "doc")
    index = candidate_index(rows, "doc")

    for row in rows:
        assert resolve_anchor({"ref": row["ref"]}, "doc", index) == (
            row["ref"], row["date"],
        )
    assert resolve_anchor({"ref": "invented.md#nope"}, "doc", index) is None


def test_the_page_keeps_the_date_outside_the_bracket(tmp_path):
    """git_ore learned this the expensive way: with the date inside the tag the
    model copied the whole body, every ref was rejected, and the page cost full
    price for nothing."""
    root = _root(tmp_path)
    (root / "docs" / "design.md").write_text(DOC)

    page = file_ore.page_as_prompt(_units(root, root / "docs" / "design.md", "doc"))

    assert "[ref=ai-agent-platform/docs/design.md#first-rule-absolute]" in page
    assert "#first-rule-absolute 2026" not in page


def test_a_path_outside_the_registered_roots_is_refused(tmp_path):
    """A source_ref is publishable text and reaches a lead's `sources`, so a
    gated repo must not be mineable — not "should not be mined"."""
    root = _root(tmp_path)
    gated = tmp_path / "_host"
    gated.mkdir()
    (gated / "README.md").write_text("# Host\n\n## Databases\n\nProse.\n")

    with pytest.raises(ValueError) as exc:
        file_ore.read_units([gated], "doc", roots=[root])

    assert "_host" in str(exc.value)


def test_an_unbuilt_splitter_says_so_rather_than_mining_wrong(tmp_path):
    with pytest.raises(ValueError) as exc:
        file_ore.read_units([tmp_path], "calendar", roots=[tmp_path])

    assert "doc" in str(exc.value) and "ledger" in str(exc.value)


def test_every_built_splitter_carries_a_stance(tmp_path):
    """The stance paragraph is what makes these one prompt instead of four; a
    splitter without one would silently mine prose with no stance at all."""
    assert set(file_ore.SPLITTERS) == set(file_ore.STANCES)
    assert all(len(s) > 200 for s in file_ore.STANCES.values())
