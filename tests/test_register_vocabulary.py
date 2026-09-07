"""The register vocabulary must be the same word list everywhere.

`NEWSROOM.md` §Content types is the Editor's routing table and has carried
FIVE content types since it was written: ticker, newsletter, field notes, blog,
and white papers / case studies. The Scout's pitch schema carried four. So the
fifth type was structurally unpitchable — and worse than absent, because
`wire_editor/run.py` coerced any unknown register to "note" with no log at all.
A value that can be produced but not routed is invisible by construction, which
is the same shape as the NOT NULL foreign key that made five of six sources
unable to produce a jewel (`jewels-are-transcript-only-2026-09-03.md`).

Found and closed 2026-09-06 by adding `paper`, scoped deliberately: a rough
ABSTRACT WITH REFERENCES, never the paper itself. The sink stays unplaced,
which NEWSROOM says is intentional.

This file states the vocabulary independently rather than importing it from one
of the sites — the same reasoning `test_stop_guards.py` gives for keeping its
own copy of the non-streaming cap. A test that imported the list could never
catch a site drifting away from it.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# The routing table's five types, in the Scout's vocabulary.
REGISTERS = {"ticker", "newsletter", "note", "blog", "paper"}


def _pipe_enums(path: str) -> list[set[str]]:
    """Every `"register": "a|b|c"` literal in a source file, as sets."""
    text = (REPO / path).read_text()
    return [set(m.split("|")) for m in
            re.findall(r'"register":\s*"([a-z|]+)"', text)]


def _list_literal(path: str, name: str) -> set[str]:
    """A module-level `NAME = [...]` or `NAME = {...}` of bare strings."""
    text = (REPO / path).read_text()
    m = re.search(rf"^{name}\s*=\s*[\[{{]([^\]}}]+)[\]}}]", text, re.M)
    assert m, f"{name} not found in {path}"
    return set(re.findall(r'"([a-z]+)"', m.group(1)))


def test_the_scout_can_pitch_every_register_the_editor_routes():
    """The gap that motivated this file: five types routed, four pitchable."""
    for enum in _pipe_enums("agents/scout_agent.py"):
        assert enum == REGISTERS


@pytest.mark.parametrize("path", ["agents/wire_editor_agent.py"])
def test_the_wire_editor_can_suggest_every_register(path):
    """The Editor sorts by type, so it needs the whole table — both its
    proposal schema and the chief's shadow schema."""
    enums = _pipe_enums(path)
    assert len(enums) == 2, "expected the proposal and shadow schemas"
    for enum in enums:
        assert enum == REGISTERS


def test_every_consumer_knows_every_register():
    """A register missing from one of these is silently mis-binned, not an
    error: wire_editor coerces to 'note', and the assay simply has no row for
    it — so the lead vanishes from the one instrument built to be unflattering."""
    assert _list_literal("pipelines/wire_editor/run.py", "REGISTERS") == REGISTERS
    assert _list_literal("tools/leads_assay.py", "REGISTERS") == REGISTERS
    assert _list_literal("tools/draft_review.py", "    order") == REGISTERS


def test_the_unknown_register_fallback_is_not_silent():
    """The fallback to 'note' is correct; doing it without a word was the bug.
    It ran that way from the day it was written."""
    text = (REPO / "pipelines/wire_editor/run.py").read_text()
    block = text[text.index("if p.get(\"register\") not in REGISTERS"):][:900]
    assert "log.warning" in block, (
        "an unknown register must announce itself — a silent coercion is how "
        "the fifth content type stayed invisible"
    )
